import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.core.database import Base, get_db
from app.main import app
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole
from app.models.warehouse import Warehouse
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.product import Product, ProductSupplier
from app.models.inventory import InventoryBalance

# Use SQLite in-memory with StaticPool so all threads & sessions share the exact same in-memory DB
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client(db):
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_users(db):
    admin = User(
        email="test_admin@stocksense.dev",
        hashed_password=hash_password("AdminPass123"),
        full_name="Test Admin",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    manager = User(
        email="test_manager@stocksense.dev",
        hashed_password=hash_password("ManagerPass123"),
        full_name="Test Manager",
        role=UserRole.MANAGER.value,
        is_active=True,
    )
    staff = User(
        email="test_staff@stocksense.dev",
        hashed_password=hash_password("StaffPass123"),
        full_name="Test Staff",
        role=UserRole.STAFF.value,
        is_active=True,
    )
    db.add_all([admin, manager, staff])
    db.commit()
    for u in [admin, manager, staff]:
        db.refresh(u)
    return {"admin": admin, "manager": manager, "staff": staff}

@pytest.fixture
def auth_headers(test_users):
    headers = {}
    for role, user in test_users.items():
        token = create_access_token(subject=user.id, role=user.role)
        headers[role] = {"Authorization": f"Bearer {token}"}
    return headers

@pytest.fixture
def test_setup_catalog(db, test_users):
    wh = Warehouse(code="WH-TEST-01", name="Test Warehouse", is_active=True)
    db.add(wh)
    db.flush()

    cat = Category(name="Test Category", description="Category for tests")
    db.add(cat)
    db.flush()

    supp = Supplier(
        name="Test Supplier Co",
        email="orders@testsupp.com",
        phone="+91 9876543210",
        lead_time_days=7,
        is_active=True,
    )
    db.add(supp)
    db.flush()

    prod = Product(
        sku="TEST-SKU-001",
        name="Test Premium Widget",
        category_id=cat.id,
        unit="pcs",
        selling_price=100.0,
        safety_stock=10,
        min_reorder_qty=15,
        lead_time_days=7,
        is_active=True,
    )
    db.add(prod)
    db.flush()

    ps = ProductSupplier(
        product_id=prod.id,
        supplier_id=supp.id,
        lead_time_days=7,
        minimum_order_qty=20,  # MOQ = 20
        pack_size=6,           # Pack Size = 6
        unit_cost=65.0,
        is_preferred=True,
    )
    db.add(ps)

    bal = InventoryBalance(
        product_id=prod.id,
        warehouse_id=wh.id,
        on_hand_qty=50,
        reserved_qty=0,
    )
    db.add(bal)
    db.commit()
    db.refresh(wh)
    db.refresh(prod)
    db.refresh(supp)
    db.refresh(bal)

    return {
        "warehouse": wh,
        "category": cat,
        "supplier": supp,
        "product": prod,
        "balance": bal,
        "product_supplier": ps,
    }
