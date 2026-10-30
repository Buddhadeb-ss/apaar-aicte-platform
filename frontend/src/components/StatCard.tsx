import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  accent?: 'blue' | 'emerald' | 'amber' | 'rose' | 'orange';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  accent = 'blue'
}) => {
  const accentIcons = {
    blue: 'text-sky-700 bg-sky-50 border-sky-200/60',
    emerald: 'text-emerald-700 bg-emerald-50 border-emerald-200/60',
    amber: 'text-amber-800 bg-amber-50 border-amber-200/60',
    rose: 'text-rose-700 bg-rose-50 border-rose-200/60',
    orange: 'text-[#C2410C] bg-[#FDF8F6] border-[#EBDBD5]',
  };

  return (
    <div className="bg-white p-5 rounded-xl border border-[#E5E4DF] shadow-[0_1px_3px_rgba(0,0,0,0.03)] hover:border-[#D5D3CA] transition-all duration-200">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-[#78716C]">{title}</p>
          <h3 className="text-2xl sm:text-3xl font-serif font-medium text-[#1C1917] mt-1">{value}</h3>
          {subtitle && (
            <p className="text-xs text-[#78716C] mt-1.5 flex items-center gap-1">{subtitle}</p>
          )}
        </div>
        <div className={`p-2.5 rounded-lg border ${accentIcons[accent]}`}>
          {icon}
        </div>
      </div>
    </div>
  );
};
