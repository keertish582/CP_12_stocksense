"""Unit tests for reporting, CSV export, and CLI integration."""

import csv
import subprocess
import sys
import pytest

from report import (
    COLOR_BLUE,
    COLOR_GREEN,
    COLOR_RED,
    COLOR_YELLOW,
    colorize_status,
    export_reorder_list_csv,
    format_table,
    strip_ansi,
)
from stocksense import run_pipeline


def test_ansi_colors_and_no_color():
    assert COLOR_RED in colorize_status("CRITICAL", no_color=False)
    assert COLOR_YELLOW in colorize_status("REORDER", no_color=False)
    assert COLOR_GREEN in colorize_status("OK", no_color=False)
    assert COLOR_BLUE in colorize_status("OVERSTOCK", no_color=False)

    assert "\033" not in colorize_status("CRITICAL", no_color=True)
    assert "\033" not in colorize_status("REORDER", no_color=True)
    assert "\033" not in colorize_status("OK", no_color=True)
    assert "\033" not in colorize_status("OVERSTOCK", no_color=True)


def test_table_formatting_and_summary_line():
    results = [
        {
            "sku": "SKU-CRIT",
            "name": "Critical Item",
            "current_stock": 0,
            "avg_daily_demand": 5.0,
            "rop": 40.0,
            "days_of_cover": 0.0,
            "status": "CRITICAL",
            "order_qty": 100,
            "urgency_rank": 1,
        },
        {
            "sku": "SKU-REORD",
            "name": "Reorder Item",
            "current_stock": 15,
            "avg_daily_demand": 2.0,
            "rop": 25.0,
            "days_of_cover": 7.5,
            "status": "REORDER",
            "order_qty": 50,
            "urgency_rank": 2,
        },
        {
            "sku": "SKU-OK",
            "name": "OK Item",
            "current_stock": 80,
            "avg_daily_demand": 2.0,
            "rop": 25.0,
            "days_of_cover": 40.0,
            "status": "OK",
            "order_qty": 0,
            "urgency_rank": 3,
        },
        {
            "sku": "SKU-OVER",
            "name": "Overstocked Item",
            "current_stock": 500,
            "avg_daily_demand": 1.0,
            "rop": 15.0,
            "days_of_cover": 500.0,
            "status": "OVERSTOCK",
            "order_qty": 0,
            "urgency_rank": 4,
        },
    ]

    table_output = format_table(results, no_color=True)
    lines = table_output.split("\n")

    # Header check
    assert "SKU" in lines[0]
    assert "Item" in lines[0]
    assert "Stock" in lines[0]
    assert "AvgDemand" in lines[0]
    assert "ROP" in lines[0]
    assert "Cover(d)" in lines[0]
    assert "Status" in lines[0]
    assert "Order Qty" in lines[0]

    # Verify sorting order: CRITICAL before REORDER before OK before OVERSTOCK
    status_order = []
    for line in lines[2:-2]:
        for st in ("CRITICAL", "REORDER", "OK", "OVERSTOCK"):
            if st in line:
                status_order.append(st)
                break
    assert status_order == ["CRITICAL", "REORDER", "OK", "OVERSTOCK"]

    # Verify summary line format exactly
    summary_line = lines[-1]
    assert summary_line == "Summary: 1 critical, 1 reorder, 1 ok, 1 overstock"


def test_export_reorder_list_csv_filters_correctly(tmp_path):
    results = [
        {"sku": "SKU-1", "name": "Crit", "supplier": "S1", "current_stock": 0, "lead_time_days": 7, "avg_daily_demand": 4.0, "rop": 30.0, "days_of_cover": 0.0, "status": "CRITICAL", "order_qty": 100, "unit_cost": 10.0, "urgency_rank": 1},
        {"sku": "SKU-2", "name": "Reord", "supplier": "S2", "current_stock": 10, "lead_time_days": 7, "avg_daily_demand": 2.0, "rop": 20.0, "days_of_cover": 5.0, "status": "REORDER", "order_qty": 50, "unit_cost": 20.0, "urgency_rank": 2},
        {"sku": "SKU-3", "name": "OkItem", "supplier": "S3", "current_stock": 100, "lead_time_days": 7, "avg_daily_demand": 2.0, "rop": 20.0, "days_of_cover": 50.0, "status": "OK", "order_qty": 0, "unit_cost": 30.0, "urgency_rank": 3},
        {"sku": "SKU-4", "name": "Over", "supplier": "S4", "current_stock": 800, "lead_time_days": 7, "avg_daily_demand": 1.0, "rop": 15.0, "days_of_cover": 800.0, "status": "OVERSTOCK", "order_qty": 0, "unit_cost": 5.0, "urgency_rank": 4},
    ]

    out_csv = tmp_path / "export_test.csv"
    count = export_reorder_list_csv(results, str(out_csv))

    assert count == 2  # Only CRITICAL and REORDER

    with open(out_csv, mode="r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 2
        skus_in_csv = [row["sku"] for row in reader]
        assert "SKU-1" in skus_in_csv
        assert "SKU-2" in skus_in_csv
        assert "SKU-3" not in skus_in_csv
        assert "SKU-4" not in skus_in_csv


def test_cli_execution_with_sample_data():
    """Run CLI against sample dataset and verify output and returncode."""
    cmd = [
        sys.executable,
        "stocksense.py",
        "--products",
        "data/products.csv",
        "--sales",
        "data/sales.csv",
        "--window",
        "30",
        "--no-color",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    stdout = res.stdout
    assert "SKU" in stdout
    assert "Summary:" in stdout
    assert "critical" in stdout
    assert "reorder" in stdout
    assert "ok" in stdout
    assert "overstock" in stdout
