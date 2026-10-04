import React from 'react';
import type { Machine, Alert } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { ArrowRight, Cpu, HelpCircle, Play, Square } from 'lucide-react';
import { useDashboardSummary, useCurrentUser } from '../api';
import { useDemoReplayStatus, useStartReplay, useStopReplay } from '../api/demo';

interface OverviewDashboardProps {
  machines: Machine[];
  alerts: Alert[];
  onSelectMachine: (machineId: string) => void;
  onOpenAlerts: () => void;
  onOpenOnboarding: () => void;
}

const HEALTH_BANDS = [
  { key: 'Excellent', label: 'Excellent (86–100)', color: 'text-emerald-400', bar: 'bg-emerald-500' },
  { key: 'Healthy',   label: 'Healthy (71–85)',   color: 'text-teal-400',    bar: 'bg-teal-500'    },
  { key: 'Warning',   label: 'Warning (51–70)',   color: 'text-amber-400',   bar: 'bg-amber-500'   },
  { key: 'Poor',      label: 'Poor (31–50)',      color: 'text-orange-400',  bar: 'bg-orange-500'  },
  { key: 'Critical',  label: 'Critical (0–30)',   color: 'text-rose-400',    bar: 'bg-rose-500'    },
] as const;

export const OverviewDashboardPage: React.FC<OverviewDashboardProps> = ({
  machines,
  alerts,
  onSelectMachine,
  onOpenAlerts,
  onOpenOnboarding,
}) => {
  const { data: summary } = useDashboardSummary();
  const { data: currentUser } = useCurrentUser();
  const isAdmin = currentUser?.role === 'admin';
  const { data: replayStatus } = useDemoReplayStatus(Boolean(isAdmin));
  const startReplayMutation = useStartReplay();
  const stopReplayMutation = useStopReplay();

  const totalMachines = summary?.total_machines ?? machines.length;
  const healthyCount  = (summary?.health_band_counts?.['Excellent'] ?? 0) + (summary?.health_band_counts?.['Healthy'] ?? 0);
  const warningCount  = (summary?.health_band_counts?.['Warning'] ?? 0) + (summary?.health_band_counts?.['Poor'] ?? 0);
  const criticalCount = summary?.health_band_counts?.['Critical'] ?? 0;
  const avgHealth = summary?.average_health_indicator != null
    ? Math.round(summary.average_health_indicator)
    : null;
  const openAlertsCount = summary?.open_alerts_count ?? alerts.filter((a) => a.status === 'open').length;
  const activeCount = summary?.active_count ?? summary?.operational_counts?.['active'] ?? 0;
  const maintCount  = summary?.maintenance_count ?? summary?.operational_counts?.['maintenance'] ?? 0;
  const openAlerts = alerts.filter((a) => a.status === 'open');

  // Sorted by failure probability descending — use backend data where available
  const priorityMachines = [...machines].sort(
    (a, b) => (b.failureProbability ?? 0) - (a.failureProbability ?? 0)
  );

  return (
    <div className="space-y-5 animate-in fade-in duration-100 select-none">
      {/* 1. Top Engineering Context Strip */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-[#111621] border border-[#1e2636] rounded-md">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-[#17202e] border border-[#253247] flex items-center justify-center text-slate-300">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
                Fleet Condition &amp; Risk Overview
              </h1>
              <span className="text-[10px] font-mono text-slate-500">•</span>
              <span className="text-xs font-mono text-slate-400">{totalMachines} Units Scored</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="xs"
            onClick={onOpenOnboarding}
            icon={<HelpCircle className="w-3 h-3 text-slate-400" />}
          >
            Platform Architecture &amp; Tour
          </Button>
        </div>
      </div>

      {/* Admin Demo Replay (Simulated Stream) Control */}
      {isAdmin && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-[#111722] border border-[#233147] rounded-md">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full shrink-0 ${replayStatus?.running ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`} />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-slate-200">
                  Demo replay (simulated stream)
                </span>
                <span
                  data-testid="replay-status-badge"
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded border uppercase ${
                    replayStatus?.running
                      ? 'bg-emerald-950/70 text-emerald-300 border-emerald-800'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}
                >
                  {replayStatus?.running ? 'Streaming' : 'Stopped'}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">
                Advances held-out demo engines cycle-by-cycle through live scoring and alert rules.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {replayStatus?.running ? (
              <Button
                variant="danger"
                size="xs"
                data-testid="stop-replay-btn"
                onClick={() => stopReplayMutation.mutate()}
                isLoading={stopReplayMutation.isPending}
                icon={<Square className="w-3 h-3" />}
              >
                Stop Replay
              </Button>
            ) : (
              <Button
                variant="primary"
                size="xs"
                data-testid="start-replay-btn"
                onClick={() => startReplayMutation.mutate()}
                isLoading={startReplayMutation.isPending}
                icon={<Play className="w-3 h-3" />}
              >
                Start Replay
              </Button>
            )}
          </div>
        </div>
      )}

      {/* 2. Compact Status Summary Strip (Single unified engineering container) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div className="p-3 rounded-md bg-[#131923] border border-[#20293a]">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Fleet Health Average
          </div>
          <div className="flex items-baseline gap-1.5 mt-1">
            <span className="text-2xl font-mono font-bold text-white tabular-nums">
              {avgHealth != null ? avgHealth : '—'}
            </span>
            <span className="text-xs font-mono text-slate-500">/ 100</span>
          </div>
          <div className="text-[10px] font-mono text-slate-500 mt-1">
            Weighted composite indicator
          </div>
        </div>

        <div className="p-3 rounded-md bg-[#131923] border border-[#20293a]">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Condition Breakdown
          </div>
          <div className="flex items-center gap-2 mt-1.5 font-mono text-xs">
            <span className="text-emerald-400 font-bold">{healthyCount} Healthy</span>
            <span className="text-slate-600">/</span>
            <span className="text-amber-400 font-bold">{warningCount} Warning</span>
            <span className="text-slate-600">/</span>
            <span className="text-rose-400 font-bold">{criticalCount} Crit</span>
          </div>
          <div className="text-[10px] font-mono text-slate-500 mt-1">
            {totalMachines} total engines in registry
          </div>
        </div>

        <div className="p-3 rounded-md bg-[#131923] border border-[#20293a]">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Operational Status
          </div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-mono font-bold text-white tabular-nums">
              {activeCount}
            </span>
            <span className="text-xs font-mono text-slate-400">Active</span>
            <span className="text-xs font-mono text-blue-400">
              ({maintCount} Maint)
            </span>
          </div>
          <div className="text-[10px] font-mono text-slate-500 mt-1">
            Syncs with maintenance logs
          </div>
        </div>

        <div className="p-3 rounded-md bg-[#131923] border border-[#20293a]">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center justify-between">
            <span>Pending Alerts</span>
            {openAlertsCount > 0 && <span className="w-2 h-2 rounded-full bg-rose-500" />}
          </div>
          <div className="flex items-baseline gap-1.5 mt-1">
            <span className="text-2xl font-mono font-bold text-rose-400 tabular-nums">
              {openAlertsCount}
            </span>
            <span className="text-xs font-mono text-slate-500">Unresolved</span>
          </div>
          <div className="text-[10px] font-mono text-slate-500 mt-1">
            Requires engineer review
          </div>
        </div>
      </div>

      {/* 3. Primary Actionable Table: Machines Requiring Attention */}
      <Card
        title="Fleet Risk &amp; Health Ranking"
        subtitle="Ranked by calibrated failure probability · Click row to open workstation"
        action={
          <span className="text-[11px] font-mono text-slate-500">
            Sorted by P(Failure) ↓
          </span>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse tabular-nums">
            <thead>
              <tr className="border-b border-[#20293a] bg-[#111721] text-[10px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">Unit ID</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Health Ind.</th>
                <th className="py-2.5 px-3">P(Failure)</th>
                <th className="py-2.5 px-3">Risk Level</th>
                <th className="py-2.5 px-3">Anomaly State</th>
                <th className="py-2.5 px-3">Current Cycle</th>
                <th className="py-2.5 px-3 text-right">Workstation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#18212e]">
              {priorityMachines.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500 font-mono text-xs">
                    No machines in registry. Seed demo data or add machines via the Datasets page.
                  </td>
                </tr>
              ) : (
                priorityMachines.map((m) => {
                  const isCrit = m.riskLevel === 'Critical';
                  const fp = m.failureProbability ?? 0;

                  return (
                    <tr
                      key={m.id}
                      onClick={() => onSelectMachine(m.id)}
                      className={`transition-colors cursor-pointer ${
                        isCrit ? 'bg-rose-950/20 hover:bg-rose-950/30' : 'hover:bg-[#161d29]'
                      }`}
                    >
                      <td className="py-2.5 px-3">
                        <div className="font-mono font-bold text-slate-100">{m.machineCode}</div>
                        {m.name && m.name !== m.machineCode && (
                          <div className="text-[10px] text-slate-400 font-sans">{m.name}</div>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        <Badge value={m.operationalStatus} size="xs" />
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {m.healthIndicator != null ? (
                          <>
                            <span className="font-bold text-slate-200">{Math.round(m.healthIndicator)}</span>
                            <span className="text-[10px] text-slate-500"> /100</span>
                          </>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 font-mono">
                        {m.currentCycle != null ? (
                          <span
                            className={`font-bold ${
                              fp >= 0.5 ? 'text-rose-400' : 'text-slate-200'
                            }`}
                          >
                            {(fp * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3">
                        {m.riskLevel ? <Badge value={m.riskLevel} size="xs" /> : <span className="text-slate-500">—</span>}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                        {m.anomalySeverity != null
                          ? `${(m.anomalySeverity * 100).toFixed(0)}% severity`
                          : '—'}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[11px] text-slate-300">
                        {m.currentCycle != null ? `Cycle ${m.currentCycle}` : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <span className="inline-flex items-center text-blue-400 hover:text-blue-300 font-mono text-[11px]">
                          Inspect <ArrowRight className="w-3 h-3 ml-1" />
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 4. Split Section: Urgent Action Queue & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Urgent Action Queue */}
        <Card
          title="Active Alert Triage Queue"
          subtitle="Alerts triggered when failure probability ≥ threshold for consecutive cycles"
          action={
            <button
              onClick={onOpenAlerts}
              className="text-[11px] font-mono text-blue-400 hover:underline cursor-pointer"
            >
              View all ({alerts.length})
            </button>
          }
        >
          <div className="space-y-2.5">
            {openAlerts.length === 0 ? (
              <p className="text-xs text-slate-500 font-mono py-4 text-center">
                All machines currently operating within nominal thresholds.
              </p>
            ) : (
              openAlerts.map((alt) => (
                <div
                  key={alt.id}
                  className="p-3 rounded bg-[#0f141e] border border-rose-900/60 space-y-2 text-xs"
                >
                  <div className="flex items-center justify-between font-mono">
                    <span className="font-bold text-white">{alt.machineCode}</span>
                    <Badge value={alt.status} size="xs" />
                  </div>
                  <p className="text-slate-300 leading-relaxed font-sans">{alt.message}</p>
                  <div className="p-2 rounded bg-[#0b0e14] border border-[#1b2332] text-[11px] text-slate-400 font-sans">
                    <span className="font-mono text-blue-400 font-bold block mb-0.5">
                      Recommendation ({alt.recommendationRuleId}):
                    </span>
                    {alt.recommendationText}
                  </div>
                  <div className="pt-1 flex items-center justify-between text-[11px]">
                    <span className="font-mono text-slate-500">As of cycle {alt.asOfCycle}</span>
                    <Button
                      variant="primary"
                      size="xs"
                      onClick={() => onSelectMachine(alt.machineId)}
                      icon={<ArrowRight className="w-3 h-3" />}
                    >
                      Open Workstation
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Fleet Health Band Distribution — from API */}
        <Card
          title="Distribution &amp; Health Bands"
          subtitle="Fixed bands covering 0–100 deterministic scoring"
        >
          <div className="space-y-3 text-xs font-mono">
            {summary == null ? (
              <p className="text-slate-500 py-4 text-center">Loading distribution…</p>
            ) : (
              HEALTH_BANDS.map(({ key, label, color, bar }) => {
                const count = summary.health_band_counts?.[key] ?? 0;
                const pct = totalMachines > 0 ? Math.round((count / totalMachines) * 100) : 0;
                return (
                  <div key={key} className="space-y-1">
                    <div className="flex justify-between text-slate-300">
                      <span className={color}>{label}</span>
                      <span className="text-slate-500">{count} unit{count !== 1 ? 's' : ''} ({pct}%)</span>
                    </div>
                    <div className="h-1.5 w-full bg-[#1b2332] rounded-xs overflow-hidden">
                      <div
                        className={`h-full ${bar} rounded-xs transition-all duration-500`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
