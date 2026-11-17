from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, POStatus
from app.repositories.purchase_order_repo import PurchaseOrderRepository
from app.repositories.supplier_repo import SupplierRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.inventory_repo import InventoryRepository
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderItemResponse,
)

class PurchaseOrderService:
    def __init__(self, db: Session):
        self.db = db
        self.po_repo = PurchaseOrderRepository(db)
        self.supplier_repo = SupplierRepository(db)
        self.product_repo = ProductRepository(db)
        self.inventory_repo = InventoryRepository(db)

    def list_orders(
        self,
        status: Optional[str] = None,
        supplier_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PurchaseOrderResponse], int]:
        orders, total = self.po_repo.list_orders(
            status=status,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            skip=skip,
            limit=limit,
        )
        return [self.build_po_response(po) for po in orders], total

    def get_order_detail(self, po_id: int) -> PurchaseOrderResponse:
        po = self.po_repo.get_by_id(po_id)
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        return self.build_po_response(po)

    def create_custom_purchase_order(self, req: PurchaseOrderCreate, user_id: int) -> PurchaseOrderResponse:
        supplier = self.supplier_repo.get_by_id(req.supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

        wh = (
            self.inventory_repo.get_warehouse_by_id(req.warehouse_id)
            if req.warehouse_id
            else self.inventory_repo.get_or_create_default_warehouse()
        )
        if not wh:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        po_number = self.po_repo.generate_po_number()
        total_amount = Decimal("0.00")

        po = PurchaseOrder(
            po_number=po_number,
            supplier_id=supplier.id,
            warehouse_id=wh.id,
            status=POStatus.DRAFT,
            expected_delivery_date=req.expected_delivery_date,
            notes=req.notes,
            total_amount=Decimal("0.00"),
            created_by=user_id,
        )
        self.po_repo.create(po)

        for it in req.items:
            product = self.product_repo.get_by_id(it.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product ID {it.product_id} not found")
            subtotal = it.unit_cost * Decimal(it.quantity_ordered)
            total_amount += subtotal

            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=product.id,
                quantity_ordered=it.quantity_ordered,
                quantity_received=0,
                unit_cost=it.unit_cost,
                subtotal=subtotal,
            )
            self.db.add(po_item)

        po.total_amount = total_amount
        self.db.commit()
        self.db.refresh(po)
        return self.build_po_response(po)

    def place_order(self, po_id: int) -> PurchaseOrderResponse:
        po = self.po_repo.get_by_id(po_id)
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        if po.status != POStatus.DRAFT:
            raise HTTPException(
                status_code=400,
                detail=f"Only DRAFT orders can be placed. Current status is {po.status}",
            )

        po.status = POStatus.PLACED
        po.placed_at = datetime.now(timezone.utc)
        self.po_repo.update(po)
        return self.build_po_response(po)

    def cancel_order(self, po_id: int, reason: Optional[str] = None) -> PurchaseOrderResponse:
        po = self.po_repo.get_by_id(po_id)
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        if po.status in [POStatus.PARTIALLY_RECEIVED, POStatus.RECEIVED]:
            raise HTTPException(
                status_code=400,
                detail="Cannot cancel purchase order that has already received deliveries.",
            )

        if po.status == POStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Purchase order is already cancelled")

        po.status = POStatus.CANCELLED
        if reason:
            po.notes = f"{po.notes or ''}\n[Cancellation Reason: {reason}]".strip()
        self.po_repo.update(po)
        return self.build_po_response(po)

    def build_po_response(self, po: PurchaseOrder) -> PurchaseOrderResponse:
        items = []
        for it in po.items:
            items.append(
                PurchaseOrderItemResponse(
                    id=it.id,
                    product_id=it.product_id,
                    product_sku=it.product.sku,
                    product_name=it.product.name,
                    quantity_ordered=it.quantity_ordered,
                    quantity_received=it.quantity_received,
                    remaining_qty=it.remaining_qty,
                    unit_cost=it.unit_cost,
                    subtotal=it.subtotal,
                )
            )
        return PurchaseOrderResponse(
            id=po.id,
            po_number=po.po_number,
            supplier_id=po.supplier_id,
            supplier_name=po.supplier.name if po.supplier else "Unknown",
            warehouse_id=po.warehouse_id,
            warehouse_code=po.warehouse.code if po.warehouse else "Unknown",
            recommendation_id=po.recommendation_id,
            status=po.status,
            expected_delivery_date=po.expected_delivery_date,
            notes=po.notes,
            total_amount=po.total_amount,
            placed_at=po.placed_at,
            completed_at=po.completed_at,
            created_by_name=po.user.full_name if po.user else None,
            created_at=po.created_at,
            updated_at=po.updated_at,
            items=items,
        )
