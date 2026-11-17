from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class ForecastItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    forecast_date: date
    forecast_qty: Decimal
    method: str
    mae: Optional[Decimal] = None
    wape: Optional[Decimal] = None
    is_cold_start: bool
    has_censored_demand: bool

class ForecastRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str
    status: str
    data_cutoff: date
    forecast_horizon_days: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    summary_metrics: Optional[dict] = None

class HistoricalActualPoint(BaseModel):
    date: date
    actual_qty: int
    is_stockout: bool = False

class ForecastPoint(BaseModel):
    date: date
    forecast_qty: Decimal

class ProductForecastDetailResponse(BaseModel):
    product_id: int
    product_sku: str
    product_name: str
    method: str
    data_cutoff: date
    mae: Optional[Decimal] = None
    wape: Optional[Decimal] = None
    is_cold_start: bool = False
    has_censored_demand: bool = False
    projected_stockout_date: Optional[date] = None
    current_available_stock: int = 0
    historical_actuals: List[HistoricalActualPoint] = []
    future_forecasts: List[ForecastPoint] = []
    candidate_methods_comparison: Optional[dict] = None

class TriggerForecastRequest(BaseModel):
    coverage_days: Optional[int] = 14
    forecast_horizon_days: Optional[int] = 30
