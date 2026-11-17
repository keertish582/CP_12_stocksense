import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  TrendingUp,
  RefreshCw,
  Sparkles,
  Calendar,
  AlertTriangle,
  Info,
  CheckCircle,
  HelpCircle,
  Clock,
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
import { Product, ProductForecastDetail, Paginated } from '../types';
import { Badge } from '../components/Badge';
import { useAuth } from '../context/AuthContext';

export const ForecastsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const canTrigger = hasRole(['ADMIN', 'MANAGER']);

  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);

  // Fetch all active products for selector
  const { data: productsData } = useQuery<Paginated<Product>>({
    queryKey: ['products', 'all_active'],
    queryFn: () => api.get<Paginated<Product>>('/products?limit=100'),
  });

  // Default to first product if none selected
  const activeProduct =
    selectedProductId && productsData?.items
      ? productsData.items.find((p) => p.id === selectedProductId)
      : productsData?.items?.[0] || null;

  const currentProductId = activeProduct?.id;

  // Fetch Product Forecast Details
  const { data: forecastDetail, isLoading: isForecastLoading } = useQuery<ProductForecastDetail>({
    queryKey: ['forecast', currentProductId],
    queryFn: () => api.get<ProductForecastDetail>(`/forecasts/product/${currentProductId}`),
    enabled: !!currentProductId,
  });

  // Trigger Forecast Pipeline Mutation
  const triggerMutation = useMutation({
    mutationFn: () => api.post('/forecasts/trigger', { coverage_days: 14, forecast_horizon_days: 30 }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forecast'] });
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  // Prepare combined chronological chart data
  const chartData: any[] = [];

  if (forecastDetail) {
    forecastDetail.historical_actuals.forEach((pt) => {
      chartData.push({
        date: pt.date.slice(5),
        fullDate: pt.date,
        'Historical Actuals': pt.actual_qty,
        'Projected Forecast': null,
      });
    });

    forecastDetail.future_forecasts.forEach((pt) => {
      chartData.push({
        date: pt.date.slice(5),
        fullDate: pt.date,
        'Historical Actuals': null,
        'Projected Forecast': parseFloat(String(pt.forecast_qty)),
      });
    });
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Demand Forecasting Engine</h1>
          <p className="text-sm text-slate-500 mt-1">
            Baseline walk-forward evaluated statistical forecasts and cold-start fallback projections.
          </p>
        </div>

        {canTrigger && (
          <button
            onClick={() => triggerMutation.mutate()}
            disabled={triggerMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs sm:text-sm font-semibold shadow-sm transition disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${triggerMutation.isPending ? 'animate-spin' : ''}`} />
            <span>{triggerMutation.isPending ? 'Running Engine...' : 'Run Forecast Pipeline'}</span>
          </button>
        )}
      </div>

      {/* Product Selector Bar */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="w-full sm:max-w-md">
          <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
            Select Product to Inspect Forecast
          </label>
          <select
            value={currentProductId || ''}
            onChange={(e) => setSelectedProductId(Number(e.target.value))}
            className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm font-semibold text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-teal-500 shadow-sm"
          >
            {productsData?.items?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.sku}) — {p.category_name || 'General'}
              </option>
            ))}
          </select>
        </div>

        {forecastDetail && (
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 text-xs font-medium text-slate-600">
              <Calendar className="w-3.5 h-3.5 text-slate-500" />
              <span>Cutoff Date: {forecastDetail.data_cutoff}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 font-medium">Selected Method:</span>
              <Badge type="method" value={forecastDetail.method} />
            </div>
          </div>
        )}
      </div>

      {/* Main Forecast Inspection Card */}
      {isForecastLoading ? (
        <div className="bg-white rounded-2xl p-16 border border-slate-200/80 shadow-sm text-center text-slate-400">
          Evaluating time series and generating projection horizon...
        </div>
      ) : forecastDetail ? (
        <div className="space-y-6">
          {/* Metrics & Warning Banners */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Metric: MAE */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-sm">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Holdout MAE (Error)
              </span>
              <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                {forecastDetail.mae !== null ? `${forecastDetail.mae} units` : 'N/A'}
              </div>
              <span className="text-[11px] text-slate-500">Mean Absolute Error</span>
            </div>

            {/* Metric: WAPE */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-sm">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Holdout WAPE
              </span>
              <div className="text-xl font-bold font-mono text-slate-900 mt-1">
                {forecastDetail.wape !== null ? `${(Number(forecastDetail.wape) * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <span className="text-[11px] text-slate-500">Weighted Percentage Error</span>
            </div>

            {/* Available Stock */}
            <div className="bg-white rounded-2xl p-4 border border-slate-200/80 shadow-sm">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Current Available Stock
              </span>
              <div className="text-xl font-bold font-mono text-teal-700 mt-1">
                {forecastDetail.current_available_stock} units
              </div>
              <span className="text-[11px] text-slate-500">On-hand minus reserved</span>
            </div>

            {/* Stockout Projection */}
            <div
              className={`rounded-2xl p-4 border shadow-sm ${
                forecastDetail.projected_stockout_date
                  ? 'bg-rose-50 border-rose-200 text-rose-900'
                  : 'bg-emerald-50 border-emerald-200 text-emerald-900'
              }`}
            >
              <span className="text-xs font-semibold uppercase tracking-wider opacity-75">
                Projected Stockout Date
              </span>
              <div className="text-xl font-bold font-mono mt-1">
                {forecastDetail.projected_stockout_date || 'No Stockout'}
              </div>
              <span className="text-[11px] opacity-75">
                {forecastDetail.projected_stockout_date
                  ? 'Ignoring future receipts'
                  : 'Safe within 30-day horizon'}
              </span>
            </div>
          </div>

          {/* Cold start or censored warning alert */}
          {forecastDetail.is_cold_start && (
            <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Cold Start Notice:</p>
                <p className="mt-0.5">
                  This product has limited or zero historical sales history. The forecasting engine is using{' '}
                  <strong className="font-semibold">{forecastDetail.method}</strong> without fabricating statistical
                  numbers.
                </p>
              </div>
            </div>
          )}

          {/* Interactive Chart */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Trajectory: Historical Actuals vs 30-Day Forecast
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Chronological progression showing recent daily sales followed by projected future demand rate.
                </p>
              </div>
            </div>

            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
                  <Bar dataKey="Historical Actuals" fill="#0d9488" radius={[4, 4, 0, 0]} barSize={12} />
                  <Line
                    type="monotone"
                    dataKey="Projected Forecast"
                    stroke="#8b5cf6"
                    strokeWidth={2.5}
                    strokeDasharray="4 4"
                    dot={{ fill: '#8b5cf6', r: 3 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};
