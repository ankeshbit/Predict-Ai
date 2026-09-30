import React from 'react';
import type { Machine, Alert } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { ArrowRight, Cpu, HelpCircle } from 'lucide-react';

interface OverviewDashboardProps {
  machines: Machine[];
  alerts: Alert[];
  onSelectMachine: (machineId: string) => void;
  onOpenAlerts: () => void;
  onOpenOnboarding: () => void;
}

export const OverviewDashboardPage: React.FC<OverviewDashboardProps> = ({
  machines,
  alerts,
  onSelectMachine,
  onOpenAlerts,
  onOpenOnboarding,
}) => {
  const totalMachines = machines.length;
  const healthyCount = machines.filter(
    (m) => m.healthBand === 'Healthy' || m.healthBand === 'Excellent'
  ).length;
  const warningCount = machines.filter(
    (m) => m.healthBand === 'Warning' || m.healthBand === 'Poor'
  ).length;
  const criticalCount = machines.filter(
    (m) => m.healthBand === 'Critical' || m.riskLevel === 'Critical'
  ).length;
  const avgHealth = Math.round(
    machines.reduce((acc, m) => acc + m.healthIndicator, 0) / (totalMachines || 1)
  );
  const openAlerts = alerts.filter((a) => a.status === 'open');

  // Sorted by failure probability descending
  const priorityMachines = [...machines].sort(
    (a, b) => b.failureProbability - a.failureProbability
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
                Fleet Condition & Risk Overview
              </h1>
              <span className="text-[10px] font-mono text-slate-500">•</span>
              <span className="text-xs font-mono text-slate-400">8 Units Scored</span>
            </div>
            <p className="text-[11px] text-slate-400">
              Active models: <span className="font-mono text-slate-300">LightGBM-FD001-v1.2</span> &bull; <span className="font-mono text-slate-300">IsolationForest-v1.0</span> &bull; Horizon H = 30 cycles
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

      {/* 2. Compact Status Summary Strip (Single unified engineering container) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div className="p-3 rounded-md bg-[#131923] border border-[#20293a]">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
            Fleet Health Average
          </div>
          <div className="flex items-baseline gap-1.5 mt-1">
            <span className="text-2xl font-mono font-bold text-white tabular-nums">{avgHealth}</span>
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
              {machines.filter((m) => m.operationalStatus === 'active').length}
            </span>
            <span className="text-xs font-mono text-slate-400">Active</span>
            <span className="text-xs font-mono text-blue-400">
              ({machines.filter((m) => m.operationalStatus === 'maintenance').length} Maint)
            </span>
          </div>
          <div className="text-[10px] font-mono text-slate-500 mt-1">
            Syncs with maintenance logs
          </div>
        </div>

        <div className="p-3 rounded-md bg-[#131923] border border-[#20293a]">
          <div className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold flex items-center justify-between">
            <span>Pending Alerts</span>
            {openAlerts.length > 0 && <span className="w-2 h-2 rounded-full bg-rose-500" />}
          </div>
          <div className="flex items-baseline gap-1.5 mt-1">
            <span className="text-2xl font-mono font-bold text-rose-400 tabular-nums">
              {openAlerts.length}
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
        title="Fleet Risk & Health Ranking"
        subtitle="Ranked by calibrated failure probability at horizon H = 30 cycles &bull; Click row to open workstation"
        action={
          <span className="text-[11px] font-mono text-slate-500">
            Sorted by P(Failure) &darr;
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
                <th className="py-2.5 px-3">P(Failure) [H=30]</th>
                <th className="py-2.5 px-3">Risk Level</th>
                <th className="py-2.5 px-3">Anomaly State</th>
                <th className="py-2.5 px-3">Primary Drift Feature</th>
                <th className="py-2.5 px-3 text-right">Workstation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#18212e]">
              {priorityMachines.map((m) => {
                const isCrit = m.riskLevel === 'Critical';

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
                      <div className="text-[10px] text-slate-400 font-sans">{m.name}</div>
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge value={m.operationalStatus} size="xs" />
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      <span className="font-bold text-slate-200">{m.healthIndicator}</span>
                      <span className="text-[10px] text-slate-500"> /100</span>
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      <span
                        className={`font-bold ${
                          m.failureProbability >= 0.5 ? 'text-rose-400' : 'text-slate-200'
                        }`}
                      >
                        {(m.failureProbability * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge value={m.riskLevel} size="xs" />
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                      {(m.anomalySeverity * 100).toFixed(0)}% severity
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-300">
                      {m.explanation.topContributingFeatures[0]?.feature || '—'}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <span className="inline-flex items-center text-blue-400 hover:text-blue-300 font-mono text-[11px]">
                        Inspect <ArrowRight className="w-3 h-3 ml-1" />
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 4. Split Section: Urgent Action Queue & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Urgent Action Queue */}
        <Card
          title="Active Alert Triage Queue"
          subtitle="Alerts triggered when failure probability &ge; threshold for consecutive cycles"
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

        {/* Fleet Health Band Distribution Summary */}
        <Card
          title="Distribution & Health Bands"
          subtitle="Fixed bands covering 0–100 deterministic scoring"
        >
          <div className="space-y-3 text-xs font-mono">
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span className="text-emerald-400">Excellent (86–100)</span>
                <span className="text-slate-500">2 units (25%)</span>
              </div>
              <div className="h-1.5 w-full bg-[#1b2332] rounded-xs overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-xs" style={{ width: '25%' }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span className="text-teal-400">Healthy (71–85)</span>
                <span className="text-slate-500">2 units (25%)</span>
              </div>
              <div className="h-1.5 w-full bg-[#1b2332] rounded-xs overflow-hidden">
                <div className="h-full bg-teal-500 rounded-xs" style={{ width: '25%' }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span className="text-amber-400">Warning (51–70)</span>
                <span className="text-slate-500">2 units (25%)</span>
              </div>
              <div className="h-1.5 w-full bg-[#1b2332] rounded-xs overflow-hidden">
                <div className="h-full bg-amber-500 rounded-xs" style={{ width: '25%' }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span className="text-orange-400">Poor (31–50)</span>
                <span className="text-slate-500">2 units (25%)</span>
              </div>
              <div className="h-1.5 w-full bg-[#1b2332] rounded-xs overflow-hidden">
                <div className="h-full bg-orange-500 rounded-xs" style={{ width: '25%' }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span className="text-rose-400">Critical (0–30)</span>
                <span className="text-slate-500">0 units (0%)</span>
              </div>
              <div className="h-1.5 w-full bg-[#1b2332] rounded-xs overflow-hidden">
                <div className="h-full bg-rose-500 rounded-xs" style={{ width: '0%' }} />
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
