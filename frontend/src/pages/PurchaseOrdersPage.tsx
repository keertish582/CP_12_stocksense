import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ClipboardList,
  Send,
  PackageCheck,
  XCircle,
  Eye,
  AlertCircle,
  CheckCircle2,
  Calendar,
  Truck,
  Plus,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react';
import { api } from '../services/api';
import { PurchaseOrder, Paginated, GoodsReceipt } from '../types';
import { Badge } from '../components/Badge';
import { Currency } from '../components/Currency';
import { Modal } from '../components/Modal';
import { useAuth } from '../context/AuthContext';

export const PurchaseOrdersPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const canOperate = hasRole(['ADMIN', 'MANAGER']);

  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [selectedPo, setSelectedPo] = useState<PurchaseOrder | null>(null);

  // Partial Receiving Modal
  const [receivingPo, setReceivingPo] = useState<PurchaseOrder | null>(null);
  const [receivedDate, setReceivedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [receiptNotes, setReceiptNotes] = useState<string>('');
  const [receivingQuantities, setReceivingQuantities] = useState<Record<number, number>>({});
  const [receivingError, setReceivingError] = useState<string | null>(null);

  // Expanded PO rows
  const [expandedOrders, setExpandedOrders] = useState<Record<number, boolean>>({});

  // Fetch Purchase Orders
  const { data: poData, isLoading } = useQuery<Paginated<PurchaseOrder>>({
    queryKey: ['purchase_orders', statusFilter, page],
    queryFn: () =>
      api.get<Paginated<PurchaseOrder>>('/purchase-orders', {
        status: statusFilter || undefined,
        page,
        page_size: 15,
      }),
  });

  const toggleExpand = (id: number) => {
    setExpandedOrders((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Place Order Mutation
  const placeMutation = useMutation({
    mutationFn: (poId: number) => api.post(`/purchase-orders/${poId}/place`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase_orders'] });
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  // Cancel Order Mutation
  const cancelMutation = useMutation({
    mutationFn: (poId: number) => api.post(`/purchase-orders/${poId}/cancel?reason=Cancelled+by+manager`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase_orders'] });
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  // Receive Delivery Mutation
  const receiveMutation = useMutation({
    mutationFn: async () => {
      if (!receivingPo) return;

      const itemsToReceive = Object.entries(receivingQuantities)
        .filter(([_, qty]) => qty > 0)
        .map(([poItemId, qty]) => ({
          po_item_id: Number(poItemId),
          quantity_received: Number(qty),
        }));

      if (itemsToReceive.length === 0) {
        throw new Error('Please enter a received quantity of at least 1 unit.');
      }

      return api.post<GoodsReceipt>('/receiving', {
        purchase_order_id: receivingPo.id,
        received_date: receivedDate,
        notes: receiptNotes.trim() || undefined,
        items: itemsToReceive,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase_orders'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['recommendations'] });
      setReceivingPo(null);
    },
    onError: (err: any) => {
      setReceivingError(err.message || 'Failed to record goods receipt');
    },
  });

  const openReceivingModal = (po: PurchaseOrder) => {
    setReceivingPo(po);
    setReceivedDate(new Date().toISOString().split('T')[0]);
    setReceiptNotes('');
    setReceivingError(null);

    // Default receiving quantities to remaining outstanding qty
    const initialQtys: Record<number, number> = {};
    po.items.forEach((it) => {
      initialQtys[it.id] = it.remaining_qty;
    });
    setReceivingQuantities(initialQtys);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Purchase Orders & Receiving</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track procurement lifecycle from draft to placed orders and process partial delivery goods receipts.
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-500">Filter Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="">All Statuses</option>
            <option value="DRAFT">DRAFT</option>
            <option value="PLACED">PLACED</option>
            <option value="PARTIALLY_RECEIVED">PARTIALLY_RECEIVED</option>
            <option value="RECEIVED">RECEIVED</option>
            <option value="CANCELLED">CANCELLED</option>
          </select>
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="py-3.5 pl-6 w-10"></th>
                <th className="py-3.5">PO Number</th>
                <th className="py-3.5">Supplier</th>
                <th className="py-3.5">Expected Delivery</th>
                <th className="py-3.5">Status</th>
                <th className="py-3.5 text-right">Total Amount</th>
                <th className="py-3.5 text-right pr-6">Procurement Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    Loading purchase orders...
                  </td>
                </tr>
              ) : poData && poData.items.length > 0 ? (
                poData.items.map((po) => (
                  <React.Fragment key={po.id}>
                    <tr
                      onClick={() => toggleExpand(po.id)}
                      className="hover:bg-slate-50/70 transition cursor-pointer"
                    >
                      <td className="py-3.5 pl-6 text-slate-400">
                        {expandedOrders[po.id] ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </td>
                      <td className="py-3.5 font-bold font-mono text-slate-900">
                        {po.po_number}
                      </td>
                      <td className="py-3.5 font-medium text-slate-800">{po.supplier_name}</td>
                      <td className="py-3.5 font-mono text-slate-600">
                        {po.expected_delivery_date || 'Unspecified'}
                      </td>
                      <td className="py-3.5">
                        <Badge type="po" value={po.status} />
                      </td>
                      <td className="py-3.5 text-right font-mono font-bold text-slate-900">
                        <Currency value={po.total_amount} />
                      </td>
                      <td className="py-3.5 text-right pr-6">
                        <div
                          className="flex items-center justify-end gap-2"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {canOperate && po.status === 'DRAFT' && (
                            <button
                              onClick={() => placeMutation.mutate(po.id)}
                              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm flex items-center gap-1.5 transition"
                            >
                              <Send className="w-3.5 h-3.5" />
                              <span>Place Order</span>
                            </button>
                          )}

                          {canOperate && (po.status === 'PLACED' || po.status === 'PARTIALLY_RECEIVED') && (
                            <button
                              onClick={() => openReceivingModal(po)}
                              className="px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm flex items-center gap-1.5 transition"
                            >
                              <PackageCheck className="w-3.5 h-3.5" />
                              <span>Receive Delivery</span>
                            </button>
                          )}

                          {canOperate && po.status === 'DRAFT' && (
                            <button
                              onClick={() => {
                                if (confirm(`Cancel purchase order ${po.po_number}?`)) {
                                  cancelMutation.mutate(po.id);
                                }
                              }}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition"
                              title="Cancel Order"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>

                    {/* Expanded Items Drawer */}
                    {expandedOrders[po.id] && (
                      <tr className="bg-slate-50/60">
                        <td colSpan={7} className="py-4 px-12 border-b border-slate-100">
                          <div className="space-y-3">
                            <div className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-slate-400">
                              <span>Ordered Items Breakdown</span>
                              <span>Fulfillment Progress</span>
                            </div>

                            <div className="space-y-2">
                              {po.items.map((it) => (
                                <div
                                  key={it.id}
                                  className="flex items-center justify-between p-2.5 rounded-xl bg-white border border-slate-200/80 text-xs"
                                >
                                  <div>
                                    <span className="font-semibold text-slate-800">{it.product_name}</span>
                                    <span className="font-mono text-slate-400 ml-2">({it.product_sku})</span>
                                  </div>

                                  <div className="flex items-center gap-6 font-mono">
                                    <div>
                                      <span className="text-slate-500">Ordered:</span>{' '}
                                      <strong className="text-slate-900">{it.quantity_ordered}</strong>
                                    </div>
                                    <div>
                                      <span className="text-slate-500">Received:</span>{' '}
                                      <strong className="text-emerald-700">{it.quantity_received}</strong>
                                    </div>
                                    <div>
                                      <span className="text-slate-500">Outstanding:</span>{' '}
                                      <strong className="text-amber-700">{it.remaining_qty}</strong>
                                    </div>
                                    <div className="w-24 text-right font-bold text-slate-900">
                                      <Currency value={it.subtotal} />
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>

                            {po.notes && (
                              <p className="text-[11px] text-slate-500 italic mt-2">Notes: {po.notes}</p>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    No purchase orders found matching filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {poData && poData.pages > 1 && (
          <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <div>
              Page <span className="font-semibold text-slate-700">{page}</span> of{' '}
              <span className="font-semibold text-slate-700">{poData.pages}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={page >= poData.pages}
                onClick={() => setPage(page + 1)}
                className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Partial / Full Goods Receiving Modal */}
      {receivingPo && (
        <Modal
          isOpen={true}
          onClose={() => setReceivingPo(null)}
          title={`Receive Goods — ${receivingPo.po_number}`}
          description="Enter received quantities for incoming consignment. Increases inventory balance atomically."
          maxWidth="2xl"
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              receiveMutation.mutate();
            }}
            className="space-y-4"
          >
            {receivingError && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{receivingError}</span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Receipt Date *</label>
                <input
                  type="date"
                  required
                  value={receivedDate}
                  onChange={(e) => setReceivedDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Delivery / LR / Gate Pass #</label>
                <input
                  type="text"
                  value={receiptNotes}
                  onChange={(e) => setReceiptNotes(e.target.value)}
                  placeholder="e.g. Challan #CH-8821 via SafeExpress"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="space-y-2 pt-2">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Consignment Items Verification
              </span>

              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {receivingPo.items.map((it) => (
                  <div
                    key={it.id}
                    className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <p className="font-semibold text-slate-800">{it.product_name}</p>
                      <p className="text-[11px] font-mono text-slate-500 mt-0.5">
                        SKU: {it.product_sku} • Remaining Outstanding: <strong className="text-amber-700">{it.remaining_qty}</strong>
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-slate-500 text-[11px]">Receive now:</span>
                      <input
                        type="number"
                        min="0"
                        max={it.remaining_qty}
                        value={receivingQuantities[it.id] || 0}
                        onChange={(e) => {
                          const val = parseInt(e.target.value, 10) || 0;
                          setReceivingQuantities((prev) => ({ ...prev, [it.id]: val }));
                        }}
                        className="w-24 px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-mono font-bold text-center bg-white"
                      />
                      <span className="text-slate-400 text-xs font-mono">/ {it.remaining_qty}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setReceivingPo(null)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={receiveMutation.isPending}
                className="px-5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
              >
                {receiveMutation.isPending ? 'Verifying & Receiving...' : 'Confirm Goods Receipt'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
