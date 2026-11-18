"""Reporting module: aligned terminal table, ANSI color formatting, and CSV export."""

import csv
import re
from typing import Any, Dict, List, Optional


# ANSI color codes
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_GREEN = "\033[92m"
COLOR_BLUE = "\033[94m"
COLOR_RESET = "\033[0m"

STATUS_COLORS = {
    "CRITICAL": COLOR_RED,
    "REORDER": COLOR_YELLOW,
    "OK": COLOR_GREEN,
    "OVERSTOCK": COLOR_BLUE,
}


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences to compute visual string length."""
    ansi_regex = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_regex.sub("", text)


def colorize_status(status: str, no_color: bool = False) -> str:
    """Apply ANSI color to status string unless no_color is True."""
    if no_color:
        return status
    color = STATUS_COLORS.get(status.upper(), "")
    if color:
        return f"{color}{status}{COLOR_RESET}"
    return status


def sort_evaluation_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort by urgency (CRITICAL, REORDER, OK, OVERSTOCK),
    then by days_of_cover ascending (None/inf sorted last), then SKU.
    """
    def sort_key(item: Dict[str, Any]):
        urgency = item.get("urgency_rank", 99)
        doc = item.get("days_of_cover")
        doc_val = doc if doc is not None else float("inf")
        return (urgency, doc_val, item.get("sku", ""))

    return sorted(results, key=sort_key)


def format_table(results: List[Dict[str, Any]], no_color: bool = False) -> str:
    """
    Format evaluation results into an aligned terminal table:
    SKU | Item | Stock | AvgDemand | ROP | Cover(d) | Status | Order Qty
    """
    sorted_items = sort_evaluation_results(results)

    # Column headers
    headers = ["SKU", "Item", "Stock", "AvgDemand", "ROP", "Cover(d)", "Status", "Order Qty"]

    rows_data: List[List[str]] = []
    colored_status_list: List[str] = []

    for item in sorted_items:
        sku = str(item["sku"])
        name = str(item["name"])
        stock = str(item["current_stock"])
        avg_demand = f"{item['avg_daily_demand']:.2f}"
        rop = f"{item['rop']:.1f}"

        doc = item["days_of_cover"]
        if doc is None:
            cover_str = "N/A"
        elif doc >= 999.0:
            cover_str = ">999"
        else:
            cover_str = f"{doc:.1f}"

        status_raw = item["status"]
        colored_status = colorize_status(status_raw, no_color=no_color)
        colored_status_list.append(colored_status)

        order_qty = str(item["order_qty"])

        rows_data.append([sku, name, stock, avg_demand, rop, cover_str, status_raw, order_qty])

    # Determine visual column widths
    col_widths = [len(h) for h in headers]
    for row in rows_data:
        for idx, cell in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(cell))

    # Build header and separator
    # SKU (left), Item (left), Stock (right), AvgDemand (right), ROP (right), Cover (right), Status (center), Order Qty (right)
    alignments = ["<", "<", ">", ">", ">", ">", "^", ">"]

    def build_row(cells: List[str], raw_cells: Optional[List[str]] = None) -> str:
        parts = []
        for i in range(len(cells)):
            c = cells[i]
            align = alignments[i]
            w = col_widths[i]
            if raw_cells is not None and i == 6:  # Status column with possible ANSI codes
                raw_len = len(raw_cells[i])
                pad_total = max(0, w - raw_len)
                pad_left = pad_total // 2
                pad_right = pad_total - pad_left
                parts.append(" " * pad_left + c + " " * pad_right)
            else:
                parts.append(f"{c:{align}{w}}")
        return " | ".join(parts)

    lines = []
    header_line = build_row(headers)
    separator_line = "-+-".join("-" * w for w in col_widths)

    lines.append(header_line)
    lines.append(separator_line)

    for idx, row in enumerate(rows_data):
        display_cells = list(row)
        display_cells[6] = colored_status_list[idx]
        lines.append(build_row(display_cells, raw_cells=row))

    lines.append(separator_line)

    # Summary line
    summary_counts = {"CRITICAL": 0, "REORDER": 0, "OK": 0, "OVERSTOCK": 0}
    for item in results:
        st = item.get("status", "OK").upper()
        if st in summary_counts:
            summary_counts[st] += 1
        else:
            summary_counts["OK"] += 1

    summary_line = (
        f"Summary: {summary_counts['CRITICAL']} critical, "
        f"{summary_counts['REORDER']} reorder, "
        f"{summary_counts['OK']} ok, "
        f"{summary_counts['OVERSTOCK']} overstock"
    )
    lines.append(summary_line)

    return "\n".join(lines)


def export_reorder_list_csv(
    results: List[Dict[str, Any]],
    output_path: str,
) -> int:
    """
    Export only CRITICAL and REORDER items to CSV.
    Returns the count of exported items.
    """
    reorder_items = [
        item for item in results
        if item.get("status") in ("CRITICAL", "REORDER")
    ]
    reorder_items = sort_evaluation_results(reorder_items)

    fieldnames = [
        "sku",
        "name",
        "supplier",
        "current_stock",
        "lead_time_days",
        "avg_daily_demand",
        "rop",
        "days_of_cover",
        "status",
        "order_qty",
        "unit_cost",
        "total_cost",
    ]

    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in reorder_items:
            unit_cost = float(item.get("unit_cost", 0.0))
            order_qty = int(item.get("order_qty", 0))
            total_cost = round(unit_cost * order_qty, 2)
            doc = item.get("days_of_cover")
            doc_str = f"{doc:.2f}" if doc is not None else "N/A"

            writer.writerow({
                "sku": item["sku"],
                "name": item["name"],
                "supplier": item.get("supplier", ""),
                "current_stock": item["current_stock"],
                "lead_time_days": item["lead_time_days"],
                "avg_daily_demand": round(item["avg_daily_demand"], 2),
                "rop": round(item["rop"], 2),
                "days_of_cover": doc_str,
                "status": item["status"],
                "order_qty": order_qty,
                "unit_cost": f"{unit_cost:.2f}",
                "total_cost": f"{total_cost:.2f}",
            })

    return len(reorder_items)
