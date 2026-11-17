from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class GoodsReceiptItemCreate(BaseModel):
    po_item_id: int
    quantity_received: int = Field(..., gt=0, description="Quantity to receive in this delivery")

class GoodsReceiptCreate(BaseModel):
    purchase_order_id: int
    received_date: date
    notes: Optional[str] = None
    items: List[GoodsReceiptItemCreate] = Field(..., min_length=1)

class GoodsReceiptItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_item_id: int
    product_id: int
    product_sku: str
    product_name: str
    quantity_received: int
    unit_cost: Decimal

class GoodsReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_number: str
    purchase_order_id: int
    po_number: str
    warehouse_id: int
    warehouse_code: str
    received_date: date
    notes: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    items: List[GoodsReceiptItemResponse] = []
