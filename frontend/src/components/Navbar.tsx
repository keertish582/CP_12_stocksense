import React from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, MapPin, Warehouse as WarehouseIcon } from 'lucide-react';

export const Navbar: React.FC<{ title?: string }> = ({ title }) => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 bg-white border-b border-slate-200/80 px-8 flex items-center justify-between sticky top-0 z-30 shadow-sm/50">
      <div className="flex items-center gap-4">
        {title && <h2 className="text-xl font-bold text-slate-800 tracking-tight">{title}</h2>}
      </div>

      <div className="flex items-center gap-4">
        {/* Warehouse Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-100/80 border border-slate-200 text-xs font-medium text-slate-600">
          <WarehouseIcon className="w-3.5 h-3.5 text-teal-600" />
          <span>Central Hub (WH-BLR-01)</span>
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 ml-1" />
        </div>

        {/* User Pill & Logout */}
        <div className="flex items-center gap-3 pl-2 border-l border-slate-200">
          <div className="text-right hidden sm:block">
            <p className="text-xs font-semibold text-slate-800 leading-none">{user?.full_name}</p>
            <p className="text-[11px] text-slate-500 font-mono mt-0.5">{user?.email}</p>
          </div>

          <button
            onClick={logout}
            title="Sign out"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:text-rose-600 hover:bg-rose-50 border border-slate-200 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Sign Out</span>
          </button>
        </div>
      </div>
    </header>
  );
};
