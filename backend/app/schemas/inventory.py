from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class InventoryBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_sku: str
    product_name: str
    category_name: Optional[str] = None
    warehouse_id: int
    warehouse_code: str
    warehouse_name: str
    on_hand_qty: int
    reserved_qty: int
    available_qty: int
    eligible_open_inbound: int = 0
    inventory_position: int = 0
    reorder_point: int = 0
    stock_status: str = "HEALTHY"  # OUT_OF_STOCK, STOCKOUT_RISK, REORDER_SOON, HEALTHY
    updated_at: datetime

class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_sku: str
    product_name: str
    warehouse_id: int
    warehouse_code: str
    quantity_delta: int
    movement_type: str
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    balance_after: int
    reason: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime

class StockAdjustmentCreate(BaseModel):
    product_id: int
    warehouse_id: Optional[int] = None
    quantity_delta: int = Field(..., description="Positive to add stock, negative to deduct")
    reason: str = Field(..., min_length=3, description="Mandatory reason for audit trail")
