import React from 'react';
import { AlertTriangle, Info, CheckCircle2, AlertCircle } from 'lucide-react';

interface AlertBannerProps {
  type?: 'info' | 'warning' | 'error' | 'success';
  title?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({
  type = 'info',
  title,
  children,
  action,
  className = '',
}) => {
  const styles = {
    info: 'bg-blue-950/40 border-blue-800/60 text-blue-200',
    warning: 'bg-amber-950/40 border-amber-800/60 text-amber-200',
    error: 'bg-rose-950/40 border-rose-800/60 text-rose-200',
    success: 'bg-emerald-950/40 border-emerald-800/60 text-emerald-200',
  };

  const icons = {
    info: <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />,
    error: <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />,
    success: <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />,
  };

  return (
    <div
      className={`flex items-start gap-3 p-4 rounded-xl border ${styles[type]} text-sm ${className}`}
    >
      {icons[type]}
      <div className="flex-1">
        {title && <h4 className="font-semibold text-slate-100 mb-0.5">{title}</h4>}
        <div className="text-xs leading-relaxed text-slate-300">{children}</div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
};
