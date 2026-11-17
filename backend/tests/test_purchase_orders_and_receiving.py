from datetime import date, timedelta
from decimal import Decimal
import pytest
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, POStatus
from app.models.inventory import InventoryBalance
from app.repositories.inventory_repo import InventoryRepository

def test_purchase_order_lifecycle_and_partial_receiving(client, auth_headers, test_setup_catalog, db):
    prod = test_setup_catalog["product"]
    wh = test_setup_catalog["warehouse"]
    supp = test_setup_catalog["supplier"]
    initial_stock = test_setup_catalog["balance"].on_hand_qty

    # 1. Create Purchase Order (Starts in DRAFT)
    res_create = client.post(
        "/api/v1/purchase-orders",
        headers=auth_headers["manager"],
        json={
            "supplier_id": supp.id,
            "warehouse_id": wh.id,
            "expected_delivery_date": str(date.today() + timedelta(days=7)),
            "notes": "PO Lifecycle Test",
            "items": [
                {"product_id": prod.id, "quantity_ordered": 50, "unit_cost": "65.00"}
            ],
        },
    )
    assert res_create.status_code == 201
    po_data = res_create.json()
    po_id = po_data["id"]
    po_item_id = po_data["items"][0]["id"]
    assert po_data["status"] == "DRAFT"

    # Cannot receive against DRAFT order
    res_bad_receive = client.post(
        "/api/v1/receiving",
        headers=auth_headers["manager"],
        json={
            "purchase_order_id": po_id,
            "received_date": str(date.today()),
            "items": [{"po_item_id": po_item_id, "quantity_received": 20}],
        },
    )
    assert res_bad_receive.status_code == 400

    # 2. Place order
    res_place = client.post(f"/api/v1/purchase-orders/{po_id}/place", headers=auth_headers["manager"])
    assert res_place.status_code == 200
    assert res_place.json()["status"] == "PLACED"

    # 3. Partial Delivery: Receive 20 out of 50
    res_receive_1 = client.post(
        "/api/v1/receiving",
        headers=auth_headers["manager"],
        json={
            "purchase_order_id": po_id,
            "received_date": str(date.today()),
            "notes": "First partial batch",
            "items": [{"po_item_id": po_item_id, "quantity_received": 20}],
        },
    )
    assert res_receive_1.status_code == 201
    grn_data = res_receive_1.json()
    assert grn_data["receipt_number"].startswith("GRN-")

    # Check PO status is now PARTIALLY_RECEIVED
    po_check = client.get(f"/api/v1/purchase-orders/{po_id}", headers=auth_headers["manager"]).json()
    assert po_check["status"] == "PARTIALLY_RECEIVED"
    assert po_check["items"][0]["quantity_received"] == 20
    assert po_check["items"][0]["remaining_qty"] == 30

    # Check warehouse on-hand stock increased by 20
    bal_res = client.get(f"/api/v1/inventory/balances?warehouse_id={wh.id}", headers=auth_headers["manager"]).json()
    item = next(i for i in bal_res["items"] if i["product_id"] == prod.id)
    assert item["on_hand_qty"] == initial_stock + 20

    # 4. Over-receipt prevention: Remaining is 30, attempt to receive 35
    res_over_receipt = client.post(
        "/api/v1/receiving",
        headers=auth_headers["manager"],
        json={
            "purchase_order_id": po_id,
            "received_date": str(date.today()),
            "items": [{"po_item_id": po_item_id, "quantity_received": 35}],
        },
    )
    assert res_over_receipt.status_code == 400
    assert "over-receipt prevented" in res_over_receipt.json()["detail"].lower()

    # 5. Cancellation restriction: cannot cancel partially received order
    res_cancel = client.post(f"/api/v1/purchase-orders/{po_id}/cancel", headers=auth_headers["manager"])
    assert res_cancel.status_code == 400
    assert "already received deliveries" in res_cancel.json()["detail"].lower()

    # 6. Receive final remaining 30 units -> PO status becomes RECEIVED
    res_receive_2 = client.post(
        "/api/v1/receiving",
        headers=auth_headers["manager"],
        json={
            "purchase_order_id": po_id,
            "received_date": str(date.today()),
            "notes": "Final batch",
            "items": [{"po_item_id": po_item_id, "quantity_received": 30}],
        },
    )
    assert res_receive_2.status_code == 201

    po_final = client.get(f"/api/v1/purchase-orders/{po_id}", headers=auth_headers["manager"]).json()
    assert po_final["status"] == "RECEIVED"
    assert po_final["items"][0]["quantity_received"] == 50
    assert po_final["items"][0]["remaining_qty"] == 0
    assert po_final["completed_at"] is not None
