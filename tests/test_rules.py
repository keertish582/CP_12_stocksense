"""Unit tests for inventory rules: safety stock, ROP, EOQ with min_order_qty, and status rules."""

import math
import pytest

from rules import (
    calculate_days_of_cover,
    calculate_eoq,
    calculate_reorder_point,
    calculate_safety_stock,
    classify_status,
    evaluate_inventory_item,
)


def test_hand_calculated_safety_stock():
    """
    Safety stock = Z * std_dev * sqrt(lead_time_days).
    Z = 1.65, std_dev = 2.0, lead_time_days = 9.
    sqrt(9) = 3.0.
    1.65 * 2.0 * 3.0 = 9.9.
    """
    ss = calculate_safety_stock(std_daily_demand=2.0, lead_time_days=9, z_score=1.65)
    assert math.isclose(ss, 9.9, rel_tol=1e-5)


def test_hand_calculated_reorder_point():
    """
    ROP = avg_daily_demand * lead_time_days + safety_stock.
    avg_demand = 4.0, lead_time = 7, safety_stock = 12.5.
    ROP = 4.0 * 7 + 12.5 = 28.0 + 12.5 = 40.5.
    """
    rop = calculate_reorder_point(avg_daily_demand=4.0, lead_time_days=7, safety_stock=12.5)
    assert math.isclose(rop, 40.5, rel_tol=1e-5)


def test_days_of_cover_and_zero_division():
    """Days of cover must not divide by zero when demand is zero."""
    # Normal case: stock 50, demand 5 -> 10.0
    assert calculate_days_of_cover(50, 5.0) == 10.0

    # Current stock 0 -> 0.0
    assert calculate_days_of_cover(0, 5.0) == 0.0

    # Demand 0 with stock > 0 -> None (prevents division by zero)
    assert calculate_days_of_cover(50, 0.0) is None
    assert calculate_days_of_cover(50, -1.0) is None


def test_eoq_with_min_order_qty_rounding():
    """
    EOQ = sqrt(2 * annual_demand * order_cost / holding_cost).
    holding_cost = holding_cost_pct * unit_cost.
    Round up, raise to at least min_order_qty, and round up to a multiple of min_order_qty.
    """
    # Case 1: Hand calculation
    # annual_demand = 365 * 2 = 730
    # order_cost = 500
    # unit_cost = 50, holding_cost_pct = 0.20 -> holding_cost = 10.0
    # raw_eoq = sqrt(2 * 730 * 500 / 10) = sqrt(73000) = 270.185...
    # ceil = 271
    # min_order_qty = 50:
    # 271 is raised to next multiple of 50 -> 300
    eoq1 = calculate_eoq(
        annual_demand=730.0,
        unit_cost=50.0,
        order_cost=500.0,
        holding_cost_pct=0.20,
        min_order_qty=50,
    )
    assert eoq1 == 300

    # Case 2: raw_eoq < min_order_qty
    # annual_demand = 10, unit_cost = 100, holding_cost = 20
    # raw_eoq = sqrt(2 * 10 * 500 / 20) = sqrt(500) = 22.36... -> ceil = 23
    # min_order_qty = 50
    # Must be raised to at least min_order_qty (50)
    eoq2 = calculate_eoq(
        annual_demand=10.0,
        unit_cost=100.0,
        order_cost=500.0,
        holding_cost_pct=0.20,
        min_order_qty=50,
    )
    assert eoq2 == 50

    # Case 3: annual_demand == 0
    eoq3 = calculate_eoq(
        annual_demand=0.0,
        unit_cost=50.0,
        order_cost=500.0,
        holding_cost_pct=0.20,
        min_order_qty=25,
    )
    assert eoq3 == 25


def test_each_status_rule_order():
    """
    Verify status classification rules in strict priority order:
      1. CRITICAL: current_stock == 0 or days_of_cover < lead_time_days
      2. OVERSTOCK: days_of_cover > 90
      3. REORDER: current_stock <= ROP
      4. OK: otherwise
    """
    # 1a. CRITICAL via zero stock
    # Even if cover > 90 or stock <= ROP
    assert classify_status(current_stock=0, lead_time_days=7, rop=10.0, days_of_cover=0.0) == "CRITICAL"

    # 1b. CRITICAL via days_of_cover < lead_time_days
    # stock = 10, lead_time = 14, days_of_cover = 5.0 (< 14)
    assert classify_status(current_stock=10, lead_time_days=14, rop=40.0, days_of_cover=5.0) == "CRITICAL"

    # 2. OVERSTOCK: days_of_cover > 90 (and not critical)
    # stock = 500, lead_time = 7, days_of_cover = 100.0 (> 90), rop = 30.0
    assert classify_status(current_stock=500, lead_time_days=7, rop=30.0, days_of_cover=100.0) == "OVERSTOCK"

    # 3. REORDER: current_stock <= ROP (and not critical or overstocked)
    # stock = 25, lead_time = 7, days_of_cover = 10.0 (> 7 and <= 90), rop = 30.0 (stock <= rop)
    assert classify_status(current_stock=25, lead_time_days=7, rop=30.0, days_of_cover=10.0) == "REORDER"

    # 4. OK: otherwise
    # stock = 50, lead_time = 7, days_of_cover = 20.0 (> 7 and <= 90), rop = 30.0 (stock > rop)
    assert classify_status(current_stock=50, lead_time_days=7, rop=30.0, days_of_cover=20.0) == "OK"


def test_new_product_and_zero_demand_evaluation():
    """Verify evaluation of a new product with 0 demand and stock > 0."""
    product = {
        "sku": "SKU-NEW",
        "name": "New Item",
        "current_stock": 20,
        "supplier": "Test Supplier",
        "lead_time_days": 10,
        "unit_cost": 40.0,
        "min_order_qty": 15,
    }
    forecast = {
        "sku": "SKU-NEW",
        "has_sales_history": False,
        "avg_daily_demand": 0.0,
        "std_daily_demand": 0.0,
        "is_insufficient_data": True,
    }

    eval_result = evaluate_inventory_item(product, forecast)
    assert eval_result["safety_stock"] == 0.0
    assert eval_result["rop"] == 0.0
    assert eval_result["days_of_cover"] is None
    # Stock 20 > ROP 0, cover is None -> Status falls to OK
    assert eval_result["status"] == "OK"
    # For OK status, recommended order_qty is 0
    assert eval_result["order_qty"] == 0
    # But EOQ is min_order_qty
    assert eval_result["eoq"] == 15
