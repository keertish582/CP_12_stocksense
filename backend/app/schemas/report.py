from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel

class DashboardSummaryResponse(BaseModel):
    active_products_count: int
    low_stock_products_count: int
    stockout_risk_count: int
    open_purchase_orders_count: int
    total_inventory_valuation: Decimal
    total_sales_today: Decimal
    latest_forecast_run: Optional[dict] = None

class InventoryAttentionItem(BaseModel):
    product_id: int
    sku: str
    name: str
    category_name: Optional[str] = None
    on_hand_qty: int
    reserved_qty: int
    available_qty: int
    eligible_open_inbound: int
    reorder_point: int
    stock_status: str
    projected_stockout_date: Optional[date] = None
    suggested_qty: int = 0

class SalesVsForecastPoint(BaseModel):
    date: date
    actual_sales: int
    forecast_sales: Decimal

class InventoryValuationItem(BaseModel):
    product_id: int
    sku: str
    name: str
    category_name: Optional[str] = None
    on_hand_qty: int
    unit_cost: Decimal
    total_valuation: Decimal

class SalesReportItem(BaseModel):
    sale_date: date
    product_sku: str
    product_name: str
    category_name: Optional[str] = None
    quantity_sold: int
    total_revenue: Decimal

class ForecastEvaluationReportItem(BaseModel):
    product_id: int
    sku: str
    name: str
    best_method: str
    mae: Optional[Decimal] = None
    wape: Optional[Decimal] = None
    data_points_count: int
    status: str
