import React from 'react';

interface BadgeProps {
  variant?: 'success' | 'danger' | 'warning' | 'info' | 'neutral' | 'saffron' | 'emerald';
  children: React.ReactNode;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ variant = 'neutral', children, className = '' }) => {
  const variantStyles = {
    success: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    emerald: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    danger: 'bg-rose-50 text-rose-800 border-rose-200/80',
    warning: 'bg-amber-50 text-amber-900 border-amber-200/80',
    info: 'bg-sky-50 text-sky-800 border-sky-200/80',
    neutral: 'bg-[#F4F3EE] text-[#57534E] border-[#E5E4DF]',
    saffron: 'bg-[#FDF8F6] text-[#C2410C] border-[#EBDBD5]'
  };

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${variantStyles[variant]} ${className}`}>
      {children}
    </span>
  );
};
