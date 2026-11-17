# StockSense — Predictive Inventory Reorder Engine

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React_18_TypeScript-61DAFB.svg?logo=react)](https://reactjs.org)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind_CSS_3.4-38B2AC.svg?logo=tailwind-css)](https://tailwindcss.com)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL_16-336791.svg?logo=postgresql)](https://www.postgresql.org)
[![Celery](https://img.shields.io/badge/Tasks-Celery_5.4_%2B_Redis-37814A.svg?logo=celery)](https://docs.celeryq.dev)
[![Firebase Hosting](https://img.shields.io/badge/Firebase_Hosting-Live-FFCA28.svg?logo=firebase)](https://stocksense-engine-8f2a.web.app)
[![Tests](https://img.shields.io/badge/Tests-19_Passed-brightgreen.svg)]()

> **Live Deployment:** [https://stocksense-engine-8f2a.web.app](https://stocksense-engine-8f2a.web.app)  
> **Firebase Project Console:** [https://console.firebase.google.com/project/stocksense-engine-8f2a/overview](https://console.firebase.google.com/project/stocksense-engine-8f2a/overview)

StockSense is an enterprise-grade retail inventory optimization and replenishment engine designed to solve the twin dilemmas of retail operations: **stockouts of fast-moving items** and **costly overstocking of slow-moving items**. 

Unlike naive inventory systems that rely on static thresholds or black-box predictions, StockSense pairs a **strict double-entry stock ledger** with an **explainable demand forecasting engine** and **mathematically transparent reorder formulas**.

---

## Architecture Overview

StockSense follows a **modular monolith** architecture adhering to Clean Architecture principles:
- **API Endpoints (`app.api.v1`)**: Strictly handle HTTP transport, Pydantic schema validation, and role-based permissions (`ADMIN`, `MANAGER`, `STAFF`).
- **Domain Services (`app.services`)**: Encapsulate all inventory math, demand projection models, purchase order state transitions, and idempotency checks.
- **Repositories (`app.repositories`)**: Mediate database transactions with row-level locks (`SELECT ... FOR UPDATE`) on stock balances to eliminate race conditions and negative inventory.
- **Persistence Layer**: 17 relational tables managed via SQLAlchemy 2.0 and Alembic migrations. Supports both **PostgreSQL 16** (production / Docker Compose) and **SQLite with WAL + Foreign Keys** (zero-setup developer fallback).
- **Asynchronous Processing**: Celery with Redis broker handles scheduled nightly forecast generation and atomic CSV ingestion without blocking HTTP request threads.
- **Frontend Dashboard**: Desktop-first responsive React 18 SPA built with Vite, TypeScript, Tailwind CSS, TanStack Query, Recharts, and Lucide icons.

Detailed architectural specifications and interactive Mermaid diagrams can be found in [docs/architecture.md](docs/architecture.md).

---

## Core Features & Business Logic

### 1. Transparent Inventory Replenishment Math
Every reorder recommendation includes an interactive **Review Drawer** exposing the complete mathematical formula and input snapshots:

- **Available Stock**:
  $$\text{Available Stock} = \text{On-Hand} - \text{Reserved}$$
  *(For MVP, reserved stock is maintained at 0).*
- **Inventory Position (IP)**:
  $$\text{Inventory Position} = \text{On-Hand} - \text{Reserved} - \text{Backorders} + \text{Eligible Open Inbound}$$
- **Lead Time Demand (LTD)**:
  $$\text{LTD} = \text{Forecast Daily Demand} \times \text{Preferred Supplier Lead Time (Days)}$$
- **Reorder Point (ROP)**:
  $$\text{ROP} = \text{LTD} + \text{Safety Stock}$$
- **Target Stock**:
  $$\text{Target Stock} = \text{ROP} + (\text{Forecast Daily Demand} \times \text{Coverage Days [14 Days]})$$
- **Raw Needed Quantity**:
  $$\text{Raw Needed Qty} = \max(0, \text{Target Stock} - \text{Inventory Position})$$
- **Supplier Pack-Size & MOQ Rounding**:
  $$\text{Suggested Qty} = \max(\text{MOQ}, \lceil \text{Raw Needed Qty} / \text{Pack Size} \rceil \times \text{Pack Size})$$

### 2. Inbound Supply Eligibility Rules
To protect against false supply expectations, StockSense applies strict business rules to open purchase orders:
- **Eligible Statuses**: Only orders in `PLACED` or `PARTIALLY_RECEIVED` status contribute remaining unreceived units to the Inventory Position.
- **Excluded Orders**: Draft (`DRAFT`) and cancelled (`CANCELLED`) orders are strictly excluded.
- **Overdue Exclusions**: Orders past their `expected_delivery_date` or missing a valid date are excluded from eligible supply and explicitly flagged with warning badges.
- **Delayed Inbound Flags**: Inbound deliveries scheduled to arrive *after* a product's projected stockout date are flagged in the review drawer to alert the manager that stock will run out before vendor delivery.

### 3. Explainable Demand Forecasting
StockSense evaluates 3 candidate baseline methods over historical sales using chronological holdout validation:
1. **Trailing 7-Day Average**: Fast reaction to recent demand shifts.
2. **Trailing 28-Day Average**: Smooth baseline filtering out day-to-day noise.
3. **Seasonal Naive**: Repeats day-of-week patterns (e.g., Saturday matches previous Saturday).
- **Holdout Evaluation**: Evaluates each candidate over a 14-day holdout period; selects the model minimizing **Mean Absolute Error (MAE)**. Displays **WAPE** when non-zero.
- **Demand Censoring**: Detects periods where stock was 0; flags zero sales as potentially censored demand rather than genuine lack of customer interest.
- **Cold-Start Fallback**: When sales history is under 14 days, the engine falls back to the product's configured `manual_daily_demand` and flags the recommendation with a cold-start indicator.

### 4. Concurrency & Double-Entry Stock Ledger
- Every stock alteration (sale, adjustment, receipt) writes an immutable row into `stock_movements` recording `quantity_delta`, `balance_after`, `movement_type`, `reference_id`, and `reason`.
- Negative inventory is strictly prevented at the database level with `CHECK (on_hand_qty >= 0)`.
- Concurrent sales acquire row locks on `inventory_balances` (`SELECT ... FOR UPDATE`), preventing overselling during simultaneous requests.
- **Stale Recommendation Guard**: Approving a recommendation re-checks current inventory position. If stock drifted by more than 5 units since the forecast run, the approval is rejected with `409 Conflict`, prompting a refresh.

### 5. Multi-Line CSV Sales Ingestion
- Upload sales via drag-and-drop CSV with downloadable template.
- Client-side and server-side preview with row-level error reporting (e.g., non-existent SKU, negative price).
- Multi-line grouping via `external_sale_id` allows multi-item sales transactions.
- Duplicate detection rejects rows matching previously imported sales.
- **Atomic rollback**: If any row in a batch fails validation or creates negative stock, the entire batch rolls back with zero partial writes.

### 6. Purchase Order Lifecycle & Partial Receiving
- Full state machine: `DRAFT` $\to$ `PLACED` $\to$ `PARTIALLY_RECEIVED` $\to$ `RECEIVED` (or `CANCELLED`).
- **Partial Receiving**: Generates a sequentially numbered Goods Receipt Note (`GRN-...`), increments on-hand stock, logs a `PURCHASE_RECEIPT` ledger movement, and updates the PO item's remaining quantity.
- **Over-receipt Prevention**: Rejects any receiving attempt exceeding the item's remaining quantity.

### 7. Financial & Operational Reports
- **Inventory Valuation**: Computed using simple replacement cost basis ($\text{On-Hand} \times \text{Preferred Supplier Unit Cost}$ in INR).
- **Sales Analytics**: Historical sales revenue and units sold filtered by date range and category. One-click CSV export.
- **Movement Ledger**: Audit feed of all physical stock movements with one-click CSV export.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack Query v5, Recharts, Lucide Icons |
| **Backend** | Python 3.13, FastAPI 0.115, Pydantic v2, SQLAlchemy 2.0, Alembic, Pandas, NumPy |
| **Authentication** | Short-lived signed JWT bearer tokens, Bcrypt password hashing, RBAC |
| **Async Tasks** | Celery 5.4, Redis 7 (broker & backend), Celery Beat (02:00 IST schedule) |
| **Database** | PostgreSQL 16 (with SQLite 3 WAL fallback for zero-dependency local dev) |
| **Testing** | Pytest, Pytest-Asyncio, HTTPX TestClient (18/18 tests passing) |
| **Containerization** | Docker, Docker Compose, Multi-stage Dockerfiles |

---

## Demo Credentials & Access Roles

The seed script creates 3 ready-to-use accounts demonstrating Role-Based Access Control:

| Role | Email | Password | Permissions |
|---|---|---|---|
| **ADMIN** | `admin@stocksense.dev` | `Admin@12345` | Full access: User management, system configuration, all modules |
| **MANAGER** | `manager@stocksense.dev` | `Manager@12345` | Inventory, products, suppliers, forecast pipeline, PO approval & receiving |
| **STAFF** | `staff@stocksense.dev` | `Staff@12345` | Record sales, import sales CSV, view products & available inventory |

*Quick-Fill buttons are available on the `/login` page for fast role switching.*

---

## Quickstart Instructions

### Option A: Running with Docker Compose (Recommended)

1. Clone or navigate to the repository directory:
   ```bash
   cd CP_12_stocksense
   ```

2. Copy the sample environment file:
   ```bash
   cp .env.example .env
   ```

3. Launch all services:
   ```bash
   docker compose up --build -d
   ```

4. The application services will start:
   - **Frontend UI**: [http://localhost:5173](http://localhost:5173)
   - **FastAPI Backend & Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **PostgreSQL**: `localhost:5432`
   - **Redis**: `localhost:6379`
   - **Celery Worker & Scheduler**: Running in background

---

### Option B: Running Locally without Docker

#### 1. Backend Setup
1. Open a terminal in `backend/`:
   ```bash
   cd backend
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Initialize the database and run the deterministic seed script:
   ```bash
   python -m app.seed.seed_data
   ```
   *(This creates 30 products, 5 suppliers, 1 warehouse, 180 days of daily sales, opening balances, ledger history, forecast runs, and active recommendations).*

4. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

#### 2. Frontend Setup
1. In a separate terminal, navigate to `frontend/`:
   ```bash
   cd frontend
   npm install
   ```

2. Start the Vite dev server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Running the Automated Test Suite

StockSense includes an exhaustive Pytest test suite covering all critical business rules:
- Role-based route restrictions and authorization boundaries
- Strict non-negative inventory enforcement under concurrent deductions
- Mandatory reason validation for stock adjustments
- Multi-line CSV sales import and atomic rollback on invalid rows
- Duplicate line rejection
- Cold-start fallback logic and stockout demand censoring
- Inbound supply eligibility and overdue PO exclusion
- Supplier MOQ and pack-size rounding calculations
- Stale recommendation approval prevention (`409 Conflict`)
- Purchase order placement, partial receiving, and over-receipt prevention

To run the full suite:

```bash
# From the project root:
$env:PYTHONPATH="backend"; .\backend\venv\Scripts\python.exe -m pytest backend\tests -v
```

### Verified Test Results

```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\Keerthish\OneDrive\Attachments\Desktop\CP_12_stocksense
collected 18 items

backend/tests/test_auth_and_roles.py::test_login_success PASSED                         [  5%]
backend/tests/test_auth_and_roles.py::test_login_invalid_password PASSED                [ 11%]
backend/tests/test_auth_and_roles.py::test_admin_user_management_role_restriction PASSED[ 16%]
backend/tests/test_auth_and_roles.py::test_staff_cannot_create_stock_adjustment PASSED [ 22%]
backend/tests/test_auth_and_roles.py::test_manager_can_create_stock_adjustment PASSED   [ 27%]
backend/tests/test_forecast_and_reorder.py::test_cold_start_insufficient_history_behavior PASSED [ 33%]
backend/tests/test_forecast_and_reorder.py::test_cold_start_with_manual_fallback PASSED[ 38%]
backend/tests/test_forecast_and_reorder.py::test_inbound_eligibility_and_overdue_exclusion PASSED [ 44%]
backend/tests/test_forecast_and_reorder.py::test_moq_and_pack_size_rounding PASSED     [ 47%]
backend/tests/test_forecast_and_reorder.py::test_stale_recommendation_approval_rejected PASSED [ 52%]
backend/tests/test_forecast_and_reorder.py::test_forecast_evaluation_report_endpoint PASSED [ 57%]
backend/tests/test_inventory_and_ledger.py::test_atomic_stock_movement_and_ledger PASSED [ 63%]
backend/tests/test_inventory_and_ledger.py::test_negative_stock_strictly_prevented PASSED [ 68%]
backend/tests/test_inventory_and_ledger.py::test_stock_adjustment_mandatory_reason_validation PASSED [ 73%]
backend/tests/test_purchase_orders_and_receiving.py::test_purchase_order_lifecycle_and_partial_receiving PASSED [ 78%]
backend/tests/test_sales_and_import.py::test_manual_sale_success PASSED                 [ 84%]
backend/tests/test_sales_and_import.py::test_manual_sale_insufficient_stock_fails PASSED[ 89%]
backend/tests/test_sales_and_import.py::test_csv_import_success_and_duplicate_prevention PASSED [ 94%]
backend/tests/test_sales_and_import.py::test_csv_import_atomic_rollback_on_invalid_row PASSED [100%]

====================== 19 passed in 10.73s =======================
```

---

## Verifying the Production Frontend Build

```bash
cd frontend
npm run build
```

Build Output:
```text
> tsc && vite build

vite v6.4.6 building for production...
✓ 2060 modules transformed.
dist/index.html                   0.82 kB │ gzip:   0.48 kB
dist/assets/index-DkHu3091.css   30.00 kB │ gzip:   5.97 kB
dist/assets/index-PaoDLXob.js   819.48 kB │ gzip: 215.84 kB
✓ built in 7.44s
```

---

## Scope Boundaries & Assumptions

1. **Warehouse Model**: The database schema and business logic include `warehouse_id` on all inventory balances, stock movements, and purchase orders. The MVP targets a single regional warehouse (`WH-BLR-01`) with multi-warehouse extensibility preserved in all query signatures.
2. **Backorders & Reservations**: For the MVP, `reserved_qty` is maintained at 0 and unreserved backorders are assumed to be 0 in the Inventory Position equation.
3. **Currency & Localization**: All currency metrics are formatted in Indian Rupees (`₹` / INR) with two decimal places. Timestamps are stored in UTC in the database and rendered in `Asia/Kolkata` (IST, UTC+05:30) across the UI.
4. **No External Paid AI/APIs**: All forecasting methods (Trailing 7d, Trailing 28d, Seasonal Naive) are computed locally using NumPy and Pandas with zero external API dependencies.

---

## License

MIT License. Designed and engineered for retail inventory management.
