from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import get_current_user, require_roles
from app.services.product_supplier_service import ProductSupplierService
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

@router.get("", response_model=PaginatedResponse[SupplierResponse])
def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    is_active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductSupplierService(db)
    skip = (page - 1) * page_size
    items, total = service.list_suppliers(is_active_only=is_active_only, skip=skip, limit=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ProductSupplierService(db)
    return service.get_supplier(supplier_id)

@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    supp_in: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = ProductSupplierService(db)
    return service.create_supplier(supp_in)

@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: int,
    supp_in: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.MANAGER])),
):
    service = ProductSupplierService(db)
    return service.update_supplier(supplier_id, supp_in)
