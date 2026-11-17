from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import utc_now

class POStatus:
    DRAFT = "DRAFT"
    PLACED = "PLACED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String(50), unique=True, index=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    recommendation_id = Column(Integer, ForeignKey("reorder_recommendations.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(30), default=POStatus.DRAFT, nullable=False, index=True)
    expected_delivery_date = Column(Date, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    total_amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    placed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    supplier = relationship("Supplier", back_populates="purchase_orders")
    warehouse = relationship("Warehouse", back_populates="purchase_orders")
    recommendation = relationship("ReorderRecommendation", back_populates="purchase_orders")
    user = relationship("User")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan")
    goods_receipts = relationship("GoodsReceipt", back_populates="purchase_order")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0, nullable=False)
    unit_cost = Column(Numeric(12, 2), default=0.00, nullable=False)
    subtotal = Column(Numeric(14, 2), default=0.00, nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product")
    goods_receipt_items = relationship("GoodsReceiptItem", back_populates="po_item")

    __table_args__ = (
        UniqueConstraint("purchase_order_id", "product_id", name="uq_po_product"),
        CheckConstraint("quantity_ordered > 0", name="chk_po_item_ordered_positive"),
        CheckConstraint("quantity_received >= 0", name="chk_po_item_received_non_negative"),
        CheckConstraint("quantity_received <= quantity_ordered", name="chk_po_item_received_le_ordered"),
    )

    @property
    def remaining_qty(self) -> int:
        return max(0, self.quantity_ordered - self.quantity_received)
