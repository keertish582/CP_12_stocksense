"""Unit tests for loader module: CSV/JSON auto-detection, schema validation, and edge cases."""

import json
import pytest

from loader import (
    ValidationError,
    load_raw_data,
    validate_and_load_products,
    validate_and_load_sales,
)


def test_missing_sku_in_products(tmp_path):
    csv_file = tmp_path / "products.csv"
    csv_file.write_text("sku,name,current_stock,supplier,lead_time_days,unit_cost,min_order_qty\n,Widget,10,Sup,7,15.0,5\n")
    with pytest.raises(ValidationError, match="Missing required 'sku'"):
        validate_and_load_products(str(csv_file))


def test_duplicate_sku_in_products(tmp_path):
    csv_file = tmp_path / "products.csv"
    content = (
        "sku,name,current_stock,supplier,lead_time_days,unit_cost,min_order_qty\n"
        "SKU-1,Widget A,10,Sup,7,15.0,5\n"
        "SKU-1,Widget B,20,Sup,7,25.0,5\n"
    )
    csv_file.write_text(content)
    with pytest.raises(ValidationError, match="Duplicate SKU detected: 'SKU-1'"):
        validate_and_load_products(str(csv_file))


def test_negative_current_stock(tmp_path):
    csv_file = tmp_path / "products.csv"
    csv_file.write_text("sku,name,current_stock,supplier,lead_time_days,unit_cost,min_order_qty\nSKU-1,Widget,-5,Sup,7,15.0,5\n")
    with pytest.raises(ValidationError, match="Negative current_stock"):
        validate_and_load_products(str(csv_file))


def test_negative_unit_cost(tmp_path):
    csv_file = tmp_path / "products.csv"
    csv_file.write_text("sku,name,current_stock,supplier,lead_time_days,unit_cost,min_order_qty\nSKU-1,Widget,10,Sup,7,-15.0,5\n")
    with pytest.raises(ValidationError, match="Negative unit_cost"):
        validate_and_load_products(str(csv_file))


def test_non_numeric_stock(tmp_path):
    csv_file = tmp_path / "products.csv"
    csv_file.write_text("sku,name,current_stock,supplier,lead_time_days,unit_cost,min_order_qty\nSKU-1,Widget,INVALID,Sup,7,15.0,5\n")
    with pytest.raises(ValidationError, match="Non-numeric current_stock"):
        validate_and_load_products(str(csv_file))


def test_missing_lead_time_defaults_to_seven(tmp_path, capsys):
    csv_file = tmp_path / "products.csv"
    csv_file.write_text("sku,name,current_stock,supplier,lead_time_days,unit_cost,min_order_qty\nSKU-1,Widget,10,Sup,,15.0,5\n")
    products = validate_and_load_products(str(csv_file))
    assert products["SKU-1"]["lead_time_days"] == 7
    captured = capsys.readouterr()
    assert "Defaulting to 7 days" in captured.err


def test_bad_date_format_in_sales(tmp_path):
    csv_file = tmp_path / "sales.csv"
    csv_file.write_text("sku,date,qty_sold\nSKU-1,01-15-2026,10\n")
    with pytest.raises(ValidationError, match="Invalid date format"):
        validate_and_load_sales(str(csv_file))


def test_negative_qty_sold_in_sales(tmp_path):
    csv_file = tmp_path / "sales.csv"
    csv_file.write_text("sku,date,qty_sold\nSKU-1,2026-01-15,-3\n")
    with pytest.raises(ValidationError, match="Negative qty_sold"):
        validate_and_load_sales(str(csv_file))


def test_unknown_sku_in_sales_is_skipped(tmp_path, capsys):
    csv_file = tmp_path / "sales.csv"
    csv_file.write_text("sku,date,qty_sold\nSKU-KNOWN,2026-01-15,5\nSKU-UNKNOWN,2026-01-15,10\n")
    sales = validate_and_load_sales(str(csv_file), valid_skus={"SKU-KNOWN"})
    assert len(sales) == 1
    assert sales[0]["sku"] == "SKU-KNOWN"
    captured = capsys.readouterr()
    assert "Sales record for unknown SKU 'SKU-UNKNOWN'. Skipping." in captured.err


def test_json_product_and_sales_loading(tmp_path):
    prod_json = tmp_path / "products.json"
    prod_data = [
        {
            "sku": "J-01",
            "name": "JSON Gadget",
            "current_stock": 25,
            "supplier": "JSON Supplier",
            "lead_time_days": 10,
            "unit_cost": 20.0,
            "min_order_qty": 5,
        }
    ]
    prod_json.write_text(json.dumps(prod_data))
    products = validate_and_load_products(str(prod_json))
    assert "J-01" in products
    assert products["J-01"]["current_stock"] == 25

    sales_json = tmp_path / "sales.json"
    sales_data = [{"sku": "J-01", "date": "2026-02-01", "qty_sold": 4}]
    sales_json.write_text(json.dumps(sales_data))
    sales = validate_and_load_sales(str(sales_json), valid_skus={"J-01"})
    assert len(sales) == 1
    assert sales[0]["qty_sold"] == 4.0
