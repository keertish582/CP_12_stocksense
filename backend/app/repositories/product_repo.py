from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.models.product import Product, ProductSupplier
from app.models.category import Category

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(
                joinedload(Product.category),
                joinedload(Product.product_suppliers).joinedload(ProductSupplier.supplier),
            )
            .filter(Product.id == product_id)
            .first()
        )

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(
                joinedload(Product.category),
                joinedload(Product.product_suppliers).joinedload(ProductSupplier.supplier),
            )
            .filter(Product.sku == sku.strip().upper())
            .first()
        )

    def list_products(
        self,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        is_active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Product], int]:
        q = self.db.query(Product).options(
            joinedload(Product.category),
            joinedload(Product.product_suppliers).joinedload(ProductSupplier.supplier),
        )
        if is_active_only:
            q = q.filter(Product.is_active == True)
        if category_id:
            q = q.filter(Product.category_id == category_id)
        if search:
            s = f"%{search.strip()}%"
            q = q.filter(or_(Product.name.ilike(s), Product.sku.ilike(s)))

        total = q.count()
        items = q.order_by(Product.name.asc()).offset(skip).limit(limit).all()
        return items, total

    def create_product(self, product: Product) -> Product:
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_product(self, product: Product) -> Product:
        self.db.commit()
        self.db.refresh(product)
        return product

    # Category operations
    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        return self.db.query(Category).filter(Category.id == category_id).first()

    def get_category_by_name(self, name: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.name.ilike(name.strip())).first()

    def list_categories(self) -> List[Category]:
        return self.db.query(Category).order_by(Category.name.asc()).all()

    def create_category(self, category: Category) -> Category:
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    # Product Supplier operations
    def get_product_supplier(self, product_id: int, supplier_id: int) -> Optional[ProductSupplier]:
        return (
            self.db.query(ProductSupplier)
            .filter(ProductSupplier.product_id == product_id, ProductSupplier.supplier_id == supplier_id)
            .first()
        )

    def set_preferred_supplier(
        self,
        product_id: int,
        supplier_id: int,
        lead_time_days: int,
        moq: int,
        pack_size: int,
        unit_cost: float,
    ) -> ProductSupplier:
        # Clear previous preferred
        self.db.query(ProductSupplier).filter(
            ProductSupplier.product_id == product_id,
            ProductSupplier.is_preferred == True,
        ).update({"is_preferred": False})

        link = self.get_product_supplier(product_id, supplier_id)
        if link:
            link.is_preferred = True
            link.lead_time_days = lead_time_days
            link.minimum_order_qty = moq
            link.pack_size = pack_size
            link.unit_cost = unit_cost
        else:
            link = ProductSupplier(
                product_id=product_id,
                supplier_id=supplier_id,
                lead_time_days=lead_time_days,
                minimum_order_qty=moq,
                pack_size=pack_size,
                unit_cost=unit_cost,
                is_preferred=True,
            )
            self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link
