from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import utc_now

class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    external_sale_id = Column(String(100), nullable=True, index=True)
    sale_date = Column(Date, nullable=False, index=True)
    total_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    channel = Column(String(50), default="POS_STORE", nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    user = relationship("User")

class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_sale_item_qty_positive"),
    )
