from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Boolean, ForeignKey, JSON, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import utc_now

class ForecastRunStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ForecastMethod:
    TRAILING_7D = "trailing_7d"
    TRAILING_28D = "trailing_28d"
    SEASONAL_NAIVE = "seasonal_naive"
    MANUAL_FALLBACK = "manual_fallback"
    INSUFFICIENT_HISTORY = "insufficient_history"

class ForecastRun(Base):
    __tablename__ = "forecast_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), unique=True, index=True, nullable=False)
    status = Column(String(30), default=ForecastRunStatus.PENDING, nullable=False)
    data_cutoff = Column(Date, nullable=False)
    forecast_horizon_days = Column(Integer, default=30, nullable=False)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    summary_metrics = Column(JSON, nullable=True)

    forecasts = relationship("Forecast", back_populates="forecast_run", cascade="all, delete-orphan")
    recommendations = relationship("ReorderRecommendation", back_populates="forecast_run")
    user = relationship("User")

class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    forecast_run_id = Column(Integer, ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    forecast_qty = Column(Numeric(10, 2), nullable=False)
    method = Column(String(50), nullable=False)
    mae = Column(Numeric(10, 2), nullable=True)
    wape = Column(Numeric(10, 4), nullable=True)
    is_cold_start = Column(Boolean, default=False, nullable=False)
    has_censored_demand = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    forecast_run = relationship("ForecastRun", back_populates="forecasts")
    product = relationship("Product", back_populates="forecasts")

    __table_args__ = (
        UniqueConstraint("forecast_run_id", "product_id", "forecast_date", name="uq_run_product_forecast_date"),
    )
