import io
import csv
import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from app.models.sale import Sale, SaleItem
from app.models.inventory import MovementType
from app.models.import_job import ImportJob, ImportJobStatus
from app.repositories.sale_repo import SaleRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.inventory_repo import InventoryRepository, InsufficientStockError
from app.schemas.sale import (
    SaleCreate,
    SaleResponse,
    SaleItemResponse,
    CSVPreviewResponse,
    ImportRowError,
    ImportJobResponse,
)

class SalesService:
    def __init__(self, db: Session):
        self.db = db
        self.sale_repo = SaleRepository(db)
        self.product_repo = ProductRepository(db)
        self.inventory_repo = InventoryRepository(db)

    def create_manual_sale(self, sale_in: SaleCreate, user_id: int) -> SaleResponse:
        wh = (
            self.inventory_repo.get_warehouse_by_id(sale_in.warehouse_id)
            if sale_in.warehouse_id
            else self.inventory_repo.get_or_create_default_warehouse()
        )
        if not wh:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found")

        total_amount = Decimal("0.00")
        sale_items = []

        try:
            # Create Sale header
            sale = Sale(
                external_sale_id=sale_in.external_sale_id.strip() if sale_in.external_sale_id else None,
                sale_date=sale_in.sale_date,
                total_amount=Decimal("0.00"),
                channel=sale_in.channel or "POS_STORE",
                notes=sale_in.notes,
                created_by=user_id,
            )
            self.sale_repo.create_sale_record(sale)

            for item_in in sale_in.items:
                product = self.product_repo.get_by_id(item_in.product_id)
                if not product:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Product ID {item_in.product_id} not found",
                    )

                subtotal = item_in.unit_price * Decimal(item_in.quantity)
                total_amount += subtotal

                # Deduct inventory atomically with row lock
                self.inventory_repo.apply_stock_movement_atomic(
                    product_id=product.id,
                    warehouse_id=wh.id,
                    quantity_delta=-item_in.quantity,
                    movement_type=MovementType.SALE,
                    reference_type="sale",
                    reference_id=str(sale.id),
                    reason=f"Sale order #{sale.id}",
                    created_by=user_id,
                )

                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=product.id,
                    quantity=item_in.quantity,
                    unit_price=item_in.unit_price,
                    subtotal=subtotal,
                )
                self.db.add(sale_item)
                sale_items.append(sale_item)

            sale.total_amount = total_amount
            self.db.commit()
            self.db.refresh(sale)
        except InsufficientStockError as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to record sale: {str(e)}",
            )

        return self.get_sale_response(sale)

    def get_sale_response(self, sale: Sale) -> SaleResponse:
        items = []
        for it in sale.items:
            items.append(
                SaleItemResponse(
                    id=it.id,
                    product_id=it.product_id,
                    product_sku=it.product.sku,
                    product_name=it.product.name,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    subtotal=it.subtotal,
                )
            )
        return SaleResponse(
            id=sale.id,
            external_sale_id=sale.external_sale_id,
            sale_date=sale.sale_date,
            total_amount=sale.total_amount,
            channel=sale.channel,
            notes=sale.notes,
            created_by_name=sale.user.full_name if sale.user else None,
            created_at=sale.created_at,
            items=items,
        )

    def list_sales(self, skip: int = 0, limit: int = 50) -> Tuple[List[SaleResponse], int]:
        sales, total = self.sale_repo.list_sales(skip=skip, limit=limit)
        return [self.get_sale_response(s) for s in sales], total

    def generate_csv_template(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["external_sale_id", "sku", "sale_date", "quantity", "unit_price"])
        writer.writerow(["ORD-1001", "RICE-BAS-001", "2026-11-01", "2", "145.00"])
        writer.writerow(["ORD-1001", "OIL-SUN-002", "2026-11-01", "1", "175.50"])
        writer.writerow(["ORD-1002", "WHEAT-ATT-003", "2026-11-02", "5", "52.00"])
        return output.getvalue()

    def parse_and_validate_csv_content(
        self, csv_text: str
    ) -> Tuple[List[dict], List[ImportRowError]]:
        reader = csv.DictReader(io.StringIO(csv_text))
        expected_cols = {"external_sale_id", "sku", "sale_date", "quantity", "unit_price"}
        
        if not reader.fieldnames or not expected_cols.issubset(set(reader.fieldnames)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CSV headers. Required columns: {', '.join(sorted(expected_cols))}",
            )

        valid_rows = []
        errors = []
        seen_sale_skus = set()  # To detect duplicate SKU within same external_sale_id

        for idx, row in enumerate(reader, start=2):  # Line 2 is first data row
            ext_id = row.get("external_sale_id", "").strip()
            sku = row.get("sku", "").strip().upper()
            date_str = row.get("sale_date", "").strip()
            qty_str = row.get("quantity", "").strip()
            price_str = row.get("unit_price", "").strip()

            row_error = None

            if not sku:
                row_error = "Missing required SKU"
            elif not date_str:
                row_error = "Missing sale_date"
            else:
                try:
                    sale_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    row_error = f"Invalid date format '{date_str}'. Expected YYYY-MM-DD."

            if not row_error:
                try:
                    qty = int(qty_str)
                    if qty <= 0:
                        row_error = "Quantity must be a positive integer greater than 0"
                except ValueError:
                    row_error = f"Invalid quantity value '{qty_str}'"

            if not row_error:
                try:
                    price = Decimal(price_str)
                    if price < 0:
                        row_error = "Unit price cannot be negative"
                except Exception:
                    row_error = f"Invalid unit price value '{price_str}'"

            # Check product existence
            if not row_error:
                prod = self.product_repo.get_by_sku(sku)
                if not prod:
                    row_error = f"Product with SKU '{sku}' does not exist in catalog"
                else:
                    row["_product_id"] = prod.id

            # Check within-file duplicate line
            if not row_error and ext_id:
                key = (ext_id, sku)
                if key in seen_sale_skus:
                    row_error = f"Duplicate SKU '{sku}' found for external_sale_id '{ext_id}' in the same CSV"
                seen_sale_skus.add(key)

            # Check database duplicate line
            if not row_error and ext_id:
                if self.sale_repo.check_duplicate_sale_line(ext_id, sku):
                    row_error = f"Sale line with external_sale_id '{ext_id}' and SKU '{sku}' has already been imported previously"

            if row_error:
                errors.append(
                    ImportRowError(
                        row_number=idx,
                        external_sale_id=ext_id or None,
                        sku=sku or None,
                        error=row_error,
                    )
                )
            else:
                valid_rows.append({
                    "row_number": idx,
                    "external_sale_id": ext_id or None,
                    "sku": sku,
                    "product_id": row["_product_id"],
                    "sale_date": sale_date,
                    "quantity": qty,
                    "unit_price": price,
                })

        return valid_rows, errors

    def preview_csv_import(self, csv_text: str) -> CSVPreviewResponse:
        valid_rows, errors = self.parse_and_validate_csv_content(csv_text)
        total_rows = len(valid_rows) + len(errors)
        preview_sample = valid_rows[:10]
        # Convert date and decimal objects for JSON serialization
        clean_preview = [
            {
                "row_number": r["row_number"],
                "external_sale_id": r["external_sale_id"],
                "sku": r["sku"],
                "sale_date": str(r["sale_date"]),
                "quantity": r["quantity"],
                "unit_price": str(r["unit_price"]),
            }
            for r in preview_sample
        ]
        return CSVPreviewResponse(
            total_rows=total_rows,
            valid_rows_count=len(valid_rows),
            error_rows_count=len(errors),
            errors=errors,
            preview_rows=clean_preview,
        )

    def execute_atomic_csv_import(
        self, csv_text: str, filename: str, user_id: int, warehouse_id: Optional[int] = None
    ) -> ImportJobResponse:
        """
        Validates all rows. If ANY row fails, rolls back completely and reports errors.
        Groups rows by external_sale_id to create multi-line sales.
        Deducts stock atomically and writes stock ledger movements.
        """
        valid_rows, errors = self.parse_and_validate_csv_content(csv_text)
        total_rows = len(valid_rows) + len(errors)
        job_uuid = str(uuid.uuid4())

        import_job = ImportJob(
            job_id=job_uuid,
            filename=filename,
            file_type="SALES_CSV",
            status=ImportJobStatus.PROCESSING,
            total_rows=total_rows,
            processed_rows=0,
            error_count=len(errors),
            created_by=user_id,
        )
        self.db.add(import_job)
        self.db.commit()

        if errors:
            import_job.status = ImportJobStatus.FAILED
            import_job.error_details = [e.model_dump() for e in errors]
            import_job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(import_job)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV validation failed with {len(errors)} error(s). No rows were imported.",
            )

        wh = (
            self.inventory_repo.get_warehouse_by_id(warehouse_id)
            if warehouse_id
            else self.inventory_repo.get_or_create_default_warehouse()
        )

        # Group rows by external_sale_id or single row sale
        grouped_sales: Dict[str, List[dict]] = {}
        for r in valid_rows:
            group_key = r["external_sale_id"] or f"AUTO-{uuid.uuid4()}"
            if group_key not in grouped_sales:
                grouped_sales[group_key] = []
            grouped_sales[group_key].append(r)

        try:
            processed_count = 0
            for group_key, items in grouped_sales.items():
                first_item = items[0]
                sale_date = first_item["sale_date"]
                ext_id = first_item["external_sale_id"]

                sale = Sale(
                    external_sale_id=ext_id,
                    sale_date=sale_date,
                    total_amount=Decimal("0.00"),
                    channel="CSV_IMPORT",
                    notes=f"Imported from {filename} (Job {job_uuid})",
                    created_by=user_id,
                )
                self.sale_repo.create_sale_record(sale)

                total_amount = Decimal("0.00")
                for it in items:
                    qty = it["quantity"]
                    price = it["unit_price"]
                    subtotal = price * Decimal(qty)
                    total_amount += subtotal

                    # Deduct inventory atomically
                    self.inventory_repo.apply_stock_movement_atomic(
                        product_id=it["product_id"],
                        warehouse_id=wh.id,
                        quantity_delta=-qty,
                        movement_type=MovementType.SALE,
                        reference_type="sale",
                        reference_id=str(sale.id),
                        reason=f"CSV Import #{ext_id or sale.id}",
                        created_by=user_id,
                    )

                    sale_item = SaleItem(
                        sale_id=sale.id,
                        product_id=it["product_id"],
                        quantity=qty,
                        unit_price=price,
                        subtotal=subtotal,
                    )
                    self.db.add(sale_item)
                    processed_count += 1

                sale.total_amount = total_amount

            import_job.status = ImportJobStatus.COMPLETED
            import_job.processed_rows = processed_count
            import_job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(import_job)

        except InsufficientStockError as e:
            self.db.rollback()
            # Update job record with failure
            import_job = self.db.query(ImportJob).filter(ImportJob.job_id == job_uuid).first()
            if import_job:
                import_job.status = ImportJobStatus.FAILED
                import_job.error_details = [{"row_number": 0, "error": str(e)}]
                import_job.completed_at = datetime.now(timezone.utc)
                self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Inventory shortage during import: {str(e)}. Transaction rolled back.",
            )
        except Exception as e:
            self.db.rollback()
            import_job = self.db.query(ImportJob).filter(ImportJob.job_id == job_uuid).first()
            if import_job:
                import_job.status = ImportJobStatus.FAILED
                import_job.error_details = [{"row_number": 0, "error": str(e)}]
                import_job.completed_at = datetime.now(timezone.utc)
                self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Import execution failed: {str(e)}",
            )

        return ImportJobResponse.model_validate(import_job)

    def get_import_job(self, job_id: str) -> ImportJobResponse:
        job = self.db.query(ImportJob).filter(ImportJob.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found")
        return ImportJobResponse.model_validate(job)
