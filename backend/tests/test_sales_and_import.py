import io
import pytest

def test_manual_sale_success(client, auth_headers, test_setup_catalog):
    prod = test_setup_catalog["product"]
    wh = test_setup_catalog["warehouse"]

    # Initial balance is 50
    res = client.post(
        "/api/v1/sales",
        headers=auth_headers["staff"],
        json={
            "external_sale_id": "POS-TEST-100",
            "sale_date": "2026-11-17",
            "channel": "POS_STORE",
            "warehouse_id": wh.id,
            "items": [
                {"product_id": prod.id, "quantity": 10, "unit_price": "100.00"}
            ],
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["total_amount"] == "1000.00"
    assert len(data["items"]) == 1

    # Check inventory was deducted to 40 in this warehouse
    bal_res = client.get(f"/api/v1/inventory/balances?warehouse_id={wh.id}", headers=auth_headers["staff"])
    assert bal_res.status_code == 200
    items = bal_res.json()["items"]
    target = next(i for i in items if i["product_id"] == prod.id)
    assert target["on_hand_qty"] == 40

def test_manual_sale_insufficient_stock_fails(client, auth_headers, test_setup_catalog):
    prod = test_setup_catalog["product"]
    wh = test_setup_catalog["warehouse"]

    # Attempt to sell 999 units when only 50 available
    res = client.post(
        "/api/v1/sales",
        headers=auth_headers["staff"],
        json={
            "external_sale_id": "POS-TEST-SHORTAGE",
            "sale_date": "2026-11-17",
            "warehouse_id": wh.id,
            "items": [
                {"product_id": prod.id, "quantity": 999, "unit_price": "100.00"}
            ],
        },
    )
    assert res.status_code == 400
    assert "cannot deduct" in res.json()["detail"].lower()

def test_csv_import_success_and_duplicate_prevention(client, auth_headers, test_setup_catalog, db):
    sku = test_setup_catalog["product"].sku
    wh = test_setup_catalog["warehouse"]

    csv_content = f"external_sale_id,sku,sale_date,quantity,unit_price\nBATCH-01,{sku},2026-11-16,5,100.00\n"

    # 1. Preview
    res_preview = client.post(
        "/api/v1/sales/preview-csv",
        headers=auth_headers["staff"],
        files={"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert res_preview.status_code == 200
    preview_data = res_preview.json()
    assert preview_data["total_rows"] == 1
    assert preview_data["valid_rows_count"] == 1
    assert preview_data["error_rows_count"] == 0

    # 2. Import
    res_import = client.post(
        f"/api/v1/sales/import-csv?warehouse_id={wh.id}",
        headers=auth_headers["staff"],
        files={"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert res_import.status_code == 201
    import_data = res_import.json()
    assert import_data["status"] == "COMPLETED"
    assert import_data["processed_rows"] == 1

    # 3. Duplicate re-import attempt must fail
    res_dup = client.post(
        f"/api/v1/sales/import-csv?warehouse_id={wh.id}",
        headers=auth_headers["staff"],
        files={"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert res_dup.status_code == 400
    assert "validation failed" in res_dup.json()["detail"].lower()

def test_csv_import_atomic_rollback_on_invalid_row(client, auth_headers, test_setup_catalog):
    sku = test_setup_catalog["product"].sku

    # Row 1 is valid, Row 2 has unknown SKU
    bad_csv = (
        f"external_sale_id,sku,sale_date,quantity,unit_price\n"
        f"BATCH-02,{sku},2026-11-16,2,100.00\n"
        f"BATCH-02,UNKNOWN-SKU-999,2026-11-16,3,50.00\n"
    )

    res = client.post(
        "/api/v1/sales/import-csv",
        headers=auth_headers["staff"],
        files={"file": ("bad.csv", io.BytesIO(bad_csv.encode("utf-8")), "text/csv")},
    )
    assert res.status_code == 400
    assert "validation failed" in res.json()["detail"].lower()
