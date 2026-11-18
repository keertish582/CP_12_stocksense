"""Script to generate sample data for StockSense."""

import csv
import datetime
import os
import random


def generate_sample_data():
    random.seed(42)  # Deterministic generation
    os.makedirs("data", exist_ok=True)

    products = [
        {
            "sku": "SKU-001",
            "name": "Ergonomic Wireless Mouse",
            "current_stock": 0,  # Zero-stock item -> CRITICAL
            "supplier": "TechGear Ltd",
            "lead_time_days": 7,
            "unit_cost": 25.00,
            "min_order_qty": 20,
        },
        {
            "sku": "SKU-002",
            "name": "Mechanical RGB Keyboard",
            "current_stock": 12,  # Cover ~ 3 days < lead time 14 -> CRITICAL
            "supplier": "KeyWorks Co",
            "lead_time_days": 14,
            "unit_cost": 65.00,
            "min_order_qty": 10,
        },
        {
            "sku": "SKU-003",
            "name": "Ultra-Wide Gaming Monitor",
            "current_stock": 20,  # stock <= ROP -> REORDER
            "supplier": "VisionTech",
            "lead_time_days": 10,
            "unit_cost": 320.00,
            "min_order_qty": 5,
        },
        {
            "sku": "SKU-004",
            "name": "USB-C Multiport Dock",
            "current_stock": 35,  # stock <= ROP -> REORDER
            "supplier": "ConnectPro",
            "lead_time_days": 8,
            "unit_cost": 45.00,
            "min_order_qty": 25,
        },
        {
            "sku": "SKU-005",
            "name": "Noise-Cancelling Headphones",
            "current_stock": 28,  # stock <= ROP -> REORDER
            "supplier": "AcousticLab",
            "lead_time_days": 12,
            "unit_cost": 110.00,
            "min_order_qty": 15,
        },
        {
            "sku": "SKU-006",
            "name": "Anodized Aluminum Laptop Stand",
            "current_stock": 85,  # cover ~ 56d -> OK
            "supplier": "DeskMasters",
            "lead_time_days": 10,
            "unit_cost": 30.00,
            "min_order_qty": 20,
        },
        {
            "sku": "SKU-007",
            "name": "1080p HD Streaming Webcam",
            "current_stock": 120,  # cover ~ 60d -> OK
            "supplier": "VisionTech",
            "lead_time_days": 7,
            "unit_cost": 40.00,
            "min_order_qty": 25,
        },
        {
            "sku": "SKU-008",
            "name": "Braided HDMI 2.1 Cable 2m",
            "current_stock": 650,  # cover > 90d -> OVERSTOCK
            "supplier": "ConnectPro",
            "lead_time_days": 5,
            "unit_cost": 8.50,
            "min_order_qty": 50,
        },
        {
            "sku": "SKU-009",
            "name": "Fast Qi Wireless Charger",
            "current_stock": 75,  # cover ~ 75d -> OK
            "supplier": "VoltCore",
            "lead_time_days": 10,
            "unit_cost": 18.00,
            "min_order_qty": 20,
        },
        {
            "sku": "SKU-010",
            "name": "Bluetooth Conference Speakerphone",
            "current_stock": 18,  # stock <= ROP -> REORDER
            "supplier": "AcousticLab",
            "lead_time_days": 10,
            "unit_cost": 85.00,
            "min_order_qty": 10,
        },
        {
            "sku": "SKU-011",
            "name": "Microfiber Screen Cleaning Cloths",
            "current_stock": 1500,  # cover > 90d -> OVERSTOCK
            "supplier": "CleanTech",
            "lead_time_days": 7,
            "unit_cost": 2.50,
            "min_order_qty": 100,
        },
        {
            "sku": "SKU-012",
            "name": "Smart IoT Power Strip 6-Outlet",
            "current_stock": 25,  # New product, no sales history!
            "supplier": "VoltCore",
            "lead_time_days": 14,
            "unit_cost": 35.00,
            "min_order_qty": 15,
        },
    ]

    # Write products.csv
    with open("data/products.csv", mode="w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "sku",
            "name",
            "current_stock",
            "supplier",
            "lead_time_days",
            "unit_cost",
            "min_order_qty",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(products)

    # Generate 60 days of sales history (2026-01-01 to 2026-03-01)
    start_date = datetime.date(2026, 1, 1)
    days_count = 60

    # Base daily rates for each active SKU
    base_demand = {
        "SKU-001": 5.0,  # Fast mover
        "SKU-002": 4.0,  # Fast mover
        "SKU-003": 2.0,  # Steady
        "SKU-004": 3.0,  # Steady
        "SKU-005": 2.0,  # Steady
        "SKU-006": 1.5,  # Moderate
        "SKU-007": 2.0,  # Steady
        "SKU-008": 1.2,  # Slow
        "SKU-009": 1.0,  # Slow
        "SKU-010": 1.8,  # Steady
        "SKU-011": 3.0,  # Slow relative to huge 1500 stock
        # SKU-012 has NO sales records (new product)
    }

    sales_rows = []
    for day_offset in range(days_count):
        current_date = start_date + datetime.timedelta(days=day_offset)
        date_str = current_date.strftime("%Y-%m-%d")

        for sku, rate in base_demand.items():
            # Poisson-like or binomial simulation with occasional zero-sale days
            if random.random() < 0.20:
                qty = 0
            else:
                variation = random.choice([-1, 0, 0, 1, 2])
                qty = max(1, int(round(rate + variation)))

            # Only record if qty > 0 (some days have no record to test 0-sale handling)
            if qty > 0:
                sales_rows.append({"sku": sku, "date": date_str, "qty_sold": qty})

    # Add one intentional outlier to test --cap-outliers (e.g. SKU-001 had an unusually large bulk order of 25)
    sales_rows.append({"sku": "SKU-001", "date": "2026-02-15", "qty_sold": 25})

    with open("data/sales.csv", mode="w", newline="", encoding="utf-8") as f:
        fieldnames = ["sku", "date", "qty_sold"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sales_rows)

    print(f"Generated {len(products)} products and {len(sales_rows)} sales records.")


if __name__ == "__main__":
    generate_sample_data()
