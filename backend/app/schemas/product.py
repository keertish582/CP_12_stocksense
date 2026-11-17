from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime

class ProductSupplierBase(BaseModel):
    supplier_id: int
    lead_time_days: int = 7
    minimum_order_qty: int = 1
    pack_size: int = 1
    unit_cost: Decimal = Decimal("0.00")
    is_preferred: bool = False

class ProductSupplierCreate(ProductSupplierBase):
    pass

class ProductSupplierResponse(ProductSupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    supplier_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ProductBase(BaseModel):
    sku: str
    name: str
    category_id: Optional[int] = None
    unit: str = "units"
    selling_price: Decimal = Decimal("0.00")
    safety_stock: int = 10
    min_reorder_qty: int = 1
    manual_daily_demand: Optional[Decimal] = None
    lead_time_days: int = 7
    is_active: bool = True

class ProductCreate(ProductBase):
    preferred_supplier_id: Optional[int] = None
    unit_cost: Optional[Decimal] = None
    moq: Optional[int] = 1
    pack_size: Optional[int] = 1

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    unit: Optional[str] = None
    selling_price: Optional[Decimal] = None
    safety_stock: Optional[int] = None
    min_reorder_qty: Optional[int] = None
    manual_daily_demand: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_name: Optional[str] = None
    preferred_supplier_id: Optional[int] = None
    preferred_supplier_name: Optional[str] = None
    unit_cost: Optional[Decimal] = None
    moq: Optional[int] = 1
    pack_size: Optional[int] = 1
    current_on_hand: int = 0
    current_reserved: int = 0
    current_available: int = 0
    created_at: datetime
    updated_at: datetime

class ProductDetailResponse(ProductResponse):
    suppliers: List[ProductSupplierResponse] = []
