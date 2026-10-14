# CP-012 — StockSense: Predictive Inventory Reorder Engine

**Level:** Intermediate  
**Domain:** E-Commerce and Retail  

StockSense is an inventory management system that helps distributors avoid stockouts of fast-moving items and overstocking of slow-moving items. It tracks stock movements, predicts items that may run out before a new order arrives, and suggests the quantity to reorder.

## Problem Statement

A distributor either runs out of fast-moving items or overstocks slow-moving items. The system needs to answer:

- What items should be reordered?
- When should they be reordered?
- How much should be ordered?

## Core Features

1. **Item Management**  
   Maintain items with:
   - Item ID
   - Item name
   - Current stock
   - Average daily usage
   - Supplier lead time in days
   - Reorder level
   - Unit price

2. **Stock Movement Tracking**  
   Record stock-in and stock-out movements with:
   - Movement date
   - Movement type
   - Quantity
   - Remarks
   - Updated stock balance

3. **Stockout Risk Detection**  
   Flag items whose current stock will run out before a new order can arrive.

4. **Reorder Quantity Suggestion**  
   Suggest an order quantity for each flagged item to cover a selected number of days.

5. **Movement History**  
   Show the complete stock-in and stock-out history of any item.

## Stretch Features

- ABC classification of items based on consumption value
- Batch tracking with expiry dates
- Flag expired or soon-to-expire stock

## Reorder Logic

The system uses the reorder-point formula:

```text
Reorder Point = (Average Daily Usage × Supplier Lead Time) + Safety Stock
```

An item is flagged as a stockout risk when:

```text
Current Stock < (Average Daily Usage × Supplier Lead Time)
```

### Reorder Quantity

```text
Required Stock = Average Daily Usage × Coverage Days
Suggested Order Quantity = Required Stock - Current Stock
```

If the result is negative, the suggested order quantity is `0`.

### Example

| Field | Value |
|---|---:|
| Average daily usage | 10 units |
| Supplier lead time | 7 days |
| Current stock | 40 units |
| Coverage period | 30 days |

```text
Lead-time demand = 10 × 7 = 70 units
Current stock = 40 units
Status = Stockout Risk

Required stock = 10 × 30 = 300 units
Suggested order quantity = 300 - 40 = 260 units
```

## Item Status

| Status | Condition |
|---|---|
| Out of Stock | Current stock is 0 |
| Stockout Risk | Current stock is less than lead-time demand |
| Reorder Soon | Current stock is less than or equal to reorder level |
| Healthy | Current stock is sufficient |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python FastAPI |
| Database | PostgreSQL |
| Frontend | React |
| Authentication | JWT |
| Deployment | Docker |

## Database Design

### items

```sql
CREATE TABLE items (
    item_id VARCHAR(20) PRIMARY KEY,
    item_name VARCHAR(150) NOT NULL,
    current_stock INT NOT NULL DEFAULT 0,
    average_daily_usage DECIMAL(10,2) NOT NULL DEFAULT 0,
    supplier_lead_time_days INT NOT NULL DEFAULT 0,
    reorder_level INT NOT NULL DEFAULT 0,
    unit_price DECIMAL(12,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### stock_movements

```sql
CREATE TABLE stock_movements (
    movement_id BIGSERIAL PRIMARY KEY,
    item_id VARCHAR(20) NOT NULL REFERENCES items(item_id),
    movement_type VARCHAR(10) NOT NULL CHECK (movement_type IN ('STOCK_IN', 'STOCK_OUT')),
    quantity INT NOT NULL CHECK (quantity > 0),
    movement_date DATE NOT NULL,
    remarks VARCHAR(255),
    balance_after_movement INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### purchase_suggestions

```sql
CREATE TABLE purchase_suggestions (
    suggestion_id BIGSERIAL PRIMARY KEY,
    item_id VARCHAR(20) NOT NULL REFERENCES items(item_id),
    coverage_days INT NOT NULL,
    current_stock INT NOT NULL,
    required_stock INT NOT NULL,
    suggested_order_quantity INT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/items` | Create a new item |
| GET | `/api/items` | Get all items |
| GET | `/api/items/{item_id}` | Get item details |
| PUT | `/api/items/{item_id}` | Update item details |
| DELETE | `/api/items/{item_id}` | Delete an item |
| POST | `/api/movements` | Record stock-in or stock-out |
| GET | `/api/movements/item/{item_id}` | Get movement history of an item |
| GET | `/api/reorder/alerts` | Get stockout-risk items |
| POST | `/api/reorder/suggestions` | Generate reorder suggestions |
| GET | `/api/reorder/suggestions?coverage_days=30` | Get reorder suggestions |
| GET | `/api/reports/abc` | Get ABC classification |
| GET | `/api/reports/expiring-batches` | Get expired or expiring batches |

## Sample API Request

### Create Item

```json
POST /api/items
{
  "item_id": "ITEM-001",
  "item_name": "Wireless Mouse",
  "current_stock": 40,
  "average_daily_usage": 10,
  "supplier_lead_time_days": 7,
  "reorder_level": 70,
  "unit_price": 750
}
```

### Record Stock Movement

```json
POST /api/movements
{
  "item_id": "ITEM-001",
  "movement_type": "STOCK_OUT",
  "quantity": 10,
  "movement_date": "2026-10-14",
  "remarks": "Sale order #1023"
}
```

## Project Structure

```text
stocksense/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routes/
│   │   ├── services/
│   │   └── database.py
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## Setup Instructions

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend will run at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will run at:

```text
http://localhost:3000
```

### Docker Setup

```bash
docker compose up --build
```

## User Roles

| Role | Permissions |
|---|---|
| Admin | Manage items, users, movements, and reports |
| Inventory Manager | Manage items, record movements, view reorder suggestions |
| Viewer | View stock, alerts, history, and reports |

## Validation Rules

- Stock-out quantity cannot exceed available stock
- Quantity must be greater than zero
- Item ID must be unique
- Supplier lead time cannot be negative
- Average daily usage cannot be negative
- Stock balance must always be zero or positive

## Testing Checklist

- Create, update, and delete items
- Record valid stock-in and stock-out movements
- Prevent stock-out when quantity exceeds available stock
- Verify updated stock balance after every movement
- Test stockout-risk flagging
- Test reorder quantity calculation
- Verify full movement history
- Test ABC classification
- Test expired batch alerts

## Future Enhancements

- Purchase-order generation
- Supplier performance tracking
- Multi-warehouse support
- Barcode and QR-code scanning
- Email or WhatsApp reorder alerts
- Machine-learning-based demand forecasting
- Dashboard with stock-value and dead-stock analysis

## Interview Talking Points

- Reorder-point logic and lead-time demand
- Forecasting using average daily usage
- Inventory movement logs and auditability
- Safety stock and demand variability
- ABC inventory classification
- Batch expiry tracking
- Preventing negative stock and data inconsistency