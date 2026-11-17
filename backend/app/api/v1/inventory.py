from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import get_current_user, require_roles
from app.services.inventory_service import InventoryService
from app.schemas.inventory import (
    InventoryBalanceResponse,
    StockMovementResponse,
    StockAdjustmentCreate,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.get("/balances", response_model=PaginatedResponse[InventoryBalanceResponse])
def list_balances(
    warehouse_id: Optional[int] = None,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InventoryService(db)
    skip = (page - 1) * page_size
    items, total = service.list_inventory_balances(
        warehouse_id=warehouse_id,
        search=search,
        category_id=category_id,
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

@router.post("/adjustments", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
def record_adjustment(
    adj: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = InventoryService(db)
    return service.record_stock_adjustment(adj, user_id=current_user.id)

@router.get("/movements", response_model=PaginatedResponse[StockMovementResponse])
def list_movements(
    product_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = InventoryService(db)
    skip = (page - 1) * page_size
    items, total = service.list_stock_movements(
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
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
