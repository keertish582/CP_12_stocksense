from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.supplier import Supplier

class SupplierRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, supplier_id: int) -> Optional[Supplier]:
        return self.db.query(Supplier).filter(Supplier.id == supplier_id).first()

    def get_by_name(self, name: str) -> Optional[Supplier]:
        return self.db.query(Supplier).filter(Supplier.name == name.strip()).first()

    def list(self, is_active_only: bool = False, skip: int = 0, limit: int = 100) -> List[Supplier]:
        q = self.db.query(Supplier)
        if is_active_only:
            q = q.filter(Supplier.is_active == True)
        return q.order_by(Supplier.name.asc()).offset(skip).limit(limit).all()

    def count(self, is_active_only: bool = False) -> int:
        q = self.db.query(Supplier)
        if is_active_only:
            q = q.filter(Supplier.is_active == True)
        return q.count()

    def create(self, supplier: Supplier) -> Supplier:
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def update(self, supplier: Supplier) -> Supplier:
        self.db.commit()
        self.db.refresh(supplier)
        return supplier
