import React from 'react';
import type { HealthBand, HealthComponents } from '../../types';
import { Badge } from '../ui/Badge';

interface HealthGaugeProps {
  score: number | null; // 0 - 100 or null if unscored
  band?: HealthBand | null;
  components: HealthComponents;
  currentCycle?: number;
  className?: string;
}

export const HealthGauge: React.FC<HealthGaugeProps> = ({
  score,
  band,
  components,
  currentCycle,
  className = '',
}) => {
  const getBandColor = (b?: HealthBand | null) => {
    switch (b) {
      case 'Excellent':
      case 'Healthy':
        return 'bg-emerald-500';
      case 'Warning':
        return 'bg-amber-500';
      case 'Poor':
      case 'Critical':
        return 'bg-rose-500';
      default:
        return 'bg-blue-500';
    }
  };

  const getExplanation = () => {
    if (score == null) return 'No machine health calculation available yet.';
    switch (band) {
      case 'Excellent':
        return 'Optimal operational health; all monitored channels within nominal training envelopes.';
      case 'Healthy':
        return 'Nominal health with minor expected cycle accumulation across baseline sensors.';
      case 'Warning':
        return 'Degradation precursors detected; early drift emerging on thermodynamic sensors.';
      case 'Poor':
        return 'Substantial health impairment driven by failure risk and continuous anomaly episode.';
      case 'Critical':
        return 'Critical degradation stage; immediate mechanical inspection required prior to further cycles.';
      default:
        return 'Machine health evaluated within designated operating profile.';
    }
  };

  return (
    <div className={`p-4 rounded-md bg-[#131923] border border-[#222b3b] space-y-4 ${className}`}>
      {/* Top Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Machine Health Indicator
          </div>
          <div className="flex items-baseline gap-2.5 mt-1">
            {score != null ? (
              <>
                <span className="text-3xl font-mono font-bold text-white tabular-nums">{score}</span>
                <span className="text-xs font-mono text-slate-500">/ 100</span>
                {band && <Badge value={band} size="sm" />}
              </>
            ) : (
              <span className="text-2xl font-mono font-bold text-slate-400">No score yet</span>
            )}
          </div>
        </div>

        {currentCycle !== undefined && currentCycle !== null && (
          <div className="text-right text-[11px] font-mono text-slate-500">
            <div>As of cycle</div>
            <div className="text-slate-300 font-semibold">{currentCycle}</div>
          </div>
        )}
      </div>

      {/* Horizontal Segmented Health Scale */}
      <div className="space-y-1.5">
        <div className="h-2 w-full bg-[#1b2332] rounded-xs overflow-hidden flex">
          {score != null && (
            <div
              className={`h-full ${getBandColor(band)} transition-all duration-300`}
              style={{ width: `${Math.max(2, score)}%` }}
            />
          )}
        </div>
        <div className="flex justify-between text-[10px] font-mono text-slate-500 select-none">
          <span>0 (Critical)</span>
          <span>30 (Poor)</span>
          <span>50 (Warning)</span>
          <span>70 (Healthy)</span>
          <span>100</span>
        </div>
      </div>

      {/* Analytical Interpretation */}
      <p className="text-xs text-slate-300 leading-relaxed">
        {getExplanation()}
      </p>

      {/* Three-Component Penalty Breakdown */}
      <div className="pt-3 border-t border-[#1d2634] grid grid-cols-3 gap-2 text-xs">
        <div className="p-2 rounded bg-[#0f141d] border border-[#1a2230]">
          <div className="text-[10px] font-mono text-slate-400 truncate">Risk Penalty (50w)</div>
          <div className="text-sm font-mono font-bold text-rose-400 mt-0.5 tabular-nums">
            {components.failureRiskPenalty != null ? `-${components.failureRiskPenalty} pts` : '—'}
          </div>
        </div>

        <div className="p-2 rounded bg-[#0f141d] border border-[#1a2230]">
          <div className="text-[10px] font-mono text-slate-400 truncate">Anomaly Penalty (30w)</div>
          <div className="text-sm font-mono font-bold text-amber-400 mt-0.5 tabular-nums">
            {components.anomalyPenalty != null ? `-${components.anomalyPenalty} pts` : '—'}
          </div>
        </div>

        <div className="p-2 rounded bg-[#0f141d] border border-[#1a2230]">
          <div className="text-[10px] font-mono text-slate-400 truncate">Trend Penalty (20w)</div>
          <div className="text-sm font-mono font-bold text-orange-400 mt-0.5 tabular-nums">
            {components.trendPenalty != null ? `-${components.trendPenalty} pts` : '—'}
          </div>
        </div>
      </div>

      <div className="text-[10px] font-mono text-slate-500">
        Deterministic calculation: 100 - &Sigma;(W_i &times; s_i). Not a physical sensor measurement.
      </div>
    </div>
  );
};
