import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search,
  Plus,
  Filter,
  Eye,
  Edit2,
  Archive,
  AlertCircle,
  X,
  Package,
  Layers,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { Product, Category, Supplier, Paginated } from '../types';
import { Currency } from '../components/Currency';
import { Modal } from '../components/Modal';
import { useAuth } from '../context/AuthContext';

export const ProductsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const canManage = hasRole(['ADMIN', 'MANAGER']);

  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<number | ''>('');
  const [page, setPage] = useState(1);
  const pageSize = 12;

  // Selected product for drawer view
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Form Fields
  const [sku, setSku] = useState('');
  const [name, setName] = useState('');
  const [categoryId, setCategoryId] = useState<number | ''>('');
  const [unit, setUnit] = useState('units');
  const [sellingPrice, setSellingPrice] = useState('0.00');
  const [safetyStock, setSafetyStock] = useState('10');
  const [minReorderQty, setMinReorderQty] = useState('1');
  const [manualDemand, setManualDemand] = useState('');
  const [leadTimeDays, setLeadTimeDays] = useState('7');
  const [preferredSupplierId, setPreferredSupplierId] = useState<number | ''>('');
  const [unitCost, setUnitCost] = useState('0.00');
  const [packSize, setPackSize] = useState('1');

  // Fetch Categories
  const { data: categories } = useQuery<Category[]>({
    queryKey: ['categories'],
    queryFn: () => api.get<Category[]>('/products/categories'),
  });

  // Fetch Suppliers
  const { data: suppliersData } = useQuery<Paginated<Supplier>>({
    queryKey: ['suppliers'],
    queryFn: () => api.get<Paginated<Supplier>>('/suppliers?limit=100'),
  });

  // Fetch Products
  const { data: productsData, isLoading } = useQuery<Paginated<Product>>({
    queryKey: ['products', search, selectedCategory, page],
    queryFn: () =>
      api.get<Paginated<Product>>('/products', {
        search: search || undefined,
        category_id: selectedCategory || undefined,
        page,
        page_size: pageSize,
      }),
  });

  const openCreateModal = () => {
    setEditingProduct(null);
    setSku('');
    setName('');
    setCategoryId('');
    setUnit('units');
    setSellingPrice('0.00');
    setSafetyStock('10');
    setMinReorderQty('1');
    setManualDemand('');
    setLeadTimeDays('7');
    setPreferredSupplierId('');
    setUnitCost('0.00');
    setPackSize('1');
    setFormError(null);
    setIsModalOpen(true);
  };

  const openEditModal = (p: Product) => {
    setEditingProduct(p);
    setSku(p.sku);
    setName(p.name);
    setCategoryId(p.category_id || '');
    setUnit(p.unit);
    setSellingPrice(String(p.selling_price));
    setSafetyStock(String(p.safety_stock));
    setMinReorderQty(String(p.min_reorder_qty));
    setManualDemand(p.manual_daily_demand ? String(p.manual_daily_demand) : '');
    setLeadTimeDays(String(p.lead_time_days));
    setPreferredSupplierId(p.preferred_supplier_id || '');
    setUnitCost(p.unit_cost ? String(p.unit_cost) : '0.00');
    setPackSize(p.pack_size ? String(p.pack_size) : '1');
    setFormError(null);
    setIsModalOpen(true);
  };

  // Create/Update Product Mutation
  const saveProductMutation = useMutation({
    mutationFn: async () => {
      const payload: any = {
        name,
        category_id: categoryId ? Number(categoryId) : null,
        unit,
        selling_price: parseFloat(sellingPrice),
        safety_stock: parseInt(safetyStock, 10),
        min_reorder_qty: parseInt(minReorderQty, 10),
        manual_daily_demand: manualDemand ? parseFloat(manualDemand) : null,
        lead_time_days: parseInt(leadTimeDays, 10),
      };

      if (editingProduct) {
        return api.put(`/products/${editingProduct.id}`, payload);
      } else {
        payload.sku = sku.toUpperCase().trim();
        payload.preferred_supplier_id = preferredSupplierId ? Number(preferredSupplierId) : null;
        payload.unit_cost = parseFloat(unitCost);
        payload.pack_size = parseInt(packSize, 10);
        payload.moq = parseInt(minReorderQty, 10);
        return api.post('/products', payload);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['inventory'] });
      setIsModalOpen(false);
    },
    onError: (err: any) => {
      setFormError(err.message || 'Failed to save product');
    },
  });

  // Archive Mutation
  const archiveMutation = useMutation({
    mutationFn: (productId: number) => api.delete(`/products/${productId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] });
      if (selectedProduct) setSelectedProduct(null);
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Product Catalog</h1>
          <p className="text-sm text-slate-500 mt-1">
            Maintain item master, planning parameters, and supplier procurement settings.
          </p>
        </div>

        {canManage && (
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            <span>Add Product</span>
          </button>
        )}
      </div>

      {/* Filters Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="relative flex-1 w-full sm:max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by SKU or product name..."
            className="w-full pl-10 pr-4 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-56">
            <select
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value ? Number(e.target.value) : '');
                setPage(1);
              }}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
            >
              <option value="">All Categories</option>
              {categories?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Product Grid / Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/70 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="py-3.5 pl-6">SKU / Item Name</th>
                <th className="py-3.5">Category</th>
                <th className="py-3.5">Preferred Supplier</th>
                <th className="py-3.5 text-right">Selling Price</th>
                <th className="py-3.5 text-right">Unit Cost</th>
                <th className="py-3.5 text-right">Lead Time</th>
                <th className="py-3.5 text-right">Pack Size / MOQ</th>
                <th className="py-3.5 text-right pr-6">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    Loading products catalog...
                  </td>
                </tr>
              ) : productsData && productsData.items.length > 0 ? (
                productsData.items.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3.5 pl-6 font-medium text-slate-900">
                      <div>{p.name}</div>
                      <div className="text-[11px] font-mono text-teal-600 font-semibold mt-0.5">{p.sku}</div>
                    </td>
                    <td className="py-3.5 text-slate-500">{p.category_name || '—'}</td>
                    <td className="py-3.5 text-slate-600">
                      {p.preferred_supplier_name || <span className="text-slate-400 italic">Unassigned</span>}
                    </td>
                    <td className="py-3.5 text-right font-semibold">
                      <Currency value={p.selling_price} />
                    </td>
                    <td className="py-3.5 text-right text-slate-500">
                      <Currency value={p.unit_cost} />
                    </td>
                    <td className="py-3.5 text-right font-mono text-slate-600">{p.lead_time_days} days</td>
                    <td className="py-3.5 text-right font-mono text-slate-600">
                      {p.pack_size}x / {p.moq} MOQ
                    </td>
                    <td className="py-3.5 text-right pr-6">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => setSelectedProduct(p)}
                          title="View Details"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        {canManage && (
                          <>
                            <button
                              onClick={() => openEditModal(p)}
                              title="Edit"
                              className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 hover:bg-teal-50 transition"
                            >
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => {
                                if (confirm(`Archive ${p.name}?`)) archiveMutation.mutate(p.id);
                              }}
                              title="Archive"
                              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition"
                            >
                              <Archive className="w-4 h-4" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No products found matching filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        {productsData && productsData.pages > 1 && (
          <div className="px-6 py-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <div>
              Showing page <span className="font-semibold text-slate-700">{page}</span> of{' '}
              <span className="font-semibold text-slate-700">{productsData.pages}</span> ({productsData.total} products)
            </div>
            <div className="flex items-center gap-1.5">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 transition"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                disabled={page >= productsData.pages}
                onClick={() => setPage(page + 1)}
                className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 transition"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Add / Edit Product Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingProduct ? 'Edit Product' : 'Add New Product'}
        description="Configure planning parameters, pricing, and supplier pack sizes."
        maxWidth="2xl"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            saveProductMutation.mutate();
          }}
          className="space-y-4"
        >
          {formError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                SKU (Unique Identifier) *
              </label>
              <input
                type="text"
                required
                disabled={!!editingProduct}
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                placeholder="RICE-BAS-001"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono uppercase focus:ring-2 focus:ring-teal-500 focus:outline-none disabled:bg-slate-50"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Product Name *</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Basmati Rice 5kg"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Category</label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : '')}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:ring-2 focus:ring-teal-500 focus:outline-none"
              >
                <option value="">Select Category</option>
                {categories?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Unit of Measure</label>
              <input
                type="text"
                required
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                placeholder="bag, pack, bottle, pcs"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Selling Price (INR) *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                required
                value={sellingPrice}
                onChange={(e) => setSellingPrice(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Preferred Supplier</label>
              <select
                value={preferredSupplierId}
                onChange={(e) => setPreferredSupplierId(e.target.value ? Number(e.target.value) : '')}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white focus:ring-2 focus:ring-teal-500 focus:outline-none"
              >
                <option value="">Select Supplier</option>
                {suppliersData?.items?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.lead_time_days}d lead time)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Unit Cost (INR)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={unitCost}
                onChange={(e) => setUnitCost(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Lead Time (Days)</label>
              <input
                type="number"
                min="1"
                required
                value={leadTimeDays}
                onChange={(e) => setLeadTimeDays(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Pack Size Rounding</label>
              <input
                type="number"
                min="1"
                value={packSize}
                onChange={(e) => setPackSize(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Minimum Order Qty (MOQ)</label>
              <input
                type="number"
                min="1"
                value={minReorderQty}
                onChange={(e) => setMinReorderQty(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Safety Stock (Units)</label>
              <input
                type="number"
                min="0"
                value={safetyStock}
                onChange={(e) => setSafetyStock(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Manual Daily Demand (Cold Start)
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={manualDemand}
                onChange={(e) => setManualDemand(e.target.value)}
                placeholder="Optional fallback for new items"
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="pt-4 flex justify-end gap-3 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saveProductMutation.isPending}
              className="px-5 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold shadow-sm transition disabled:opacity-50"
            >
              {saveProductMutation.isPending ? 'Saving...' : 'Save Product'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Product Details Drawer */}
      {selectedProduct && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
            onClick={() => setSelectedProduct(null)}
          />

          <div className="fixed inset-y-0 right-0 max-w-md w-full bg-white shadow-2xl p-6 flex flex-col z-10 overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <span className="text-[11px] font-mono text-teal-600 font-bold uppercase tracking-wider">
                  {selectedProduct.sku}
                </span>
                <h3 className="text-lg font-bold text-slate-900 mt-0.5">{selectedProduct.name}</h3>
              </div>
              <button
                onClick={() => setSelectedProduct(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="py-6 space-y-6 flex-1 text-xs text-slate-700">
              {/* Stock Status Box */}
              <div className="grid grid-cols-3 gap-3 p-4 rounded-xl bg-slate-50 border border-slate-100 text-center">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">On Hand</span>
                  <p className="text-base font-bold font-mono text-slate-900 mt-1">
                    {selectedProduct.current_on_hand}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Reserved</span>
                  <p className="text-base font-bold font-mono text-slate-500 mt-1">
                    {selectedProduct.current_reserved}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-teal-600">Available</span>
                  <p className="text-base font-bold font-mono text-teal-700 mt-1">
                    {selectedProduct.current_available}
                  </p>
                </div>
              </div>

              {/* Planning Parameters */}
              <div className="space-y-3">
                <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider">Planning Parameters</h4>
                <div className="space-y-2 border border-slate-100 rounded-xl p-3 bg-white">
                  <div className="flex justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Safety Stock:</span>
                    <span className="font-mono font-semibold">{selectedProduct.safety_stock} units</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Supplier Lead Time:</span>
                    <span className="font-mono font-semibold">{selectedProduct.lead_time_days} days</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Minimum Order Qty (MOQ):</span>
                    <span className="font-mono font-semibold">{selectedProduct.moq} units</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Pack Size Multiple:</span>
                    <span className="font-mono font-semibold">{selectedProduct.pack_size}x</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Manual Cold Start Demand:</span>
                    <span className="font-mono font-semibold">
                      {selectedProduct.manual_daily_demand ? `${selectedProduct.manual_daily_demand} / day` : 'None (Auto)'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Procurement Pricing */}
              <div className="space-y-3">
                <h4 className="font-bold text-slate-900 text-xs uppercase tracking-wider">Procurement & Pricing</h4>
                <div className="space-y-2 border border-slate-100 rounded-xl p-3 bg-white">
                  <div className="flex justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Preferred Supplier:</span>
                    <span className="font-semibold text-slate-900">{selectedProduct.preferred_supplier_name || 'None'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-50">
                    <span className="text-slate-500">Unit Cost:</span>
                    <span className="font-mono font-semibold"><Currency value={selectedProduct.unit_cost} /></span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-500">Selling Price:</span>
                    <span className="font-mono font-semibold text-teal-700"><Currency value={selectedProduct.selling_price} /></span>
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100">
              <button
                onClick={() => setSelectedProduct(null)}
                className="w-full py-2.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Close Drawer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
