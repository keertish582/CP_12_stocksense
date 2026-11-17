from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class ReorderRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_sku: str
    product_name: str
    category_name: Optional[str] = None
    warehouse_id: int
    warehouse_code: str
    forecast_run_id: Optional[int] = None
    
    # Snapshots
    inventory_position_snapshot: int
    on_hand_snapshot: int
    eligible_inbound_snapshot: int
    
    # Reorder parameters
    reorder_point: int
    target_stock: int
    lead_time_demand: Decimal
    safety_stock: int
    
    # Order quantities
    raw_order_qty: int
    suggested_qty: int
    
    # Supplier info
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    pack_size: int
    moq: int
    unit_cost: Decimal
    total_estimated_cost: Decimal
    
    # Risk and priority
    projected_stockout_date: Optional[date] = None
    priority: str
    status: str
    
    # Calculation explanation breakdown
    calculation_details: Optional[dict] = None
    
    is_active: bool
    created_at: datetime
    updated_at: datetime

class RecommendationApprovalRequest(BaseModel):
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    custom_qty: Optional[int] = None

class RecommendationActionRequest(BaseModel):
    action: str = Field(..., description="DEFER or DISMISS")
    reason: Optional[str] = None
