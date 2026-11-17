from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import utc_now

class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id = Column(Integer, primary_key=True, index=True)
    receipt_number = Column(String(50), unique=True, index=True, nullable=False)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    received_date = Column(Date, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="goods_receipts")
    warehouse = relationship("Warehouse")
    user = relationship("User")
    items = relationship("GoodsReceiptItem", back_populates="goods_receipt", cascade="all, delete-orphan")

class GoodsReceiptItem(Base):
    __tablename__ = "goods_receipt_items"

    id = Column(Integer, primary_key=True, index=True)
    goods_receipt_id = Column(Integer, ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False, index=True)
    po_item_id = Column(Integer, ForeignKey("purchase_order_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity_received = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(12, 2), default=0.00, nullable=False)

    goods_receipt = relationship("GoodsReceipt", back_populates="items")
    po_item = relationship("PurchaseOrderItem", back_populates="goods_receipt_items")
    product = relationship("Product")

    __table_args__ = (
        CheckConstraint("quantity_received > 0", name="chk_receipt_item_qty_positive"),
    )
