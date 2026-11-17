from typing import Optional, List, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.repositories.inventory_repo import InventoryRepository, InsufficientStockError
from app.repositories.product_repo import ProductRepository
from app.models.inventory import MovementType, StockMovement
from app.schemas.inventory import InventoryBalanceResponse, StockMovementResponse, StockAdjustmentCreate

class InventoryService:
    def __init__(self, db: Session):
        self.db = db
        self.inventory_repo = InventoryRepository(db)
        self.product_repo = ProductRepository(db)

    def list_inventory_balances(
        self,
        warehouse_id: Optional[int] = None,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[InventoryBalanceResponse], int]:
        items, total = self.inventory_repo.list_inventory_balances(
            warehouse_id=warehouse_id,
            search=search,
            category_id=category_id,
            skip=skip,
            limit=limit,
        )
        return [InventoryBalanceResponse(**item) for item in items], total

    def record_stock_adjustment(self, adj: StockAdjustmentCreate, user_id: int) -> StockMovementResponse:
        product = self.product_repo.get_by_id(adj.product_id)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        wh = (
            self.inventory_repo.get_warehouse_by_id(adj.warehouse_id)
            if adj.warehouse_id
            else self.inventory_repo.get_or_create_default_warehouse()
        )
        if not wh:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

        if adj.quantity_delta == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Adjustment quantity delta cannot be zero")

        if not adj.reason or len(adj.reason.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid mandatory reason (at least 3 characters) is required for audit trail.",
            )

        try:
            balance, movement = self.inventory_repo.apply_stock_movement_atomic(
                product_id=product.id,
                warehouse_id=wh.id,
                quantity_delta=adj.quantity_delta,
                movement_type=MovementType.ADJUSTMENT,
                reference_type="manual_adjustment",
                reference_id=f"ADJ-{product.sku}",
                reason=adj.reason.strip(),
                created_by=user_id,
            )
            self.db.commit()
            self.db.refresh(movement)
        except InsufficientStockError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to record stock adjustment: {str(e)}",
            )

        return StockMovementResponse(
            id=movement.id,
            product_id=product.id,
            product_sku=product.sku,
            product_name=product.name,
            warehouse_id=wh.id,
            warehouse_code=wh.code,
            quantity_delta=movement.quantity_delta,
            movement_type=movement.movement_type,
            reference_type=movement.reference_type,
            reference_id=movement.reference_id,
            balance_after=movement.balance_after,
            reason=movement.reason,
            created_by_name=movement.user.full_name if movement.user else None,
            created_at=movement.created_at,
        )

    def list_stock_movements(
        self,
        product_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StockMovementResponse], int]:
        movements, total = self.inventory_repo.list_stock_movements(
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            skip=skip,
            limit=limit,
        )
        results = [
            StockMovementResponse(
                id=m.id,
                product_id=m.product_id,
                product_sku=m.product.sku,
                product_name=m.product.name,
                warehouse_id=m.warehouse_id,
                warehouse_code=m.warehouse.code,
                quantity_delta=m.quantity_delta,
                movement_type=m.movement_type,
                reference_type=m.reference_type,
                reference_id=m.reference_id,
                balance_after=m.balance_after,
                reason=m.reason,
                created_by_name=m.user.full_name if m.user else None,
                created_at=m.created_at,
            )
            for m in movements
        ]
        return results, total
