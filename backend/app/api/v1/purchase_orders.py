from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import get_current_user, require_roles
from app.services.purchase_order_service import PurchaseOrderService
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])

@router.get("", response_model=PaginatedResponse[PurchaseOrderResponse])
def list_orders(
    status: Optional[str] = None,
    supplier_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PurchaseOrderService(db)
    skip = (page - 1) * page_size
    items, total = service.list_orders(
        status=status, supplier_id=supplier_id, skip=skip, limit=page_size
    )
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

@router.get("/{po_id}", response_model=PurchaseOrderResponse)
def get_order(
    po_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = PurchaseOrderService(db)
    return service.get_order_detail(po_id)

@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    req: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = PurchaseOrderService(db)
    return service.create_custom_purchase_order(req, user_id=current_user.id)

@router.post("/{po_id}/place", response_model=PurchaseOrderResponse)
def place_order(
    po_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = PurchaseOrderService(db)
    return service.place_order(po_id)

@router.post("/{po_id}/cancel", response_model=PurchaseOrderResponse)
def cancel_order(
    po_id: int,
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = PurchaseOrderService(db)
    return service.cancel_order(po_id, reason=reason)
