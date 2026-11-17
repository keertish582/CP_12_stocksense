import React from 'react';

interface CurrencyProps {
  value?: number | string | null;
  amount?: number | string | null;
  className?: string;
  hideSymbol?: boolean;
}

export const formatINR = (amount: number | string | null | undefined): string => {
  if (amount === null || amount === undefined || amount === '') return '₹0.00';
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  if (isNaN(num)) return '₹0.00';

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
};

export const Currency: React.FC<CurrencyProps> = ({ value, amount, className = '', hideSymbol = false }) => {
  const val = value !== undefined ? value : amount;
  const formatted = formatINR(val);
  const display = hideSymbol ? formatted.replace('₹', '').trim() : formatted;

  return <span className={`font-medium tabular-nums ${className}`}>{display}</span>;
};
