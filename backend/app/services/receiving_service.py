from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, POStatus
from app.models.receipt import GoodsReceipt, GoodsReceiptItem
from app.models.inventory import MovementType
from app.repositories.purchase_order_repo import PurchaseOrderRepository
from app.repositories.inventory_repo import InventoryRepository
from app.schemas.receipt import (
    GoodsReceiptCreate,
    GoodsReceiptResponse,
    GoodsReceiptItemResponse,
)

class ReceivingService:
    def __init__(self, db: Session):
        self.db = db
        self.po_repo = PurchaseOrderRepository(db)
        self.inventory_repo = InventoryRepository(db)

    def receive_goods(self, req: GoodsReceiptCreate, user_id: int) -> GoodsReceiptResponse:
        """
        Executes atomic goods receipt:
        - Accepts full or partial deliveries.
        - Strictly prevents over-receipt.
        - Increases warehouse inventory.
        - Records stock movement audit ledger entry.
        - Updates PO items and overall PO status.
        """
        po = self.po_repo.get_by_id(req.purchase_order_id)
        if not po:
            raise HTTPException(status_code=404, detail="Purchase order not found")

        if po.status not in [POStatus.PLACED, POStatus.PARTIALLY_RECEIVED]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot receive goods for order in '{po.status}' status. Order must be PLACED or PARTIALLY_RECEIVED.",
            )

        if not req.items:
            raise HTTPException(status_code=400, detail="Must provide at least one item to receive")

        receipt_number = self.po_repo.generate_receipt_number()
        receipt = GoodsReceipt(
            receipt_number=receipt_number,
            purchase_order_id=po.id,
            warehouse_id=po.warehouse_id,
            received_date=req.received_date,
            notes=req.notes,
            created_by=user_id,
        )
        self.po_repo.create_goods_receipt(receipt)

        try:
            for item_req in req.items:
                po_item = self.po_repo.get_po_item(item_req.po_item_id)
                if not po_item or po_item.purchase_order_id != po.id:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Purchase order item {item_req.po_item_id} not found in this order",
                    )

                if item_req.quantity_received <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Received quantity must be greater than zero for product {po_item.product.name}",
                    )

                remaining = po_item.remaining_qty
                if item_req.quantity_received > remaining:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Over-receipt prevented for SKU '{po_item.product.sku}'. "
                            f"Attempted to receive {item_req.quantity_received} units, but remaining outstanding is {remaining} units."
                        ),
                    )

                # Update PO item received quantity
                po_item.quantity_received += item_req.quantity_received

                # Increase stock atomically and record movement ledger entry
                self.inventory_repo.apply_stock_movement_atomic(
                    product_id=po_item.product_id,
                    warehouse_id=po.warehouse_id,
                    quantity_delta=item_req.quantity_received,
                    movement_type=MovementType.PURCHASE_RECEIPT,
                    reference_type="goods_receipt",
                    reference_id=receipt_number,
                    reason=f"Delivery for PO #{po.po_number} (GRN #{receipt_number})",
                    created_by=user_id,
                )

                receipt_item = GoodsReceiptItem(
                    goods_receipt_id=receipt.id,
                    po_item_id=po_item.id,
                    product_id=po_item.product_id,
                    quantity_received=item_req.quantity_received,
                    unit_cost=po_item.unit_cost,
                )
                self.db.add(receipt_item)

            # Check if all items across entire PO are now fully received
            all_received = all(it.quantity_received >= it.quantity_ordered for it in po.items)
            if all_received:
                po.status = POStatus.RECEIVED
                po.completed_at = datetime.now(timezone.utc)
            else:
                po.status = POStatus.PARTIALLY_RECEIVED

            self.db.commit()
            self.db.refresh(receipt)

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to record goods receipt: {str(e)}",
            )

        return self.get_receipt_detail(receipt.id)

    def get_receipt_detail(self, receipt_id: int) -> GoodsReceiptResponse:
        r = (
            self.db.query(GoodsReceipt)
            .filter(GoodsReceipt.id == receipt_id)
            .first()
        )
        if not r:
            raise HTTPException(status_code=404, detail="Goods receipt not found")

        items = []
        for it in r.items:
            items.append(
                GoodsReceiptItemResponse(
                    id=it.id,
                    po_item_id=it.po_item_id,
                    product_id=it.product_id,
                    product_sku=it.product.sku,
                    product_name=it.product.name,
                    quantity_received=it.quantity_received,
                    unit_cost=it.unit_cost,
                )
            )

        return GoodsReceiptResponse(
            id=r.id,
            receipt_number=r.receipt_number,
            purchase_order_id=r.purchase_order_id,
            po_number=r.purchase_order.po_number,
            warehouse_id=r.warehouse_id,
            warehouse_code=r.warehouse.code,
            received_date=r.received_date,
            notes=r.notes,
            created_by_name=r.user.full_name if r.user else None,
            created_at=r.created_at,
            items=items,
        )

    def list_receipts(self, po_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> Tuple[List[GoodsReceiptResponse], int]:
        receipts, total = self.po_repo.list_goods_receipts(po_id=po_id, skip=skip, limit=limit)
        return [self.get_receipt_detail(r.id) for r in receipts], total
