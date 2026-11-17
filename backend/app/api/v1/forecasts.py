from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import get_current_user, require_roles
from app.services.forecast_service import ForecastService
from app.schemas.forecast import (
    ForecastRunResponse,
    ProductForecastDetailResponse,
    TriggerForecastRequest,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])

@router.get("/runs", response_model=PaginatedResponse[ForecastRunResponse])
def list_forecast_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ForecastService(db)
    skip = (page - 1) * page_size
    runs, total = service.forecast_repo.list_runs(skip=skip, limit=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=[ForecastRunResponse.model_validate(r) for r in runs],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

@router.post("/trigger", response_model=ForecastRunResponse)
def trigger_forecast_run(
    req: TriggerForecastRequest = TriggerForecastRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = ForecastService(db)
    run_response = service.run_full_forecast_pipeline(
        forecast_horizon_days=req.forecast_horizon_days or 30,
        user_id=current_user.id,
    )
    # Also refresh reorder recommendations
    from app.services.reorder_service import ReorderService
    reorder_service = ReorderService(db)
    reorder_service.refresh_all_recommendations(coverage_days=req.coverage_days or 14)
    return run_response

@router.get("/product/{product_id}", response_model=ProductForecastDetailResponse)
def get_product_forecast(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ForecastService(db)
    return service.get_product_forecast_detail(product_id)
