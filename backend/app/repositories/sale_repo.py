from datetime import date
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.sale import Sale, SaleItem
from app.models.product import Product

class SaleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, sale_id: int) -> Optional[Sale]:
        return (
            self.db.query(Sale)
            .options(
                joinedload(Sale.items).joinedload(SaleItem.product),
                joinedload(Sale.user),
            )
            .filter(Sale.id == sale_id)
            .first()
        )

    def check_duplicate_sale_line(self, external_sale_id: str, sku: str) -> bool:
        if not external_sale_id:
            return False
        existing = (
            self.db.query(SaleItem)
            .join(Sale, SaleItem.sale_id == Sale.id)
            .join(Product, SaleItem.product_id == Product.id)
            .filter(
                Sale.external_sale_id == external_sale_id.strip(),
                Product.sku == sku.strip().upper(),
            )
            .first()
        )
        return existing is not None

    def list_sales(self, skip: int = 0, limit: int = 50) -> Tuple[List[Sale], int]:
        q = (
            self.db.query(Sale)
            .options(
                joinedload(Sale.items).joinedload(SaleItem.product),
                joinedload(Sale.user),
            )
        )
        total = q.count()
        sales = q.order_by(Sale.sale_date.desc(), Sale.id.desc()).offset(skip).limit(limit).all()
        return sales, total

    def create_sale_record(self, sale: Sale) -> Sale:
        self.db.add(sale)
        self.db.flush()
        return sale
