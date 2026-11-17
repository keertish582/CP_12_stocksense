from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.recommendation import ReorderRecommendation, RecommendationStatus
from app.models.product import Product

class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, rec_id: int) -> Optional[ReorderRecommendation]:
        return (
            self.db.query(ReorderRecommendation)
            .options(
                joinedload(ReorderRecommendation.product).joinedload(Product.category),
                joinedload(ReorderRecommendation.supplier),
                joinedload(ReorderRecommendation.warehouse),
            )
            .filter(ReorderRecommendation.id == rec_id)
            .first()
        )

    def get_active_by_product_warehouse(self, product_id: int, warehouse_id: int) -> Optional[ReorderRecommendation]:
        return (
            self.db.query(ReorderRecommendation)
            .filter(
                ReorderRecommendation.product_id == product_id,
                ReorderRecommendation.warehouse_id == warehouse_id,
                ReorderRecommendation.is_active == True,
            )
            .first()
        )

    def deactivate_all_for_product_warehouse(self, product_id: int, warehouse_id: int):
        self.db.query(ReorderRecommendation).filter(
            ReorderRecommendation.product_id == product_id,
            ReorderRecommendation.warehouse_id == warehouse_id,
            ReorderRecommendation.is_active == True,
        ).update({"is_active": False})
        self.db.flush()

    def list_recommendations(
        self,
        warehouse_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        is_active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ReorderRecommendation], int]:
        q = (
            self.db.query(ReorderRecommendation)
            .options(
                joinedload(ReorderRecommendation.product).joinedload(Product.category),
                joinedload(ReorderRecommendation.supplier),
                joinedload(ReorderRecommendation.warehouse),
            )
        )
        if is_active_only:
            q = q.filter(ReorderRecommendation.is_active == True)
        if warehouse_id:
            q = q.filter(ReorderRecommendation.warehouse_id == warehouse_id)
        if status:
            q = q.filter(ReorderRecommendation.status == status)
        if priority:
            q = q.filter(ReorderRecommendation.priority == priority)

        total = q.count()
        # Order by priority HIGH first, then suggested_qty desc
        order_case = {
            "HIGH": 1,
            "MEDIUM": 2,
            "LOW": 3,
        }
        recs = q.order_by(
            ReorderRecommendation.priority.asc(),
            ReorderRecommendation.suggested_qty.desc(),
        ).offset(skip).limit(limit).all()
        return recs, total

    def create(self, rec: ReorderRecommendation) -> ReorderRecommendation:
        self.db.add(rec)
        self.db.flush()
        return rec

    def update(self, rec: ReorderRecommendation) -> ReorderRecommendation:
        self.db.commit()
        self.db.refresh(rec)
        return rec
