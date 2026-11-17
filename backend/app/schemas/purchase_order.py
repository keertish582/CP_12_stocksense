from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity_ordered: int = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)

class PurchaseOrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_sku: str
    product_name: str
    quantity_ordered: int
    quantity_received: int
    remaining_qty: int
    unit_cost: Decimal
    subtotal: Decimal

class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: Optional[int] = None
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    items: List[PurchaseOrderItemCreate] = Field(..., min_length=1)

class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_number: str
    supplier_id: int
    supplier_name: str
    warehouse_id: int
    warehouse_code: str
    recommendation_id: Optional[int] = None
    status: str
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    total_amount: Decimal
    placed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[PurchaseOrderItemResponse] = []
