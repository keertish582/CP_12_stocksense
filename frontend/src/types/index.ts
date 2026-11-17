export type UserRole = 'ADMIN' | 'MANAGER' | 'STAFF';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Category {
  id: number;
  name: string;
  description?: string;
  created_at: string;
}

export interface Supplier {
  id: number;
  name: string;
  contact_name?: string;
  email?: string;
  phone?: string;
  address?: string;
  lead_time_days: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductSupplier {
  id: number;
  product_id: number;
  supplier_id: number;
  supplier_name?: string;
  lead_time_days: number;
  minimum_order_qty: number;
  pack_size: number;
  unit_cost: string | number;
  is_preferred: boolean;
  created_at: string;
}

export interface Product {
  id: number;
  sku: string;
  name: string;
  category_id?: number;
  category_name?: string;
  unit: string;
  selling_price: string | number;
  safety_stock: number;
  min_reorder_qty: number;
  manual_daily_demand?: string | number | null;
  lead_time_days: number;
  is_active: boolean;
  preferred_supplier_id?: number;
  preferred_supplier_name?: string;
  unit_cost?: string | number;
  moq?: number;
  pack_size?: number;
  current_on_hand: number;
  current_reserved: number;
  current_available: number;
  created_at: string;
  updated_at: string;
  suppliers?: ProductSupplier[];
}

export interface InventoryBalance {
  id: number;
  product_id: number;
  product_sku: string;
  product_name: string;
  category_name?: string;
  warehouse_id: number;
  warehouse_code: string;
  warehouse_name: string;
  on_hand_qty: number;
  reserved_qty: number;
  available_qty: number;
  eligible_open_inbound: number;
  inventory_position: number;
  reorder_point: number;
  stock_status: 'HEALTHY' | 'REORDER_SOON' | 'STOCKOUT_RISK' | 'OUT_OF_STOCK';
  updated_at: string;
}

export interface StockMovement {
  id: number;
  product_id: number;
  product_sku: string;
  product_name: string;
  warehouse_id: number;
  warehouse_code: string;
  quantity_delta: number;
  movement_type: string;
  reference_type?: string;
  reference_id?: string;
  balance_after: number;
  reason?: string;
  created_by_name?: string;
  created_at: string;
}

export interface SaleItem {
  id: number;
  product_id: number;
  product_sku: string;
  product_name: string;
  quantity: number;
  unit_price: string | number;
  subtotal: string | number;
}

export interface Sale {
  id: number;
  external_sale_id?: string;
  sale_date: string;
  total_amount: string | number;
  channel: string;
  notes?: string;
  created_by_name?: string;
  created_at: string;
  items: SaleItem[];
}

export interface CSVPreviewResult {
  total_rows: number;
  valid_rows_count: number;
  error_rows_count: number;
  errors: Array<{
    row_number: number;
    external_sale_id?: string;
    sku?: string;
    error: string;
  }>;
  preview_rows: Array<{
    row_number: number;
    external_sale_id?: string;
    sku: string;
    sale_date: string;
    quantity: number;
    unit_price: string;
  }>;
}

export interface ImportJob {
  id: number;
  job_id: string;
  filename: string;
  file_type: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  total_rows: number;
  processed_rows: number;
  error_count: number;
  error_details?: any[];
  created_at: string;
  completed_at?: string;
}

export interface HistoricalActualPoint {
  date: string;
  actual_qty: number;
  is_stockout: boolean;
}

export interface ForecastPoint {
  date: string;
  forecast_qty: string | number;
}

export interface ProductForecastDetail {
  product_id: number;
  product_sku: string;
  product_name: string;
  method: string;
  data_cutoff: string;
  mae?: string | number | null;
  wape?: string | number | null;
  is_cold_start: boolean;
  has_censored_demand: boolean;
  projected_stockout_date?: string | null;
  current_available_stock: number;
  historical_actuals: HistoricalActualPoint[];
  future_forecasts: ForecastPoint[];
}

export interface ReorderRecommendation {
  id: number;
  product_id: number;
  product_sku: string;
  product_name: string;
  category_name?: string;
  warehouse_id: number;
  warehouse_code: string;
  forecast_run_id?: number;
  inventory_position_snapshot: number;
  on_hand_snapshot: number;
  eligible_inbound_snapshot: number;
  reorder_point: number;
  target_stock: number;
  lead_time_demand: string | number;
  safety_stock: number;
  raw_order_qty: number;
  suggested_qty: number;
  supplier_id?: number;
  supplier_name?: string;
  pack_size: number;
  moq: number;
  unit_cost: string | number;
  total_estimated_cost: string | number;
  projected_stockout_date?: string | null;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'PENDING' | 'APPROVED' | 'DEFERRED' | 'DISMISSED';
  calculation_details?: {
    lead_time_days: number;
    coverage_days: number;
    lead_time_demand: number;
    safety_stock: number;
    reorder_point: number;
    target_stock: number;
    formula: string;
    rounding_explanation: string;
    eligible_purchase_orders: any[];
    excluded_purchase_orders: any[];
    warnings: string[];
    projected_stockout_date?: string;
    action_reason?: string;
  };
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PurchaseOrderItem {
  id: number;
  product_id: number;
  product_sku: string;
  product_name: string;
  quantity_ordered: number;
  quantity_received: number;
  remaining_qty: number;
  unit_cost: string | number;
  subtotal: string | number;
}

export interface PurchaseOrder {
  id: number;
  po_number: string;
  supplier_id: number;
  supplier_name: string;
  warehouse_id: number;
  warehouse_code: string;
  recommendation_id?: number;
  status: 'DRAFT' | 'PLACED' | 'PARTIALLY_RECEIVED' | 'RECEIVED' | 'CANCELLED';
  expected_delivery_date?: string | null;
  notes?: string;
  total_amount: string | number;
  placed_at?: string | null;
  completed_at?: string | null;
  created_by_name?: string;
  created_at: string;
  updated_at: string;
  items: PurchaseOrderItem[];
}

export interface GoodsReceiptItem {
  id: number;
  po_item_id: number;
  product_id: number;
  product_sku: string;
  product_name: string;
  quantity_received: number;
  unit_cost: string | number;
}

export interface GoodsReceipt {
  id: number;
  receipt_number: string;
  purchase_order_id: number;
  po_number: string;
  warehouse_id: number;
  warehouse_code: string;
  received_date: string;
  notes?: string;
  created_by_name?: string;
  created_at: string;
  items: GoodsReceiptItem[];
}

export interface DashboardSummary {
  active_products_count: number;
  low_stock_products_count: number;
  stockout_risk_count: number;
  open_purchase_orders_count: number;
  total_inventory_valuation: string | number;
  total_sales_today: string | number;
  latest_forecast_run?: {
    run_id: string;
    status: string;
    data_cutoff: string;
    completed_at?: string;
    summary?: any;
  } | null;
}

export interface AttentionItem {
  product_id: number;
  sku: string;
  name: string;
  category_name?: string;
  on_hand_qty: number;
  reserved_qty: number;
  available_qty: number;
  eligible_open_inbound: number;
  reorder_point: number;
  stock_status: string;
  projected_stockout_date?: string | null;
  suggested_qty: number;
}

export interface SalesVsForecastPoint {
  date: string;
  actual_sales: number;
  forecast_sales: string | number;
}

export interface ValuationItem {
  product_id: number;
  sku: string;
  name: string;
  category_name?: string;
  on_hand_qty: number;
  unit_cost: string | number;
  total_valuation: string | number;
}

export type InventoryValuationItem = ValuationItem;

export interface SalesReportRow {
  sale_date: string;
  product_sku: string;
  product_name: string;
  category_name?: string;
  quantity_sold: number;
  total_revenue: string | number;
}

export type SalesReportItem = SalesReportRow;

export interface ForecastEvaluationReportItem {
  product_id: number;
  sku: string;
  name: string;
  best_method: string;
  mae?: string | number | null;
  wape?: string | number | null;
  data_points_count: number;
  status: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
