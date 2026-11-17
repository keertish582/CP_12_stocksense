from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Response, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.sales_service import SalesService
from app.schemas.sale import (
    SaleCreate,
    SaleResponse,
    CSVPreviewResponse,
    ImportJobResponse,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/sales", tags=["Sales & Imports"])

@router.get("", response_model=PaginatedResponse[SaleResponse])
def list_sales(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalesService(db)
    skip = (page - 1) * page_size
    items, total = service.list_sales(skip=skip, limit=page_size)
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
def create_sale(
    sale_in: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalesService(db)
    return service.create_manual_sale(sale_in, user_id=current_user.id)

@router.get("/template-csv")
def download_csv_template(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalesService(db)
    csv_content = service.generate_csv_template()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_import_template.csv"},
    )

@router.post("/preview-csv", response_model=CSVPreviewResponse)
async def preview_sales_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    csv_text = content.decode("utf-8-sig", errors="replace")
    service = SalesService(db)
    return service.preview_csv_import(csv_text)

@router.post("/import-csv", response_model=ImportJobResponse, status_code=status.HTTP_201_CREATED)
async def import_sales_csv(
    file: UploadFile = File(...),
    warehouse_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    csv_text = content.decode("utf-8-sig", errors="replace")
    service = SalesService(db)
    return service.execute_atomic_csv_import(
        csv_text=csv_text,
        filename=file.filename or "uploaded_sales.csv",
        user_id=current_user.id,
        warehouse_id=warehouse_id,
    )

@router.get("/jobs/{job_id}", response_model=ImportJobResponse)
def get_import_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SalesService(db)
    return service.get_import_job(job_id)
