from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)

class SaleItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_sku: str
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

class SaleCreate(BaseModel):
    external_sale_id: Optional[str] = None
    sale_date: date
    channel: str = "POS_STORE"
    notes: Optional[str] = None
    warehouse_id: Optional[int] = None
    items: List[SaleItemCreate] = Field(..., min_length=1)

class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_sale_id: Optional[str] = None
    sale_date: date
    total_amount: Decimal
    channel: str
    notes: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    items: List[SaleItemResponse] = []

class ImportRowError(BaseModel):
    row_number: int
    external_sale_id: Optional[str] = None
    sku: Optional[str] = None
    error: str

class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: str
    filename: str
    file_type: str
    status: str
    total_rows: int
    processed_rows: int
    error_count: int
    error_details: Optional[List[ImportRowError]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class CSVPreviewResponse(BaseModel):
    total_rows: int
    valid_rows_count: int
    error_rows_count: int
    errors: List[ImportRowError] = []
    preview_rows: List[dict] = []
