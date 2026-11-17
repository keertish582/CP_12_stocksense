from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.report_service import ReportService
from app.services.inventory_service import InventoryService
from app.schemas.report import (
    DashboardSummaryResponse,
    InventoryAttentionItem,
    SalesVsForecastPoint,
)
from app.schemas.inventory import StockMovementResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    return service.get_dashboard_summary()

@router.get("/attention", response_model=List[InventoryAttentionItem])
def get_attention_items(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    return service.get_inventory_attention_list(limit=limit)

@router.get("/sales-vs-forecast", response_model=List[SalesVsForecastPoint])
def get_sales_vs_forecast(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    return service.get_actual_vs_forecast_trend(days=days)

@router.get("/recent-movements", response_model=List[StockMovementResponse])
def get_recent_movements(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv_service = InventoryService(db)
    items, _ = inv_service.list_stock_movements(limit=limit)
    return items
