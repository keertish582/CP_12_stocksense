"""Data loader and validator for products and sales history (CSV and JSON)."""

import csv
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


class ValidationError(Exception):
    """Raised when input data fails schema or domain validation."""
    pass


def parse_date(date_str: str) -> datetime.date:
    """Parse date string formatted as YYYY-MM-DD."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except Exception:
        raise ValidationError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.")


def load_raw_data(file_path: str) -> List[Dict[str, Any]]:
    """Load records from a CSV or JSON file based on file extension."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: '{file_path}'")

    _, ext = os.path.splitext(file_path.lower())
    if ext == ".csv":
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return []
            # Strip whitespace from keys
            cleaned_rows = []
            for row in reader:
                cleaned_rows.append({k.strip(): (v.strip() if v is not None else "") for k, v in row.items() if k})
            return cleaned_rows
    elif ext == ".json":
        with open(file_path, mode="r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # If wrapped under a key like {"products": [...]} or {"sales": [...]}
                for key in ("products", "sales", "sales_history", "items", "data"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
                raise ValidationError(f"JSON object in '{file_path}' must contain a list of records.")
            else:
                raise ValidationError(f"Top-level JSON in '{file_path}' must be a list or object.")
    else:
        raise ValidationError(f"Unsupported file format '{ext}' for file '{file_path}'. Must be .csv or .json.")


def validate_and_load_products(
    file_path: str,
    default_lead_time: int = 7
) -> Dict[str, Dict[str, Any]]:
    """
    Validate and return product catalog mapped by SKU.

    Required fields: sku, name, current_stock, supplier, lead_time_days, unit_cost, min_order_qty.
    Flags:
      - Missing SKU
      - Duplicate SKUs
      - Negative stock, cost, or min_order_qty
      - Non-numeric fields
      - Missing lead_time_days (defaults to 7 with warning)
    """
    raw_records = load_raw_data(file_path)
    if not raw_records:
        raise ValidationError(f"Product file '{file_path}' is empty or contains no valid rows.")

    products: Dict[str, Dict[str, Any]] = {}
    seen_skus: Set[str] = set()

    for row_idx, row in enumerate(raw_records, start=1):
        sku = str(row.get("sku", "")).strip()
        if not sku:
            raise ValidationError(f"Row {row_idx}: Missing required 'sku' field in products.")

        if sku in seen_skus:
            raise ValidationError(f"Row {row_idx}: Duplicate SKU detected: '{sku}'.")
        seen_skus.add(sku)

        name = str(row.get("name", "")).strip() or sku
        supplier = str(row.get("supplier", "")).strip() or "Unknown"

        # Current stock
        stock_val = row.get("current_stock")
        if stock_val is None or str(stock_val).strip() == "":
            raise ValidationError(f"Row {row_idx} (SKU: {sku}): Missing 'current_stock'.")
        try:
            current_stock = int(float(stock_val))
            if current_stock < 0:
                raise ValidationError(f"Row {row_idx} (SKU: {sku}): Negative current_stock '{current_stock}'.")
        except ValueError:
            raise ValidationError(f"Row {row_idx} (SKU: {sku}): Non-numeric current_stock '{stock_val}'.")

        # Lead time days
        lead_time_val = row.get("lead_time_days")
        if lead_time_val is None or str(lead_time_val).strip() == "":
            sys.stderr.write(f"WARNING: Row {row_idx} (SKU: {sku}): Missing 'lead_time_days'. Defaulting to {default_lead_time} days.\n")
            lead_time_days = default_lead_time
        else:
            try:
                lead_time_days = int(float(lead_time_val))
                if lead_time_days <= 0:
                    sys.stderr.write(f"WARNING: Row {row_idx} (SKU: {sku}): Non-positive lead_time_days '{lead_time_days}'. Defaulting to {default_lead_time} days.\n")
                    lead_time_days = default_lead_time
            except ValueError:
                sys.stderr.write(f"WARNING: Row {row_idx} (SKU: {sku}): Non-numeric lead_time_days '{lead_time_val}'. Defaulting to {default_lead_time} days.\n")
                lead_time_days = default_lead_time

        # Unit cost
        cost_val = row.get("unit_cost")
        if cost_val is None or str(cost_val).strip() == "":
            raise ValidationError(f"Row {row_idx} (SKU: {sku}): Missing 'unit_cost'.")
        try:
            unit_cost = float(cost_val)
            if unit_cost < 0:
                raise ValidationError(f"Row {row_idx} (SKU: {sku}): Negative unit_cost '{unit_cost}'.")
        except ValueError:
            raise ValidationError(f"Row {row_idx} (SKU: {sku}): Non-numeric unit_cost '{cost_val}'.")

        # Min order qty
        moq_val = row.get("min_order_qty")
        if moq_val is None or str(moq_val).strip() == "":
            min_order_qty = 1
        else:
            try:
                min_order_qty = int(float(moq_val))
                if min_order_qty <= 0:
                    raise ValidationError(f"Row {row_idx} (SKU: {sku}): min_order_qty must be >= 1, got '{min_order_qty}'.")
            except ValueError:
                raise ValidationError(f"Row {row_idx} (SKU: {sku}): Non-numeric min_order_qty '{moq_val}'.")

        products[sku] = {
            "sku": sku,
            "name": name,
            "current_stock": current_stock,
            "supplier": supplier,
            "lead_time_days": lead_time_days,
            "unit_cost": unit_cost,
            "min_order_qty": min_order_qty,
        }

    return products


def validate_and_load_sales(
    file_path: str,
    valid_skus: Optional[Set[str]] = None
) -> List[Dict[str, Any]]:
    """
    Validate and return sales history records.

    Required fields: sku, date (YYYY-MM-DD), qty_sold.
    Flags:
      - Missing SKU or date
      - Invalid dates
      - Negative or non-numeric qty_sold
      - Unknown SKUs (warn and skip)
    """
    raw_records = load_raw_data(file_path)
    sales: List[Dict[str, Any]] = []

    for row_idx, row in enumerate(raw_records, start=1):
        sku = str(row.get("sku", "")).strip()
        if not sku:
            raise ValidationError(f"Row {row_idx}: Missing 'sku' in sales history.")

        if valid_skus is not None and sku not in valid_skus:
            sys.stderr.write(f"WARNING: Row {row_idx}: Sales record for unknown SKU '{sku}'. Skipping.\n")
            continue

        date_val = row.get("date")
        if not date_val:
            raise ValidationError(f"Row {row_idx} (SKU: {sku}): Missing 'date' in sales history.")
        parsed_dt = parse_date(str(date_val))

        qty_val = row.get("qty_sold")
        if qty_val is None or str(qty_val).strip() == "":
            raise ValidationError(f"Row {row_idx} (SKU: {sku}): Missing 'qty_sold'.")
        try:
            qty_sold = float(qty_val)
            if qty_sold < 0:
                raise ValidationError(f"Row {row_idx} (SKU: {sku}): Negative qty_sold '{qty_sold}'.")
        except ValueError:
            raise ValidationError(f"Row {row_idx} (SKU: {sku}): Non-numeric qty_sold '{qty_val}'.")

        sales.append({
            "sku": sku,
            "date": parsed_dt,
            "qty_sold": qty_sold,
        })

    return sales
