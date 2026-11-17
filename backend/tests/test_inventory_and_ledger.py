import pytest
from app.repositories.inventory_repo import InventoryRepository, InsufficientStockError
from app.models.inventory import MovementType

def test_atomic_stock_movement_and_ledger(db, test_setup_catalog, test_users):
    repo = InventoryRepository(db)
    prod = test_setup_catalog["product"]
    wh = test_setup_catalog["warehouse"]
    admin = test_users["admin"]

    # Initial balance is 50
    bal, mov = repo.apply_stock_movement_atomic(
        product_id=prod.id,
        warehouse_id=wh.id,
        quantity_delta=-10,
        movement_type=MovementType.SALE,
        reference_type="sale",
        reference_id="TEST-001",
        reason="Sale test",
        created_by=admin.id,
    )
    db.commit()

    assert bal.on_hand_qty == 40
    assert mov.quantity_delta == -10
    assert mov.balance_after == 40

def test_negative_stock_strictly_prevented(db, test_setup_catalog, test_users):
    repo = InventoryRepository(db)
    prod_id = test_setup_catalog["product"].id
    wh_id = test_setup_catalog["warehouse"].id
    admin_id = test_users["admin"].id

    # Current stock is 50. Attempting to deduct 60 must raise InsufficientStockError
    with pytest.raises(InsufficientStockError) as exc_info:
        repo.apply_stock_movement_atomic(
            product_id=prod_id,
            warehouse_id=wh_id,
            quantity_delta=-60,
            movement_type=MovementType.SALE,
            reference_type="sale",
            reference_id="TEST-OVERSALE",
            reason="Attempt oversell",
            created_by=admin_id,
        )

    db.rollback()
    assert exc_info.value.current_stock == 50
    assert exc_info.value.requested_delta == -60

    # Verify balance was NOT mutated
    fresh_bal = repo.get_balance(prod_id, wh_id)
    assert fresh_bal.on_hand_qty == 50

def test_stock_adjustment_mandatory_reason_validation(client, auth_headers, test_setup_catalog):
    prod = test_setup_catalog["product"]
    wh = test_setup_catalog["warehouse"]

    # Missing or blank reason fails validation (400 or 422)
    res = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers["manager"],
        json={"product_id": prod.id, "warehouse_id": wh.id, "quantity_delta": 5, "reason": "  "},
    )
    assert res.status_code in [400, 422]
