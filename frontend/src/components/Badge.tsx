import React from 'react';

interface BadgeProps {
  type?: 'stock' | 'po' | 'priority' | 'method' | 'default';
  value: string;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ type = 'default', value, className = '' }) => {
  let colorStyles = 'bg-slate-100 text-slate-700 border-slate-200';

  if (type === 'stock') {
    switch (value) {
      case 'HEALTHY':
        colorStyles = 'bg-emerald-50 text-emerald-700 border-emerald-200';
        break;
      case 'REORDER_SOON':
        colorStyles = 'bg-amber-50 text-amber-700 border-amber-200';
        break;
      case 'STOCKOUT_RISK':
        colorStyles = 'bg-orange-50 text-orange-700 border-orange-200 animate-pulse';
        break;
      case 'OUT_OF_STOCK':
        colorStyles = 'bg-rose-50 text-rose-700 border-rose-200 font-semibold';
        break;
    }
  } else if (type === 'po') {
    switch (value) {
      case 'DRAFT':
        colorStyles = 'bg-slate-100 text-slate-700 border-slate-300';
        break;
      case 'PLACED':
        colorStyles = 'bg-blue-50 text-blue-700 border-blue-200';
        break;
      case 'PARTIALLY_RECEIVED':
        colorStyles = 'bg-amber-50 text-amber-700 border-amber-200';
        break;
      case 'RECEIVED':
        colorStyles = 'bg-emerald-50 text-emerald-700 border-emerald-200';
        break;
      case 'CANCELLED':
        colorStyles = 'bg-rose-50 text-rose-700 border-rose-200';
        break;
    }
  } else if (type === 'priority') {
    switch (value) {
      case 'HIGH':
        colorStyles = 'bg-rose-50 text-rose-700 border-rose-200 font-semibold';
        break;
      case 'MEDIUM':
        colorStyles = 'bg-amber-50 text-amber-700 border-amber-200';
        break;
      case 'LOW':
        colorStyles = 'bg-slate-100 text-slate-600 border-slate-200';
        break;
    }
  } else if (type === 'method') {
    switch (value) {
      case 'seasonal_naive':
        colorStyles = 'bg-purple-50 text-purple-700 border-purple-200';
        break;
      case 'trailing_7d':
        colorStyles = 'bg-teal-50 text-teal-700 border-teal-200';
        break;
      case 'trailing_28d':
        colorStyles = 'bg-indigo-50 text-indigo-700 border-indigo-200';
        break;
      case 'manual_fallback':
        colorStyles = 'bg-cyan-50 text-cyan-700 border-cyan-200';
        break;
      case 'insufficient_history':
        colorStyles = 'bg-rose-50 text-rose-600 border-rose-200';
        break;
    }
  }

  // Formatting display text
  const displayText = value.replace(/_/g, ' ').toUpperCase();

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorStyles} ${className}`}
    >
      {displayText}
    </span>
  );
};
