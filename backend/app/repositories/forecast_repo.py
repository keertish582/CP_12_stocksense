from datetime import date
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from app.models.forecast import ForecastRun, Forecast, ForecastRunStatus

class ForecastRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_run_by_id(self, run_id: int) -> Optional[ForecastRun]:
        return self.db.query(ForecastRun).filter(ForecastRun.id == run_id).first()

    def get_latest_completed_run(self) -> Optional[ForecastRun]:
        return (
            self.db.query(ForecastRun)
            .filter(ForecastRun.status == ForecastRunStatus.COMPLETED)
            .order_by(ForecastRun.completed_at.desc(), ForecastRun.id.desc())
            .first()
        )

    def list_runs(self, skip: int = 0, limit: int = 20) -> Tuple[List[ForecastRun], int]:
        q = self.db.query(ForecastRun)
        total = q.count()
        runs = q.order_by(ForecastRun.started_at.desc(), ForecastRun.id.desc()).offset(skip).limit(limit).all()
        return runs, total

    def create_run(self, run: ForecastRun) -> ForecastRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def update_run(self, run: ForecastRun) -> ForecastRun:
        self.db.commit()
        self.db.refresh(run)
        return run

    def save_forecasts(self, forecasts: List[Forecast]):
        for f in forecasts:
            self.db.add(f)
        self.db.commit()

    def get_forecasts_for_product(self, product_id: int, forecast_run_id: int) -> List[Forecast]:
        return (
            self.db.query(Forecast)
            .filter(
                Forecast.product_id == product_id,
                Forecast.forecast_run_id == forecast_run_id,
            )
            .order_by(Forecast.forecast_date.asc())
            .all()
        )
