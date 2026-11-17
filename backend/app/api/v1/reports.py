from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.report_service import ReportService
from app.schemas.report import (
    InventoryValuationItem,
    SalesReportItem,
    ForecastEvaluationReportItem,
)

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])

@router.get("/valuation", response_model=List[InventoryValuationItem])
def get_inventory_valuation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    return service.get_inventory_valuation()

@router.get("/sales", response_model=List[SalesReportItem])
def get_sales_report(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    product_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    return service.get_sales_report(
        start_date=start_date, end_date=end_date, product_id=product_id, category_id=category_id
    )

@router.get("/sales/export-csv")
def export_sales_csv(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    product_id: Optional[int] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    csv_content = service.export_sales_csv(
        start_date=start_date,
        end_date=end_date,
        product_id=product_id,
        category_id=category_id,
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_report.csv"},
    )

@router.get("/movements/export-csv")
def export_movements_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    csv_content = service.export_stock_movements_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=stock_movements_ledger.csv"},
    )

@router.get("/forecast-evaluation", response_model=List[ForecastEvaluationReportItem])
def get_forecast_evaluation_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReportService(db)
    return service.get_forecast_evaluation_report()
