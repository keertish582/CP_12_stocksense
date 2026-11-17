import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { Currency } from '../components/Currency';
import { InventoryValuationItem, SalesReportItem, StockMovement, Paginated, Category, ForecastEvaluationReportItem } from '../types';
import { 
  BarChart3, FileSpreadsheet, Download, Calendar, Filter, 
  DollarSign, Package, ArrowUpRight, ArrowDownRight, RefreshCw, AlertCircle, Info, TrendingUp 
} from 'lucide-react';

export const ReportsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'valuation' | 'sales' | 'movements' | 'forecasts'>('valuation');

  // Sales filters
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');

  // Stock movements filter
  const [movementPage, setMovementPage] = useState(1);
  const [movementType, setMovementType] = useState<string>('');

  // Categories for filter
  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: () => api.get<Category[]>('/products/categories'),
  });

  // 1. Valuation query
  const { 
    data: valuationData, 
    isLoading: valuationLoading, 
    refetch: refetchValuation 
  } = useQuery({
    queryKey: ['reports-valuation'],
    queryFn: () => api.get<InventoryValuationItem[]>('/reports/valuation'),
    enabled: activeTab === 'valuation',
  });

  // 2. Sales query
  const { 
    data: salesData, 
    isLoading: salesLoading, 
    refetch: refetchSales 
  } = useQuery({
    queryKey: ['reports-sales', startDate, endDate, selectedCategory],
    queryFn: () =>
      api.get<SalesReportItem[]>('/reports/sales', {
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        category_id: selectedCategory ? parseInt(selectedCategory) : undefined,
      }),
    enabled: activeTab === 'sales',
  });

  // 3. Stock movements query
  const { 
    data: movementsData, 
    isLoading: movementsLoading, 
    refetch: refetchMovements 
  } = useQuery({
    queryKey: ['reports-movements', movementPage, movementType],
    queryFn: () =>
      api.get<Paginated<StockMovement>>('/inventory/movements', {
        page: movementPage,
        page_size: 50,
        movement_type: movementType || undefined,
      }),
    enabled: activeTab === 'movements',
  });

  // 4. Forecast Evaluation query
  const {
    data: forecastEvalData,
    isLoading: forecastEvalLoading,
    refetch: refetchForecastEval
  } = useQuery({
    queryKey: ['reports-forecast-eval'],
    queryFn: () => api.get<ForecastEvaluationReportItem[]>('/reports/forecast-evaluation'),
    enabled: activeTab === 'forecasts',
  });

  const handleExportSalesCSV = async () => {
    try {
      await api.downloadFile('/reports/sales/export-csv', 'sales_report.csv', {
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        category_id: selectedCategory ? Number(selectedCategory) : undefined,
      });
    } catch (err: any) {
      alert(err.message || 'Failed to export sales CSV');
    }
  };

  const handleExportMovementsCSV = async () => {
    try {
      await api.downloadFile('/reports/movements/export-csv', 'stock_ledger.csv');
    } catch (err: any) {
      alert(err.message || 'Failed to export ledger CSV');
    }
  };

  // Valuation computations
  const totalValuation = (valuationData || []).reduce(
    (acc, item) => acc + Number(item.total_valuation || 0),
    0
  );
  const totalUnits = (valuationData || []).reduce(
    (acc, item) => acc + Number(item.on_hand_qty || 0),
    0
  );

  // Sales computations
  const totalSalesRevenue = (salesData || []).reduce(
    (acc, item) => acc + Number(item.total_revenue || 0),
    0
  );
  const totalSalesUnits = (salesData || []).reduce(
    (acc, item) => acc + Number(item.quantity_sold || 0),
    0
  );

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <BarChart3 className="w-7 h-7 text-teal-600" />
            Financial & Operational Reports
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Audit inventory valuation, historical revenue trends, and stock ledger movements.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {activeTab === 'sales' && (
            <button
              onClick={handleExportSalesCSV}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50 transition shadow-sm"
            >
              <Download className="w-4 h-4 text-slate-500" />
              Export Sales CSV
            </button>
          )}
          {activeTab === 'movements' && (
            <button
              onClick={handleExportMovementsCSV}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50 transition shadow-sm"
            >
              <Download className="w-4 h-4 text-slate-500" />
              Export Ledger CSV
            </button>
          )}
          <button
            onClick={() => {
              if (activeTab === 'valuation') refetchValuation();
              if (activeTab === 'sales') refetchSales();
              if (activeTab === 'movements') refetchMovements();
              if (activeTab === 'forecasts') refetchForecastEval();
            }}
            className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600 transition"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-6">
        <button
          onClick={() => setActiveTab('valuation')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'valuation'
              ? 'border-teal-600 text-teal-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <DollarSign className="w-4 h-4" />
          Inventory Valuation
        </button>
        <button
          onClick={() => setActiveTab('sales')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'sales'
              ? 'border-teal-600 text-teal-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          Sales by Product & Date
        </button>
        <button
          onClick={() => setActiveTab('movements')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'movements'
              ? 'border-teal-600 text-teal-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Package className="w-4 h-4" />
          Stock Movement Ledger
        </button>
        <button
          onClick={() => setActiveTab('forecasts')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'forecasts'
              ? 'border-teal-600 text-teal-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          Forecast Model Evaluation
        </button>
      </div>

      {/* Tab 1: Valuation */}
      {activeTab === 'valuation' && (
        <div className="space-y-6">
          {/* Methodology Banner */}
          <div className="p-4 bg-teal-50 border border-teal-200 rounded-xl flex items-start gap-3">
            <Info className="w-5 h-5 text-teal-600 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-teal-900 leading-relaxed">
              <span className="font-semibold text-teal-950">Cost Basis Methodology: </span>
              Inventory valuation is calculated using the simple replacement cost basis (
              <code className="bg-teal-100 px-1 py-0.5 rounded font-mono text-[11px]">
                On-Hand Units × Preferred Supplier Unit Cost (INR)
              </code>
              ). Reserved stock is physically on hand and included in total asset value. Zero or unpriced items are valued at ₹0.00.
            </div>
          </div>

          {/* Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Total Valuation (INR)
              </div>
              <div className="text-2xl font-bold text-slate-900 mt-2">
                <Currency amount={totalValuation} />
              </div>
              <div className="text-xs text-slate-400 mt-1">Based on on-hand stock & vendor unit costs</div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Total On-Hand Inventory
              </div>
              <div className="text-2xl font-bold text-slate-900 mt-2">
                {totalUnits.toLocaleString()} units
              </div>
              <div className="text-xs text-slate-400 mt-1">Across all active catalog products</div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Cataloged SKUs
              </div>
              <div className="text-2xl font-bold text-slate-900 mt-2">
                {valuationData?.length || 0}
              </div>
              <div className="text-xs text-slate-400 mt-1">Products actively evaluated</div>
            </div>
          </div>

          {/* Valuation Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {valuationLoading ? (
              <div className="py-20 text-center text-slate-500">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto text-teal-600 mb-2" />
                Calculating inventory valuation...
              </div>
            ) : !valuationData || valuationData.length === 0 ? (
              <div className="py-16 text-center text-slate-500">
                <Package className="w-10 h-10 mx-auto text-slate-300 mb-2" />
                <p>No inventory valuation records found.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">SKU</th>
                      <th className="py-3 px-4">Product Name</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4 text-right">On-Hand Qty</th>
                      <th className="py-3 px-4 text-right">Unit Cost</th>
                      <th className="py-3 px-4 text-right">Total Valuation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {valuationData.map((row) => (
                      <tr key={row.product_id} className="hover:bg-slate-50/80 transition">
                        <td className="py-3 px-4 font-mono font-semibold text-slate-900 text-xs">
                          {row.sku}
                        </td>
                        <td className="py-3 px-4 text-slate-800 font-medium">{row.name}</td>
                        <td className="py-3 px-4 text-slate-500">{row.category_name || '—'}</td>
                        <td className="py-3 px-4 text-right font-semibold text-slate-900">
                          {row.on_hand_qty}
                        </td>
                        <td className="py-3 px-4 text-right text-slate-600 font-mono text-xs">
                          <Currency amount={row.unit_cost} />
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-teal-700 font-mono text-xs">
                          <Currency amount={row.total_valuation} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-slate-50 border-t-2 border-slate-300 font-semibold text-slate-900 text-sm">
                    <tr>
                      <td colSpan={3} className="py-3.5 px-4 text-right">
                        Total Valuation:
                      </td>
                      <td className="py-3.5 px-4 text-right">{totalUnits.toLocaleString()}</td>
                      <td className="py-3.5 px-4"></td>
                      <td className="py-3.5 px-4 text-right font-bold text-teal-800 text-base">
                        <Currency amount={totalValuation} />
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Sales Analytics */}
      {activeTab === 'sales' && (
        <div className="space-y-6">
          {/* Filters */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-slate-400" />
              <label className="text-xs font-semibold text-slate-600">From:</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-semibold text-slate-600">To:</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              >
                <option value="">All Categories</option>
                {categories?.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>
            </div>

            {(startDate || endDate || selectedCategory) && (
              <button
                onClick={() => {
                  setStartDate('');
                  setEndDate('');
                  setSelectedCategory('');
                }}
                className="text-xs text-teal-600 hover:text-teal-700 font-semibold"
              >
                Clear Filters
              </button>
            )}
          </div>

          {/* Metrics summary */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Total Revenue
                </div>
                <div className="text-2xl font-bold text-slate-900 mt-1">
                  <Currency amount={totalSalesRevenue} />
                </div>
              </div>
              <div className="w-10 h-10 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <DollarSign className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
              <div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Total Units Sold
                </div>
                <div className="text-2xl font-bold text-slate-900 mt-1">
                  {totalSalesUnits.toLocaleString()} units
                </div>
              </div>
              <div className="w-10 h-10 rounded-full bg-teal-50 text-teal-600 flex items-center justify-center">
                <Package className="w-5 h-5" />
              </div>
            </div>
          </div>

          {/* Sales Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {salesLoading ? (
              <div className="py-20 text-center text-slate-500">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto text-teal-600 mb-2" />
                Loading sales report...
              </div>
            ) : !salesData || salesData.length === 0 ? (
              <div className="py-16 text-center text-slate-500">
                <FileSpreadsheet className="w-10 h-10 mx-auto text-slate-300 mb-2" />
                <p>No sales records found for this period.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Date</th>
                      <th className="py-3 px-4">SKU</th>
                      <th className="py-3 px-4">Product Name</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4 text-right">Units Sold</th>
                      <th className="py-3 px-4 text-right">Revenue</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {salesData.map((row, idx) => (
                      <tr key={`${row.sale_date}-${row.product_sku}-${idx}`} className="hover:bg-slate-50/80 transition">
                        <td className="py-3 px-4 font-mono text-xs text-slate-600">
                          {row.sale_date}
                        </td>
                        <td className="py-3 px-4 font-mono font-semibold text-slate-900 text-xs">
                          {row.product_sku}
                        </td>
                        <td className="py-3 px-4 text-slate-800 font-medium">{row.product_name}</td>
                        <td className="py-3 px-4 text-slate-500">{row.category_name || '—'}</td>
                        <td className="py-3 px-4 text-right font-semibold text-slate-900">
                          {row.quantity_sold}
                        </td>
                        <td className="py-3 px-4 text-right font-bold text-slate-900 font-mono text-xs">
                          <Currency amount={row.total_revenue} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="bg-slate-50 border-t-2 border-slate-300 font-semibold text-slate-900 text-sm">
                    <tr>
                      <td colSpan={4} className="py-3.5 px-4 text-right">
                        Summary:
                      </td>
                      <td className="py-3.5 px-4 text-right">{totalSalesUnits.toLocaleString()}</td>
                      <td className="py-3.5 px-4 text-right font-bold text-teal-800 text-base">
                        <Currency amount={totalSalesRevenue} />
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Stock Movement Ledger */}
      {activeTab === 'movements' && (
        <div className="space-y-6">
          {/* Movement Type Filter */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div className="flex items-center gap-3">
              <label className="text-xs font-semibold text-slate-600">Movement Type:</label>
              <select
                value={movementType}
                onChange={(e) => {
                  setMovementType(e.target.value);
                  setMovementPage(1);
                }}
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              >
                <option value="">All Movement Types</option>
                <option value="SALE">SALE (Customer Deductions)</option>
                <option value="PURCHASE_RECEIPT">PURCHASE_RECEIPT (PO Receiving)</option>
                <option value="ADJUSTMENT_IN">ADJUSTMENT_IN (Manual Increases)</option>
                <option value="ADJUSTMENT_OUT">ADJUSTMENT_OUT (Damaged/Lost/Scrap)</option>
                <option value="INITIAL">INITIAL (Opening Balances)</option>
              </select>
            </div>
            <div className="text-xs text-slate-500">
              Page {movementPage} of {movementsData?.pages || 1} (Total: {movementsData?.total || 0} entries)
            </div>
          </div>

          {/* Ledger Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {movementsLoading ? (
              <div className="py-20 text-center text-slate-500">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto text-teal-600 mb-2" />
                Loading ledger entries...
              </div>
            ) : !movementsData?.items || movementsData.items.length === 0 ? (
              <div className="py-16 text-center text-slate-500">
                <Package className="w-10 h-10 mx-auto text-slate-300 mb-2" />
                <p>No stock movement entries found.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Timestamp (UTC)</th>
                      <th className="py-3 px-4">SKU / Product</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4 text-right">Delta</th>
                      <th className="py-3 px-4 text-right">Balance After</th>
                      <th className="py-3 px-4">Reference</th>
                      <th className="py-3 px-4">Reason / Notes</th>
                      <th className="py-3 px-4">Created By</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {movementsData.items.map((m) => (
                      <tr key={m.id} className="hover:bg-slate-50/80 transition">
                        <td className="py-3 px-4 font-mono text-slate-500 whitespace-nowrap">
                          {new Date(m.created_at).toLocaleString('en-IN', {
                            timeZone: 'Asia/Kolkata',
                            year: 'numeric',
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>
                        <td className="py-3 px-4">
                          <div className="font-mono font-semibold text-slate-900">{m.product_sku}</div>
                          <div className="text-[11px] text-slate-500 truncate max-w-[180px]">{m.product_name}</div>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px]">
                          <span
                            className={`px-2 py-0.5 rounded-full font-medium ${
                              m.movement_type.includes('IN') || m.movement_type === 'PURCHASE_RECEIPT'
                                ? 'bg-emerald-50 text-emerald-700'
                                : m.movement_type === 'SALE' || m.movement_type.includes('OUT')
                                ? 'bg-rose-50 text-rose-700'
                                : 'bg-slate-100 text-slate-700'
                            }`}
                          >
                            {m.movement_type}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-bold">
                          {m.quantity_delta > 0 ? (
                            <span className="text-emerald-600 inline-flex items-center">
                              <ArrowUpRight className="w-3.5 h-3.5" />+{m.quantity_delta}
                            </span>
                          ) : (
                            <span className="text-rose-600 inline-flex items-center">
                              <ArrowDownRight className="w-3.5 h-3.5" />{m.quantity_delta}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-semibold text-slate-900">
                          {m.balance_after}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-500">
                          {m.reference_type ? `${m.reference_type} #${m.reference_id || ''}` : '—'}
                        </td>
                        <td className="py-3 px-4 text-slate-600 max-w-xs truncate">
                          {m.reason || '—'}
                        </td>
                        <td className="py-3 px-4 text-slate-500">
                          {m.created_by_name || 'System'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Pagination */}
          {movementsData && movementsData.pages > 1 && (
            <div className="flex items-center justify-between bg-white px-4 py-3 border border-slate-200 rounded-xl">
              <button
                disabled={movementPage <= 1}
                onClick={() => setMovementPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-xs text-slate-500 font-medium">
                Page {movementPage} of {movementsData.pages}
              </span>
              <button
                disabled={movementPage >= movementsData.pages}
                onClick={() => setMovementPage((p) => p + 1)}
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Forecast Model Evaluation */}
      {activeTab === 'forecasts' && (
        <div className="space-y-6">
          <div className="p-4 bg-teal-50 border border-teal-200 rounded-xl flex items-start gap-3">
            <Info className="w-5 h-5 text-teal-600 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-teal-900 leading-relaxed">
              <span className="font-semibold text-teal-950">Evaluation Protocol: </span>
              Candidate baseline models (<code className="bg-teal-100 px-1 py-0.5 rounded font-mono text-[11px]">trailing_7d</code>, <code className="bg-teal-100 px-1 py-0.5 rounded font-mono text-[11px]">trailing_28d</code>, <code className="bg-teal-100 px-1 py-0.5 rounded font-mono text-[11px]">seasonal_naive</code>) are evaluated on a 14-day holdout validation window. The method with the lowest Mean Absolute Error (MAE) is selected as the production baseline. Periods with zero stock are flagged as censored demand to prevent underforecasting.
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {forecastEvalLoading ? (
              <div className="py-20 text-center text-slate-500">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto text-teal-600 mb-2" />
                Loading forecast evaluation metrics...
              </div>
            ) : !forecastEvalData || forecastEvalData.length === 0 ? (
              <div className="py-16 text-center text-slate-500">
                <TrendingUp className="w-10 h-10 mx-auto text-slate-300 mb-2" />
                <p>No completed forecast evaluation runs found.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">SKU</th>
                      <th className="py-3 px-4">Product Name</th>
                      <th className="py-3 px-4">Selected Method</th>
                      <th className="py-3 px-4 text-right">Holdout MAE</th>
                      <th className="py-3 px-4 text-right">Holdout WAPE</th>
                      <th className="py-3 px-4 text-center">Horizon Points</th>
                      <th className="py-3 px-4 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {forecastEvalData.map((row) => (
                      <tr key={row.product_id} className="hover:bg-slate-50/80 transition">
                        <td className="py-3 px-4 font-mono font-semibold text-slate-900 text-xs">
                          {row.sku}
                        </td>
                        <td className="py-3 px-4 text-slate-800 font-medium">{row.name}</td>
                        <td className="py-3 px-4">
                          <span className="font-mono text-xs px-2.5 py-1 rounded bg-slate-100 text-slate-800 border border-slate-200">
                            {row.best_method}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-semibold text-slate-900">
                          {row.mae !== null && row.mae !== undefined ? `${Number(row.mae).toFixed(2)} units` : '—'}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-600">
                          {row.wape !== null && row.wape !== undefined ? `${(Number(row.wape) * 100).toFixed(1)}%` : '—'}
                        </td>
                        <td className="py-3 px-4 text-center font-mono text-slate-600">
                          {row.data_points_count} days
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              row.status === 'Optimal'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : row.status === 'Cold Start'
                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                : 'bg-purple-50 text-purple-700 border border-purple-200'
                            }`}
                          >
                            {row.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
