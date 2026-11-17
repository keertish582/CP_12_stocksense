from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, POStatus
from app.models.receipt import GoodsReceipt, GoodsReceiptItem

class PurchaseOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def generate_po_number(self) -> str:
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        count = self.db.query(PurchaseOrder).filter(PurchaseOrder.po_number.like(f"PO-{today_str}-%")).count()
        return f"PO-{today_str}-{count + 1:04d}"

    def generate_receipt_number(self) -> str:
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        count = self.db.query(GoodsReceipt).filter(GoodsReceipt.receipt_number.like(f"GRN-{today_str}-%")).count()
        return f"GRN-{today_str}-{count + 1:04d}"

    def get_by_id(self, po_id: int) -> Optional[PurchaseOrder]:
        return (
            self.db.query(PurchaseOrder)
            .options(
                joinedload(PurchaseOrder.supplier),
                joinedload(PurchaseOrder.warehouse),
                joinedload(PurchaseOrder.user),
                joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            )
            .filter(PurchaseOrder.id == po_id)
            .first()
        )

    def get_by_number(self, po_number: str) -> Optional[PurchaseOrder]:
        return (
            self.db.query(PurchaseOrder)
            .options(
                joinedload(PurchaseOrder.supplier),
                joinedload(PurchaseOrder.warehouse),
                joinedload(PurchaseOrder.user),
                joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            )
            .filter(PurchaseOrder.po_number == po_number)
            .first()
        )

    def list_orders(
        self,
        status: Optional[str] = None,
        supplier_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[PurchaseOrder], int]:
        q = (
            self.db.query(PurchaseOrder)
            .options(
                joinedload(PurchaseOrder.supplier),
                joinedload(PurchaseOrder.warehouse),
                joinedload(PurchaseOrder.user),
                joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product),
            )
        )
        if status:
            q = q.filter(PurchaseOrder.status == status)
        if supplier_id:
            q = q.filter(PurchaseOrder.supplier_id == supplier_id)
        if warehouse_id:
            q = q.filter(PurchaseOrder.warehouse_id == warehouse_id)

        total = q.count()
        orders = q.order_by(PurchaseOrder.created_at.desc(), PurchaseOrder.id.desc()).offset(skip).limit(limit).all()
        return orders, total

    def create(self, po: PurchaseOrder) -> PurchaseOrder:
        self.db.add(po)
        self.db.flush()
        return po

    def update(self, po: PurchaseOrder) -> PurchaseOrder:
        self.db.commit()
        self.db.refresh(po)
        return po

    def get_po_item(self, po_item_id: int) -> Optional[PurchaseOrderItem]:
        return (
            self.db.query(PurchaseOrderItem)
            .options(joinedload(PurchaseOrderItem.product))
            .filter(PurchaseOrderItem.id == po_item_id)
            .first()
        )

    def create_goods_receipt(self, receipt: GoodsReceipt) -> GoodsReceipt:
        self.db.add(receipt)
        self.db.flush()
        return receipt

    def list_goods_receipts(self, po_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> Tuple[List[GoodsReceipt], int]:
        q = (
            self.db.query(GoodsReceipt)
            .options(
                joinedload(GoodsReceipt.purchase_order),
                joinedload(GoodsReceipt.warehouse),
                joinedload(GoodsReceipt.user),
                joinedload(GoodsReceipt.items).joinedload(GoodsReceiptItem.product),
            )
        )
        if po_id:
            q = q.filter(GoodsReceipt.purchase_order_id == po_id)

        total = q.count()
        receipts = q.order_by(GoodsReceipt.created_at.desc()).offset(skip).limit(limit).all()
        return receipts, total
