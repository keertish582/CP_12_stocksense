import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShoppingCart,
  UploadCloud,
  FileSpreadsheet,
  Download,
  Plus,
  Trash2,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react';
import { api } from '../services/api';
import { Sale, Product, CSVPreviewResult, ImportJob, Paginated } from '../types';
import { Currency } from '../components/Currency';
import { Modal } from '../components/Modal';

export const SalesPage: React.FC = () => {
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<'history' | 'import'>('history');
  const [salesPage, setSalesPage] = useState(1);

  // Manual Sale Modal
  const [isSaleModalOpen, setIsSaleModalOpen] = useState(false);
  const [externalSaleId, setExternalSaleId] = useState('');
  const [saleDate, setSaleDate] = useState(new Date().toISOString().split('T')[0]);
  const [channel, setChannel] = useState('POS_STORE');
  const [notes, setNotes] = useState('');
  const [saleItems, setSaleItems] = useState<Array<{ product_id: number; quantity: number; unit_price: string }>>([
    { product_id: 0, quantity: 1, unit_price: '0.00' },
  ]);
  const [saleError, setSaleError] = useState<string | null>(null);

  // Expanded rows in Sales History table
  const [expandedSales, setExpandedSales] = useState<Record<number, boolean>>({});

  // CSV Import State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewResult, setPreviewResult] = useState<CSVPreviewResult | null>(null);
  const [importResult, setImportResult] = useState<ImportJob | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // Fetch Sales
  const { data: salesData, isLoading: isSalesLoading } = useQuery<Paginated<Sale>>({
    queryKey: ['sales', salesPage],
    queryFn: () => api.get<Paginated<Sale>>('/sales', { page: salesPage, page_size: 15 }),
  });

  // Fetch Products for manual sale entry
  const { data: productsData } = useQuery<Paginated<Product>>({
    queryKey: ['products', 'list_all'],
    queryFn: () => api.get<Paginated<Product>>('/products?limit=100'),
  });

  const toggleExpand = (id: number) => {
    setExpandedSales((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleAddItemRow = () => {
    setSaleItems((prev) => [...prev, { product_id: 0, quantity: 1, unit_price: '0.00' }]);
  };

  const handleRemoveItemRow = (index: number) => {
    setSaleItems((prev) => prev.filter((_, i) => i !== index));
  };

  const handleProductChange = (index: number, productId: number) => {
    const prod = productsData?.items.find((p) => p.id === productId);
    setSaleItems((prev) =>
      prev.map((item, i) =>
        i === index
          ? {
              ...item,
              product_id: productId,
              unit_price: prod ? String(prod.selling_price) : '0.00',
            }
          : item
      )
    );
  };

  // Manual Sale Mutation
  const createSaleMutation = useMutation({
    mutationFn: () => {
      const validItems = saleItems
        .filter((it) => it.product_id > 0 && it.quantity > 0)
        .map((it) => ({
          product_id: Number(it.product_id),
          quantity: Number(it.quantity),
          unit_price: parseFloat(it.unit_price),
        }));

      if (validItems.length === 0) {
        throw new Error('Please add at least one valid product line.');
      }

      return api.post('/sales', {
        external_sale_id: externalSaleId.trim() || undefined,
        sale_date: saleDate,
        channel,
        notes: notes.trim() || undefined,
        items: validItems,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setIsSaleModalOpen(false);
      setSaleItems([{ product_id: 0, quantity: 1, unit_price: '0.00' }]);
      setExternalSaleId('');
      setNotes('');
      setSaleError(null);
    },
    onError: (err: any) => {
      setSaleError(err.message || 'Failed to record sale');
    },
  });

  // CSV Preview Handler
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setPreviewResult(null);
    setImportResult(null);
    setImportError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.upload<CSVPreviewResult>('/sales/preview-csv', formData);
      setPreviewResult(res);
    } catch (err: any) {
      setImportError(err.message || 'Failed to parse CSV preview');
    }
  };

  // CSV Import Mutation
  const importCsvMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error('No file selected');
      const formData = new FormData();
      formData.append('file', selectedFile);
      return api.upload<ImportJob>('/sales/import-csv', formData);
    },
    onSuccess: (data) => {
      setImportResult(data);
      queryClient.invalidateQueries({ queryKey: ['sales'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err: any) => {
      setImportError(err.message || 'Import failed');
    },
  });

  const downloadTemplate = async () => {
    try {
      await api.downloadFile('/sales/template-csv', 'sales_import_template.csv');
    } catch (err: any) {
      alert(err.message || 'Failed to download template');
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Sales & Data Imports</h1>
          <p className="text-sm text-slate-500 mt-1">
            Record manual sales orders and import bulk daily transactions via verified CSV upload.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setSaleError(null);
              setIsSaleModalOpen(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs sm:text-sm font-semibold shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            <span>Record Sale</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab('history')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 text-sm font-semibold transition ${
            activeTab === 'history'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <ShoppingCart className="w-4 h-4" />
          <span>Sales Order History</span>
        </button>

        <button
          onClick={() => setActiveTab('import')}
          className={`flex items-center gap-2 px-5 py-3 border-b-2 text-sm font-semibold transition ${
            activeTab === 'import'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <UploadCloud className="w-4 h-4" />
          <span>Batch CSV Import</span>
        </button>
      </div>

      {/* Tab 1: Sales History */}
      {activeTab === 'history' && (
        <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  <th className="py-3.5 pl-6 w-10"></th>
                  <th className="py-3.5">Sale ID / Ref</th>
                  <th className="py-3.5">Date</th>
                  <th className="py-3.5">Channel</th>
                  <th className="py-3.5 text-right">Items Count</th>
                  <th className="py-3.5 text-right pr-6">Total Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                {isSalesLoading ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      Loading sales history...
                    </td>
                  </tr>
                ) : salesData && salesData.items.length > 0 ? (
                  salesData.items.map((s) => (
                    <React.Fragment key={s.id}>
                      <tr
                        onClick={() => toggleExpand(s.id)}
                        className="hover:bg-slate-50/70 transition cursor-pointer"
                      >
                        <td className="py-3.5 pl-6 text-slate-400">
                          {expandedSales[s.id] ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                        </td>
                        <td className="py-3.5 font-medium text-slate-900">
                          <div>#{s.id}</div>
                          {s.external_sale_id && (
                            <div className="text-[11px] font-mono text-teal-600 font-semibold">
                              {s.external_sale_id}
                            </div>
                          )}
                        </td>
                        <td className="py-3.5 font-mono text-slate-600">{s.sale_date}</td>
                        <td className="py-3.5">
                          <span className="px-2 py-0.5 rounded bg-slate-100 font-medium text-[11px] text-slate-600">
                            {s.channel}
                          </span>
                        </td>
                        <td className="py-3.5 text-right font-mono font-semibold text-slate-600">
                          {s.items?.length || 0} line(s)
                        </td>
                        <td className="py-3.5 text-right pr-6 font-bold font-mono text-slate-900">
                          <Currency value={s.total_amount} />
                        </td>
                      </tr>

                      {/* Expanded line items */}
                      {expandedSales[s.id] && (
                        <tr className="bg-slate-50/50">
                          <td colSpan={6} className="py-3 px-12 border-b border-slate-100">
                            <div className="space-y-1.5 py-1">
                              <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                                Order Line Items
                              </p>
                              {s.items?.map((it) => (
                                <div
                                  key={it.id}
                                  className="flex items-center justify-between text-xs py-1 border-b border-slate-100/80 last:border-0"
                                >
                                  <div>
                                    <span className="font-semibold text-slate-800">{it.product_name}</span>
                                    <span className="font-mono text-slate-400 ml-2">({it.product_sku})</span>
                                  </div>
                                  <div className="flex items-center gap-6 font-mono text-slate-600">
                                    <span>
                                      {it.quantity} x <Currency value={it.unit_price} />
                                    </span>
                                    <span className="font-bold text-slate-900 w-24 text-right">
                                      <Currency value={it.subtotal} />
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-slate-400">
                      No sales recorded yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {salesData && salesData.pages > 1 && (
            <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <div>
                Page <span className="font-semibold text-slate-700">{salesPage}</span> of{' '}
                <span className="font-semibold text-slate-700">{salesData.pages}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  disabled={salesPage <= 1}
                  onClick={() => setSalesPage(salesPage - 1)}
                  className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  disabled={salesPage >= salesData.pages}
                  onClick={() => setSalesPage(salesPage + 1)}
                  className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Batch CSV Import */}
      {activeTab === 'import' && (
        <div className="space-y-6">
          {/* Instructions & Template Card */}
          <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Standard CSV Format</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-xl">
                Columns required: <code className="font-mono font-semibold text-teal-700 bg-teal-50 px-1 py-0.5 rounded">external_sale_id,sku,sale_date,quantity,unit_price</code>.
                Multi-line orders are automatically grouped by <code className="font-mono">external_sale_id</code>.
                Validation is atomic: all rows must pass before stock is deducted.
              </p>
            </div>

            <button
              onClick={downloadTemplate}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold shrink-0 transition"
            >
              <Download className="w-4 h-4 text-slate-500" />
              <span>Download Template</span>
            </button>
          </div>

          {/* File Dropzone */}
          <div className="bg-white rounded-2xl p-8 border-2 border-dashed border-slate-200 hover:border-teal-500 transition text-center flex flex-col items-center justify-center">
            <FileSpreadsheet className="w-12 h-12 text-teal-600 mb-3" />
            <h4 className="text-sm font-bold text-slate-800">Choose sales CSV file to preview & validate</h4>
            <p className="text-xs text-slate-500 mt-1 mb-4">Click to browse your local device (.csv)</p>

            <label className="cursor-pointer inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm transition">
              <span>Select CSV File</span>
              <input type="file" accept=".csv" onChange={handleFileChange} className="hidden" />
            </label>

            {selectedFile && (
              <p className="text-xs font-mono font-semibold text-teal-700 mt-3">
                Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
              </p>
            )}
          </div>

          {/* Errors or Alerts */}
          {importError && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex items-start gap-3">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Import Failure:</p>
                <p className="mt-0.5">{importError}</p>
              </div>
            </div>
          )}

          {importResult && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              <div>
                <p className="font-bold text-emerald-900 text-sm">Import Completed Successfully!</p>
                <p className="mt-1">
                  Job ID: <span className="font-mono">{importResult.job_id}</span> • Processed{' '}
                  <span className="font-bold">{importResult.processed_rows}</span> rows. Inventory ledger balances
                  have been updated.
                </p>
              </div>
            </div>
          )}

          {/* Preview & Validation Results */}
          {previewResult && (
            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h4 className="text-base font-bold text-slate-900">Pre-Import Validation Preview</h4>
                  <div className="flex items-center gap-4 text-xs mt-1">
                    <span className="text-slate-600">
                      Total Rows: <strong className="font-mono">{previewResult.total_rows}</strong>
                    </span>
                    <span className="text-emerald-700 font-semibold">
                      Valid Rows: <strong className="font-mono">{previewResult.valid_rows_count}</strong>
                    </span>
                    {previewResult.error_rows_count > 0 && (
                      <span className="text-rose-700 font-bold">
                        Errors: <strong className="font-mono">{previewResult.error_rows_count}</strong>
                      </span>
                    )}
                  </div>
                </div>

                <button
                  disabled={previewResult.error_rows_count > 0 || importCsvMutation.isPending}
                  onClick={() => importCsvMutation.mutate()}
                  className="px-5 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm transition disabled:opacity-40"
                >
                  {importCsvMutation.isPending ? 'Importing...' : 'Execute Atomic Import'}
                </button>
              </div>

              {/* Error Rows Table if any */}
              {previewResult.errors && previewResult.errors.length > 0 && (
                <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs space-y-2">
                  <div className="flex items-center gap-2 font-bold text-rose-800">
                    <AlertTriangle className="w-4 h-4 text-rose-600" />
                    <span>Row Validation Errors (Must be resolved before import)</span>
                  </div>
                  <ul className="list-disc list-inside space-y-1 text-rose-700 font-mono text-[11px]">
                    {previewResult.errors.map((err, i) => (
                      <li key={i}>
                        Row {err.row_number} [{err.sku || 'No SKU'}]: {err.error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Sample Data Preview Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-700">
                  <thead>
                    <tr className="border-b border-slate-100 text-[11px] font-semibold uppercase text-slate-400">
                      <th className="py-2.5">Row</th>
                      <th className="py-2.5">External Sale ID</th>
                      <th className="py-2.5">SKU</th>
                      <th className="py-2.5">Date</th>
                      <th className="py-2.5 text-right">Quantity</th>
                      <th className="py-2.5 text-right">Unit Price</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {previewResult.preview_rows.map((r) => (
                      <tr key={r.row_number}>
                        <td className="py-2 font-mono text-slate-400">{r.row_number}</td>
                        <td className="py-2 font-mono">{r.external_sale_id || '—'}</td>
                        <td className="py-2 font-mono font-semibold text-teal-700">{r.sku}</td>
                        <td className="py-2 font-mono">{r.sale_date}</td>
                        <td className="py-2 text-right font-mono font-bold">{r.quantity}</td>
                        <td className="py-2 text-right font-mono"><Currency value={r.unit_price} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Manual Sale Modal */}
      <Modal
        isOpen={isSaleModalOpen}
        onClose={() => setIsSaleModalOpen(false)}
        title="Record New Point-of-Sale Transaction"
        description="Creates sale order header and deducts warehouse inventory atomically."
        maxWidth="2xl"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            createSaleMutation.mutate();
          }}
          className="space-y-4"
        >
          {saleError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{saleError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">External Ref / Invoice #</label>
              <input
                type="text"
                value={externalSaleId}
                onChange={(e) => setExternalSaleId(e.target.value)}
                placeholder="POS-20261117-001"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Sale Date *</label>
              <input
                type="date"
                required
                value={saleDate}
                onChange={(e) => setSaleDate(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Channel</label>
              <select
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:ring-2 focus:ring-teal-500 focus:outline-none"
              >
                <option value="POS_STORE">Store POS</option>
                <option value="ONLINE_DELIVERY">Online Delivery</option>
                <option value="B2B_WHOLESALE">B2B Wholesale</option>
              </select>
            </div>
          </div>

          {/* Line items */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">Sale Line Items</span>
              <button
                type="button"
                onClick={handleAddItemRow}
                className="text-xs font-semibold text-teal-600 hover:text-teal-700 flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Item</span>
              </button>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {saleItems.map((item, index) => (
                <div key={index} className="flex items-center gap-2 p-2 rounded-xl bg-slate-50 border border-slate-100">
                  <select
                    required
                    value={item.product_id}
                    onChange={(e) => handleProductChange(index, Number(e.target.value))}
                    className="flex-1 px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs bg-white"
                  >
                    <option value={0}>Select Product</option>
                    {productsData?.items?.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.sku}) — Available: {p.current_available}
                      </option>
                    ))}
                  </select>

                  <input
                    type="number"
                    min="1"
                    required
                    value={item.quantity}
                    onChange={(e) =>
                      setSaleItems((prev) =>
                        prev.map((it, i) => (i === index ? { ...it, quantity: parseInt(e.target.value, 10) || 1 } : it))
                      )
                    }
                    placeholder="Qty"
                    className="w-20 px-2 py-1.5 rounded-lg border border-slate-200 text-xs font-mono font-bold text-center"
                  />

                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={item.unit_price}
                    onChange={(e) =>
                      setSaleItems((prev) =>
                        prev.map((it, i) => (i === index ? { ...it, unit_price: e.target.value } : it))
                      )
                    }
                    placeholder="Price"
                    className="w-24 px-2 py-1.5 rounded-lg border border-slate-200 text-xs font-mono text-right"
                  />

                  {saleItems.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveItemRow(index)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Notes</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Optional sale remarks or customer reference..."
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>

          <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsSaleModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createSaleMutation.isPending}
              className="px-5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
            >
              {createSaleMutation.isPending ? 'Processing...' : 'Confirm Sale Order'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
