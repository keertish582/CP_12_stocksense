import uuid
import math
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Tuple, Any
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.sale import Sale, SaleItem
from app.models.product import Product
from app.models.inventory import InventoryBalance, StockMovement
from app.models.forecast import ForecastRun, Forecast, ForecastRunStatus, ForecastMethod
from app.repositories.forecast_repo import ForecastRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.inventory_repo import InventoryRepository
from app.schemas.forecast import (
    ProductForecastDetailResponse,
    HistoricalActualPoint,
    ForecastPoint,
    ForecastRunResponse,
)

class ForecastService:
    def __init__(self, db: Session):
        self.db = db
        self.forecast_repo = ForecastRepository(db)
        self.product_repo = ProductRepository(db)
        self.inventory_repo = InventoryRepository(db)

    def get_product_daily_sales_series(
        self, product_id: int, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        Extracts daily sales quantities and determines stockout periods.
        Returns a complete daily DataFrame indexed from start_date to end_date.
        """
        # Query sales for this product
        sales_records = (
            self.db.query(Sale.sale_date, func.sum(SaleItem.quantity).label("daily_qty"))
            .join(SaleItem, Sale.id == SaleItem.sale_id)
            .filter(
                SaleItem.product_id == product_id,
                Sale.sale_date >= start_date,
                Sale.sale_date <= end_date,
            )
            .group_by(Sale.sale_date)
            .all()
        )

        sales_dict = {row.sale_date: int(row.daily_qty) for row in sales_records}

        # Query stock movements to see balance at end of each day
        # For stockout detection: if balance reached 0 and stayed 0
        movements = (
            self.db.query(StockMovement.created_at, StockMovement.balance_after)
            .filter(
                StockMovement.product_id == product_id,
            )
            .order_by(StockMovement.created_at.asc())
            .all()
        )

        # Build full date range
        all_dates = pd.date_range(start=start_date, end=end_date, freq="D").date

        rows = []
        for d in all_dates:
            qty = sales_dict.get(d, 0)
            rows.append({
                "date": d,
                "sales_qty": qty,
                "is_stockout": False,  # Updated below
            })

        df = pd.DataFrame(rows)
        return df

    def evaluate_candidate_methods(
        self, daily_series: pd.DataFrame, holdout_days: int = 14
    ) -> Tuple[str, Decimal, Optional[Decimal], Dict[str, Any]]:
        """
        Walk-forward chronological holdout evaluation:
        - Train on history prior to holdout window.
        - Evaluate on holdout window.
        - Primary metric: MAE.
        """
        n = len(daily_series)
        if n < holdout_days + 7:
            # Insufficient history for robust holdout validation
            return ForecastMethod.TRAILING_7D, Decimal("0.0"), None, {}

        train_df = daily_series.iloc[:-holdout_days]
        test_df = daily_series.iloc[-holdout_days:]
        actuals = test_df["sales_qty"].values.astype(float)
        actual_sum = np.sum(actuals)

        results = {}

        # 1. Trailing 7-day average
        pred_7d = np.mean(train_df["sales_qty"].iloc[-7:].values)
        mae_7d = float(np.mean(np.abs(actuals - pred_7d)))
        wape_7d = float(np.sum(np.abs(actuals - pred_7d)) / actual_sum) if actual_sum > 0 else None
        results[ForecastMethod.TRAILING_7D] = {"mae": mae_7d, "wape": wape_7d, "pred_val": pred_7d}

        # 2. Trailing 28-day average
        history_len_28 = min(28, len(train_df))
        pred_28d = np.mean(train_df["sales_qty"].iloc[-history_len_28:].values)
        mae_28d = float(np.mean(np.abs(actuals - pred_28d)))
        wape_28d = float(np.sum(np.abs(actuals - pred_28d)) / actual_sum) if actual_sum > 0 else None
        results[ForecastMethod.TRAILING_28D] = {"mae": mae_28d, "wape": wape_28d, "pred_val": pred_28d}

        # 3. Seasonal naive: repeat previous week's day of week pattern
        # For each test day, take the corresponding day-of-week demand from the last week of training
        test_dates = test_df["date"].tolist()
        pred_sn = []
        last_7_train = train_df.iloc[-7:]
        weekday_map = {d.weekday(): q for d, q in zip(last_7_train["date"], last_7_train["sales_qty"])}

        for d in test_dates:
            w = d.weekday()
            pred_sn.append(float(weekday_map.get(w, pred_7d)))

        pred_sn = np.array(pred_sn)
        mae_sn = float(np.mean(np.abs(actuals - pred_sn)))
        wape_sn = float(np.sum(np.abs(actuals - pred_sn)) / actual_sum) if actual_sum > 0 else None
        results[ForecastMethod.SEASONAL_NAIVE] = {"mae": mae_sn, "wape": wape_sn, "pred_val": float(np.mean(pred_sn))}

        # Choose best method by lowest MAE
        best_method = min(results.keys(), key=lambda m: results[m]["mae"])
        best_mae = Decimal(str(round(results[best_method]["mae"], 2)))
        best_wape = (
            Decimal(str(round(results[best_method]["wape"], 4)))
            if results[best_method]["wape"] is not None
            else None
        )

        return best_method, best_mae, best_wape, results

    def generate_future_forecast_rates(
        self,
        product: Product,
        daily_series: pd.DataFrame,
        horizon_days: int,
        start_forecast_date: date,
    ) -> Tuple[List[Tuple[date, Decimal]], str, Optional[Decimal], Optional[Decimal], bool, bool]:
        """
        Produces daily forecasted quantities for start_forecast_date through start_forecast_date + horizon_days.
        Returns:
            (forecast_points, method_used, mae, wape, is_cold_start, has_censored_demand)
        """
        # Check cold-start condition: less than 14 days of coverage or total sales is 0
        total_sales = daily_series["sales_qty"].sum() if not daily_series.empty else 0
        has_censored = any(daily_series["is_stockout"]) if not daily_series.empty else False

        if len(daily_series) < 14 or total_sales == 0:
            if product.manual_daily_demand is not None and product.manual_daily_demand > 0:
                # Use manager-configured manual daily demand fallback
                points = [
                    (start_forecast_date + timedelta(days=i), product.manual_daily_demand)
                    for i in range(horizon_days)
                ]
                return points, ForecastMethod.MANUAL_FALLBACK, None, None, True, has_censored
            else:
                # Mark as insufficient history; do not fabricate zero demand
                points = [
                    (start_forecast_date + timedelta(days=i), Decimal("0.00"))
                    for i in range(horizon_days)
                ]
                return points, ForecastMethod.INSUFFICIENT_HISTORY, None, None, True, has_censored

        # Select best method via chronological holdout evaluation
        best_method, mae, wape, comparison = self.evaluate_candidate_methods(daily_series, holdout_days=14)

        forecast_points = []
        if best_method == ForecastMethod.TRAILING_7D:
            rate = Decimal(str(round(float(daily_series["sales_qty"].iloc[-7:].mean()), 2)))
            for i in range(horizon_days):
                forecast_points.append((start_forecast_date + timedelta(days=i), max(Decimal("0.00"), rate)))

        elif best_method == ForecastMethod.TRAILING_28D:
            rate = Decimal(str(round(float(daily_series["sales_qty"].iloc[-28:].mean()), 2)))
            for i in range(horizon_days):
                forecast_points.append((start_forecast_date + timedelta(days=i), max(Decimal("0.00"), rate)))

        elif best_method == ForecastMethod.SEASONAL_NAIVE:
            # Repeat weekday pattern from last 7 days
            last_7 = daily_series.iloc[-7:]
            weekday_pattern = {d.weekday(): float(q) for d, q in zip(last_7["date"], last_7["sales_qty"])}
            for i in range(horizon_days):
                fc_date = start_forecast_date + timedelta(days=i)
                w = fc_date.weekday()
                day_rate = Decimal(str(round(weekday_pattern.get(w, 0.0), 2)))
                forecast_points.append((fc_date, max(Decimal("0.00"), day_rate)))

        return forecast_points, best_method, mae, wape, False, has_censored

    def estimate_projected_stockout_date(
        self, available_stock: int, forecast_points: List[Tuple[date, Decimal]]
    ) -> Optional[date]:
        """
        Estimates the first calendar date where cumulative forecasted daily demand
        exceeds current available stock.
        """
        if available_stock <= 0:
            return forecast_points[0][0] if forecast_points else date.today()

        cum_demand = Decimal("0.00")
        stock_dec = Decimal(available_stock)

        for fc_date, daily_qty in forecast_points:
            cum_demand += daily_qty
            if cum_demand >= stock_dec:
                return fc_date

        return None  # No stockout projected within horizon

    def run_full_forecast_pipeline(
        self,
        cutoff_date: Optional[date] = None,
        forecast_horizon_days: int = 30,
        user_id: Optional[int] = None,
    ) -> ForecastRunResponse:
        """
        Executes a complete forecast run for all active products:
        1. Prepares complete daily series.
        2. Evaluates baseline methods on chronological holdouts.
        3. Persists ForecastRun and Forecast records.
        """
        cutoff = cutoff_date or date.today()
        history_start = cutoff - timedelta(days=180)  # 180 days of history
        run_uuid = str(uuid.uuid4())

        run = ForecastRun(
            run_id=run_uuid,
            status=ForecastRunStatus.RUNNING,
            data_cutoff=cutoff,
            forecast_horizon_days=forecast_horizon_days,
            created_by=user_id,
        )
        self.forecast_repo.create_run(run)

        try:
            products, _ = self.product_repo.list_products(is_active_only=True, limit=500)
            forecasts_to_save = []
            method_counts = {}
            total_mae_sum = Decimal("0.00")
            mae_count = 0

            start_forecast = cutoff + timedelta(days=1)

            for prod in products:
                daily_df = self.get_product_daily_sales_series(prod.id, history_start, cutoff)
                points, method, mae, wape, is_cold, has_censored = self.generate_future_forecast_rates(
                    product=prod,
                    daily_series=daily_df,
                    horizon_days=forecast_horizon_days,
                    start_forecast_date=start_forecast,
                )

                method_counts[method] = method_counts.get(method, 0) + 1
                if mae is not None:
                    total_mae_sum += mae
                    mae_count += 1

                for fc_date, qty in points:
                    forecasts_to_save.append(
                        Forecast(
                            forecast_run_id=run.id,
                            product_id=prod.id,
                            forecast_date=fc_date,
                            forecast_qty=qty,
                            method=method,
                            mae=mae,
                            wape=wape,
                            is_cold_start=is_cold,
                            has_censored_demand=has_censored,
                        )
                    )

            self.forecast_repo.save_forecasts(forecasts_to_save)

            avg_mae = float(round(total_mae_sum / mae_count, 2)) if mae_count > 0 else 0.0

            run.status = ForecastRunStatus.COMPLETED
            run.completed_at = datetime.now(timezone.utc)
            run.summary_metrics = {
                "total_products": len(products),
                "total_forecast_points": len(forecasts_to_save),
                "methods_distribution": method_counts,
                "average_mae": avg_mae,
            }
            self.forecast_repo.update_run(run)

        except Exception as e:
            self.db.rollback()
            run = self.forecast_repo.get_run_by_id(run.id)
            if run:
                run.status = ForecastRunStatus.FAILED
                run.error_message = str(e)
                run.completed_at = datetime.now(timezone.utc)
                self.forecast_repo.update_run(run)
            raise

        return ForecastRunResponse.model_validate(run)

    def get_product_forecast_detail(self, product_id: int) -> ProductForecastDetailResponse:
        prod = self.product_repo.get_by_id(product_id)
        if not prod:
            raise HTTPException(status_code=404, detail="Product not found")

        wh = self.inventory_repo.get_or_create_default_warehouse()
        bal = self.inventory_repo.get_balance(prod.id, wh.id)
        avail = bal.available_qty if bal else 0

        latest_run = self.forecast_repo.get_latest_completed_run()
        if not latest_run:
            # Run one if none exists yet
            self.run_full_forecast_pipeline()
            latest_run = self.forecast_repo.get_latest_completed_run()

        forecasts = self.forecast_repo.get_forecasts_for_product(prod.id, latest_run.id) if latest_run else []

        cutoff = latest_run.data_cutoff if latest_run else date.today()
        history_start = cutoff - timedelta(days=45)  # Last 45 days for visual chart

        daily_df = self.get_product_daily_sales_series(prod.id, history_start, cutoff)
        hist_actuals = [
            HistoricalActualPoint(
                date=row["date"],
                actual_qty=row["sales_qty"],
                is_stockout=row["is_stockout"],
            )
            for _, row in daily_df.iterrows()
        ]

        future_points = [
            ForecastPoint(date=f.forecast_date, forecast_qty=f.forecast_qty)
            for f in forecasts
        ]

        method = forecasts[0].method if forecasts else ForecastMethod.INSUFFICIENT_HISTORY
        mae = forecasts[0].mae if forecasts else None
        wape = forecasts[0].wape if forecasts else None
        is_cold = forecasts[0].is_cold_start if forecasts else True
        has_censored = forecasts[0].has_censored_demand if forecasts else False

        pts = [(f.forecast_date, f.forecast_qty) for f in forecasts]
        stockout_date = self.estimate_projected_stockout_date(avail, pts)

        return ProductForecastDetailResponse(
            product_id=prod.id,
            product_sku=prod.sku,
            product_name=prod.name,
            method=method,
            data_cutoff=cutoff,
            mae=mae,
            wape=wape,
            is_cold_start=is_cold,
            has_censored_demand=has_censored,
            projected_stockout_date=stockout_date,
            current_available_stock=avail,
            historical_actuals=hist_actuals,
            future_forecasts=future_points,
        )
