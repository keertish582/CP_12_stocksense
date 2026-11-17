from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import get_current_user, require_roles
from app.services.reorder_service import ReorderService
from app.schemas.recommendation import (
    ReorderRecommendationResponse,
    RecommendationApprovalRequest,
    RecommendationActionRequest,
)
from app.schemas.purchase_order import PurchaseOrderResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/recommendations", tags=["Reorder Recommendations"])

@router.get("", response_model=PaginatedResponse[ReorderRecommendationResponse])
def list_recommendations(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    is_active_only: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReorderService(db)
    skip = (page - 1) * page_size
    items, total = service.list_recommendations(
        status=status,
        priority=priority,
        is_active_only=is_active_only,
        skip=skip,
        limit=page_size,
    )
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

@router.post("/refresh", response_model=List[ReorderRecommendationResponse])
def refresh_recommendations(
    coverage_days: int = Query(14, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = ReorderService(db)
    recs = service.refresh_all_recommendations(coverage_days=coverage_days)
    items, _ = service.list_recommendations(is_active_only=True, limit=100)
    return items

@router.post("/{rec_id}/approve", response_model=PurchaseOrderResponse)
def approve_recommendation(
    rec_id: int,
    req: RecommendationApprovalRequest = RecommendationApprovalRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = ReorderService(db)
    return service.approve_recommendation(rec_id, req, user_id=current_user.id)

@router.post("/{rec_id}/action", response_model=ReorderRecommendationResponse)
def action_recommendation(
    rec_id: int,
    req: RecommendationActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = ReorderService(db)
    return service.take_action(rec_id, req)
