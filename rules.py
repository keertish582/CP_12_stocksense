"""Inventory rules: Safety stock, Reorder Point (ROP), EOQ, and status classification."""

import math
from typing import Any, Dict, Optional


# Urgency ranking for sorting
STATUS_URGENCY = {
    "CRITICAL": 1,
    "REORDER": 2,
    "OK": 3,
    "OVERSTOCK": 4,
}


def calculate_safety_stock(
    std_daily_demand: float,
    lead_time_days: int,
    z_score: float = 1.65,
) -> float:
    """
    Safety stock = Z * std_dev(daily demand) * sqrt(lead_time_days).
    """
    if std_daily_demand <= 0 or lead_time_days <= 0 or z_score <= 0:
        return 0.0
    return z_score * std_daily_demand * math.sqrt(float(lead_time_days))


def calculate_reorder_point(
    avg_daily_demand: float,
    lead_time_days: int,
    safety_stock: float,
) -> float:
    """
    Reorder point (ROP) = avg_daily_demand * lead_time_days + safety_stock.
    """
    return (avg_daily_demand * float(lead_time_days)) + safety_stock


def calculate_days_of_cover(
    current_stock: int,
    avg_daily_demand: float,
) -> Optional[float]:
    """
    Days of cover = current_stock / avg_daily_demand.
    Returns 0.0 if current_stock == 0.
    Returns None if avg_daily_demand == 0 to prevent division by zero.
    """
    if current_stock == 0:
        return 0.0
    if avg_daily_demand <= 0:
        return None
    return float(current_stock) / avg_daily_demand


def calculate_eoq(
    annual_demand: float,
    unit_cost: float,
    order_cost: float = 500.0,
    holding_cost_pct: float = 0.20,
    min_order_qty: int = 1,
) -> int:
    """
    Reorder quantity = EOQ = sqrt(2 * annual_demand * order_cost / holding_cost).
    Round up, then raise to at least min_order_qty and round up to a multiple of min_order_qty.
    """
    if min_order_qty < 1:
        min_order_qty = 1

    if annual_demand <= 0:
        return min_order_qty

    holding_cost = holding_cost_pct * unit_cost
    if holding_cost <= 0:
        return min_order_qty

    raw_eoq = math.sqrt((2.0 * annual_demand * order_cost) / holding_cost)
    eoq = math.ceil(raw_eoq)

    if eoq < min_order_qty:
        return min_order_qty

    # Round up to a multiple of min_order_qty
    remainder = eoq % min_order_qty
    if remainder != 0:
        eoq += (min_order_qty - remainder)

    return eoq


def classify_status(
    current_stock: int,
    lead_time_days: int,
    rop: float,
    days_of_cover: Optional[float],
) -> str:
    """
    Status rules, evaluated strictly in this order:
      1. CRITICAL: current_stock == 0 or days_of_cover < lead_time_days
      2. OVERSTOCK: days_of_cover > 90
      3. REORDER: current_stock <= ROP
      4. OK: otherwise
    """
    # 1. CRITICAL
    if current_stock == 0:
        return "CRITICAL"
    if days_of_cover is not None and days_of_cover < float(lead_time_days):
        return "CRITICAL"

    # 2. OVERSTOCK
    if days_of_cover is not None and days_of_cover > 90.0:
        return "OVERSTOCK"

    # 3. REORDER
    if current_stock <= rop:
        return "REORDER"

    # 4. OK
    return "OK"


def evaluate_inventory_item(
    product: Dict[str, Any],
    forecast: Dict[str, Any],
    z_score: float = 1.65,
    order_cost: float = 500.0,
    holding_cost_pct: float = 0.20,
) -> Dict[str, Any]:
    """
    Evaluate full inventory metrics and status for a single product.
    """
    sku = product["sku"]
    name = product["name"]
    current_stock = product["current_stock"]
    lead_time_days = product["lead_time_days"]
    unit_cost = product["unit_cost"]
    min_order_qty = product["min_order_qty"]

    avg_demand = forecast.get("avg_daily_demand", 0.0)
    std_demand = forecast.get("std_daily_demand", 0.0)
    is_insufficient_data = forecast.get("is_insufficient_data", False)

    safety_stock = calculate_safety_stock(
        std_daily_demand=std_demand,
        lead_time_days=lead_time_days,
        z_score=z_score,
    )

    rop = calculate_reorder_point(
        avg_daily_demand=avg_demand,
        lead_time_days=lead_time_days,
        safety_stock=safety_stock,
    )

    days_of_cover = calculate_days_of_cover(
        current_stock=current_stock,
        avg_daily_demand=avg_demand,
    )

    annual_demand = avg_demand * 365.0
    eoq = calculate_eoq(
        annual_demand=annual_demand,
        unit_cost=unit_cost,
        order_cost=order_cost,
        holding_cost_pct=holding_cost_pct,
        min_order_qty=min_order_qty,
    )

    status = classify_status(
        current_stock=current_stock,
        lead_time_days=lead_time_days,
        rop=rop,
        days_of_cover=days_of_cover,
    )

    # Order quantity: only CRITICAL and REORDER items need an order placed now
    order_qty = eoq if status in ("CRITICAL", "REORDER") else 0

    return {
        "sku": sku,
        "name": name,
        "current_stock": current_stock,
        "supplier": product.get("supplier", "Unknown"),
        "lead_time_days": lead_time_days,
        "unit_cost": unit_cost,
        "min_order_qty": min_order_qty,
        "avg_daily_demand": avg_demand,
        "std_daily_demand": std_demand,
        "safety_stock": safety_stock,
        "rop": rop,
        "days_of_cover": days_of_cover,
        "status": status,
        "eoq": eoq,
        "order_qty": order_qty,
        "is_insufficient_data": is_insufficient_data,
        "urgency_rank": STATUS_URGENCY.get(status, 99),
    }
