#!/usr/bin/env python3
"""
StockSense: Predictive Inventory Reorder Engine (CP-012)
Command-line interface and interactive menu.
"""

import argparse
import datetime
import os
import sys
from typing import Any, Dict, List, Optional

from forecast import compute_all_forecasts, compute_sku_forecast
from loader import (
    ValidationError,
    parse_date,
    validate_and_load_products,
    validate_and_load_sales,
)
from report import colorize_status, export_reorder_list_csv, format_table
from rules import evaluate_inventory_item


def run_pipeline(
    products: Dict[str, Dict[str, Any]],
    sales: List[Dict[str, Any]],
    window_days: int = 30,
    z_score: float = 1.65,
    order_cost: float = 500.0,
    holding_cost_pct: float = 0.20,
    apply_cap_outliers: bool = False,
    reference_date: Optional[datetime.date] = None,
) -> List[Dict[str, Any]]:
    """Execute demand forecasting and inventory evaluation for all products."""
    skus = list(products.keys())
    forecasts = compute_all_forecasts(
        skus=skus,
        sales_records=sales,
        window_days=window_days,
        reference_date=reference_date,
        apply_cap_outliers=apply_cap_outliers,
    )

    results = []
    for sku, product in products.items():
        fc = forecasts[sku]
        item_eval = evaluate_inventory_item(
            product=product,
            forecast=fc,
            z_score=z_score,
            order_cost=order_cost,
            holding_cost_pct=holding_cost_pct,
        )
        results.append(item_eval)

    return results


def show_sku_forecast_details(
    sku: str,
    product: Dict[str, Any],
    sales: List[Dict[str, Any]],
    window_days: int = 30,
    z_score: float = 1.65,
    order_cost: float = 500.0,
    holding_cost_pct: float = 0.20,
    apply_cap_outliers: bool = False,
    reference_date: Optional[datetime.date] = None,
    no_color: bool = False,
) -> None:
    """Print an in-depth forecast breakdown for a specific SKU."""
    fc = compute_sku_forecast(
        sku=sku,
        sales_records=sales,
        window_days=window_days,
        reference_date=reference_date,
        apply_cap_outliers=apply_cap_outliers,
    )

    ev = evaluate_inventory_item(
        product=product,
        forecast=fc,
        z_score=z_score,
        order_cost=order_cost,
        holding_cost_pct=holding_cost_pct,
    )

    print("\n" + "=" * 60)
    print(f"FORECAST DETAIL: {sku} - {product['name']}")
    print("=" * 60)
    print(f"Supplier:           {product['supplier']}")
    print(f"Unit Cost:          ${product['unit_cost']:.2f}")
    print(f"Min Order Qty:      {product['min_order_qty']}")
    print(f"Lead Time:          {product['lead_time_days']} days")
    print(f"Current Stock:      {product['current_stock']} units")
    print("-" * 60)

    if fc["is_insufficient_data"] or not fc["has_sales_history"]:
        print("Demand Forecast:    insufficient data (no sales history found)")
    else:
        print(f"Window:             Last {window_days} days")
        print(f"Total Window Sales: {fc['total_window_sales']:.1f} units")
        print(f"Avg Daily Demand:   {fc['avg_daily_demand']:.2f} units/day")
        print(f"Std Dev (Daily):    {fc['std_daily_demand']:.2f}")
        if apply_cap_outliers:
            print(f"Outliers Capped:    {fc['outliers_capped']} day(s)")

    print("-" * 60)
    print(f"Safety Stock (Z={z_score}): {ev['safety_stock']:.2f} units")
    print(f"Reorder Point (ROP):       {ev['rop']:.2f} units")

    doc = ev["days_of_cover"]
    doc_str = f"{doc:.1f} days" if doc is not None else "N/A (insufficient data)"
    print(f"Days of Cover:             {doc_str}")

    status_colored = colorize_status(ev["status"], no_color=no_color)
    print(f"Urgency Status:            {status_colored}")
    print(f"EOQ (Lot Size):            {ev['eoq']} units")
    print(f"Recommended Order Qty:     {ev['order_qty']} units")
    print("=" * 60 + "\n")


def interactive_menu(
    products: Dict[str, Dict[str, Any]],
    sales: List[Dict[str, Any]],
    window_days: int = 30,
    z_score: float = 1.65,
    order_cost: float = 500.0,
    holding_cost_pct: float = 0.20,
    apply_cap_outliers: bool = False,
    no_color: bool = False,
) -> None:
    """Run interactive terminal menu loop."""
    while True:
        print("\n=== StockSense Reorder Engine Menu ===")
        print("1. Show reorder report")
        print("2. Add sales record")
        print("3. Update stock")
        print("4. Show item forecast (by SKU)")
        print("5. Export reorder list")
        print("6. Exit")

        try:
            choice = input("Enter choice (1-6): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting StockSense.")
            break

        if choice == "1":
            results = run_pipeline(
                products=products,
                sales=sales,
                window_days=window_days,
                z_score=z_score,
                order_cost=order_cost,
                holding_cost_pct=holding_cost_pct,
                apply_cap_outliers=apply_cap_outliers,
            )
            print("\n" + format_table(results, no_color=no_color) + "\n")

        elif choice == "2":
            sku_input = input("Enter SKU: ").strip()
            if sku_input not in products:
                print(f"Error: SKU '{sku_input}' not found in products catalog.")
                continue

            date_input = input("Enter date (YYYY-MM-DD) [Leave blank for today]: ").strip()
            if not date_input:
                record_date = datetime.date.today()
            else:
                try:
                    record_date = parse_date(date_input)
                except ValidationError as e:
                    print(f"Error: {e}")
                    continue

            qty_input = input("Enter quantity sold: ").strip()
            try:
                qty_sold = float(qty_input)
                if qty_sold < 0:
                    print("Error: Quantity sold cannot be negative.")
                    continue
            except ValueError:
                print("Error: Quantity sold must be a number.")
                continue

            sales.append({"sku": sku_input, "date": record_date, "qty_sold": qty_sold})
            print(f"Success: Added sale of {qty_sold} units for {sku_input} on {record_date}.")

        elif choice == "3":
            sku_input = input("Enter SKU: ").strip()
            if sku_input not in products:
                print(f"Error: SKU '{sku_input}' not found in products catalog.")
                continue

            stock_input = input(f"Enter new current stock for {sku_input} (current: {products[sku_input]['current_stock']}): ").strip()
            try:
                new_stock = int(float(stock_input))
                if new_stock < 0:
                    print("Error: Stock cannot be negative.")
                    continue
            except ValueError:
                print("Error: Stock must be a valid integer.")
                continue

            products[sku_input]["current_stock"] = new_stock
            print(f"Success: Updated stock for {sku_input} to {new_stock}.")

        elif choice == "4":
            sku_input = input("Enter SKU to forecast: ").strip()
            if sku_input not in products:
                print(f"Error: SKU '{sku_input}' not found.")
                continue

            show_sku_forecast_details(
                sku=sku_input,
                product=products[sku_input],
                sales=sales,
                window_days=window_days,
                z_score=z_score,
                order_cost=order_cost,
                holding_cost_pct=holding_cost_pct,
                apply_cap_outliers=apply_cap_outliers,
                no_color=no_color,
            )

        elif choice == "5":
            out_file = input("Enter export CSV filename [reorder_list.csv]: ").strip()
            if not out_file:
                out_file = "reorder_list.csv"

            results = run_pipeline(
                products=products,
                sales=sales,
                window_days=window_days,
                z_score=z_score,
                order_cost=order_cost,
                holding_cost_pct=holding_cost_pct,
                apply_cap_outliers=apply_cap_outliers,
            )
            count = export_reorder_list_csv(results, out_file)
            print(f"Success: Exported {count} items (CRITICAL & REORDER) to '{out_file}'.")

        elif choice == "6":
            print("Exiting StockSense. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 6.")


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="stocksense",
        description="StockSense: Predictive Inventory Reorder Engine",
    )
    parser.add_argument(
        "--products",
        required=True,
        help="Path to products file (CSV or JSON)",
    )
    parser.add_argument(
        "--sales",
        required=True,
        help="Path to sales history file (CSV or JSON)",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help="Moving average window in days (default: 30)",
    )
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        help="Path to export reorder list CSV (CRITICAL and REORDER items only)",
    )
    parser.add_argument(
        "--menu",
        action="store_true",
        help="Launch interactive terminal menu",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output in terminal",
    )
    parser.add_argument(
        "--cap-outliers",
        action="store_true",
        help="Cap sales outliers at mean + 3 * std_dev",
    )
    parser.add_argument(
        "--z-score",
        type=float,
        default=1.65,
        help="Service level Z-score (default: 1.65 for 95%%)",
    )
    parser.add_argument(
        "--order-cost",
        type=float,
        default=500.0,
        help="Fixed cost per order (default: 500.0)",
    )
    parser.add_argument(
        "--holding-cost-pct",
        type=float,
        default=0.20,
        help="Annual holding cost percentage of unit cost (default: 0.20)",
    )
    parser.add_argument(
        "--reference-date",
        type=str,
        default=None,
        help="Anchor date for moving window (YYYY-MM-DD, defaults to latest sale date)",
    )
    return parser


def main() -> int:
    """Entry point for CLI."""
    parser = build_parser()
    args = parser.parse_args()

    ref_date = None
    if args.reference_date:
        try:
            ref_date = parse_date(args.reference_date)
        except ValidationError as e:
            sys.stderr.write(f"Error: {e}\n")
            return 1

    if args.window <= 0:
        sys.stderr.write(f"Error: --window must be a positive integer, got {args.window}\n")
        return 1

    try:
        products = validate_and_load_products(args.products)
        sales = validate_and_load_sales(args.sales, valid_skus=set(products.keys()))
    except (ValidationError, FileNotFoundError) as err:
        sys.stderr.write(f"Validation Error: {err}\n")
        return 1
    except Exception as ex:
        sys.stderr.write(f"Unexpected Error loading data: {ex}\n")
        return 1

    if args.menu:
        interactive_menu(
            products=products,
            sales=sales,
            window_days=args.window,
            z_score=args.z_score,
            order_cost=args.order_cost,
            holding_cost_pct=args.holding_cost_pct,
            apply_cap_outliers=args.cap_outliers,
            no_color=args.no_color,
        )
        return 0

    results = run_pipeline(
        products=products,
        sales=sales,
        window_days=args.window,
        z_score=args.z_score,
        order_cost=args.order_cost,
        holding_cost_pct=args.holding_cost_pct,
        apply_cap_outliers=args.cap_outliers,
        reference_date=ref_date,
    )

    print(format_table(results, no_color=args.no_color))

    if args.export:
        count = export_reorder_list_csv(results, args.export)
        print(f"\nExported {count} items to '{args.export}'.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
