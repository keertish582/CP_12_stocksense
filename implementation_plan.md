# StockSense — Predictive Inventory Reorder Engine
## Implementation Plan & Architectural Specification

### 1. Overview & System Goals
StockSense is an enterprise-grade retail inventory management and predictive reorder recommendation engine tailored for Indian retail operations (using INR currency and `Asia/Kolkata` display formatting, with UTC storage). It bridges the gap between historical sales velocity, supplier constraints (MOQ, pack size, lead times), and warehouse inventory positions to generate explainable reorder recommendations and manage the purchase order lifecycle from draft to partial goods receipt.

---

### 2. System Architecture & Component Design

#### A. Backend Architecture (Modular Monolith)
- **Framework:** FastAPI with Python 3.11+
- **Layers:**
  - `API Endpoints` (`app/api/v1/`): Request validation, role checks, HTTP status codes.
  - `Services` (`app/services/`): Pure business logic (inventory ledger transactions, forecast calculations, reorder calculations, inbound eligibility, goods receiving).
  - `Repositories` (`app/repositories/`): Data access queries, transactional locks (`SELECT ... FOR UPDATE` where applicable).
  - `Database Models` (`app/models/`): SQLAlchemy 2.0 declarative models with Alembic migrations.
  - `Background Worker` (`app/tasks/`): Celery + Redis for asynchronous forecast runs, nightly schedules, and CSV batch processing. Supports synchronous execution fallback for direct local running without Celery worker.

#### B. Database Engine Compatibility
- Supports PostgreSQL 16 (for Docker Compose and production environments) with standard indexes, foreign key constraints, and numeric money types.
- Supports SQLite with transactional guarantees for development and local testing when external database servers are not present.

#### C. Frontend Architecture
- **Framework:** React 18 / 19 with Vite & TypeScript
- **Styling:** Tailwind CSS with custom styling matching enterprise theme (Dark Navy `#0f172a` sidebar, Teal `#0d9488` primary accent, Soft Gray `#f8fafc` background, crisp white cards).
- **State & Data Fetching:** TanStack Query (React Query) for caching and background refetching, React Hook Form + Zod for validation.
- **Routing:** React Router v6 with Role-Based Route Guards (`ADMIN`, `MANAGER`, `STAFF`).
- **Data Visualization:** Recharts for sales vs. forecast projections and inventory trends.
- **Icons:** Lucide React.

---

### 3. Core Business Logic & Invariants

1. **Inventory Stock Ledger:**
   - `available_stock = on_hand_qty - reserved_qty`
   - `inventory_position = on_hand_qty - reserved_qty - unreserved_backorders + eligible_open_inbound`
   - Every stock balance change is atomically paired with a record in `stock_movements`.
   - Strict non-negative inventory enforcement (`CHECK (on_hand_qty >= 0)`).

2. **Inbound Eligibility Rules:**
   - Only purchase orders in `PLACED` or `PARTIALLY_RECEIVED` status qualify.
   - `DRAFT` and `CANCELLED` orders are strictly excluded.
   - Overdue inbound orders (expected delivery date in the past) or orders missing expected dates are excluded from eligible supply and explicitly flagged as data-quality warnings.
   - Deliveries scheduled after the projected stockout date are flagged.
   - Transparent breakdown of contributing purchase orders is saved in calculation details.

3. **Forecasting Engine:**
   - Evaluates three candidate baseline methods:
     1. Trailing 7-day average
     2. Trailing 28-day average
     3. Seasonal Naive (repeating previous week's weekday pattern)
   - Evaluates on chronological holdout window (e.g., 14 days) using MAE (Mean Absolute Error) as primary selection criterion, with WAPE (Weighted Absolute Percentage Error) computed when actual demand is non-zero.
   - Flags stockout days (inventory balance = 0) as censored demand periods.
   - Handles cold-start items: fallback to manager-configured manual daily demand; if absent, flags product as insufficient history without fabricating zero demand.
   - Estimates projected stockout date: the earliest day where cumulative forecasted demand exceeds available inventory.

4. **Reorder Engine & Explainability:**
   - Lead-time demand: $\sum_{t=1}^{L} \text{DailyForecast}_t$
   - Reorder Point ($ROP$): $\text{Lead-Time Demand} + \text{Safety Stock}$
   - Trigger condition: $\text{Inventory Position} \le ROP$
   - Target Stock: $\sum_{t=1}^{L+C} \text{DailyForecast}_t + \text{Safety Stock}$
   - Raw Order Quantity: $\max(0, \lceil \text{Target Stock} - \text{Inventory Position} \rceil)$
   - Constraints: Enforces supplier Minimum Order Quantity (MOQ) and upward rounding to Pack Size.
   - Full explainability snapshot persisted in JSON for audit and approval inspection.
   - Material check at approval time: verifies that current on-hand and eligible inbound have not drifted from snapshot values before permitting order creation.

5. **Purchase Order & Goods Receiving Workflow:**
   - Transitions: `DRAFT` $\to$ `PLACED` $\to$ `PARTIALLY_RECEIVED` $\to$ `RECEIVED`.
   - Approval of recommendation creates a `DRAFT` purchase order.
   - Placing the order marks it as eligible inbound.
   - Partial goods receipt atomically records goods receipt items, updates PO item received quantities, increments warehouse on-hand stock, logs stock ledger movements, and updates PO status. Over-receipt is strictly prohibited.

---

### 4. Implementation Checklist & Phase Tracking

- [ ] **Phase 1: Project Setup & Database Foundations**
  - [ ] Initialize backend structure, virtual environment, and dependency specifications (`requirements.txt`).
  - [ ] Configure database connection (`app/core/database.py`), settings (`app/core/config.py`), and security (`app/core/security.py`).
  - [ ] Define SQLAlchemy models for users, categories, products, suppliers, product_suppliers, warehouses, inventory_balances, stock_movements, sales, sale_items, import_jobs, forecast_runs, forecasts, reorder_recommendations, purchase_orders, purchase_order_items, goods_receipts, goods_receipt_items, audit_logs.
  - [ ] Configure Alembic migrations and verify schema generation.
  - [ ] Set up Docker Compose configuration (`docker-compose.yml`, Dockerfiles, `.env.example`).

- [ ] **Phase 2: Authentication, Authorization & Inventory Engine**
  - [ ] Implement JWT authentication with password hashing (passlib/bcrypt) and RBAC dependencies (`ADMIN`, `MANAGER`, `STAFF`).
  - [ ] Build Inventory Repository and Service with atomic ledger updates, row-level locking, and negative-stock prevention.
  - [ ] Implement Product and Supplier management CRUD with preferred supplier and planning parameters.
  - [ ] Expose API endpoints for Auth, Products, Suppliers, and Inventory adjustments.

- [ ] **Phase 3: Sales Engine & CSV Import**
  - [ ] Build manual sales entry API with atomic stock deduction and ledger logging.
  - [ ] Implement CSV template generator and batch sales import parser with row validation, multi-line sale grouping (`external_sale_id` + `sku`), and duplicate detection.
  - [ ] Create background/asynchronous CSV import processing and status reporting.

- [ ] **Phase 4: Predictive Forecasting & Reorder Recommendation Engine**
  - [ ] Implement forecasting algorithms: Trailing 7-day, Trailing 28-day, Seasonal Naive with holdout evaluation (MAE/WAPE).
  - [ ] Implement stockout period censoring and cold-start fallback.
  - [ ] Build Reorder Engine computing Lead-Time Demand, Safety Stock, Reorder Point, Target Stock, MOQ, and Pack Size rounding.
  - [ ] Implement Inbound Supply Eligibility filtering (excluding overdue and missing dates).
  - [ ] Persist explainable recommendation snapshots and provide refresh/approval/deferral/dismissal APIs.

- [ ] **Phase 5: Purchase Order Management & Partial Goods Receiving**
  - [ ] Implement PO state machine (`DRAFT` -> `PLACED` -> `PARTIALLY_RECEIVED` -> `RECEIVED`).
  - [ ] Convert approved recommendation into PO with idempotency check.
  - [ ] Implement Goods Receiving API supporting partial deliveries, stock increase, movement ledger logging, and over-receipt prevention.

- [ ] **Phase 6: Comprehensive Seed Data & Business Reporting**
  - [ ] Create deterministic synthetic seed data: 30 products, 5 suppliers, 1 warehouse, ~180 days of realistic sales history, open and overdue POs, reconciled ledger balances.
  - [ ] Build reporting endpoints (Sales analytics, Stock Movement ledger, Inventory Valuation, Forecast evaluation, CSV exports).
  - [ ] Build Dashboard summary endpoint with live PostgreSQL queries.

- [ ] **Phase 7: Frontend Application**
  - [ ] Initialize React + TypeScript + Vite project with Tailwind CSS, Lucide, Recharts, TanStack Query.
  - [ ] Implement authentication context with memory-based token storage and role checks.
  - [ ] Build Dark Navy + Teal responsive layout with Sidebar, Topbar, and notifications.
  - [ ] Develop full application screens:
    - Dashboard (KPI cards, attention table, actuals vs forecast chart, stock movements)
    - Products (List, filters, create/edit modal, details view)
    - Inventory (Balances, adjustment modal with mandatory reason, ledger history)
    - Sales & CSV Import (Manual sale modal, CSV drag-and-drop, template download, validation error display)
    - Forecasts (Product selector, interactive history/forecast chart, method comparison, metrics)
    - Reorder Recommendations (Priority badges, review drawer with full calculation formula and inbound breakdown, approval modal)
    - Purchase Orders (Order list, PO details, status transitions, partial receiving modal)
    - Suppliers (Directory, lead times, contact details)
    - Reports (Sales report, inventory valuation, movement export)
    - Settings (User profile, planning defaults, forecast schedule info)

- [ ] **Phase 8: Testing, Verification & Documentation**
  - [ ] Write and run comprehensive backend pytest suite (Auth, Ledger, Negative Stock, Duplicate Imports, Forecast Evaluation, MOQ/Pack Size, Partial Receipts, Stale Approvals).
  - [ ] Build and verify frontend distribution (`npm run build`).
  - [ ] Create detailed README, Mermaid architecture diagrams, and user guide.
