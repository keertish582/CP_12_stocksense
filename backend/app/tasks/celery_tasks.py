import logging
from app.core.celery_app import celery
from app.core.database import SessionLocal
from app.services.forecast_service import ForecastService
from app.services.reorder_service import ReorderService
from app.services.sales_service import SalesService

logger = logging.getLogger("stocksense.tasks")

@celery.task(name="app.tasks.celery_tasks.run_nightly_forecast_and_reorder")
def run_nightly_forecast_and_reorder():
    logger.info("Executing scheduled nightly forecast and reorder pipeline...")
    db = SessionLocal()
    try:
        fc_service = ForecastService(db)
        fc_run = fc_service.run_full_forecast_pipeline()
        logger.info(f"Forecast run completed: ID={fc_run.id}, Status={fc_run.status}")

        reorder_service = ReorderService(db)
        recs = reorder_service.refresh_all_recommendations()
        logger.info(f"Reorder recommendations refreshed: {len(recs)} active recommendations generated.")
        return {"status": "SUCCESS", "forecast_run_id": fc_run.id, "recommendations_count": len(recs)}
    except Exception as e:
        logger.exception(f"Scheduled forecast task failed: {e}")
        return {"status": "FAILED", "error": str(e)}
    finally:
        db.close()

@celery.task(name="app.tasks.celery_tasks.process_csv_import_async")
def process_csv_import_async(csv_text: str, filename: str, user_id: int):
    logger.info(f"Processing background CSV import for file: {filename}")
    db = SessionLocal()
    try:
        sales_service = SalesService(db)
        job = sales_service.execute_atomic_csv_import(csv_text=csv_text, filename=filename, user_id=user_id)
        return {"status": "SUCCESS", "job_id": job.job_id, "processed_rows": job.processed_rows}
    except Exception as e:
        logger.exception(f"Background CSV import task failed: {e}")
        return {"status": "FAILED", "error": str(e)}
    finally:
        db.close()
