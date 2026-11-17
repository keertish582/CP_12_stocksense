import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Boxes,
  History,
  Sliders,
  Download,
  Search,
  Filter,
  AlertCircle,
  Plus,
  Minus,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { api } from '../services/api';
import { InventoryBalance, StockMovement, Paginated, Product } from '../types';
import { Badge } from '../components/Badge';
import { Modal } from '../components/Modal';
import { useAuth } from '../context/AuthContext';

export const InventoryPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const canAdjust = hasRole(['ADMIN', 'MANAGER']);

  const [activeTab, setActiveTab] = useState<'balances' | 'movements'>('balances');
  const [search, setSearch] = useState('');
  const [balancePage, setBalancePage] = useState(1);
  const [movementPage, setMovementPage] = useState(1);
  const [movementFilterType, setMovementFilterType] = useState<string>('');

  // Adjustment Modal
  const [isAdjModalOpen, setIsAdjModalOpen] = useState(false);
  const [selectedProductId, setSelectedProductId] = useState<number | ''>('');
  const [adjustmentDelta, setAdjustmentDelta] = useState<number>(0);
  const [adjustmentReason, setAdjustmentReason] = useState<string>('');
  const [adjError, setAdjError] = useState<string | null>(null);

  // Fetch Balances
  const { data: balancesData, isLoading: isBalancesLoading } = useQuery<Paginated<InventoryBalance>>({
    queryKey: ['inventory', 'balances', search, balancePage],
    queryFn: () =>
      api.get<Paginated<InventoryBalance>>('/inventory/balances', {
        search: search || undefined,
        page: balancePage,
        page_size: 15,
      }),
  });

  // Fetch Movements
  const { data: movementsData, isLoading: isMovementsLoading } = useQuery<Paginated<StockMovement>>({
    queryKey: ['inventory', 'movements', movementFilterType, movementPage],
    queryFn: () =>
      api.get<Paginated<StockMovement>>('/inventory/movements', {
        movement_type: movementFilterType || undefined,
        page: movementPage,
        page_size: 20,
      }),
    enabled: activeTab === 'movements',
  });

  // Fetch Products for adjustment dropdown
  const { data: productsData } = useQuery<Paginated<Product>>({
    queryKey: ['products', 'list_all'],
    queryFn: () => api.get<Paginated<Product>>('/products?limit=100'),
    enabled: isAdjModalOpen,
  });

  // Stock Adjustment Mutation
  const adjustMutation = useMutation({
    mutationFn: () =>
      api.post('/inventory/adjustments', {
        product_id: Number(selectedProductId),
        quantity_delta: Number(adjustmentDelta),
        reason: adjustmentReason.trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setIsAdjModalOpen(false);
      setAdjustmentDelta(0);
      setAdjustmentReason('');
      setSelectedProductId('');
      setAdjError(null);
    },
    onError: (err: any) => {
      setAdjError(err.message || 'Failed to apply adjustment');
    },
  });

  const downloadLedgerCSV = () => {
    window.open('/api/v1/reports/movements/export-csv', '_blank');
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Inventory & Stock Ledger</h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time on-hand positions, reserved units, and auditable movement ledger.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {activeTab === 'movements' && (
            <button
              onClick={downloadLedgerCSV}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition"
            >
              <Download className="w-4 h-4 text-slate-500" />
              <span>Export Ledger CSV</span>
            </button>
          )}

          {canAdjust && (
            <button
              onClick={() => {
                setAdjError(null);
                setIsAdjModalOpen(true);
              }}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs sm:text-sm font-semibold shadow-sm transition"
            >
              <Sliders className="w-4 h-4" />
              <span>Stock Adjustment</span>
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('balances')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 text-sm font-semibold transition ${
            activeTab === 'balances'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Boxes className="w-4 h-4" />
          <span>Warehouse Balances</span>
        </button>

        <button
          onClick={() => setActiveTab('movements')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 text-sm font-semibold transition ${
            activeTab === 'movements'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Stock Movement Ledger</span>
        </button>
      </div>

      {/* Tab 1: Balances Table */}
      {activeTab === 'balances' && (
        <div className="space-y-4">
          {/* Search bar */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
            <div className="relative w-full max-w-md">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setBalancePage(1);
                }}
                placeholder="Search inventory by SKU or product name..."
                className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    <th className="py-3.5 pl-6">Product / SKU</th>
                    <th className="py-3.5">Category</th>
                    <th className="py-3.5 text-right">On Hand</th>
                    <th className="py-3.5 text-right">Reserved</th>
                    <th className="py-3.5 text-right">Available</th>
                    <th className="py-3.5 text-right">Eligible Inbound</th>
                    <th className="py-3.5 text-right">Inventory Position</th>
                    <th className="py-3.5 text-right">Reorder Point</th>
                    <th className="py-3.5 text-right pr-6">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                  {isBalancesLoading ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-slate-400">
                        Loading balances...
                      </td>
                    </tr>
                  ) : balancesData && balancesData.items.length > 0 ? (
                    balancesData.items.map((b) => (
                      <tr key={b.product_id} className="hover:bg-slate-50/70 transition">
                        <td className="py-3.5 pl-6 font-medium text-slate-900">
                          <div>{b.product_name}</div>
                          <div className="text-[11px] font-mono text-teal-600 font-semibold mt-0.5">{b.product_sku}</div>
                        </td>
                        <td className="py-3.5 text-slate-500">{b.category_name || '—'}</td>
                        <td className="py-3.5 text-right font-mono font-semibold text-slate-900">{b.on_hand_qty}</td>
                        <td className="py-3.5 text-right font-mono text-slate-400">{b.reserved_qty}</td>
                        <td className="py-3.5 text-right font-mono font-bold text-teal-700">{b.available_qty}</td>
                        <td className="py-3.5 text-right font-mono text-blue-600">
                          {b.eligible_open_inbound > 0 ? `+${b.eligible_open_inbound}` : '0'}
                        </td>
                        <td className="py-3.5 text-right font-mono font-extrabold text-slate-900">
                          {b.inventory_position}
                        </td>
                        <td className="py-3.5 text-right font-mono text-slate-500">{b.reorder_point}</td>
                        <td className="py-3.5 text-right pr-6">
                          <Badge type="stock" value={b.stock_status} />
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-slate-400">
                        No inventory balances found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {balancesData && balancesData.pages > 1 && (
              <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <div>
                  Page <span className="font-semibold text-slate-700">{balancePage}</span> of{' '}
                  <span className="font-semibold text-slate-700">{balancesData.pages}</span> ({balancesData.total} items)
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    disabled={balancePage <= 1}
                    onClick={() => setBalancePage(balancePage - 1)}
                    className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    disabled={balancePage >= balancesData.pages}
                    onClick={() => setBalancePage(balancePage + 1)}
                    className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Stock Movement Ledger */}
      {activeTab === 'movements' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-slate-500">Movement Type:</span>
              <select
                value={movementFilterType}
                onChange={(e) => {
                  setMovementFilterType(e.target.value);
                  setMovementPage(1);
                }}
                className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              >
                <option value="">All Types</option>
                <option value="SALE">SALE</option>
                <option value="PURCHASE_RECEIPT">PURCHASE_RECEIPT</option>
                <option value="ADJUSTMENT">ADJUSTMENT</option>
                <option value="INITIAL">INITIAL</option>
                <option value="RETURN">RETURN</option>
              </select>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    <th className="py-3.5 pl-6">Timestamp (UTC)</th>
                    <th className="py-3.5">Product / SKU</th>
                    <th className="py-3.5">Type</th>
                    <th className="py-3.5 text-right">Delta</th>
                    <th className="py-3.5 text-right">Balance After</th>
                    <th className="py-3.5">Reference / Reason</th>
                    <th className="py-3.5 text-right pr-6">Actor</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                  {isMovementsLoading ? (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-slate-400">
                        Loading stock ledger...
                      </td>
                    </tr>
                  ) : movementsData && movementsData.items.length > 0 ? (
                    movementsData.items.map((m) => (
                      <tr key={m.id} className="hover:bg-slate-50/70 transition">
                        <td className="py-3.5 pl-6 font-mono text-slate-500 text-[11px]">
                          {new Date(m.created_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })}
                        </td>
                        <td className="py-3.5 font-medium text-slate-900">
                          <div>{m.product_name}</div>
                          <div className="text-[11px] font-mono text-slate-400">{m.product_sku}</div>
                        </td>
                        <td className="py-3.5">
                          <span className="font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded text-[11px]">
                            {m.movement_type}
                          </span>
                        </td>
                        <td className="py-3.5 text-right font-mono font-bold">
                          <span className={m.quantity_delta > 0 ? 'text-emerald-600' : 'text-slate-800'}>
                            {m.quantity_delta > 0 ? `+${m.quantity_delta}` : m.quantity_delta}
                          </span>
                        </td>
                        <td className="py-3.5 text-right font-mono font-semibold text-slate-900">
                          {m.balance_after}
                        </td>
                        <td className="py-3.5 text-slate-600">
                          <div>{m.reason || '—'}</div>
                          {m.reference_id && (
                            <span className="text-[10px] font-mono text-slate-400">Ref: {m.reference_id}</span>
                          )}
                        </td>
                        <td className="py-3.5 text-right pr-6 text-slate-500 font-medium">
                          {m.created_by_name || 'System'}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="py-12 text-center text-slate-400">
                        No ledger movements recorded.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {movementsData && movementsData.pages > 1 && (
              <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <div>
                  Page <span className="font-semibold text-slate-700">{movementPage}</span> of{' '}
                  <span className="font-semibold text-slate-700">{movementsData.pages}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    disabled={movementPage <= 1}
                    onClick={() => setMovementPage(movementPage - 1)}
                    className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    disabled={movementPage >= movementsData.pages}
                    onClick={() => setMovementPage(movementPage + 1)}
                    className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stock Adjustment Modal */}
      <Modal
        isOpen={isAdjModalOpen}
        onClose={() => setIsAdjModalOpen(false)}
        title="Record Stock Adjustment"
        description="Manually adjust on-hand warehouse inventory with mandatory audit reason."
        maxWidth="lg"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            adjustMutation.mutate();
          }}
          className="space-y-4"
        >
          {adjError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{adjError}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select Product *</label>
            <select
              required
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value ? Number(e.target.value) : '')}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:ring-2 focus:ring-teal-500 focus:outline-none"
            >
              <option value="">Select a Product</option>
              {productsData?.items?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.sku}) — Available: {p.current_available}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Quantity Delta * (Positive to add, Negative to deduct)
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                required
                value={adjustmentDelta}
                onChange={(e) => setAdjustmentDelta(parseInt(e.target.value, 10) || 0)}
                placeholder="e.g. 5 or -3"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono font-bold focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
              <span className="text-xs text-slate-500 whitespace-nowrap">
                {adjustmentDelta > 0 ? (
                  <span className="text-emerald-600 font-semibold">+ Adding stock</span>
                ) : adjustmentDelta < 0 ? (
                  <span className="text-rose-600 font-semibold">- Deducting stock</span>
                ) : (
                  'Specify change'
                )}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Mandatory Audit Reason * (min. 3 characters)
            </label>
            <textarea
              required
              minLength={3}
              rows={3}
              value={adjustmentReason}
              onChange={(e) => setAdjustmentReason(e.target.value)}
              placeholder="e.g., Physical cycle count adjustment; damaged goods written off; shelf relocation."
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>

          <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsAdjModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={adjustMutation.isPending || !selectedProductId || adjustmentDelta === 0}
              className="px-5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
            >
              {adjustMutation.isPending ? 'Applying...' : 'Apply Stock Adjustment'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
