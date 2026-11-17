import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { User, Paginated, UserRole } from '../types';
import { useAuth } from '../context/AuthContext';
import { Modal } from '../components/Modal';
import { 
  Settings, User as UserIcon, Shield, Users, Clock, 
  CheckCircle, Plus, Edit3, AlertCircle, RefreshCw, Sliders, Calendar 
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();
  const isAdmin = user?.role === 'ADMIN';

  const [activeTab, setActiveTab] = useState<'profile' | 'users' | 'planning' | 'scheduler'>('profile');

  // User management state
  const [userPage, setUserPage] = useState(1);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [newUser, setNewUser] = useState({
    email: '',
    full_name: '',
    password: '',
    role: 'STAFF' as UserRole,
  });

  const { data: usersData, isLoading: usersLoading, refetch: refetchUsers } = useQuery({
    queryKey: ['users', userPage],
    queryFn: () => api.get<Paginated<User>>('/users', { page: userPage, page_size: 20 }),
    enabled: isAdmin && activeTab === 'users',
  });

  const createUserMutation = useMutation({
    mutationFn: (payload: typeof newUser) => api.post<User>('/users', payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setCreateModalOpen(false);
      setNewUser({ email: '', full_name: '', password: '', role: 'STAFF' });
      setFormError(null);
    },
    onError: (err: any) => {
      setFormError(err.message || 'Failed to create user');
    },
  });

  const handleCreateUser = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUser.email || !newUser.full_name || !newUser.password) {
      setFormError('All fields are required');
      return;
    }
    if (newUser.password.length < 6) {
      setFormError('Password must be at least 6 characters');
      return;
    }
    createUserMutation.mutate(newUser);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Settings className="w-7 h-7 text-teal-600" />
            System Settings & Administration
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Configure system parameters, manage staff access roles, and monitor background tasks.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-6">
        <button
          onClick={() => setActiveTab('profile')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'profile'
              ? 'border-teal-600 text-teal-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <UserIcon className="w-4 h-4" />
          My Profile
        </button>

        {isAdmin && (
          <button
            onClick={() => setActiveTab('users')}
            className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
              activeTab === 'users'
                ? 'border-teal-600 text-teal-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Users className="w-4 h-4" />
            User Access Management
          </button>
        )}

        <button
          onClick={() => setActiveTab('planning')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'planning'
              ? 'border-teal-600 text-teal-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Sliders className="w-4 h-4" />
          Planning Defaults & Policy
        </button>

        <button
          onClick={() => setActiveTab('scheduler')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition ${
            activeTab === 'scheduler'
              ? 'border-teal-600 text-teal-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Clock className="w-4 h-4" />
          Scheduler & Engine
        </button>
      </div>

      {/* Tab: Profile */}
      {activeTab === 'profile' && (
        <div className="max-w-2xl bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-teal-100 text-teal-700 font-bold text-2xl flex items-center justify-center">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">{user?.full_name}</h2>
              <p className="text-sm text-slate-500">{user?.email}</p>
              <div className="mt-1">
                <span
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    user?.role === 'ADMIN'
                      ? 'bg-rose-100 text-rose-800'
                      : user?.role === 'MANAGER'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}
                >
                  <Shield className="w-3 h-3 mr-1" />
                  {user?.role}
                </span>
              </div>
            </div>
          </div>

          <div className="border-t border-slate-200 pt-4 space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Account ID:</span>
              <span className="font-mono text-slate-800">#{user?.id}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Account Status:</span>
              <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                <CheckCircle className="w-4 h-4" /> Active
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Default Warehouse:</span>
              <span className="font-medium text-slate-800">Bengaluru Central Hub (WH-BLR-01)</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">System Timezone:</span>
              <span className="font-mono text-slate-800">Asia/Kolkata (IST, UTC+05:30)</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-slate-500">Base Currency:</span>
              <span className="font-semibold text-slate-800">INR (₹)</span>
            </div>
          </div>

          <div className="border-t border-slate-200 pt-4 flex justify-end">
            <button
              onClick={logout}
              className="px-4 py-2 border border-rose-300 text-rose-700 hover:bg-rose-50 rounded-lg text-sm font-medium transition"
            >
              Sign Out of Session
            </button>
          </div>
        </div>
      )}

      {/* Tab: Users (Admin only) */}
      {isAdmin && activeTab === 'users' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-500">
              Manage accounts and assigned access roles across the organization.
            </p>
            <button
              onClick={() => {
                setFormError(null);
                setCreateModalOpen(true);
              }}
              className="inline-flex items-center gap-2 px-4 py-2 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-700 transition shadow-sm text-sm"
            >
              <Plus className="w-4 h-4" />
              Add User
            </button>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {usersLoading ? (
              <div className="py-20 text-center text-slate-500">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto text-teal-600 mb-2" />
                Loading user directory...
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs font-semibold text-slate-700 uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">User</th>
                      <th className="py-3 px-4">Email</th>
                      <th className="py-3 px-4">Role</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4">Created Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {usersData?.items.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-50/80 transition">
                        <td className="py-3.5 px-4 font-semibold text-slate-900 flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 font-bold text-xs flex items-center justify-center">
                            {u.full_name.charAt(0)}
                          </div>
                          {u.full_name}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-xs text-slate-600">{u.email}</td>
                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                              u.role === 'ADMIN'
                                ? 'bg-rose-100 text-rose-800'
                                : u.role === 'MANAGER'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-blue-100 text-blue-800'
                            }`}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          {u.is_active ? (
                            <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
                              <CheckCircle className="w-3.5 h-3.5" /> Active
                            </span>
                          ) : (
                            <span className="text-xs text-slate-400">Inactive</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-xs text-slate-500">
                          {new Date(u.created_at).toLocaleDateString('en-IN')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Create User Modal */}
          <Modal
            isOpen={createModalOpen}
            onClose={() => setCreateModalOpen(false)}
            title="Create New User Account"
          >
            <form onSubmit={handleCreateUser} className="space-y-4">
              {formError && (
                <div className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  value={newUser.full_name}
                  onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:outline-none"
                  placeholder="e.g. Anand Sharma"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Email Address *
                </label>
                <input
                  type="email"
                  required
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:outline-none"
                  placeholder="user@stocksense.dev"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Initial Password *
                </label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:outline-none"
                  placeholder="Minimum 6 characters"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Access Role *
                </label>
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value as UserRole })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-teal-500 focus:outline-none"
                >
                  <option value="STAFF">STAFF — Sales Entry & Stock View Only</option>
                  <option value="MANAGER">MANAGER — Full Inventory, Forecasts & PO Receiving</option>
                  <option value="ADMIN">ADMIN — Full System Access & User Administration</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createUserMutation.isPending}
                  className="px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 transition disabled:opacity-50"
                >
                  {createUserMutation.isPending ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          </Modal>
        </div>
      )}

      {/* Tab: Planning Defaults */}
      {activeTab === 'planning' && (
        <div className="max-w-3xl space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Sliders className="w-5 h-5 text-teal-600" />
              Reorder Formula Specifications
            </h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              StockSense enforces transparent, explainable replenishment formulas. All recommendations display the underlying math before purchase order approval.
            </p>

            <div className="space-y-4 pt-2">
              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                <div className="font-semibold text-xs text-slate-800 uppercase tracking-wider">
                  1. Inventory Position (IP)
                </div>
                <div className="font-mono text-sm text-teal-700 mt-1">
                  IP = On-Hand Stock - Reserved Stock - Unreserved Backorders + Eligible Open Inbound
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  *MVP Note: Reserved stock and backorders are fixed at 0. Eligible inbound includes only POs with status <code className="text-slate-700 font-mono">PLACED</code> or <code className="text-slate-700 font-mono">PARTIALLY_RECEIVED</code> whose expected delivery date is valid and not overdue.
                </p>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                <div className="font-semibold text-xs text-slate-800 uppercase tracking-wider">
                  2. Reorder Point (ROP) & Safety Stock (SS)
                </div>
                <div className="font-mono text-sm text-teal-700 mt-1">
                  ROP = Lead Time Demand (LTD) + Safety Stock (SS)
                </div>
                <div className="font-mono text-xs text-slate-600 mt-1">
                  LTD = Forecast Daily Demand × Preferred Supplier Lead Time (Days)
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Default Safety Stock is configured per product or defaults to 7 days of daily demand to buffer against variability.
                </p>
              </div>

              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                <div className="font-semibold text-xs text-slate-800 uppercase tracking-wider">
                  3. Target Stock & Supplier Constraints
                </div>
                <div className="font-mono text-sm text-teal-700 mt-1">
                  Target Stock = ROP + (Forecast Daily Demand × Coverage Period [14 Days])
                </div>
                <div className="font-mono text-xs text-slate-600 mt-1">
                  Raw Needed Qty = max(0, Target Stock - Inventory Position)
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Suggested Quantity is then rounded up to satisfy the preferred supplier’s Minimum Order Quantity (MOQ) and integer multiple of Pack Size.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Scheduler & Background Engine */}
      {activeTab === 'scheduler' && (
        <div className="max-w-3xl space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-teal-600" />
              Automated Forecasting & Reorder Pipeline
            </h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              StockSense utilizes Celery with Redis for decoupled, background execution of time-intensive forecasting pipelines and large CSV sales ingestion.
            </p>

            <div className="border-t border-slate-200 pt-4 space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="font-medium text-slate-700">Scheduled Beat Frequency:</span>
                <span className="font-mono text-slate-900 bg-slate-100 px-2 py-0.5 rounded">
                  Daily at 02:00 IST (20:30 UTC)
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="font-medium text-slate-700">Candidate Forecast Models:</span>
                <span className="text-slate-800 text-xs">
                  Trailing 7d Avg, Trailing 28d Avg, Seasonal Naive (7-day weekday cycle)
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="font-medium text-slate-700">Model Selection Metric:</span>
                <span className="font-mono text-teal-700 font-semibold text-xs">
                  Primary: Minimum MAE (Holdout Evaluation)
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="font-medium text-slate-700">Demand Censoring Rule:</span>
                <span className="text-slate-700 text-xs">
                  Flagged when zero-sales coincide with zero on-hand stockout periods
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="font-medium text-slate-700">Cold-Start Rule:</span>
                <span className="text-slate-700 text-xs">
                  Fallback to manual product daily demand setting when history &lt; 14 days
                </span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="font-medium text-slate-700">Stale Approval Guard:</span>
                <span className="text-slate-700 text-xs">
                  Re-verifies inventory position before order approval; rejects if drift &gt; 5 units (409 Conflict)
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
