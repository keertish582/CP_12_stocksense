"""Unit tests for forecasting engine: moving average, std dev, outlier capping, zero demand."""

import datetime
import math
import statistics
import pytest

from forecast import (
    cap_outliers,
    compute_all_forecasts,
    compute_sku_forecast,
    get_daily_sales_series,
)


def test_hand_calculated_moving_average():
    """
    Test moving average with explicit hand-calculated numbers.
    Window = 5 days.
    Day 1: 10
    Day 2: 0 (missing day)
    Day 3: 5
    Day 4: 0 (missing day)
    Day 5: 15
    Total sales = 10 + 0 + 5 + 0 + 15 = 30.
    Average daily demand = 30 / 5 = 6.0.
    """
    ref_date = datetime.date(2026, 1, 5)
    sales = [
        {"sku": "SKU-A", "date": datetime.date(2026, 1, 1), "qty_sold": 10},
        {"sku": "SKU-A", "date": datetime.date(2026, 1, 3), "qty_sold": 5},
        {"sku": "SKU-A", "date": datetime.date(2026, 1, 5), "qty_sold": 15},
    ]

    series, dates = get_daily_sales_series(sales, window_days=5, reference_date=ref_date)
    assert series == [10.0, 0.0, 5.0, 0.0, 15.0]
    assert len(dates) == 5

    fc = compute_sku_forecast("SKU-A", sales, window_days=5, reference_date=ref_date)
    assert fc["total_window_sales"] == 30.0
    assert fc["avg_daily_demand"] == 6.0

    # Hand-calculated sample standard deviation for [10, 0, 5, 0, 15]
    # Mean = 6.0
    # Squared diffs: (10-6)^2=16, (0-6)^2=36, (5-6)^2=1, (0-6)^2=36, (15-6)^2=81
    # Sum of sq diffs = 170
    # Variance = 170 / (5 - 1) = 42.5
    # Stdev = sqrt(42.5) ~= 6.5192024
    expected_stdev = math.sqrt(42.5)
    assert math.isclose(fc["std_daily_demand"], expected_stdev, rel_tol=1e-5)


def test_missing_days_count_as_zero():
    """Days within window with no recorded sales must count as 0."""
    ref_date = datetime.date(2026, 2, 10)
    sales = [
        {"sku": "SKU-B", "date": datetime.date(2026, 2, 10), "qty_sold": 20},
    ]
    # Window of 4 days: 2026-02-07, 08, 09, 10
    series, _ = get_daily_sales_series(sales, window_days=4, reference_date=ref_date)
    assert series == [0.0, 0.0, 0.0, 20.0]
    fc = compute_sku_forecast("SKU-B", sales, window_days=4, reference_date=ref_date)
    assert fc["avg_daily_demand"] == 5.0  # 20 / 4


def test_outlier_capping():
    """Test that outliers exceeding mean + 3*std are capped properly."""
    # Series: 10 days of 2 units, then one day with 100 units
    daily_sales = [2.0] * 10 + [100.0]
    mean_val = statistics.mean(daily_sales)
    std_val = statistics.stdev(daily_sales)
    threshold = mean_val + 3.0 * std_val

    capped_series, capped_count = cap_outliers(daily_sales)
    assert capped_count == 1
    assert math.isclose(capped_series[-1], threshold, rel_tol=1e-5)
    assert all(val <= threshold for val in capped_series)


def test_zero_demand():
    """When sales records exist but all quantities in the window are zero."""
    ref_date = datetime.date(2026, 1, 3)
    sales = [
        {"sku": "SKU-ZERO", "date": datetime.date(2026, 1, 1), "qty_sold": 0},
        {"sku": "SKU-ZERO", "date": datetime.date(2026, 1, 2), "qty_sold": 0},
    ]
    fc = compute_sku_forecast("SKU-ZERO", sales, window_days=3, reference_date=ref_date)
    assert fc["avg_daily_demand"] == 0.0
    assert fc["std_daily_demand"] == 0.0
    assert fc["total_window_sales"] == 0.0


def test_new_product_no_sales_history():
    """A new product with no sales records in sales_history."""
    sales = []
    fc = compute_sku_forecast("SKU-NEW", sales, window_days=30, reference_date=datetime.date(2026, 3, 1))
    assert fc["has_sales_history"] is False
    assert fc["avg_daily_demand"] == 0.0
    assert fc["std_daily_demand"] == 0.0
    assert fc["is_insufficient_data"] is True


def test_compute_all_forecasts():
    """Verify batch forecasting across multiple SKUs."""
    sales = [
        {"sku": "SKU-1", "date": datetime.date(2026, 1, 10), "qty_sold": 5},
        {"sku": "SKU-2", "date": datetime.date(2026, 1, 10), "qty_sold": 10},
    ]
    forecasts = compute_all_forecasts(["SKU-1", "SKU-2", "SKU-EMPTY"], sales, window_days=10)
    assert "SKU-1" in forecasts
    assert "SKU-2" in forecasts
    assert "SKU-EMPTY" in forecasts
    assert forecasts["SKU-EMPTY"]["has_sales_history"] is False
