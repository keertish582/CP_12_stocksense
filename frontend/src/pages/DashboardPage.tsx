import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Package,
  AlertTriangle,
  AlertOctagon,
  ClipboardList,
  TrendingUp,
  CircleDollarSign,
  ArrowUpRight,
  Clock,
  Sparkles,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { api } from '../services/api';
import {
  DashboardSummary,
  AttentionItem,
  SalesVsForecastPoint,
  StockMovement,
} from '../types';
import { Currency } from '../components/Currency';
import { Badge } from '../components/Badge';

export const DashboardPage: React.FC = () => {
  // 1. Fetch Dashboard KPI Summary
  const { data: summary, isLoading: isSummaryLoading, refetch: refetchSummary } = useQuery<DashboardSummary>({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => api.get<DashboardSummary>('/dashboard/summary'),
  });

  // 2. Fetch Attention Items
  const { data: attentionItems, isLoading: isAttentionLoading } = useQuery<AttentionItem[]>({
    queryKey: ['dashboard', 'attention'],
    queryFn: () => api.get<AttentionItem[]>('/dashboard/attention?limit=6'),
  });

  // 3. Fetch Sales vs Forecast Trend
  const { data: trendData, isLoading: isTrendLoading } = useQuery<SalesVsForecastPoint[]>({
    queryKey: ['dashboard', 'sales-vs-forecast'],
    queryFn: () => api.get<SalesVsForecastPoint[]>('/dashboard/sales-vs-forecast?days=21'),
  });

  // 4. Fetch Recent Movements
  const { data: recentMovements, isLoading: isMovementsLoading } = useQuery<StockMovement[]>({
    queryKey: ['dashboard', 'recent-movements'],
    queryFn: () => api.get<StockMovement[]>('/dashboard/recent-movements?limit=7'),
  });

  const formattedChartData = (trendData || []).map((pt) => ({
    date: pt.date.slice(5), // MM-DD
    'Actual Sales': pt.actual_sales,
    'Forecast Demand': parseFloat(String(pt.forecast_sales)),
  }));

  return (
    <div className="space-y-8">
      {/* Page Title & Status Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Operations Overview</h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time warehouse inventory, demand projection velocity, and replenishment pipeline.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {summary?.latest_forecast_run && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-teal-50 border border-teal-200 text-teal-800 text-xs font-medium">
              <Sparkles className="w-3.5 h-3.5 text-teal-600" />
              <span>Forecast Freshness: {summary.latest_forecast_run.data_cutoff}</span>
            </div>
          )}
          <button
            onClick={() => refetchSummary()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 text-xs font-semibold shadow-sm transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {/* Active Products */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Catalog</span>
            <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
              <Package className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {isSummaryLoading ? '...' : summary?.active_products_count}
          </div>
          <span className="text-[11px] text-slate-500 font-medium">Monitored SKUs</span>
        </div>

        {/* Low Stock Alerts */}
        <div className="bg-white rounded-2xl p-5 border border-amber-200/80 shadow-sm bg-gradient-to-br from-white to-amber-50/30">
          <div className="flex items-center justify-between text-amber-600 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Low Stock</span>
            <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center text-amber-700">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-amber-900">
            {isSummaryLoading ? '...' : summary?.low_stock_products_count}
          </div>
          <span className="text-[11px] text-amber-700 font-medium">At or below ROP</span>
        </div>

        {/* Stockout Risk */}
        <div className="bg-white rounded-2xl p-5 border border-rose-200/80 shadow-sm bg-gradient-to-br from-white to-rose-50/30">
          <div className="flex items-center justify-between text-rose-600 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Stockout Risk</span>
            <div className="w-8 h-8 rounded-lg bg-rose-100 flex items-center justify-center text-rose-700">
              <AlertOctagon className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-rose-900">
            {isSummaryLoading ? '...' : summary?.stockout_risk_count}
          </div>
          <span className="text-[11px] text-rose-700 font-medium">Critical attention needed</span>
        </div>

        {/* Open POs */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Open Orders</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
              <ClipboardList className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {isSummaryLoading ? '...' : summary?.open_purchase_orders_count}
          </div>
          <span className="text-[11px] text-blue-600 font-medium">Inbound pipeline</span>
        </div>

        {/* Valuation */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Inventory Value</span>
            <div className="w-8 h-8 rounded-lg bg-teal-50 flex items-center justify-center text-teal-600">
              <CircleDollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-lg font-bold text-slate-900 truncate">
            {isSummaryLoading ? '...' : <Currency value={summary?.total_inventory_valuation} />}
          </div>
          <span className="text-[11px] text-slate-500 font-medium">Cost basis</span>
        </div>

        {/* Today's Sales */}
        <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Today's Sales</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="text-lg font-bold text-slate-900 truncate">
            {isSummaryLoading ? '...' : <Currency value={summary?.total_sales_today} />}
          </div>
          <span className="text-[11px] text-emerald-600 font-medium">Recorded revenue</span>
        </div>
      </div>

      {/* Main Grid: Chart & Priority Attention Table */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Actual Sales vs Forecast Chart */}
        <div className="xl:col-span-2 bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-bold text-slate-900">Actual Sales vs. Forecast Demand</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Daily aggregated store velocity compared against predictive forecast model
              </p>
            </div>
            <Link
              to="/forecasts"
              className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center gap-1"
            >
              <span>Explore Forecasts</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="h-72 w-full">
            {isTrendLoading ? (
              <div className="h-full flex items-center justify-center text-sm text-slate-400">
                Loading trajectory trend...
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={formattedChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="date" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      borderColor: '#334155',
                      borderRadius: '12px',
                      color: '#fff',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                  <Bar dataKey="Actual Sales" fill="#0d9488" radius={[4, 4, 0, 0]} barSize={16} />
                  <Line
                    type="monotone"
                    dataKey="Forecast Demand"
                    stroke="#8b5cf6"
                    strokeWidth={2.5}
                    dot={{ fill: '#8b5cf6', r: 3 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Recent Stock Movement Feed */}
        <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-base font-bold text-slate-900">Recent Movements</h3>
              <p className="text-xs text-slate-500 mt-0.5">Auditable inventory ledger</p>
            </div>
            <Link
              to="/inventory"
              className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center gap-1"
            >
              <span>Ledger</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="flex-1 space-y-3.5 overflow-y-auto max-h-80 pr-1">
            {isMovementsLoading ? (
              <div className="text-xs text-slate-400 py-6 text-center">Loading ledger...</div>
            ) : recentMovements && recentMovements.length > 0 ? (
              recentMovements.map((m) => (
                <div
                  key={m.id}
                  className="p-3 rounded-xl bg-slate-50 hover:bg-slate-100/80 border border-slate-100 transition flex items-center justify-between text-xs"
                >
                  <div className="min-w-0 pr-2">
                    <p className="font-semibold text-slate-800 truncate">{m.product_name}</p>
                    <div className="flex items-center gap-1.5 mt-1 text-[11px] text-slate-500">
                      <span className="font-mono text-slate-400">{m.product_sku}</span>
                      <span>•</span>
                      <span>{m.movement_type}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <span
                      className={`font-bold font-mono text-xs ${
                        m.quantity_delta > 0 ? 'text-emerald-600' : 'text-slate-700'
                      }`}
                    >
                      {m.quantity_delta > 0 ? `+${m.quantity_delta}` : m.quantity_delta}
                    </span>
                    <p className="text-[10px] text-slate-400 mt-0.5">Bal: {m.balance_after}</p>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-400 py-8 text-center">No movements recorded yet.</div>
            )}
          </div>
        </div>
      </div>

      {/* Inventory Attention Table */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-base font-bold text-slate-900">Inventory Attention Table</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Items flagged with stockout risk, below reorder point, or currently out of stock
            </p>
          </div>
          <Link
            to="/recommendations"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-teal-50 hover:bg-teal-100 text-teal-700 text-xs font-semibold border border-teal-200 transition"
          >
            <span>Review Reorder Recommendations</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-100 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="pb-3 pl-2">Product / SKU</th>
                <th className="pb-3">Category</th>
                <th className="pb-3 text-right">Available</th>
                <th className="pb-3 text-right">Open Inbound</th>
                <th className="pb-3 text-right">Position</th>
                <th className="pb-3 text-right">ROP</th>
                <th className="pb-3">Status</th>
                <th className="pb-3 text-right pr-2">Suggested Order</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {isAttentionLoading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    Scanning inventory levels...
                  </td>
                </tr>
              ) : attentionItems && attentionItems.length > 0 ? (
                attentionItems.map((item) => (
                  <tr key={item.product_id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3.5 pl-2 font-medium text-slate-900">
                      <div>{item.name}</div>
                      <div className="text-[11px] font-mono text-slate-400 mt-0.5">{item.sku}</div>
                    </td>
                    <td className="py-3.5 text-slate-500">{item.category_name || '—'}</td>
                    <td className="py-3.5 text-right font-semibold font-mono">{item.available_qty}</td>
                    <td className="py-3.5 text-right font-mono text-slate-600">
                      {item.eligible_open_inbound > 0 ? `+${item.eligible_open_inbound}` : '0'}
                    </td>
                    <td className="py-3.5 text-right font-bold font-mono text-slate-900">
                      {item.available_qty + item.eligible_open_inbound}
                    </td>
                    <td className="py-3.5 text-right font-mono text-slate-500">{item.reorder_point}</td>
                    <td className="py-3.5">
                      <Badge type="stock" value={item.stock_status} />
                    </td>
                    <td className="py-3.5 text-right pr-2">
                      {item.suggested_qty > 0 ? (
                        <span className="font-bold font-mono text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                          {item.suggested_qty} units
                        </span>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    All stock positions are currently healthy!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
