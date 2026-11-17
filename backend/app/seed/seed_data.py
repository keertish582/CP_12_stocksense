import os
import random
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.product import Product, ProductSupplier
from app.models.warehouse import Warehouse
from app.models.inventory import InventoryBalance, StockMovement, MovementType
from app.models.sale import Sale, SaleItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem, POStatus
from app.models.receipt import GoodsReceipt, GoodsReceiptItem
from app.services.forecast_service import ForecastService
from app.services.reorder_service import ReorderService

# Fix seed for deterministic synthetic dataset
random.seed(42)

def seed_database():
    print("Beginning deterministic StockSense seed data generation...")
    from app.core.database import Base, engine
    import app.models  # Ensure all models are registered on Base
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        # 1. Clean existing data if any
        # Wipe in proper foreign key order
        db.query(GoodsReceiptItem).delete()
        db.query(GoodsReceipt).delete()
        db.query(PurchaseOrderItem).delete()
        db.query(PurchaseOrder).delete()
        from app.models.recommendation import ReorderRecommendation
        from app.models.forecast import Forecast, ForecastRun
        from app.models.import_job import ImportJob
        db.query(ReorderRecommendation).delete()
        db.query(Forecast).delete()
        db.query(ForecastRun).delete()
        db.query(ImportJob).delete()
        db.query(SaleItem).delete()
        db.query(Sale).delete()
        db.query(StockMovement).delete()
        db.query(InventoryBalance).delete()
        db.query(ProductSupplier).delete()
        db.query(Product).delete()
        db.query(Category).delete()
        db.query(Supplier).delete()
        db.query(Warehouse).delete()
        db.query(User).delete()
        db.commit()

        # 2. Seed Users
        print("Seeding users...")
        users = [
            User(
                email="admin@stocksense.dev",
                hashed_password=hash_password("Admin@12345"),
                full_name="Rajesh Sharma (Admin)",
                role=UserRole.ADMIN.value,
                is_active=True,
            ),
            User(
                email="manager@stocksense.dev",
                hashed_password=hash_password("Manager@12345"),
                full_name="Priya Patel (Operations Manager)",
                role=UserRole.MANAGER.value,
                is_active=True,
            ),
            User(
                email="staff@stocksense.dev",
                hashed_password=hash_password("Staff@12345"),
                full_name="Anil Kumar (Inventory Staff)",
                role=UserRole.STAFF.value,
                is_active=True,
            ),
        ]
        db.add_all(users)
        db.commit()
        admin_user = users[0]
        manager_user = users[1]

        # 3. Seed Warehouse
        print("Seeding central warehouse...")
        wh = Warehouse(
            code="WH-BLR-01",
            name="Central Distribution Hub - Bengaluru",
            location="Plot 42, Electronic City Phase 1, Bengaluru, Karnataka 560100",
            is_active=True,
        )
        db.add(wh)
        db.commit()

        # 4. Seed Categories
        print("Seeding categories...")
        categories_data = [
            ("Staples & Grains", "Daily consumption rice, flours, pulses, and grains"),
            ("Cooking Essentials", "Cooking oils, ghee, spices, and seasonings"),
            ("Beverages", "Tea, coffee, health drinks, and juices"),
            ("Packaged Foods", "Biscuits, snacks, breakfast cereals, and noodles"),
            ("Personal Care", "Soaps, shampoos, oral hygiene, and skincare"),
            ("Household Care", "Detergents, floor cleaners, and surface sanitizers"),
        ]
        cat_map = {}
        for name, desc in categories_data:
            c = Category(name=name, description=desc)
            db.add(c)
            db.flush()
            cat_map[name] = c

        # 5. Seed Suppliers
        print("Seeding suppliers...")
        suppliers_data = [
            ("Bharat Agro Supplies Pvt Ltd", "Vikram Reddy", "contact@bharatagro.in", "+91 80 2345 6789", "Bengaluru, Karnataka", 7),
            ("Kaveri FMCG Distributors", "Meena Iyer", "orders@kaverifmcg.com", "+91 44 2876 5432", "Chennai, Tamil Nadu", 5),
            ("Himalayan Naturals & Oils", "Sanjay Gupta", "sales@himalayanoils.co.in", "+91 11 2654 9870", "New Delhi", 10),
            ("Deccan Consumer Goods", "Ramesh Rao", "supply@deccanconsumer.com", "+91 40 2398 1122", "Hyderabad, Telangana", 6),
            ("Narmada Packaged Products", "Sunita Nair", "narmada@packagedfoods.in", "+91 22 2844 3300", "Mumbai, Maharashtra", 8),
        ]
        suppliers = []
        for name, contact, email, phone, addr, lt in suppliers_data:
            s = Supplier(
                name=name,
                contact_name=contact,
                email=email,
                phone=phone,
                address=addr,
                lead_time_days=lt,
                is_active=True,
            )
            db.add(s)
            db.flush()
            suppliers.append(s)

        # 6. Seed 30 Products
        print("Seeding 30 realistic retail products...")
        products_specs = [
            # (sku, name, category, unit, price, cost, lead_time, moq, pack_size, safety_stock, avg_daily, manual_demand, supplier_idx)
            # High-velocity fast-moving staples
            ("RICE-BAS-001", "Royal Heritage Basmati Rice 5kg", "Staples & Grains", "bag", 650.00, 480.00, 7, 20, 5, 25, 12, None, 0),
            ("RICE-SON-002", "Sona Masoori Raw Rice 10kg", "Staples & Grains", "bag", 720.00, 540.00, 7, 25, 5, 30, 15, None, 0),
            ("WHEAT-ATT-003", "Chakki Fresh Whole Wheat Atta 10kg", "Staples & Grains", "bag", 440.00, 330.00, 5, 30, 10, 35, 18, None, 1),
            ("TOOR-DAL-004", "Premium Unpolished Toor Dal 1kg", "Staples & Grains", "pack", 165.00, 120.00, 6, 50, 10, 40, 20, None, 3),
            ("MOONG-DAL-005", "Yellow Moong Dal Split 1kg", "Staples & Grains", "pack", 140.00, 105.00, 6, 40, 10, 25, 10, None, 3),
            ("SUGAR-CRY-006", "Refined Crystal Sugar 5kg", "Staples & Grains", "bag", 240.00, 185.00, 5, 30, 5, 30, 14, None, 1),
            
            # Cooking Essentials
            ("OIL-SUN-007", "Pure Sunflower Cooking Oil 1L Pouch", "Cooking Essentials", "pouch", 145.00, 112.00, 8, 60, 12, 50, 22, None, 2),
            ("OIL-MUST-008", "Kachi Ghani Mustard Oil 1L Bottle", "Cooking Essentials", "bottle", 175.00, 135.00, 10, 36, 12, 25, 8, None, 2),
            ("GHEE-COW-009", "Pure Desi Cow Ghee 500ml Jar", "Cooking Essentials", "jar", 360.00, 275.00, 10, 24, 6, 20, 7, None, 2),
            ("SALT-IOD-010", "Vacuum Evaporated Iodized Salt 1kg", "Cooking Essentials", "pack", 28.00, 20.00, 5, 100, 25, 60, 25, None, 1),
            ("SPICE-TUR-011", "Organic Turmeric Powder 500g", "Cooking Essentials", "pack", 125.00, 90.00, 6, 30, 6, 15, 6, None, 3),
            ("SPICE-CHIL-012", "Guntur Red Chilli Powder 500g", "Cooking Essentials", "pack", 180.00, 135.00, 6, 30, 6, 15, 7, None, 3),

            # Beverages
            ("TEA-PREM-013", "Assam Gold CTC Leaf Tea 500g", "Beverages", "pack", 270.00, 200.00, 7, 30, 10, 25, 11, None, 0),
            ("COFF-FLTR-014", "South Indian Filter Coffee Powder 500g", "Beverages", "pack", 295.00, 220.00, 7, 24, 6, 20, 8, None, 0),
            ("DRNK-MALT-015", "Malted Nutritional Health Drink 1kg", "Beverages", "jar", 460.00, 360.00, 8, 18, 6, 15, 5, None, 4),
            ("JUICE-MAN-016", "Alphonso Mango Fruit Drink 1L Tetra", "Beverages", "pack", 110.00, 82.00, 5, 48, 12, 30, 12, None, 1),
            ("TEA-GRN-017", "Organic Kashmiri Green Tea Bags 25s", "Beverages", "box", 220.00, 160.00, 10, 20, 4, 10, 3, None, 2),

            # Packaged Foods
            ("NOOD-INST-018", "Masala Instant Noodles Family Pack 4x70g", "Packaged Foods", "pack", 60.00, 45.00, 8, 48, 12, 40, 19, None, 4),
            ("BISC-MAR-019", "Digestive High Fiber Biscuits 400g", "Packaged Foods", "pack", 90.00, 68.00, 8, 36, 12, 20, 9, None, 4),
            ("BISC-CRK-020", "Butter Salt Crackers 250g", "Packaged Foods", "pack", 45.00, 33.00, 8, 60, 20, 25, 10, None, 4),
            ("OATS-ROL-021", "Rolled Wholegrain Breakfast Oats 1kg", "Packaged Foods", "pack", 195.00, 145.00, 8, 24, 6, 15, 5, None, 4),
            ("CORN-FLK-022", "Crunchy Corn Flakes Box 875g", "Packaged Foods", "box", 330.00, 250.00, 8, 16, 4, 12, 4, None, 4),

            # Personal Care
            ("SOAP-NDL-023", "Neem & Tulsi Herbal Bath Soap 125g (Pack of 4)", "Personal Care", "pack", 190.00, 140.00, 6, 36, 6, 20, 8, None, 3),
            ("SHAM-ANTI-024", "Anti-Dandruff Tea Tree Shampoo 400ml", "Personal Care", "bottle", 375.00, 280.00, 6, 20, 4, 15, 4, None, 3),
            ("PAST-HERB-025", "Complete Care Herbal Toothpaste 200g", "Personal Care", "tube", 115.00, 85.00, 6, 40, 10, 25, 11, None, 3),
            ("WASH-FACE-026", "Gentle Hydrating Face Wash 150ml", "Personal Care", "tube", 210.00, 155.00, 6, 24, 6, 12, 4, None, 3),

            # Household Care
            ("DET-POW-027", "Active Enzyme Detergent Powder 4kg", "Household Care", "bag", 499.00, 370.00, 5, 20, 4, 25, 10, None, 1),
            ("DISH-LIQ-028", "Lemon Degreasing Dishwash Liquid 750ml", "Household Care", "bottle", 155.00, 115.00, 5, 36, 6, 20, 9, None, 1),
            
            # Cold-start products (to test and verify cold-start logic)
            ("OIL-AVO-029", "Cold Pressed Avocado Cooking Oil 500ml", "Cooking Essentials", "bottle", 850.00, 640.00, 10, 12, 4, 10, 0, Decimal("2.00"), 2),
            ("SEED-CHIA-030", "Organic Black Chia Seeds 250g Jar", "Staples & Grains", "jar", 320.00, 230.00, 7, 15, 5, 10, 0, None, 0), # No manual demand -> insufficient history!
        ]

        products_list = []
        product_meta = {}

        for sku, name, cat_name, unit, price, cost, lt, moq, pack_sz, ss, avg_d, manual_d, supp_idx in products_specs:
            p = Product(
                sku=sku,
                name=name,
                category_id=cat_map[cat_name].id,
                unit=unit,
                selling_price=Decimal(str(price)),
                safety_stock=ss,
                min_reorder_qty=moq,
                manual_daily_demand=manual_d,
                lead_time_days=lt,
                is_active=True,
            )
            db.add(p)
            db.flush()
            products_list.append(p)

            # Link preferred supplier
            supp = suppliers[supp_idx]
            ps = ProductSupplier(
                product_id=p.id,
                supplier_id=supp.id,
                lead_time_days=lt,
                minimum_order_qty=moq,
                pack_size=pack_sz,
                unit_cost=Decimal(str(cost)),
                is_preferred=True,
            )
            db.add(ps)
            db.flush()

            product_meta[p.id] = {
                "sku": sku,
                "name": name,
                "avg_daily": avg_d,
                "price": price,
                "cost": cost,
                "lead_time": lt,
                "moq": moq,
                "pack_size": pack_sz,
                "safety_stock": ss,
                "supplier": supp,
            }

        db.commit()

        # 7. Generate ~180 Days of Daily Sales History with Realistic Patterns
        # Range: from 180 days ago until yesterday
        print("Generating ~180 days of reconciled historical sales and stock movements...")
        today = date.today()
        start_date = today - timedelta(days=180)

        # To ensure ending inventory is consistent, we first determine total historical sales per product,
        # grant opening stock movements on day 0, then record sales day by day!
        # For a few specific products, we intentionally simulate low stock or stockout to test engine!

        # 7a. First pass: simulate daily sales series per product
        product_daily_sales = {p.id: {} for p in products_list}
        product_total_sales = {p.id: 0 for p in products_list}

        curr = start_date
        while curr < today:
            weekday = curr.weekday()
            # Weekend uplift multiplier (Friday=4, Saturday=5, Sunday=6)
            day_multiplier = 1.35 if weekday in [4, 5, 6] else 0.90

            for p in products_list:
                meta = product_meta[p.id]
                base_daily = meta["avg_daily"]

                if base_daily == 0:
                    # Cold start products have 0 historical sales
                    product_daily_sales[p.id][curr] = 0
                    continue

                # Add Poisson/normal-like variance
                mean_qty = base_daily * day_multiplier
                # Sample bounded daily quantity
                sample_qty = max(0, int(round(random.gauss(mean_qty, max(1.0, math.sqrt(mean_qty))))))

                # Special condition: For RICE-BAS-001 and TOOR-DAL-004, simulate recent high sales to trigger reorder!
                if meta["sku"] == "RICE-BAS-001" and curr >= today - timedelta(days=15):
                    sample_qty = int(sample_qty * 1.8)

                product_daily_sales[p.id][curr] = sample_qty
                product_total_sales[p.id] += sample_qty

            curr += timedelta(days=1)

        # 7b. Determine Opening Stock so that:
        # Ending on-hand = (Desired ending stock target)
        # Desired ending:
        # Fast movers: some low (e.g. 8-15 units), some healthy (e.g. 50-80 units), one stockout (0 units)
        desired_ending_stock = {}
        for p in products_list:
            sku = product_meta[p.id]["sku"]
            avg_d = product_meta[p.id]["avg_daily"]
            ss = product_meta[p.id]["safety_stock"]

            if sku == "RICE-BAS-001":
                desired_ending_stock[p.id] = 12  # Low stock! LTD ~ 84, SS=25 -> ROP=109. Position=12 -> Strong reorder!
            elif sku == "OIL-SUN-007":
                desired_ending_stock[p.id] = 0   # Out of stock!
            elif sku == "TOOR-DAL-004":
                desired_ending_stock[p.id] = 18  # Low stock!
            elif sku == "NOOD-INST-018":
                desired_ending_stock[p.id] = 22  # Low stock!
            elif sku in ["OIL-AVO-029", "SEED-CHIA-030"]:
                desired_ending_stock[p.id] = 15  # Cold start initial stock
            else:
                # Healthy stock: ~ 3 to 4 weeks of demand
                desired_ending_stock[p.id] = max(ss + 20, int(avg_d * 22))

        # Total opening stock needed = total_sales + desired_ending_stock
        print("Creating initial opening stock ledger movements...")
        for p in products_list:
            total_sold = product_total_sales[p.id]
            desired_end = desired_ending_stock[p.id]
            opening_qty = total_sold + desired_end

            # Set initial balance and movement
            bal = InventoryBalance(
                product_id=p.id,
                warehouse_id=wh.id,
                on_hand_qty=opening_qty,
                reserved_qty=0,
                updated_at=datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc),
            )
            db.add(bal)
            db.flush()

            movement = StockMovement(
                product_id=p.id,
                warehouse_id=wh.id,
                quantity_delta=opening_qty,
                movement_type=MovementType.INITIAL,
                reference_type="seed",
                reference_id="SEED-INIT-001",
                balance_after=opening_qty,
                reason="Initial inventory opening stock balance",
                created_by=admin_user.id,
                created_at=datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc),
            )
            db.add(movement)

        db.commit()

        # 7c. Record sales day-by-day with atomic ledger deduction
        print("Simulating daily sales transactions across 180 days...")
        curr = start_date
        sale_counter = 1000

        # Preload inventory balance objects
        balances = {b.product_id: b for b in db.query(InventoryBalance).filter(InventoryBalance.warehouse_id == wh.id).all()}

        while curr < today:
            # Create a daily consolidated store POS sale batch
            day_sale_items = []
            day_total = Decimal("0.00")

            for p in products_list:
                qty = product_daily_sales[p.id].get(curr, 0)
                if qty <= 0:
                    continue

                price = Decimal(str(product_meta[p.id]["price"]))
                subtotal = price * Decimal(qty)
                day_total += subtotal

                bal = balances[p.id]
                new_bal = bal.on_hand_qty - qty
                bal.on_hand_qty = new_bal
                bal.updated_at = datetime.combine(curr, datetime.min.time(), tzinfo=timezone.utc)

                # Record stock ledger movement
                mov = StockMovement(
                    product_id=p.id,
                    warehouse_id=wh.id,
                    quantity_delta=-qty,
                    movement_type=MovementType.SALE,
                    reference_type="sale",
                    reference_id=f"POS-SALE-{sale_counter}",
                    balance_after=new_bal,
                    reason=f"Daily store sales on {curr}",
                    created_by=admin_user.id,
                    created_at=datetime.combine(curr, datetime.min.time(), tzinfo=timezone.utc),
                )
                db.add(mov)

                day_sale_items.append((p.id, qty, price, subtotal))

            if day_sale_items:
                sale = Sale(
                    external_sale_id=f"STORE-{curr.strftime('%Y%m%d')}",
                    sale_date=curr,
                    total_amount=day_total,
                    channel="POS_STORE",
                    notes=f"Daily aggregated store point-of-sale {curr}",
                    created_by=admin_user.id,
                    created_at=datetime.combine(curr, datetime.min.time(), tzinfo=timezone.utc),
                )
                db.add(sale)
                db.flush()

                for prod_id, q, pr, sub in day_sale_items:
                    si = SaleItem(
                        sale_id=sale.id,
                        product_id=prod_id,
                        quantity=q,
                        unit_price=pr,
                        subtotal=sub,
                    )
                    db.add(si)

                sale_counter += 1

            curr += timedelta(days=1)

        db.commit()

        # 8. Seed Purchase Orders & Goods Receipts
        print("Seeding representative purchase orders across lifecycle states...")

        # PO 1: PLACED order (counts as eligible open inbound, expected in 4 days)
        # For RICE-BAS-001 (50 units ordered, 0 received)
        prod_rice = next(p for p in products_list if product_meta[p.id]["sku"] == "RICE-BAS-001")
        supp_bharat = suppliers[0]
        po1 = PurchaseOrder(
            po_number="PO-20261114-0001",
            supplier_id=supp_bharat.id,
            warehouse_id=wh.id,
            status=POStatus.PLACED,
            expected_delivery_date=today + timedelta(days=4),
            notes="Regular replenishment order for Basmati Rice",
            total_amount=Decimal("24000.00"),
            placed_at=datetime.now(timezone.utc) - timedelta(days=3),
            created_by=manager_user.id,
        )
        db.add(po1)
        db.flush()
        db.add(
            PurchaseOrderItem(
                purchase_order_id=po1.id,
                product_id=prod_rice.id,
                quantity_ordered=50,
                quantity_received=0,
                unit_cost=Decimal("480.00"),
                subtotal=Decimal("24000.00"),
            )
        )

        # PO 2: PARTIALLY_RECEIVED order (to test partial delivery, receipts, and remaining inbound)
        # For WHEAT-ATT-003: 60 units ordered, 30 received 2 days ago, 30 remaining
        prod_wheat = next(p for p in products_list if product_meta[p.id]["sku"] == "WHEAT-ATT-003")
        supp_kaveri = suppliers[1]
        po2 = PurchaseOrder(
            po_number="PO-20261110-0002",
            supplier_id=supp_kaveri.id,
            warehouse_id=wh.id,
            status=POStatus.PARTIALLY_RECEIVED,
            expected_delivery_date=today + timedelta(days=2),
            notes="Split delivery agreed with Kaveri Distributors",
            total_amount=Decimal("19800.00"),
            placed_at=datetime.now(timezone.utc) - timedelta(days=7),
            created_by=manager_user.id,
        )
        db.add(po2)
        db.flush()
        po2_item = PurchaseOrderItem(
            purchase_order_id=po2.id,
            product_id=prod_wheat.id,
            quantity_ordered=60,
            quantity_received=30,
            unit_cost=Decimal("330.00"),
            subtotal=Decimal("19800.00"),
        )
        db.add(po2_item)
        db.flush()

        # Add Goods Receipt record for the 30 units received on PO 2
        grn1 = GoodsReceipt(
            receipt_number="GRN-20261115-0001",
            purchase_order_id=po2.id,
            warehouse_id=wh.id,
            received_date=today - timedelta(days=2),
            notes="First tranche of 30 bags received in good condition",
            created_by=manager_user.id,
        )
        db.add(grn1)
        db.flush()
        db.add(
            GoodsReceiptItem(
                goods_receipt_id=grn1.id,
                po_item_id=po2_item.id,
                product_id=prod_wheat.id,
                quantity_received=30,
                unit_cost=Decimal("330.00"),
            )
        )
        # Increment balance & record receipt movement
        bal_wheat = balances[prod_wheat.id]
        bal_wheat.on_hand_qty += 30
        db.add(
            StockMovement(
                product_id=prod_wheat.id,
                warehouse_id=wh.id,
                quantity_delta=30,
                movement_type=MovementType.PURCHASE_RECEIPT,
                reference_type="goods_receipt",
                reference_id=grn1.receipt_number,
                balance_after=bal_wheat.on_hand_qty,
                reason=f"Partial receipt against {po2.po_number}",
                created_by=manager_user.id,
            )
        )

        # PO 3: OVERDUE purchase order (expected delivery date in the past!)
        # For OIL-SUN-007: expected 3 days ago. Must be EXCLUDED from eligible inbound and flagged!
        prod_oil = next(p for p in products_list if product_meta[p.id]["sku"] == "OIL-SUN-007")
        supp_himalayan = suppliers[2]
        po3 = PurchaseOrder(
            po_number="PO-20261105-0003",
            supplier_id=supp_himalayan.id,
            warehouse_id=wh.id,
            status=POStatus.PLACED,
            expected_delivery_date=today - timedelta(days=3),  # OVERDUE!
            notes="Delayed consignment due to truck logistics. Flagged as overdue.",
            total_amount=Decimal("6720.00"),
            placed_at=datetime.now(timezone.utc) - timedelta(days=12),
            created_by=manager_user.id,
        )
        db.add(po3)
        db.flush()
        db.add(
            PurchaseOrderItem(
                purchase_order_id=po3.id,
                product_id=prod_oil.id,
                quantity_ordered=60,
                quantity_received=0,
                unit_cost=Decimal("112.00"),
                subtotal=Decimal("6720.00"),
            )
        )

        # PO 4: DRAFT order (must NOT count as inbound)
        prod_toor = next(p for p in products_list if product_meta[p.id]["sku"] == "TOOR-DAL-004")
        supp_deccan = suppliers[3]
        po4 = PurchaseOrder(
            po_number="PO-20261117-0004",
            supplier_id=supp_deccan.id,
            warehouse_id=wh.id,
            status=POStatus.DRAFT,
            expected_delivery_date=today + timedelta(days=6),
            notes="Draft awaiting internal budget approval",
            total_amount=Decimal("6000.00"),
            created_by=manager_user.id,
        )
        db.add(po4)
        db.flush()
        db.add(
            PurchaseOrderItem(
                purchase_order_id=po4.id,
                product_id=prod_toor.id,
                quantity_ordered=50,
                quantity_received=0,
                unit_cost=Decimal("120.00"),
                subtotal=Decimal("6000.00"),
            )
        )

        db.commit()

        # 9. Run Initial Forecasting Pipeline & Generate Explainable Reorder Recommendations
        print("Running forecasting pipeline and generating reorder recommendations...")
        fc_service = ForecastService(db)
        fc_run = fc_service.run_full_forecast_pipeline(cutoff_date=today, user_id=admin_user.id)
        print(f"Forecast pipeline complete: Run ID = {fc_run.run_id}, Summary = {fc_run.summary_metrics}")

        reorder_service = ReorderService(db)
        recs = reorder_service.refresh_all_recommendations(coverage_days=14)
        print(f"Reorder engine complete: {len(recs)} active explainable recommendations generated.")

        print("Deterministic database seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"Database seeding failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
