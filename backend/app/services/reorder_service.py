import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.recommendation import (
    ReorderRecommendation,
    RecommendationStatus,
    RecommendationPriority,
)
from app.models.product import Product, ProductSupplier
from app.models.forecast import ForecastMethod
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, POStatus
from app.repositories.recommendation_repo import RecommendationRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.forecast_repo import ForecastRepository
from app.repositories.purchase_order_repo import PurchaseOrderRepository
from app.services.forecast_service import ForecastService
from app.schemas.recommendation import (
    ReorderRecommendationResponse,
    RecommendationApprovalRequest,
    RecommendationActionRequest,
)
from app.schemas.purchase_order import PurchaseOrderResponse
from app.core.config import settings

class ReorderService:
    def __init__(self, db: Session):
        self.db = db
        self.rec_repo = RecommendationRepository(db)
        self.product_repo = ProductRepository(db)
        self.inventory_repo = InventoryRepository(db)
        self.forecast_repo = ForecastRepository(db)
        self.po_repo = PurchaseOrderRepository(db)
        self.forecast_service = ForecastService(db)

    def calculate_reorder_for_product(
        self,
        product: Product,
        warehouse_id: int,
        coverage_days: int = 14,
    ) -> Optional[ReorderRecommendation]:
        """
        Calculates reorder recommendation for a single product with full explainability.
        """
        today = date.today()

        # 1. Fetch current inventory balance
        bal = self.inventory_repo.get_balance(product.id, warehouse_id)
        on_hand = bal.on_hand_qty if bal else 0
        reserved = bal.reserved_qty if bal else 0
        available = max(0, on_hand - reserved)

        # 2. Fetch eligible open inbound orders
        eligible_inbound, eligible_orders, excluded_orders = self.inventory_repo.get_eligible_inbound_qty(
            product.id, warehouse_id, as_of_date=today
        )

        inventory_position = available + eligible_inbound

        # 3. Preferred supplier & planning settings
        pref_supp = next((ps for ps in product.product_suppliers if ps.is_preferred), None)
        if not pref_supp and product.product_suppliers:
            pref_supp = product.product_suppliers[0]

        lead_time_days = pref_supp.lead_time_days if pref_supp else product.lead_time_days
        moq = pref_supp.minimum_order_qty if pref_supp else product.min_reorder_qty
        pack_size = pref_supp.pack_size if pref_supp else 1
        unit_cost = pref_supp.unit_cost if pref_supp else Decimal("0.00")
        supplier_id = pref_supp.supplier_id if pref_supp else None

        safety_stock = product.safety_stock

        # 4. Get latest forecasts
        latest_run = self.forecast_repo.get_latest_completed_run()
        if not latest_run:
            self.forecast_service.run_full_forecast_pipeline()
            latest_run = self.forecast_repo.get_latest_completed_run()

        forecasts = self.forecast_repo.get_forecasts_for_product(product.id, latest_run.id) if latest_run else []
        forecast_map = {f.forecast_date: f.forecast_qty for f in forecasts}

        # Check for insufficient history or missing configuration
        has_insufficient_history = any(f.method == ForecastMethod.INSUFFICIENT_HISTORY for f in forecasts)

        # Lead-time demand: sum of daily forecasts for the next L days
        lead_time_demand = Decimal("0.00")
        for i in range(1, lead_time_days + 1):
            target_date = today + timedelta(days=i)
            lead_time_demand += forecast_map.get(target_date, Decimal("0.00"))

        reorder_point = int(math.ceil(float(lead_time_demand))) + safety_stock

        # Target stock: sum of forecasts for next (L + C) days + safety stock
        target_horizon = lead_time_days + coverage_days
        target_demand = Decimal("0.00")
        for i in range(1, target_horizon + 1):
            target_date = today + timedelta(days=i)
            target_demand += forecast_map.get(target_date, Decimal("0.00"))

        target_stock = int(math.ceil(float(target_demand))) + safety_stock

        # Projected stockout date
        fc_points = [(f.forecast_date, f.forecast_qty) for f in forecasts]
        projected_stockout = self.forecast_service.estimate_projected_stockout_date(available, fc_points)

        # Inbound orders arriving after stockout check
        warnings = []
        if excluded_orders:
            for ex in excluded_orders:
                warnings.append(f"Inbound order {ex['po_number']} ({ex['remaining_qty']} units) excluded: {ex['reason']}")

        if projected_stockout and eligible_orders:
            for el in eligible_orders:
                if el["expected_delivery_date"]:
                    deliv_date = datetime.strptime(el["expected_delivery_date"], "%Y-%m-%d").date()
                    if deliv_date > projected_stockout:
                        warnings.append(
                            f"Eligible order {el['po_number']} is expected on {deliv_date}, which is after projected stockout date {projected_stockout}."
                        )

        if has_insufficient_history:
            warnings.append("Insufficient sales history for reliable statistical demand. Please configure manual daily demand.")

        # Trigger condition: inventory_position <= reorder_point
        is_triggered = inventory_position <= reorder_point

        if not is_triggered and not has_insufficient_history:
            # No recommendation needed
            return None

        # Compute raw order quantity
        raw_qty = max(0, int(math.ceil(target_stock - inventory_position)))

        # Apply MOQ and pack size rounding
        if raw_qty > 0:
            qty_with_moq = max(raw_qty, moq)
            suggested_qty = int(math.ceil(qty_with_moq / pack_size) * pack_size)
        else:
            suggested_qty = 0

        total_cost = unit_cost * Decimal(suggested_qty)

        # Priority calculation
        if available == 0:
            priority = RecommendationPriority.HIGH
        elif projected_stockout and projected_stockout <= (today + timedelta(days=lead_time_days)):
            priority = RecommendationPriority.HIGH
        elif inventory_position <= reorder_point:
            priority = RecommendationPriority.MEDIUM
        else:
            priority = RecommendationPriority.LOW

        calculation_details = {
            "lead_time_days": lead_time_days,
            "coverage_days": coverage_days,
            "lead_time_demand": float(lead_time_demand),
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "target_stock": target_stock,
            "formula": f"ROP = ({float(lead_time_demand):.1f} LTD) + {safety_stock} SS = {reorder_point}. Position = {inventory_position} ({available} avail + {eligible_inbound} inbound).",
            "rounding_explanation": f"Raw {raw_qty} -> MOQ {moq} -> Pack Size {pack_size}x = {suggested_qty} units.",
            "eligible_purchase_orders": eligible_orders,
            "excluded_purchase_orders": excluded_orders,
            "warnings": warnings,
            "projected_stockout_date": str(projected_stockout) if projected_stockout else None,
        }

        # Deactivate any existing active recommendation for this product/warehouse
        self.rec_repo.deactivate_all_for_product_warehouse(product.id, warehouse_id)

        rec = ReorderRecommendation(
            product_id=product.id,
            warehouse_id=warehouse_id,
            forecast_run_id=latest_run.id if latest_run else None,
            inventory_position_snapshot=inventory_position,
            on_hand_snapshot=on_hand,
            eligible_inbound_snapshot=eligible_inbound,
            reorder_point=reorder_point,
            target_stock=target_stock,
            lead_time_demand=lead_time_demand,
            safety_stock=safety_stock,
            raw_order_qty=raw_qty,
            suggested_qty=suggested_qty,
            supplier_id=supplier_id,
            pack_size=pack_size,
            moq=moq,
            unit_cost=unit_cost,
            total_estimated_cost=total_cost,
            projected_stockout_date=projected_stockout,
            priority=priority,
            status=RecommendationStatus.PENDING,
            calculation_details=calculation_details,
            is_active=True,
        )
        self.rec_repo.create(rec)
        return rec

    def refresh_all_recommendations(self, coverage_days: int = 14) -> List[ReorderRecommendation]:
        """
        Calculates and stores fresh active recommendations for all active products.
        """
        wh = self.inventory_repo.get_or_create_default_warehouse()
        products, _ = self.product_repo.list_products(is_active_only=True, limit=500)

        created_recs = []
        for p in products:
            rec = self.calculate_reorder_for_product(p, wh.id, coverage_days=coverage_days)
            if rec:
                created_recs.append(rec)

        self.db.commit()
        return created_recs

    def list_recommendations(
        self,
        warehouse_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        is_active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ReorderRecommendationResponse], int]:
        wh = (
            self.inventory_repo.get_warehouse_by_id(warehouse_id)
            if warehouse_id
            else self.inventory_repo.get_or_create_default_warehouse()
        )
        recs, total = self.rec_repo.list_recommendations(
            warehouse_id=wh.id,
            status=status,
            priority=priority,
            is_active_only=is_active_only,
            skip=skip,
            limit=limit,
        )
        results = []
        for r in recs:
            results.append(
                ReorderRecommendationResponse(
                    id=r.id,
                    product_id=r.product_id,
                    product_sku=r.product.sku,
                    product_name=r.product.name,
                    category_name=r.product.category.name if r.product.category else None,
                    warehouse_id=r.warehouse_id,
                    warehouse_code=r.warehouse.code,
                    forecast_run_id=r.forecast_run_id,
                    inventory_position_snapshot=r.inventory_position_snapshot,
                    on_hand_snapshot=r.on_hand_snapshot,
                    eligible_inbound_snapshot=r.eligible_inbound_snapshot,
                    reorder_point=r.reorder_point,
                    target_stock=r.target_stock,
                    lead_time_demand=r.lead_time_demand,
                    safety_stock=r.safety_stock,
                    raw_order_qty=r.raw_order_qty,
                    suggested_qty=r.suggested_qty,
                    supplier_id=r.supplier_id,
                    supplier_name=r.supplier.name if r.supplier else None,
                    pack_size=r.pack_size,
                    moq=r.moq,
                    unit_cost=r.unit_cost,
                    total_estimated_cost=r.total_estimated_cost,
                    projected_stockout_date=r.projected_stockout_date,
                    priority=r.priority,
                    status=r.status,
                    calculation_details=r.calculation_details,
                    is_active=r.is_active,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
            )
        return results, total

    def approve_recommendation(
        self, rec_id: int, req: RecommendationApprovalRequest, user_id: int
    ) -> PurchaseOrderResponse:
        """
        Validates the recommendation, verifies that inventory inputs have not drifted materially,
        and atomically creates a DRAFT purchase order.
        """
        rec = self.rec_repo.get_by_id(rec_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        if rec.status != RecommendationStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve recommendation in '{rec.status}' status. Only PENDING recommendations can be approved.",
            )

        if not rec.supplier_id:
            raise HTTPException(
                status_code=400,
                detail="Recommendation lacks a preferred supplier. Please assign a supplier before approving.",
            )

        # STALE DATA CHECK:
        # Check current on_hand and eligible inbound to see if stock changed materially (> 10% or >= 5 units)
        bal = self.inventory_repo.get_balance(rec.product_id, rec.warehouse_id)
        current_on_hand = bal.on_hand_qty if bal else 0
        current_inbound, _, _ = self.inventory_repo.get_eligible_inbound_qty(rec.product_id, rec.warehouse_id)

        drift_on_hand = abs(current_on_hand - rec.on_hand_snapshot)
        drift_inbound = abs(current_inbound - rec.eligible_inbound_snapshot)

        if drift_on_hand > 5 or drift_inbound > 5:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Inventory position has materially changed since recommendation was computed! "
                    f"Snapshot on-hand: {rec.on_hand_snapshot}, Current on-hand: {current_on_hand}. "
                    f"Snapshot inbound: {rec.eligible_inbound_snapshot}, Current inbound: {current_inbound}. "
                    f"Please refresh recommendations before approving."
                ),
            )

        # Idempotency / duplicate check: ensure no active PO exists for this recommendation
        existing_po = (
            self.db.query(PurchaseOrder)
            .filter(PurchaseOrder.recommendation_id == rec.id)
            .first()
        )
        if existing_po:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Purchase order {existing_po.po_number} has already been created for this recommendation.",
            )

        order_qty = req.custom_qty if req.custom_qty and req.custom_qty > 0 else rec.suggested_qty
        if order_qty <= 0:
            raise HTTPException(status_code=400, detail="Order quantity must be greater than zero")

        # Create Draft Purchase Order
        po_number = self.po_repo.generate_po_number()
        lead_time = rec.calculation_details.get("lead_time_days", 7) if rec.calculation_details else 7
        expected_date = req.expected_delivery_date or (date.today() + timedelta(days=lead_time))

        total_amount = rec.unit_cost * Decimal(order_qty)

        po = PurchaseOrder(
            po_number=po_number,
            supplier_id=rec.supplier_id,
            warehouse_id=rec.warehouse_id,
            recommendation_id=rec.id,
            status=POStatus.DRAFT,
            expected_delivery_date=expected_date,
            notes=req.notes or f"Created from Recommendation #{rec.id} ({rec.product.name})",
            total_amount=total_amount,
            created_by=user_id,
        )
        self.po_repo.create(po)

        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            product_id=rec.product_id,
            quantity_ordered=order_qty,
            quantity_received=0,
            unit_cost=rec.unit_cost,
            subtotal=total_amount,
        )
        self.db.add(po_item)

        # Mark recommendation as APPROVED
        rec.status = RecommendationStatus.APPROVED
        rec.is_active = False

        self.db.commit()
        self.db.refresh(po)

        from app.services.purchase_order_service import PurchaseOrderService
        po_service = PurchaseOrderService(self.db)
        return po_service.get_order_detail(po.id)

    def take_action(self, rec_id: int, req: RecommendationActionRequest) -> ReorderRecommendationResponse:
        rec = self.rec_repo.get_by_id(rec_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        action = req.action.upper().strip()
        if action == "DEFER":
            rec.status = RecommendationStatus.DEFERRED
        elif action == "DISMISS":
            rec.status = RecommendationStatus.DISMISSED
            rec.is_active = False
        else:
            raise HTTPException(status_code=400, detail="Action must be DEFER or DISMISS")

        if req.reason and rec.calculation_details:
            details = dict(rec.calculation_details)
            details["action_reason"] = req.reason
            rec.calculation_details = details

        self.rec_repo.update(rec)
        return ReorderRecommendationResponse.model_validate(rec)
