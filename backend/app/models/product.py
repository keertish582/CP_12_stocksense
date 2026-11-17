from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import utc_now

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(200), index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    unit = Column(String(20), default="units", nullable=False)
    selling_price = Column(Numeric(12, 2), default=0.00, nullable=False)
    safety_stock = Column(Integer, default=10, nullable=False)
    min_reorder_qty = Column(Integer, default=1, nullable=False)
    manual_daily_demand = Column(Numeric(10, 2), nullable=True)  # For cold start fallback
    lead_time_days = Column(Integer, default=7, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    category = relationship("Category", back_populates="products")
    product_suppliers = relationship("ProductSupplier", back_populates="product", cascade="all, delete-orphan")
    inventory_balances = relationship("InventoryBalance", back_populates="product", cascade="all, delete-orphan")
    stock_movements = relationship("StockMovement", back_populates="product")
    forecasts = relationship("Forecast", back_populates="product", cascade="all, delete-orphan")
    reorder_recommendations = relationship("ReorderRecommendation", back_populates="product", cascade="all, delete-orphan")

class ProductSupplier(Base):
    __tablename__ = "product_suppliers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    lead_time_days = Column(Integer, default=7, nullable=False)
    minimum_order_qty = Column(Integer, default=1, nullable=False)  # MOQ
    pack_size = Column(Integer, default=1, nullable=False)
    unit_cost = Column(Numeric(12, 2), default=0.00, nullable=False)
    is_preferred = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    product = relationship("Product", back_populates="product_suppliers")
    supplier = relationship("Supplier", back_populates="product_suppliers")

    __table_args__ = (
        UniqueConstraint("product_id", "supplier_id", name="uq_product_supplier"),
    )
