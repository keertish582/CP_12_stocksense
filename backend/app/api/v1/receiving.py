from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import get_current_user, require_roles
from app.services.receiving_service import ReceivingService
from app.schemas.receipt import (
    GoodsReceiptCreate,
    GoodsReceiptResponse,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/receiving", tags=["Goods Receiving"])

@router.get("", response_model=PaginatedResponse[GoodsReceiptResponse])
def list_receipts(
    po_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReceivingService(db)
    skip = (page - 1) * page_size
    items, total = service.list_receipts(po_id=po_id, skip=skip, limit=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

@router.get("/{receipt_id}", response_model=GoodsReceiptResponse)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReceivingService(db)
    return service.get_receipt_detail(receipt_id)

@router.post("", response_model=GoodsReceiptResponse, status_code=status.HTTP_201_CREATED)
def receive_goods(
    req: GoodsReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = ReceivingService(db)
    return service.receive_goods(req, user_id=current_user.id)
