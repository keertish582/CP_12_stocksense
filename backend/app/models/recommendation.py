from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import utc_now

class RecommendationStatus:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DEFERRED = "DEFERRED"
    DISMISSED = "DISMISSED"

class RecommendationPriority:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ReorderRecommendation(Base):
    __tablename__ = "reorder_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_run_id = Column(Integer, ForeignKey("forecast_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Snapshots of input state at time of calculation
    inventory_position_snapshot = Column(Integer, nullable=False)
    on_hand_snapshot = Column(Integer, nullable=False)
    eligible_inbound_snapshot = Column(Integer, nullable=False)
    
    # Reorder parameters
    reorder_point = Column(Integer, nullable=False)
    target_stock = Column(Integer, nullable=False)
    lead_time_demand = Column(Numeric(10, 2), nullable=False)
    safety_stock = Column(Integer, nullable=False)
    
    # Quantities
    raw_order_qty = Column(Integer, nullable=False)
    suggested_qty = Column(Integer, nullable=False)  # After MOQ and pack size rounding
    
    # Supplier parameters applied
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    pack_size = Column(Integer, default=1, nullable=False)
    moq = Column(Integer, default=1, nullable=False)
    unit_cost = Column(Numeric(12, 2), default=0.00, nullable=False)
    total_estimated_cost = Column(Numeric(14, 2), default=0.00, nullable=False)
    
    # Stockout risk
    projected_stockout_date = Column(Date, nullable=True)
    priority = Column(String(20), default=RecommendationPriority.MEDIUM, nullable=False)
    status = Column(String(30), default=RecommendationStatus.PENDING, nullable=False, index=True)
    
    # Full calculation explanation details (JSON)
    # {
    #   "lead_time_days": 7,
    #   "coverage_days": 14,
    #   "daily_forecast_rates": [...],
    #   "formula": "...",
    #   "eligible_purchase_orders": [{"po_number": "...", "remaining_qty": ...}],
    #   "ineligible_purchase_orders": [{"po_number": "...", "reason": "overdue"}],
    #   "warnings": [...]
    # }
    calculation_details = Column(JSON, nullable=True)
    
    # Uniqueness strategy: Only one active recommendation per product + warehouse
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    product = relationship("Product", back_populates="reorder_recommendations")
    warehouse = relationship("Warehouse")
    forecast_run = relationship("ForecastRun", back_populates="recommendations")
    supplier = relationship("Supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="recommendation")
