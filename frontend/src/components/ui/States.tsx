import React from 'react';
import { Loader2, Inbox, AlertTriangle } from 'lucide-react';
import { Button } from './Button';

export const LoadingState: React.FC<{ message?: string }> = ({ message = 'Loading data...' }) => (
  <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
    <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-3" />
    <p className="text-sm text-slate-400">{message}</p>
  </div>
);

export const EmptyState: React.FC<{
  title?: string;
  description?: string;
  action?: { label: string; onClick: () => void };
  icon?: React.ReactNode;
}> = ({
  title = 'No items found',
  description = 'There is currently no data to display for this selection.',
  action,
  icon,
}) => (
  <div className="flex flex-col items-center justify-center py-16 px-4 text-center rounded-xl border border-dashed border-[#1b2b48] bg-[#090f1b]/50">
    <div className="p-3 bg-slate-800/40 rounded-full text-slate-400 mb-3">
      {icon || <Inbox className="w-6 h-6" />}
    </div>
    <h3 className="text-sm font-semibold text-slate-200 mb-1">{title}</h3>
    <p className="text-xs text-slate-400 max-w-sm mb-4 leading-relaxed">{description}</p>
    {action && (
      <Button variant="secondary" size="sm" onClick={action.onClick}>
        {action.label}
      </Button>
    )}
  </div>
);

export const ErrorState: React.FC<{
  title?: string;
  message?: string;
  onRetry?: () => void;
}> = ({
  title = 'Something went wrong',
  message = 'An unexpected error occurred while loading this view.',
  onRetry,
}) => (
  <div className="flex flex-col items-center justify-center py-16 px-4 text-center rounded-xl border border-rose-900/40 bg-rose-950/10">
    <div className="p-3 bg-rose-950/60 rounded-full text-rose-400 mb-3">
      <AlertTriangle className="w-6 h-6" />
    </div>
    <h3 className="text-sm font-semibold text-slate-200 mb-1">{title}</h3>
    <p className="text-xs text-slate-400 max-w-sm mb-4">{message}</p>
    {onRetry && (
      <Button variant="secondary" size="sm" onClick={onRetry}>
        Retry
      </Button>
    )}
  </div>
);
