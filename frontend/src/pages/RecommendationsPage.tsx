import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  RefreshCw,
  Eye,
  CheckCircle,
  Clock,
  XCircle,
  AlertTriangle,
  Info,
  Calendar,
  Layers,
  ArrowRight,
  AlertCircle,
  X,
  Truck,
} from 'lucide-react';
import { api } from '../services/api';
import { ReorderRecommendation, Paginated, PurchaseOrder } from '../types';
import { Badge } from '../components/Badge';
import { Currency } from '../components/Currency';
import { Modal } from '../components/Modal';
import { useAuth } from '../context/AuthContext';

export const RecommendationsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const canApprove = hasRole(['ADMIN', 'MANAGER']);

  const [selectedRec, setSelectedRec] = useState<ReorderRecommendation | null>(null);

  // Approval Modal
  const [approvingRec, setApprovingRec] = useState<ReorderRecommendation | null>(null);
  const [customQty, setCustomQty] = useState<number>(0);
  const [expectedDate, setExpectedDate] = useState<string>('');
  const [approvalNotes, setApprovalNotes] = useState<string>('');
  const [approvalError, setApprovalError] = useState<string | null>(null);

  // Fetch Active Recommendations
  const { data: recsData, isLoading, refetch } = useQuery<Paginated<ReorderRecommendation>>({
    queryKey: ['recommendations', 'active'],
    queryFn: () => api.get<Paginated<ReorderRecommendation>>('/recommendations?is_active_only=true&page_size=50'),
  });

  // Refresh Recommendations Mutation
  const refreshMutation = useMutation({
    mutationFn: () => api.post('/recommendations/refresh?coverage_days=14'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  // Approve Recommendation Mutation
  const approveMutation = useMutation({
    mutationFn: async () => {
      if (!approvingRec) return;
      return api.post<PurchaseOrder>(`/recommendations/${approvingRec.id}/approve`, {
        expected_delivery_date: expectedDate || undefined,
        custom_qty: customQty > 0 ? customQty : undefined,
        notes: approvalNotes.trim() || undefined,
      });
    },
    onSuccess: (po) => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['purchase_orders'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setApprovingRec(null);
      if (po?.id) {
        navigate('/purchase-orders');
      }
    },
    onError: (err: any) => {
      setApprovalError(err.message || 'Failed to approve recommendation');
    },
  });

  // Action Mutation (Defer/Dismiss)
  const actionMutation = useMutation({
    mutationFn: ({ id, action, reason }: { id: number; action: string; reason?: string }) =>
      api.post(`/recommendations/${id}/action`, { action, reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      if (selectedRec) setSelectedRec(null);
    },
  });

  const openApprovalModal = (rec: ReorderRecommendation) => {
    setApprovingRec(rec);
    setCustomQty(rec.suggested_qty);
    setExpectedDate('');
    setApprovalNotes('');
    setApprovalError(null);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Reorder Recommendations</h1>
          <p className="text-sm text-slate-500 mt-1">
            Predictive stock replenishment suggestions calculated against lead-time demand, safety stock, and open inbound orders.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {canApprove && (
            <button
              onClick={() => refreshMutation.mutate()}
              disabled={refreshMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs sm:text-sm font-semibold shadow-sm transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${refreshMutation.isPending ? 'animate-spin' : ''}`} />
              <span>{refreshMutation.isPending ? 'Re-calculating...' : 'Refresh Recommendations'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Recommendations Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="py-3.5 pl-6">Product / SKU</th>
                <th className="py-3.5">Priority</th>
                <th className="py-3.5 text-right">Available</th>
                <th className="py-3.5 text-right">Inbound</th>
                <th className="py-3.5 text-right">Position</th>
                <th className="py-3.5 text-right">ROP</th>
                <th className="py-3.5 text-right">Suggested Order</th>
                <th className="py-3.5 text-right">Est. Cost</th>
                <th className="py-3.5 text-right pr-6">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    Evaluating inventory positions and generating recommendations...
                  </td>
                </tr>
              ) : recsData && recsData.items.length > 0 ? (
                recsData.items.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3.5 pl-6 font-medium text-slate-900">
                      <div>{r.product_name}</div>
                      <div className="text-[11px] font-mono text-teal-600 font-semibold mt-0.5">{r.product_sku}</div>
                    </td>
                    <td className="py-3.5">
                      <Badge type="priority" value={r.priority} />
                    </td>
                    <td className="py-3.5 text-right font-mono font-semibold text-slate-900">
                      {r.on_hand_snapshot}
                    </td>
                    <td className="py-3.5 text-right font-mono text-blue-600">
                      {r.eligible_inbound_snapshot > 0 ? `+${r.eligible_inbound_snapshot}` : '0'}
                    </td>
                    <td className="py-3.5 text-right font-mono font-bold text-slate-900">
                      {r.inventory_position_snapshot}
                    </td>
                    <td className="py-3.5 text-right font-mono text-slate-500">{r.reorder_point}</td>
                    <td className="py-3.5 text-right font-mono">
                      <span className="font-extrabold text-teal-700 bg-teal-50 px-2.5 py-1 rounded-md border border-teal-200">
                        {r.suggested_qty} units
                      </span>
                    </td>
                    <td className="py-3.5 text-right font-mono font-semibold text-slate-800">
                      <Currency value={r.total_estimated_cost} />
                    </td>
                    <td className="py-3.5 text-right pr-6">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setSelectedRec(r)}
                          className="px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1 transition"
                        >
                          <Eye className="w-3.5 h-3.5 text-slate-400" />
                          <span>Inspect</span>
                        </button>

                        {canApprove && (
                          <button
                            onClick={() => openApprovalModal(r)}
                            className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm transition"
                          >
                            Approve
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    No active reorder recommendations. All product inventory positions are currently above their reorder points.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Full Explainability Review Drawer */}
      {selectedRec && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
            onClick={() => setSelectedRec(null)}
          />

          <div className="fixed inset-y-0 right-0 max-w-lg w-full bg-white shadow-2xl p-6 flex flex-col z-10 overflow-y-auto">
            {/* Drawer Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <span className="text-[11px] font-mono text-teal-600 font-bold uppercase tracking-wider">
                  Recommendation #{selectedRec.id} • {selectedRec.product_sku}
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-0.5">{selectedRec.product_name}</h3>
              </div>
              <button
                onClick={() => setSelectedRec(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Content */}
            <div className="py-6 space-y-6 flex-1 text-xs text-slate-700">
              {/* Warnings if any */}
              {selectedRec.calculation_details?.warnings &&
                selectedRec.calculation_details.warnings.length > 0 && (
                  <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs space-y-1.5">
                    <div className="flex items-center gap-2 font-bold text-amber-800">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                      <span>Data Quality & Pipeline Warnings</span>
                    </div>
                    <ul className="list-disc list-inside space-y-1 text-amber-800 text-[11px]">
                      {selectedRec.calculation_details.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

              {/* Order Quantities Summary Box */}
              <div className="p-4 rounded-xl bg-teal-50/60 border border-teal-200/80 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-teal-900">Recommended Order Quantity:</span>
                  <span className="text-base font-extrabold font-mono text-teal-800">
                    {selectedRec.suggested_qty} units
                  </span>
                </div>
                <div className="flex items-center justify-between text-slate-600 pt-1 border-t border-teal-200/50">
                  <span>Estimated Consignment Cost:</span>
                  <span className="font-mono font-bold text-slate-900">
                    <Currency value={selectedRec.total_estimated_cost} />
                  </span>
                </div>
              </div>

              {/* Formula & Derivation Breakdown */}
              <div className="space-y-3">
                <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-teal-600" />
                  <span>Explainable Mathematical Derivation</span>
                </h4>

                <div className="space-y-2 border border-slate-100 rounded-xl p-3.5 bg-slate-50/50 font-mono text-[11px]">
                  <div className="flex justify-between py-1 border-b border-slate-200/60">
                    <span className="text-slate-500">Supplier Lead Time (L):</span>
                    <span className="font-bold">{selectedRec.calculation_details?.lead_time_days || 7} days</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200/60">
                    <span className="text-slate-500">Lead-Time Demand (LTD):</span>
                    <span className="font-bold">{selectedRec.lead_time_demand} units</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200/60">
                    <span className="text-slate-500">Configured Safety Stock (SS):</span>
                    <span className="font-bold">{selectedRec.safety_stock} units</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200/60 text-slate-900">
                    <span className="font-bold">Reorder Point (ROP = LTD + SS):</span>
                    <span className="font-bold text-teal-700">{selectedRec.reorder_point} units</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200/60">
                    <span className="text-slate-500">Coverage Horizon (C):</span>
                    <span className="font-bold">{selectedRec.calculation_details?.coverage_days || 14} days</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200/60">
                    <span className="text-slate-500">Target Stock (L+C + SS):</span>
                    <span className="font-bold">{selectedRec.target_stock} units</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200/60">
                    <span className="text-slate-500">Current Position (Avail + Inbound):</span>
                    <span className="font-bold">{selectedRec.inventory_position_snapshot} units</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Raw Needed Quantity:</span>
                    <span className="font-bold">{selectedRec.raw_order_qty} units</span>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 text-[11px] text-slate-600">
                  <p className="font-semibold text-slate-800 mb-1">Constraints & Rounding Logic:</p>
                  <p>{selectedRec.calculation_details?.rounding_explanation}</p>
                </div>
              </div>

              {/* Inbound Supply Orders Contributing */}
              <div className="space-y-2">
                <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <Truck className="w-3.5 h-3.5 text-teal-600" />
                  <span>Contributing Open Inbound Orders</span>
                </h4>

                {selectedRec.calculation_details?.eligible_purchase_orders &&
                selectedRec.calculation_details.eligible_purchase_orders.length > 0 ? (
                  <div className="space-y-1.5">
                    {selectedRec.calculation_details.eligible_purchase_orders.map((po: any, idx: number) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-2.5 rounded-xl border border-slate-200/80 bg-white"
                      >
                        <div>
                          <span className="font-mono font-bold text-slate-800">{po.po_number}</span>
                          <span className="text-[11px] text-slate-500 ml-2">
                            Expected: {po.expected_delivery_date || 'N/A'}
                          </span>
                        </div>
                        <span className="font-mono font-bold text-blue-600">+{po.remaining_qty} units</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">No eligible open inbound purchase orders for this SKU.</p>
                )}
              </div>
            </div>

            {/* Actions Footer */}
            <div className="pt-4 border-t border-slate-100 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                {canApprove && (
                  <>
                    <button
                      onClick={() =>
                        actionMutation.mutate({
                          id: selectedRec.id,
                          action: 'DEFER',
                          reason: 'Deferred by manager inspection',
                        })
                      }
                      className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50"
                    >
                      Defer
                    </button>
                    <button
                      onClick={() =>
                        actionMutation.mutate({
                          id: selectedRec.id,
                          action: 'DISMISS',
                          reason: 'Dismissed by manager',
                        })
                      }
                      className="px-3 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-rose-600 hover:bg-rose-50"
                    >
                      Dismiss
                    </button>
                  </>
                )}
              </div>

              {canApprove && (
                <button
                  onClick={() => openApprovalModal(selectedRec)}
                  className="px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm transition"
                >
                  Approve to Purchase Order
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Approval Modal */}
      {approvingRec && (
        <Modal
          isOpen={true}
          onClose={() => setApprovingRec(null)}
          title="Approve Reorder Recommendation"
          description={`Generates a Draft Purchase Order for ${approvingRec.supplier_name || 'Preferred Supplier'}.`}
          maxWidth="md"
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              approveMutation.mutate();
            }}
            className="space-y-4"
          >
            {approvalError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{approvalError}</span>
              </div>
            )}

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 space-y-1 text-xs">
              <p className="font-semibold text-slate-800">{approvingRec.product_name}</p>
              <p className="text-[11px] font-mono text-slate-500">
                SKU: {approvingRec.product_sku} • Supplier: {approvingRec.supplier_name}
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Order Quantity (Units) * (Pack Size Multiple: {approvingRec.pack_size}x)
              </label>
              <input
                type="number"
                min="1"
                required
                value={customQty}
                onChange={(e) => setCustomQty(parseInt(e.target.value, 10) || 0)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono font-bold focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Calculated suggested quantity is {approvingRec.suggested_qty} units.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Expected Delivery Date</label>
              <input
                type="date"
                value={expectedDate}
                onChange={(e) => setExpectedDate(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Defaults to today + supplier lead time ({approvingRec.calculation_details?.lead_time_days || 7} days) if empty.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Approval Notes</label>
              <textarea
                rows={2}
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="Optional internal remarks for the procurement order..."
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setApprovingRec(null)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={approveMutation.isPending || customQty <= 0}
                className="px-5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
              >
                {approveMutation.isPending ? 'Validating & Approving...' : 'Confirm & Create Draft PO'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
