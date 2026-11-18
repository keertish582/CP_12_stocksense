"""Demand forecasting engine: moving average, std dev, and outlier capping."""

import datetime
import math
import statistics
from typing import Any, Dict, List, Optional, Tuple


def get_daily_sales_series(
    sales_records: List[Dict[str, Any]],
    window_days: int = 30,
    reference_date: Optional[datetime.date] = None,
) -> Tuple[List[float], List[datetime.date]]:
    """
    Construct a contiguous daily sales quantity list for the last `window_days`.
    Missing days in the window are populated with 0.0 sales.
    """
    if window_days <= 0:
        raise ValueError(f"Window must be a positive integer, got {window_days}")

    if not sales_records and reference_date is None:
        return [0.0] * window_days, []

    if reference_date is None:
        reference_date = max(r["date"] for r in sales_records)

    # Aggregate sales by date
    sales_by_date: Dict[datetime.date, float] = {}
    for r in sales_records:
        sales_by_date[r["date"]] = sales_by_date.get(r["date"], 0.0) + float(r["qty_sold"])

    # Generate dates from (reference_date - window_days + 1) to reference_date
    date_list = [
        reference_date - datetime.timedelta(days=i)
        for i in range(window_days - 1, -1, -1)
    ]

    daily_sales = [sales_by_date.get(d, 0.0) for d in date_list]
    return daily_sales, date_list


def cap_outliers(daily_sales: List[float]) -> Tuple[List[float], int]:
    """
    Cap outliers exceeding mean + 3 * std_dev.
    Returns (capped_daily_sales, count_of_capped_days).
    """
    if len(daily_sales) < 2:
        return list(daily_sales), 0

    mean_val = statistics.mean(daily_sales)
    std_val = statistics.stdev(daily_sales)

    if std_val <= 0:
        return list(daily_sales), 0

    threshold = mean_val + (3.0 * std_val)
    capped_series = []
    capped_count = 0

    for val in daily_sales:
        if val > threshold:
            capped_series.append(threshold)
            capped_count += 1
        else:
            capped_series.append(val)

    return capped_series, capped_count


def compute_sku_forecast(
    sku: str,
    sales_records: List[Dict[str, Any]],
    window_days: int = 30,
    reference_date: Optional[datetime.date] = None,
    apply_cap_outliers: bool = False,
) -> Dict[str, Any]:
    """
    Compute demand statistics for a SKU over the designated window.

    Returns dict with:
      - sku: str
      - has_sales_history: bool (whether any sales records exist at all)
      - window_days: int
      - total_window_sales: float
      - avg_daily_demand: float
      - std_daily_demand: float
      - outliers_capped: int
      - daily_series: List[float]
      - is_insufficient_data: bool
    """
    sku_sales = [r for r in sales_records if r["sku"] == sku]
    has_history = len(sku_sales) > 0

    if not has_history:
        return {
            "sku": sku,
            "has_sales_history": False,
            "window_days": window_days,
            "total_window_sales": 0.0,
            "avg_daily_demand": 0.0,
            "std_daily_demand": 0.0,
            "outliers_capped": 0,
            "daily_series": [0.0] * window_days,
            "is_insufficient_data": True,
        }

    daily_series, dates = get_daily_sales_series(
        sku_sales,
        window_days=window_days,
        reference_date=reference_date,
    )

    capped_count = 0
    if apply_cap_outliers:
        daily_series, capped_count = cap_outliers(daily_series)

    total_window_sales = sum(daily_series)
    avg_demand = total_window_sales / float(window_days)

    if len(daily_series) >= 2:
        std_demand = statistics.stdev(daily_series)
    else:
        std_demand = 0.0

    # Insufficient data if no sales at all during the window or history
    is_insufficient = (total_window_sales == 0.0 and not has_history)

    return {
        "sku": sku,
        "has_sales_history": has_history,
        "window_days": window_days,
        "total_window_sales": total_window_sales,
        "avg_daily_demand": avg_demand,
        "std_daily_demand": std_demand,
        "outliers_capped": capped_count,
        "daily_series": daily_series,
        "is_insufficient_data": is_insufficient,
    }


def compute_all_forecasts(
    skus: List[str],
    sales_records: List[Dict[str, Any]],
    window_days: int = 30,
    reference_date: Optional[datetime.date] = None,
    apply_cap_outliers: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Compute forecasts for all requested SKUs."""
    # Find dataset reference date if not provided
    if reference_date is None and sales_records:
        reference_date = max(r["date"] for r in sales_records)

    forecasts: Dict[str, Dict[str, Any]] = {}
    for sku in skus:
        forecasts[sku] = compute_sku_forecast(
            sku=sku,
            sales_records=sales_records,
            window_days=window_days,
            reference_date=reference_date,
            apply_cap_outliers=apply_cap_outliers,
        )
    return forecasts
