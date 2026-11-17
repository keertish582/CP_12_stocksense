from datetime import date, timedelta
from decimal import Decimal
import pandas as pd
import pytest
from app.services.forecast_service import ForecastService
from app.services.reorder_service import ReorderService
from app.models.product import Product
from app.models.forecast import ForecastMethod
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, POStatus
from app.schemas.recommendation import RecommendationApprovalRequest

def test_cold_start_insufficient_history_behavior(db):
    prod = Product(
        sku="COLD-TEST-NO-MANUAL",
        name="Cold Start Item No Manual Demand",
        unit="pcs",
        selling_price=50.0,
        safety_stock=5,
        min_reorder_qty=10,
        manual_daily_demand=None,
        lead_time_days=7,
        is_active=True,
    )
    db.add(prod)
    db.commit()

    service = ForecastService(db)
    empty_series = pd.DataFrame(columns=["date", "sales_qty", "is_stockout"])

    points, method, mae, wape, is_cold, has_censored = service.generate_future_forecast_rates(
        product=prod,
        daily_series=empty_series,
        horizon_days=30,
        start_forecast_date=date.today() + timedelta(days=1),
    )

    assert is_cold is True
    assert method == ForecastMethod.INSUFFICIENT_HISTORY

def test_cold_start_with_manual_fallback(db):
    prod = Product(
        sku="COLD-TEST-MANUAL",
        name="Cold Start Item With Manual Demand",
        unit="pcs",
        selling_price=50.0,
        safety_stock=5,
        min_reorder_qty=10,
        manual_daily_demand=Decimal("4.50"),
        lead_time_days=7,
        is_active=True,
    )
    db.add(prod)
    db.commit()

    service = ForecastService(db)
    empty_series = pd.DataFrame(columns=["date", "sales_qty", "is_stockout"])

    points, method, mae, wape, is_cold, has_censored = service.generate_future_forecast_rates(
        product=prod,
        daily_series=empty_series,
        horizon_days=30,
        start_forecast_date=date.today() + timedelta(days=1),
    )

    assert is_cold is True
    assert method == ForecastMethod.MANUAL_FALLBACK
    assert points[0][1] == Decimal("4.50")

def test_inbound_eligibility_and_overdue_exclusion(db, test_setup_catalog, test_users):
    prod = test_setup_catalog["product"]
    wh = test_setup_catalog["warehouse"]
    supp = test_setup_catalog["supplier"]
    admin = test_users["admin"]
    today = date.today()

    # 1. Draft PO: must NOT be counted
    po_draft = PurchaseOrder(
        po_number="PO-TEST-DRAFT",
        supplier_id=supp.id,
        warehouse_id=wh.id,
        status=POStatus.DRAFT,
        expected_delivery_date=today + timedelta(days=5),
        created_by=admin.id,
    )
    db.add(po_draft)
    db.flush()
    db.add(PurchaseOrderItem(purchase_order_id=po_draft.id, product_id=prod.id, quantity_ordered=100, quantity_received=0, unit_cost=50, subtotal=5000))

    # 2. Overdue PO: must be EXCLUDED and flagged
    po_overdue = PurchaseOrder(
        po_number="PO-TEST-OVERDUE",
        supplier_id=supp.id,
        warehouse_id=wh.id,
        status=POStatus.PLACED,
        expected_delivery_date=today - timedelta(days=2),  # In the past!
        created_by=admin.id,
    )
    db.add(po_overdue)
    db.flush()
    db.add(PurchaseOrderItem(purchase_order_id=po_overdue.id, product_id=prod.id, quantity_ordered=50, quantity_received=0, unit_cost=50, subtotal=2500))

    # 3. Eligible PO: PLACED with future expected delivery date
    po_eligible = PurchaseOrder(
        po_number="PO-TEST-ELIGIBLE",
        supplier_id=supp.id,
        warehouse_id=wh.id,
        status=POStatus.PLACED,
        expected_delivery_date=today + timedelta(days=3),
        created_by=admin.id,
    )
    db.add(po_eligible)
    db.flush()
    db.add(PurchaseOrderItem(purchase_order_id=po_eligible.id, product_id=prod.id, quantity_ordered=40, quantity_received=0, unit_cost=50, subtotal=2000))
    db.commit()

    from app.repositories.inventory_repo import InventoryRepository
    inv_repo = InventoryRepository(db)
    eligible_qty, eligible_orders, excluded_orders = inv_repo.get_eligible_inbound_qty(prod.id, wh.id, as_of_date=today)

    assert eligible_qty == 40
    assert len(eligible_orders) == 1
    assert eligible_orders[0]["po_number"] == "PO-TEST-ELIGIBLE"

    assert len(excluded_orders) == 1
    assert excluded_orders[0]["po_number"] == "PO-TEST-OVERDUE"
    assert "Overdue" in excluded_orders[0]["reason"]

def test_moq_and_pack_size_rounding(db, test_setup_catalog):
    """
    Test setup:
    Product MOQ = 20, Pack Size = 6.
    If raw needed quantity is 7:
    max(7, 20) = 20
    Round up to pack size: ceil(20 / 6) * 6 = 4 * 6 = 24 units!
    """
    prod = test_setup_catalog["product"]
    wh = test_setup_catalog["warehouse"]

    # Temporarily set high safety stock to trigger raw needed qty of ~7
    prod.safety_stock = 45
    test_setup_catalog["balance"].on_hand_qty = 38
    db.commit()

    reorder_service = ReorderService(db)
    rec = reorder_service.calculate_reorder_for_product(prod, wh.id, coverage_days=14)

    assert rec is not None
    # Suggested qty must be a multiple of pack size (6) and >= MOQ (20)
    assert rec.suggested_qty >= 20
    assert rec.suggested_qty % 6 == 0

def test_stale_recommendation_approval_rejected(client, auth_headers, test_setup_catalog, db):
    prod = test_setup_catalog["product"]
    wh = test_setup_catalog["warehouse"]
    bal = test_setup_catalog["balance"]

    bal.on_hand_qty = 5
    db.commit()

    reorder_service = ReorderService(db)
    rec = reorder_service.calculate_reorder_for_product(prod, wh.id, coverage_days=14)
    assert rec is not None
    snapshot_on_hand = rec.on_hand_snapshot

    # Simulate material change in on-hand inventory (+20 units)
    bal.on_hand_qty = snapshot_on_hand + 20
    db.commit()

    # Approving stale recommendation must fail with 409 Conflict
    res = client.post(
        f"/api/v1/recommendations/{rec.id}/approve",
        headers=auth_headers["manager"],
        json={"notes": "Approval attempt with stale inventory"},
    )
    assert res.status_code == 409
    assert "materially changed" in res.json()["detail"].lower()

def test_forecast_evaluation_report_endpoint(client, auth_headers):
    res = client.get(
        "/api/v1/reports/forecast-evaluation",
        headers=auth_headers["manager"],
    )
    assert res.status_code == 200
    assert isinstance(res.json(), list)
