import React from 'react';
import type { HealthBand, RiskLevel, MachineStatus, AlertStatus, ReliabilityStatus } from '../../types';

interface BadgeProps {
  children?: React.ReactNode;
  variant?: 'health' | 'risk' | 'status' | 'alert' | 'reliability' | 'neutral' | 'demo';
  value?: HealthBand | RiskLevel | MachineStatus | AlertStatus | ReliabilityStatus | string | null;
  size?: 'xs' | 'sm';
  className?: string;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  value,
  size = 'xs',
  className = '',
  dot = true,
}) => {
  const content = children != null ? children : value;
  if (content == null || content === '—') {
    return <span className="font-mono text-xs text-slate-500">—</span>;
  }
  const val = String(content);

  const sizeClasses = size === 'xs' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5';

  const getColorClasses = (): { bgBorderText: string; dotColor: string } => {
    // Health bands (PRD §FR-10)
    if (val === 'Excellent' || val === 'Healthy' || val === 'active') {
      return {
        bgBorderText: 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60',
        dotColor: 'bg-emerald-400',
      };
    }
    if (val === 'Warning' || val === 'acknowledged') {
      return {
        bgBorderText: 'bg-amber-950/40 text-amber-300 border-amber-800/60',
        dotColor: 'bg-amber-400',
      };
    }
    if (val === 'Poor' || val === 'High') {
      return {
        bgBorderText: 'bg-orange-950/40 text-orange-300 border-orange-800/60',
        dotColor: 'bg-orange-400',
      };
    }
    if (val === 'Critical' || val === 'open') {
      return {
        bgBorderText: 'bg-rose-950/50 text-rose-300 border-rose-800/70',
        dotColor: 'bg-rose-500',
      };
    }

    // Risk levels
    if (val === 'Low') {
      return {
        bgBorderText: 'bg-slate-900/60 text-slate-300 border-slate-700/60',
        dotColor: 'bg-slate-400',
      };
    }
    if (val === 'Medium') {
      return {
        bgBorderText: 'bg-amber-950/40 text-amber-300 border-amber-800/60',
        dotColor: 'bg-amber-400',
      };
    }

    // Maintenance / status
    if (val === 'maintenance') {
      return {
        bgBorderText: 'bg-blue-950/40 text-blue-300 border-blue-800/60',
        dotColor: 'bg-blue-400',
      };
    }
    if (val === 'resolved') {
      return {
        bgBorderText: 'bg-slate-900/60 text-slate-300 border-slate-700/60',
        dotColor: 'bg-emerald-400',
      };
    }

    // Reliability
    if (val === 'ok') {
      return {
        bgBorderText: 'bg-slate-900/60 text-slate-300 border-slate-700/60',
        dotColor: 'bg-emerald-400',
      };
    }
    if (val === 'reduced') {
      return {
        bgBorderText: 'bg-amber-950/60 text-amber-300 border-amber-700/80',
        dotColor: 'bg-amber-400',
      };
    }

    // Demo / Simulated
    if (variant === 'demo' || val.includes('Demo') || val.includes('Simulated')) {
      return {
        bgBorderText: 'bg-[#18212e] text-slate-400 border-[#2a374c] font-mono',
        dotColor: 'bg-blue-400',
      };
    }

    return {
      bgBorderText: 'bg-slate-900/60 text-slate-300 border-slate-700/60',
      dotColor: 'bg-slate-400',
    };
  };

  const { bgBorderText, dotColor } = getColorClasses();

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-sm border font-medium uppercase tracking-wider font-mono select-none ${sizeClasses} ${bgBorderText} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColor} shrink-0`} />}
      <span>{content}</span>
    </span>
  );
};
