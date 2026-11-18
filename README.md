# StockSense (CP-012)
**Predictive Inventory Reorder Engine (E-Commerce and Retail, Intermediate level)**

StockSense is a high-reliability, zero-external-dependency Python command-line engine that analyzes historical sales transactions and product inventory to forecast customer demand, calculate statistical safety stock and reorder points, determine economic batch replenishment quantities, and prioritize stock reorders by operational urgency.

---

## Features
- **Auto-Detecting File Loader**: Parses and validates product and sales records in both `.csv` and `.json` formats.
- **Statistical Demand Forecasting**: Computes moving average daily demand and standard deviation over a sliding $N$-day window (filling days without transactions as 0 demand).
- **Outlier Capping**: Optional `--cap-outliers` flag caps sudden demand spikes at $\mu + 3\sigma$.
- **Automated Reorder Point (ROP)**: Integrates supplier lead times and configurable $Z$-score service levels (default 95% / $Z=1.65$).
- **Batch-Rounded EOQ**: Recommends Economic Order Quantities based on unit cost, annual demand, and order holding costs, respecting supplier `min_order_qty` constraints.
- **Urgency Classification**: Categorizes SKUs into `CRITICAL`, `REORDER`, `OK`, and `OVERSTOCK` with ANSI terminal colors and aligned tabular reporting.
- **Reorder List Export**: Filters and exports actionable replenishment batches (`CRITICAL` and `REORDER`) to CSV.
- **Interactive Terminal Menu**: Inspect forecasts per SKU, update live stock, record sales transactions, and re-run simulations.

---

## Project Structure

```text
stocksense/
├── stocksense.py          # CLI entry point, argument parser, and interactive menu
├── loader.py              # CSV/JSON file reading, schema validation, and edge-case handling
├── forecast.py            # Moving average, standard deviation, and outlier capping
├── rules.py               # Safety stock, ROP, EOQ, and status classification logic
├── report.py              # Terminal table alignment, ANSI color formatting, and CSV export
├── data/
│   ├── products.csv       # Sample product catalog (12 products)
│   └── sales.csv          # Sample sales transactions (60 days)
├── tests/                 # Comprehensive pytest test suite
│   ├── test_forecast.py
│   ├── test_rules.py
│   ├── test_loader.py
│   └── test_cli_and_report.py
└── README.md              # Project documentation and formulas
```

---

## Mathematical Formulas & Core Logic

### 1. Moving Average Daily Demand
Over the last $N$ days (configured via `--window`, default $30$):
$$\bar{D} = \frac{\sum_{i=1}^{N} \text{sales}_i}{N}$$
Days within the window with no sales count as $0.0$.

### 2. Daily Demand Standard Deviation
$$s = \sqrt{\frac{1}{N - 1} \sum_{i=1}^{N} (\text{sales}_i - \bar{D})^2} \quad (N \ge 2)$$

### 3. Outlier Capping (Optional `--cap-outliers`)
When enabled, daily sales exceeding the upper statistical threshold are capped:
$$\text{Threshold} = \bar{D} + 3s$$

### 4. Safety Stock ($SS$)
$$SS = Z \times s \times \sqrt{\text{lead\_time\_days}}$$
Where $Z = 1.65$ corresponds to a 95% service level (configurable via `--z-score`).

### 5. Reorder Point ($ROP$)
$$ROP = (\bar{D} \times \text{lead\_time\_days}) + SS$$

### 6. Days of Cover ($DoC$)
$$\text{Days of Cover} = \frac{\text{current\_stock}}{\bar{D}} \quad (\text{if } \bar{D} > 0)$$
*(If $\bar{D} = 0$, avoids division by zero and reports `N/A`).*

### 7. Economic Order Quantity ($EOQ$) & Batch Rounding
$$\text{Annual Demand } (D_a) = \bar{D} \times 365$$
$$\text{Holding Cost } (H) = \text{holding\_cost\_pct} \times \text{unit\_cost} \quad (\text{default } 20\%)$$
$$\text{Raw EOQ} = \sqrt{\frac{2 \times D_a \times \text{order\_cost}}{H}} \quad (\text{order\_cost default } \$500)$$
$$\text{EOQ} = \lceil \text{Raw EOQ} \rceil$$
$$\text{Order Qty} = \max(\text{min\_order\_qty}, \lceil \text{EOQ} / \text{min\_order\_qty} \rceil \times \text{min\_order\_qty})$$

### 8. Status Priority Order
Status is evaluated strictly in this sequence:
1. **CRITICAL**: `current_stock == 0` or `days_of_cover < lead_time_days`
2. **OVERSTOCK**: `days_of_cover > 90`
3. **REORDER**: `current_stock <= ROP`
4. **OK**: otherwise

---

## Installation & Requirements

StockSense uses **only** the Python Standard Library (`argparse`, `csv`, `json`, `statistics`, `math`, `datetime`) plus `pytest` for tests.

Ensure Python 3.8+ is installed.

```bash
# Install pytest for running tests
pip install pytest
```

---

## CLI Usage

### Basic Reorder Report
Run the reorder engine with the default 30-day moving window:
```bash
python stocksense.py --products data/products.csv --sales data/sales.csv --window 30
```

### Export Actionable Reorder List
Export only `CRITICAL` and `REORDER` items to CSV:
```bash
python stocksense.py --products data/products.csv --sales data/sales.csv --export reorder_list.csv
```

### Enable Outlier Capping and Disable Colors
```bash
python stocksense.py --products data/products.csv --sales data/sales.csv --cap-outliers --no-color
```

### Advanced Configurable Parameters
```bash
python stocksense.py \
  --products data/products.csv \
  --sales data/sales.csv \
  --window 45 \
  --z-score 1.96 \
  --order-cost 400 \
  --holding-cost-pct 0.25 \
  --export my_reorder.csv
```

### CLI Flag Reference
| Flag | Type | Default | Description |
|---|---|---|---|
| `--products` | `string` | *(Required)* | Path to products file (`.csv` or `.json`) |
| `--sales` | `string` | *(Required)* | Path to sales transactions file (`.csv` or `.json`) |
| `--window` | `int` | `30` | Moving average window in days |
| `--export` | `string` | `None` | CSV destination for CRITICAL and REORDER items |
| `--menu` | `flag` | `False` | Launch interactive terminal menu |
| `--no-color` | `flag` | `False` | Disable ANSI color codes in table output |
| `--cap-outliers`| `flag` | `False` | Cap daily sales outliers at $\mu + 3\sigma$ |
| `--z-score` | `float` | `1.65` | Service level $Z$-score (e.g. 1.65 for 95%, 1.96 for 97.5%) |
| `--order-cost` | `float` | `500.0` | Fixed cost per replenishment order |
| `--holding-cost-pct` | `float` | `0.20` | Annual holding cost percentage of unit cost |
| `--reference-date` | `string` | `None` | YYYY-MM-DD anchor date (defaults to latest sales date) |

---

## Interactive Menu

Launch the interactive console with `--menu`:
```bash
python stocksense.py --products data/products.csv --sales data/sales.csv --menu
```

### Menu Options:
1. **Show reorder report**: Computes and displays the urgency-sorted inventory table and summary.
2. **Add sales record**: Records a new transaction (SKU, date, quantity sold) and integrates it into subsequent calculations.
3. **Update stock**: Modifies on-hand stock for a SKU and updates days of cover and status.
4. **Show item forecast (by SKU)**: Displays item details, sales statistics, ROP, safety stock, and recommended batch sizes.
5. **Export reorder list**: Exports current replenishment recommendations to a chosen CSV path.
6. **Exit**: Gracefully terminates the session.

---

## Terminal Output Sample

```text
SKU     | Item                              | Stock | AvgDemand |  ROP | Cover(d) |  Status   | Order Qty
--------+-----------------------------------+-------+-----------+------+----------+-----------+----------
SKU-001 | Ergonomic Wireless Mouse          |     0 |      5.60 | 62.2 |      0.0 | CRITICAL  |       640
SKU-002 | Mechanical RGB Keyboard           |    12 |      3.73 | 64.2 |      3.2 | CRITICAL  |       330
SKU-003 | Ultra-Wide Gaming Monitor         |    20 |      1.93 | 26.3 |     10.3 |  REORDER  |       110
SKU-010 | Bluetooth Conference Speakerphone |    18 |      1.43 | 21.3 |     12.6 |  REORDER  |       180
SKU-005 | Noise-Cancelling Headphones       |    28 |      2.20 | 33.7 |     12.7 |  REORDER  |       195
SKU-004 | USB-C Multiport Dock              |    35 |      2.97 | 30.5 |     11.8 |    OK     |         0
SKU-009 | Fast Qi Wireless Charger          |    75 |      1.40 | 18.7 |     53.6 |    OK     |         0
SKU-006 | Anodized Aluminum Laptop Stand    |    85 |      1.57 | 22.9 |     54.3 |    OK     |         0
SKU-007 | 1080p HD Streaming Webcam         |   120 |      1.73 | 17.1 |     69.2 |    OK     |         0
SKU-012 | Smart IoT Power Strip 6-Outlet    |    25 |      0.00 |  0.0 |      N/A |    OK     |         0
SKU-008 | Braided HDMI 2.1 Cable 2m         |   650 |      1.47 | 10.9 |    443.2 | OVERSTOCK |         0
SKU-011 | Microfiber Screen Cleaning Cloths |  1500 |      2.93 | 26.8 |    511.4 | OVERSTOCK |         0
--------+-----------------------------------+-------+-----------+------+----------+-----------+----------
Summary: 2 critical, 3 reorder, 5 ok, 2 overstock
```

---

## Running the Unit Tests

Execute the full automated test suite with `pytest`:
```bash
python -m pytest -v
```

The test suite covers:
- Hand-calculated moving averages and standard deviations.
- Handling of days with no sales as 0.0.
- Outlier detection and capping.
- Safety stock and ROP calculations.
- Economic Order Quantity (EOQ) with `min_order_qty` thresholding and multiple rounding.
- Strict evaluation order of all status rules (`CRITICAL`, `OVERSTOCK`, `REORDER`, `OK`).
- Edge cases: items with zero demand, brand new products with no sales history, division-by-zero protection.
- Input validation: missing SKUs, duplicate SKUs, negative stocks/costs/quantities, invalid dates, non-numeric values, and unknown SKUs in sales logs.
