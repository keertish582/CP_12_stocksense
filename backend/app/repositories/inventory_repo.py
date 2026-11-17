from datetime import datetime, date, timezone
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.models.inventory import InventoryBalance, StockMovement, MovementType
from app.models.warehouse import Warehouse
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, POStatus
from app.models.product import Product
from app.models.recommendation import ReorderRecommendation
from app.core.config import settings

class InsufficientStockError(Exception):
    def __init__(self, message: str, current_stock: int, requested_delta: int):
        super().__init__(message)
        self.current_stock = current_stock
        self.requested_delta = requested_delta

class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_default_warehouse(self) -> Warehouse:
        wh = self.db.query(Warehouse).filter(Warehouse.code == settings.DEFAULT_WAREHOUSE_CODE).first()
        if not wh:
            wh = Warehouse(
                code=settings.DEFAULT_WAREHOUSE_CODE,
                name=settings.DEFAULT_WAREHOUSE_NAME,
                location="Bengaluru, Karnataka, India",
                is_active=True,
            )
            self.db.add(wh)
            self.db.commit()
            self.db.refresh(wh)
        return wh

    def get_warehouse_by_id(self, warehouse_id: int) -> Optional[Warehouse]:
        return self.db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()

    def get_balance(self, product_id: int, warehouse_id: int, for_update: bool = False) -> Optional[InventoryBalance]:
        q = self.db.query(InventoryBalance).filter(
            InventoryBalance.product_id == product_id,
            InventoryBalance.warehouse_id == warehouse_id,
        )
        # Apply row-level lock if supported by dialect
        bind = self.db.get_bind()
        if for_update and bind and bind.dialect.name != "sqlite":
            q = q.with_for_update()
        return q.first()

    def get_or_create_balance(self, product_id: int, warehouse_id: int, for_update: bool = False) -> InventoryBalance:
        balance = self.get_balance(product_id, warehouse_id, for_update=for_update)
        if not balance:
            balance = InventoryBalance(
                product_id=product_id,
                warehouse_id=warehouse_id,
                on_hand_qty=0,
                reserved_qty=0,
            )
            self.db.add(balance)
            self.db.flush()
        return balance

    def apply_stock_movement_atomic(
        self,
        product_id: int,
        warehouse_id: int,
        quantity_delta: int,
        movement_type: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        reason: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> Tuple[InventoryBalance, StockMovement]:
        """
        Atomically updates the inventory balance and records the stock movement ledger entry.
        Strictly prevents negative stock.
        """
        balance = self.get_or_create_balance(product_id, warehouse_id, for_update=True)
        new_on_hand = balance.on_hand_qty + quantity_delta

        if new_on_hand < 0:
            raise InsufficientStockError(
                f"Cannot deduct {abs(quantity_delta)} units. Current on-hand is {balance.on_hand_qty}.",
                current_stock=balance.on_hand_qty,
                requested_delta=quantity_delta,
            )

        balance.on_hand_qty = new_on_hand
        balance.updated_at = datetime.now(timezone.utc)

        movement = StockMovement(
            product_id=product_id,
            warehouse_id=warehouse_id,
            quantity_delta=quantity_delta,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            balance_after=new_on_hand,
            reason=reason,
            created_by=created_by,
        )
        self.db.add(movement)
        self.db.flush()
        return balance, movement

    def get_eligible_inbound_qty(
        self,
        product_id: int,
        warehouse_id: int,
        as_of_date: Optional[date] = None,
    ) -> Tuple[int, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Returns:
            (eligible_qty, eligible_orders_details, excluded_orders_details)
        Eligible inbound rules:
        - Only purchase orders in PLACED or PARTIALLY_RECEIVED status.
        - Exclude overdue (expected_delivery_date < as_of_date) or missing-date inbound.
        - DRAFT and CANCELLED are completely ignored.
        """
        today = as_of_date or date.today()

        po_items = (
            self.db.query(PurchaseOrderItem, PurchaseOrder)
            .join(PurchaseOrder, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
            .filter(
                PurchaseOrderItem.product_id == product_id,
                PurchaseOrder.warehouse_id == warehouse_id,
                PurchaseOrder.status.in_([POStatus.PLACED, POStatus.PARTIALLY_RECEIVED]),
            )
            .all()
        )

        eligible_qty = 0
        eligible_orders = []
        excluded_orders = []

        for item, po in po_items:
            remaining = item.quantity_ordered - item.quantity_received
            if remaining <= 0:
                continue

            order_info = {
                "po_number": po.po_number,
                "status": po.status,
                "expected_delivery_date": str(po.expected_delivery_date) if po.expected_delivery_date else None,
                "quantity_ordered": item.quantity_ordered,
                "quantity_received": item.quantity_received,
                "remaining_qty": remaining,
            }

            if not po.expected_delivery_date:
                excluded_orders.append({**order_info, "reason": "Missing expected delivery date"})
            elif po.expected_delivery_date < today:
                excluded_orders.append({**order_info, "reason": f"Overdue since {po.expected_delivery_date}"})
            else:
                eligible_qty += remaining
                eligible_orders.append(order_info)

        return eligible_qty, eligible_orders, excluded_orders

    def list_inventory_balances(
        self,
        warehouse_id: Optional[int] = None,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Returns enriched inventory items with available stock, eligible inbound, and stock status.
        """
        wh = self.get_or_create_default_warehouse()
        target_wh_id = warehouse_id or wh.id

        q = (
            self.db.query(Product, InventoryBalance)
            .outerjoin(
                InventoryBalance,
                (Product.id == InventoryBalance.product_id) & (InventoryBalance.warehouse_id == target_wh_id),
            )
            .options(joinedload(Product.category))
            .filter(Product.is_active == True)
        )

        if category_id:
            q = q.filter(Product.category_id == category_id)
        if search:
            s = f"%{search.strip()}%"
            q = q.filter(Product.name.ilike(s) | Product.sku.ilike(s))

        total = q.count()
        results = q.order_by(Product.name.asc()).offset(skip).limit(limit).all()

        today = date.today()
        items = []
        for prod, bal in results:
            on_hand = bal.on_hand_qty if bal else 0
            reserved = bal.reserved_qty if bal else 0
            available = max(0, on_hand - reserved)

            eligible_inbound, _, _ = self.get_eligible_inbound_qty(prod.id, target_wh_id, as_of_date=today)
            inv_position = available + eligible_inbound

            # Active recommendation if any
            rec = (
                self.db.query(ReorderRecommendation)
                .filter(
                    ReorderRecommendation.product_id == prod.id,
                    ReorderRecommendation.warehouse_id == target_wh_id,
                    ReorderRecommendation.is_active == True,
                )
                .first()
            )

            reorder_point = rec.reorder_point if rec else (prod.safety_stock + (prod.lead_time_days * 2))

            # Status classification
            if on_hand == 0:
                stock_status = "OUT_OF_STOCK"
            elif inv_position <= (prod.lead_time_days * 2):
                stock_status = "STOCKOUT_RISK"
            elif inv_position <= reorder_point:
                stock_status = "REORDER_SOON"
            else:
                stock_status = "HEALTHY"

            items.append({
                "id": bal.id if bal else 0,
                "product_id": prod.id,
                "product_sku": prod.sku,
                "product_name": prod.name,
                "category_name": prod.category.name if prod.category else None,
                "warehouse_id": target_wh_id,
                "warehouse_code": wh.code,
                "warehouse_name": wh.name,
                "on_hand_qty": on_hand,
                "reserved_qty": reserved,
                "available_qty": available,
                "eligible_open_inbound": eligible_inbound,
                "inventory_position": inv_position,
                "reorder_point": reorder_point,
                "stock_status": stock_status,
                "updated_at": bal.updated_at if bal else datetime.now(timezone.utc),
            })

        return items, total

    def list_stock_movements(
        self,
        product_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StockMovement], int]:
        q = (
            self.db.query(StockMovement)
            .options(
                joinedload(StockMovement.product),
                joinedload(StockMovement.warehouse),
                joinedload(StockMovement.user),
            )
        )
        if product_id:
            q = q.filter(StockMovement.product_id == product_id)
        if warehouse_id:
            q = q.filter(StockMovement.warehouse_id == warehouse_id)
        if movement_type:
            q = q.filter(StockMovement.movement_type == movement_type)

        total = q.count()
        movements = q.order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).offset(skip).limit(limit).all()
        return movements, total
