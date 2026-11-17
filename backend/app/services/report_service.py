import io
import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.product import Product, ProductSupplier
from app.models.inventory import InventoryBalance, StockMovement
from app.models.sale import Sale, SaleItem
from app.models.purchase_order import PurchaseOrder, POStatus
from app.models.forecast import ForecastRun, Forecast, ForecastRunStatus
from app.models.recommendation import ReorderRecommendation
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.forecast_repo import ForecastRepository
from app.schemas.report import (
    DashboardSummaryResponse,
    InventoryAttentionItem,
    SalesVsForecastPoint,
    InventoryValuationItem,
    SalesReportItem,
    ForecastEvaluationReportItem,
)

class ReportService:
    def __init__(self, db: Session):
        self.db = db
        self.inventory_repo = InventoryRepository(db)
        self.product_repo = ProductRepository(db)
        self.forecast_repo = ForecastRepository(db)

    def get_dashboard_summary(self) -> DashboardSummaryResponse:
        wh = self.inventory_repo.get_or_create_default_warehouse()
        today = date.today()

        # 1. Active products
        active_products_count = self.db.query(Product).filter(Product.is_active == True).count()

        # 2. Open purchase orders
        open_po_count = (
            self.db.query(PurchaseOrder)
            .filter(
                PurchaseOrder.warehouse_id == wh.id,
                PurchaseOrder.status.in_([POStatus.PLACED, POStatus.PARTIALLY_RECEIVED]),
            )
            .count()
        )

        # 3. Total sales today
        sales_today = (
            self.db.query(func.coalesce(func.sum(Sale.total_amount), 0.0))
            .filter(Sale.sale_date == today)
            .scalar()
        )

        # 4. Inventory counts and valuation
        balances, _ = self.inventory_repo.list_inventory_balances(warehouse_id=wh.id, limit=500)
        low_stock_count = 0
        stockout_risk_count = 0

        for b in balances:
            status = b["stock_status"]
            if status in ["OUT_OF_STOCK", "STOCKOUT_RISK"]:
                stockout_risk_count += 1
                low_stock_count += 1
            elif status == "REORDER_SOON":
                low_stock_count += 1

        # Valuation
        valuation_items = self.get_inventory_valuation()
        total_valuation = sum((v.total_valuation for v in valuation_items), Decimal("0.00"))

        # Latest forecast run
        latest_run = self.forecast_repo.get_latest_completed_run()
        run_info = None
        if latest_run:
            run_info = {
                "run_id": latest_run.run_id,
                "status": latest_run.status,
                "data_cutoff": str(latest_run.data_cutoff),
                "completed_at": latest_run.completed_at.isoformat() if latest_run.completed_at else None,
                "summary": latest_run.summary_metrics,
            }

        return DashboardSummaryResponse(
            active_products_count=active_products_count,
            low_stock_products_count=low_stock_count,
            stockout_risk_count=stockout_risk_count,
            open_purchase_orders_count=open_po_count,
            total_inventory_valuation=total_valuation,
            total_sales_today=Decimal(str(round(sales_today, 2))),
            latest_forecast_run=run_info,
        )

    def get_inventory_attention_list(self, limit: int = 10) -> List[InventoryAttentionItem]:
        wh = self.inventory_repo.get_or_create_default_warehouse()
        balances, _ = self.inventory_repo.list_inventory_balances(warehouse_id=wh.id, limit=500)

        attention_items = []
        for b in balances:
            if b["stock_status"] in ["OUT_OF_STOCK", "STOCKOUT_RISK", "REORDER_SOON"]:
                rec = (
                    self.db.query(ReorderRecommendation)
                    .filter(
                        ReorderRecommendation.product_id == b["product_id"],
                        ReorderRecommendation.warehouse_id == wh.id,
                        ReorderRecommendation.is_active == True,
                    )
                    .first()
                )
                attention_items.append(
                    InventoryAttentionItem(
                        product_id=b["product_id"],
                        sku=b["product_sku"],
                        name=b["product_name"],
                        category_name=b["category_name"],
                        on_hand_qty=b["on_hand_qty"],
                        reserved_qty=b["reserved_qty"],
                        available_qty=b["available_qty"],
                        eligible_open_inbound=b["eligible_open_inbound"],
                        reorder_point=b["reorder_point"],
                        stock_status=b["stock_status"],
                        projected_stockout_date=rec.projected_stockout_date if rec else None,
                        suggested_qty=rec.suggested_qty if rec else 0,
                    )
                )

        # Sort: OUT_OF_STOCK first, then STOCKOUT_RISK, then REORDER_SOON
        order_rank = {"OUT_OF_STOCK": 1, "STOCKOUT_RISK": 2, "REORDER_SOON": 3}
        attention_items.sort(key=lambda x: order_rank.get(x.stock_status, 99))
        return attention_items[:limit]

    def get_actual_vs_forecast_trend(self, days: int = 30) -> List[SalesVsForecastPoint]:
        """
        Returns actual daily sales vs forecasted sales aggregated across all products
        for the past `days` days.
        """
        today = date.today()
        start_date = today - timedelta(days=days)

        actual_sales = (
            self.db.query(Sale.sale_date, func.sum(SaleItem.quantity).label("total_qty"))
            .join(SaleItem, Sale.id == SaleItem.sale_id)
            .filter(Sale.sale_date >= start_date, Sale.sale_date <= today)
            .group_by(Sale.sale_date)
            .all()
        )
        actuals_dict = {row.sale_date: int(row.total_qty) for row in actual_sales}

        # Forecasts from latest run
        latest_run = self.forecast_repo.get_latest_completed_run()
        forecast_dict = {}
        if latest_run:
            fc_rows = (
                self.db.query(Forecast.forecast_date, func.sum(Forecast.forecast_qty).label("total_fc"))
                .filter(Forecast.forecast_run_id == latest_run.id)
                .group_by(Forecast.forecast_date)
                .all()
            )
            forecast_dict = {row.forecast_date: Decimal(str(round(row.total_fc, 2))) for row in fc_rows}

        results = []
        curr = start_date
        while curr <= today + timedelta(days=14):  # Include 14 days of future forecast
            actual_q = actuals_dict.get(curr, 0)
            fc_q = forecast_dict.get(curr, Decimal("0.00"))
            results.append(
                SalesVsForecastPoint(
                    date=curr,
                    actual_sales=actual_q if curr <= today else 0,
                    forecast_sales=fc_q,
                )
            )
            curr += timedelta(days=1)

        return results

    def get_inventory_valuation(self) -> List[InventoryValuationItem]:
        wh = self.inventory_repo.get_or_create_default_warehouse()
        products, _ = self.product_repo.list_products(is_active_only=True, limit=500)

        results = []
        for p in products:
            bal = self.inventory_repo.get_balance(p.id, wh.id)
            on_hand = bal.on_hand_qty if bal else 0

            # Cost basis: preferred supplier unit cost
            pref_supp = next((ps for ps in p.product_suppliers if ps.is_preferred), None)
            if not pref_supp and p.product_suppliers:
                pref_supp = p.product_suppliers[0]

            unit_cost = pref_supp.unit_cost if pref_supp else Decimal("0.00")
            total_val = unit_cost * Decimal(on_hand)

            results.append(
                InventoryValuationItem(
                    product_id=p.id,
                    sku=p.sku,
                    name=p.name,
                    category_name=p.category.name if p.category else None,
                    on_hand_qty=on_hand,
                    unit_cost=unit_cost,
                    total_valuation=total_val,
                )
            )

        return results

    def get_sales_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        product_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> List[SalesReportItem]:
        q = (
            self.db.query(
                Sale.sale_date,
                Product.sku,
                Product.name,
                func.coalesce(func.sum(SaleItem.quantity), 0).label("qty_sold"),
                func.coalesce(func.sum(SaleItem.subtotal), 0.0).label("total_revenue"),
            )
            .join(SaleItem, Sale.id == SaleItem.sale_id)
            .join(Product, SaleItem.product_id == Product.id)
        )

        if start_date:
            q = q.filter(Sale.sale_date >= start_date)
        if end_date:
            q = q.filter(Sale.sale_date <= end_date)
        if product_id:
            q = q.filter(Product.id == product_id)
        if category_id:
            q = q.filter(Product.category_id == category_id)

        rows = (
            q.group_by(Sale.sale_date, Product.sku, Product.name)
            .order_by(Sale.sale_date.desc(), Product.name.asc())
            .all()
        )

        return [
            SalesReportItem(
                sale_date=r.sale_date,
                product_sku=r.sku,
                product_name=r.name,
                quantity_sold=int(r.qty_sold),
                total_revenue=Decimal(str(round(r.total_revenue, 2))),
            )
            for r in rows
        ]

    def export_sales_csv(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        product_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> str:
        report = self.get_sales_report(
            start_date=start_date,
            end_date=end_date,
            product_id=product_id,
            category_id=category_id,
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Sale Date", "SKU", "Product Name", "Quantity Sold", "Total Revenue (INR)"])
        for r in report:
            writer.writerow([str(r.sale_date), r.product_sku, r.product_name, r.quantity_sold, str(r.total_revenue)])
        return output.getvalue()

    def export_stock_movements_csv(self) -> str:
        movements, _ = self.inventory_repo.list_stock_movements(limit=1000)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Timestamp",
            "Warehouse",
            "SKU",
            "Product Name",
            "Quantity Delta",
            "Movement Type",
            "Balance After",
            "Reference",
            "Reason",
            "Actor",
        ])
        for m in movements:
            writer.writerow([
                m.created_at.isoformat(),
                m.warehouse.code,
                m.product.sku,
                m.product.name,
                m.quantity_delta,
                m.movement_type,
                m.balance_after,
                m.reference_id or "",
                m.reason or "",
                m.user.full_name if m.user else "",
            ])
        return output.getvalue()

    def get_forecast_evaluation_report(self) -> List[ForecastEvaluationReportItem]:
        latest_run = self.forecast_repo.get_latest_completed_run()
        if not latest_run:
            return []

        products = self.db.query(Product).filter(Product.is_active == True).all()
        results = []

        for p in products:
            sample_fc = (
                self.db.query(Forecast)
                .filter(
                    Forecast.forecast_run_id == latest_run.id,
                    Forecast.product_id == p.id,
                )
                .first()
            )

            if sample_fc:
                count = (
                    self.db.query(Forecast)
                    .filter(
                        Forecast.forecast_run_id == latest_run.id,
                        Forecast.product_id == p.id,
                    )
                    .count()
                )
                status_label = "Optimal"
                if sample_fc.is_cold_start:
                    status_label = "Cold Start"
                elif sample_fc.has_censored_demand:
                    status_label = "Censored Demand"

                results.append(
                    ForecastEvaluationReportItem(
                        product_id=p.id,
                        sku=p.sku,
                        name=p.name,
                        best_method=sample_fc.method,
                        mae=sample_fc.mae,
                        wape=sample_fc.wape,
                        data_points_count=count,
                        status=status_label,
                    )
                )

        return results
