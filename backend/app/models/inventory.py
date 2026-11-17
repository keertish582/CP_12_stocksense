from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import utc_now

class MovementType:
    SALE = "SALE"
    PURCHASE_RECEIPT = "PURCHASE_RECEIPT"
    ADJUSTMENT = "ADJUSTMENT"
    INITIAL = "INITIAL"
    RETURN = "RETURN"

class InventoryBalance(Base):
    __tablename__ = "inventory_balances"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    on_hand_qty = Column(Integer, default=0, nullable=False)
    reserved_qty = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    product = relationship("Product", back_populates="inventory_balances")
    warehouse = relationship("Warehouse", back_populates="inventory_balances")

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", name="uq_product_warehouse_balance"),
        CheckConstraint("on_hand_qty >= 0", name="chk_on_hand_non_negative"),
        CheckConstraint("reserved_qty >= 0", name="chk_reserved_non_negative"),
    )

    @property
    def available_qty(self) -> int:
        return max(0, self.on_hand_qty - self.reserved_qty)

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity_delta = Column(Integer, nullable=False)  # positive (in) or negative (out)
    movement_type = Column(String(30), nullable=False, index=True)
    reference_type = Column(String(50), nullable=True)  # 'sale', 'goods_receipt', 'manual_adjustment', 'seed'
    reference_id = Column(String(100), nullable=True, index=True)
    balance_after = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    product = relationship("Product", back_populates="stock_movements")
    warehouse = relationship("Warehouse", back_populates="stock_movements")
    user = relationship("User")
