from typing import Optional, List, Tuple
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.product import Product, ProductSupplier
from app.models.supplier import Supplier
from app.models.category import Category
from app.repositories.product_repo import ProductRepository
from app.repositories.supplier_repo import SupplierRepository
from app.repositories.inventory_repo import InventoryRepository
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductDetailResponse, ProductSupplierResponse, CategoryCreate, CategoryResponse
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse

class ProductSupplierService:
    def __init__(self, db: Session):
        self.db = db
        self.product_repo = ProductRepository(db)
        self.supplier_repo = SupplierRepository(db)
        self.inventory_repo = InventoryRepository(db)

    # Categories
    def list_categories(self) -> List[CategoryResponse]:
        cats = self.product_repo.list_categories()
        return [CategoryResponse.model_validate(c) for c in cats]

    def create_category(self, cat_in: CategoryCreate) -> CategoryResponse:
        existing = self.product_repo.get_category_by_name(cat_in.name)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists")
        cat = Category(name=cat_in.name.strip(), description=cat_in.description)
        created = self.product_repo.create_category(cat)
        return CategoryResponse.model_validate(created)

    # Suppliers
    def list_suppliers(self, is_active_only: bool = False, skip: int = 0, limit: int = 100) -> Tuple[List[SupplierResponse], int]:
        suppliers = self.supplier_repo.list(is_active_only=is_active_only, skip=skip, limit=limit)
        total = self.supplier_repo.count(is_active_only=is_active_only)
        return [SupplierResponse.model_validate(s) for s in suppliers], total

    def get_supplier(self, supplier_id: int) -> SupplierResponse:
        s = self.supplier_repo.get_by_id(supplier_id)
        if not s:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
        return SupplierResponse.model_validate(s)

    def create_supplier(self, supp_in: SupplierCreate) -> SupplierResponse:
        existing = self.supplier_repo.get_by_name(supp_in.name)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supplier name already exists")
        supp = Supplier(
            name=supp_in.name.strip(),
            contact_name=supp_in.contact_name,
            email=supp_in.email,
            phone=supp_in.phone,
            address=supp_in.address,
            lead_time_days=supp_in.lead_time_days,
            is_active=supp_in.is_active,
        )
        created = self.supplier_repo.create(supp)
        return SupplierResponse.model_validate(created)

    def update_supplier(self, supplier_id: int, supp_in: SupplierUpdate) -> SupplierResponse:
        supp = self.supplier_repo.get_by_id(supplier_id)
        if not supp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
        for k, v in supp_in.model_dump(exclude_unset=True).items():
            setattr(supp, k, v)
        updated = self.supplier_repo.update(supp)
        return SupplierResponse.model_validate(updated)

    # Products
    def list_products(
        self,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        is_active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProductResponse], int]:
        products, total = self.product_repo.list_products(
            search=search, category_id=category_id, is_active_only=is_active_only, skip=skip, limit=limit
        )
        wh = self.inventory_repo.get_or_create_default_warehouse()
        results = []
        for p in products:
            bal = self.inventory_repo.get_balance(p.id, wh.id)
            on_hand = bal.on_hand_qty if bal else 0
            reserved = bal.reserved_qty if bal else 0
            avail = max(0, on_hand - reserved)

            # Preferred supplier info
            pref_supp = next((ps for ps in p.product_suppliers if ps.is_preferred), None)
            if not pref_supp and p.product_suppliers:
                pref_supp = p.product_suppliers[0]

            results.append(
                ProductResponse(
                    id=p.id,
                    sku=p.sku,
                    name=p.name,
                    category_id=p.category_id,
                    category_name=p.category.name if p.category else None,
                    unit=p.unit,
                    selling_price=p.selling_price,
                    safety_stock=p.safety_stock,
                    min_reorder_qty=p.min_reorder_qty,
                    manual_daily_demand=p.manual_daily_demand,
                    lead_time_days=p.lead_time_days,
                    is_active=p.is_active,
                    preferred_supplier_id=pref_supp.supplier_id if pref_supp else None,
                    preferred_supplier_name=pref_supp.supplier.name if pref_supp and pref_supp.supplier else None,
                    unit_cost=pref_supp.unit_cost if pref_supp else Decimal("0.00"),
                    moq=pref_supp.minimum_order_qty if pref_supp else p.min_reorder_qty,
                    pack_size=pref_supp.pack_size if pref_supp else 1,
                    current_on_hand=on_hand,
                    current_reserved=reserved,
                    current_available=avail,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
            )
        return results, total

    def get_product_detail(self, product_id: int) -> ProductDetailResponse:
        p = self.product_repo.get_by_id(product_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        wh = self.inventory_repo.get_or_create_default_warehouse()
        bal = self.inventory_repo.get_balance(p.id, wh.id)
        on_hand = bal.on_hand_qty if bal else 0
        reserved = bal.reserved_qty if bal else 0
        avail = max(0, on_hand - reserved)

        pref_supp = next((ps for ps in p.product_suppliers if ps.is_preferred), None)
        if not pref_supp and p.product_suppliers:
            pref_supp = p.product_suppliers[0]

        supplier_responses = []
        for ps in p.product_suppliers:
            supplier_responses.append(
                ProductSupplierResponse(
                    id=ps.id,
                    product_id=ps.product_id,
                    supplier_id=ps.supplier_id,
                    supplier_name=ps.supplier.name if ps.supplier else None,
                    lead_time_days=ps.lead_time_days,
                    minimum_order_qty=ps.minimum_order_qty,
                    pack_size=ps.pack_size,
                    unit_cost=ps.unit_cost,
                    is_preferred=ps.is_preferred,
                    created_at=ps.created_at,
                    updated_at=ps.updated_at,
                )
            )

        return ProductDetailResponse(
            id=p.id,
            sku=p.sku,
            name=p.name,
            category_id=p.category_id,
            category_name=p.category.name if p.category else None,
            unit=p.unit,
            selling_price=p.selling_price,
            safety_stock=p.safety_stock,
            min_reorder_qty=p.min_reorder_qty,
            manual_daily_demand=p.manual_daily_demand,
            lead_time_days=p.lead_time_days,
            is_active=p.is_active,
            preferred_supplier_id=pref_supp.supplier_id if pref_supp else None,
            preferred_supplier_name=pref_supp.supplier.name if pref_supp and pref_supp.supplier else None,
            unit_cost=pref_supp.unit_cost if pref_supp else Decimal("0.00"),
            moq=pref_supp.minimum_order_qty if pref_supp else p.min_reorder_qty,
            pack_size=pref_supp.pack_size if pref_supp else 1,
            current_on_hand=on_hand,
            current_reserved=reserved,
            current_available=avail,
            suppliers=supplier_responses,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )

    def create_product(self, prod_in: ProductCreate) -> ProductResponse:
        sku = prod_in.sku.strip().upper()
        existing = self.product_repo.get_by_sku(sku)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Product with SKU '{sku}' already exists.")

        product = Product(
            sku=sku,
            name=prod_in.name.strip(),
            category_id=prod_in.category_id,
            unit=prod_in.unit.strip(),
            selling_price=prod_in.selling_price,
            safety_stock=prod_in.safety_stock,
            min_reorder_qty=prod_in.min_reorder_qty,
            manual_daily_demand=prod_in.manual_daily_demand,
            lead_time_days=prod_in.lead_time_days,
            is_active=prod_in.is_active,
        )
        created = self.product_repo.create_product(product)

        # Initialize warehouse inventory balance at 0
        wh = self.inventory_repo.get_or_create_default_warehouse()
        self.inventory_repo.get_or_create_balance(created.id, wh.id)

        # Link preferred supplier if provided
        if prod_in.preferred_supplier_id:
            self.product_repo.set_preferred_supplier(
                product_id=created.id,
                supplier_id=prod_in.preferred_supplier_id,
                lead_time_days=prod_in.lead_time_days,
                moq=prod_in.moq or 1,
                pack_size=prod_in.pack_size or 1,
                unit_cost=float(prod_in.unit_cost or 0.0),
            )

        return self.get_product_detail(created.id)

    def update_product(self, product_id: int, prod_in: ProductUpdate) -> ProductResponse:
        p = self.product_repo.get_by_id(product_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        for k, v in prod_in.model_dump(exclude_unset=True).items():
            setattr(p, k, v)
        updated = self.product_repo.update_product(p)
        return self.get_product_detail(updated.id)

    def archive_product(self, product_id: int) -> ProductResponse:
        p = self.product_repo.get_by_id(product_id)
        if not p:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        p.is_active = False
        updated = self.product_repo.update_product(p)
        return self.get_product_detail(updated.id)
