import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.api.v1 import (
    auth,
    users,
    products,
    suppliers,
    inventory,
    sales,
    forecasts,
    recommendations,
    purchase_orders,
    receiving,
    reports,
    dashboard,
)
from app.repositories.inventory_repo import InventoryRepository
from app.repositories.user_repo import UserRepository
from app.core.security import hash_password
from app.models.user import User, UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stocksense.app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing StockSense application...")
    # Ensure default warehouse and admin user exist if not seeded yet
    db = SessionLocal()
    try:
        inv_repo = InventoryRepository(db)
        inv_repo.get_or_create_default_warehouse()

        user_repo = UserRepository(db)
        admin = user_repo.get_by_email("admin@stocksense.dev")
        if not admin:
            admin = User(
                email="admin@stocksense.dev",
                hashed_password=hash_password("Admin@12345"),
                full_name="System Administrator",
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            user_repo.create(admin)
            logger.info("Created default administrator: admin@stocksense.dev")
    except Exception as e:
        logger.warning(f"Startup initialization notice: {e}")
    finally:
        db.close()

    yield
    logger.info("Shutting down StockSense application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="StockSense — Predictive Inventory Reorder Engine for Retail Management",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routers
prefix = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)
app.include_router(products.router, prefix=prefix)
app.include_router(suppliers.router, prefix=prefix)
app.include_router(inventory.router, prefix=prefix)
app.include_router(sales.router, prefix=prefix)
app.include_router(forecasts.router, prefix=prefix)
app.include_router(recommendations.router, prefix=prefix)
app.include_router(purchase_orders.router, prefix=prefix)
app.include_router(receiving.router, prefix=prefix)
app.include_router(reports.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)

@app.get("/health", tags=["Health"])
@app.get(f"{prefix}/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "timezone": settings.DISPLAY_TIMEZONE,
        "currency": settings.CURRENCY_CODE,
    }
