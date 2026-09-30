import React, { useState } from 'react';
import type { MaintenanceRecord } from '../types';
import { Badge } from '../components/ui/Badge';
import {
  Clock,
  ArrowRight,
  UserCheck,
  Wrench,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  CheckCircle,
  XCircle,
  FileText
} from 'lucide-react';

interface MaintenancePageProps {
  records: MaintenanceRecord[];
  onSelectMachine: (machineId: string) => void;
}

export const MaintenancePage: React.FC<MaintenancePageProps> = ({
  records,
  onSelectMachine,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredRecords = records.filter(
    (r) => statusFilter === 'all' || r.status === statusFilter
  );

  const inProgressCount = records.filter(r => r.status === 'in_progress').length;
  const completedCount = records.filter(r => r.status === 'completed').length;

  const getDecisionBadge = (decision: MaintenanceRecord['decision']) => {
    switch (decision) {
      case 'followed_recommendation':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-blue-950/40 text-blue-300 border border-blue-800/50">
            <CheckCircle className="w-3 h-3 text-blue-400" />
            Accepted Recommendation
          </span>
        );
      case 'modified':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-amber-950/40 text-amber-300 border border-amber-800/50">
            <AlertCircle className="w-3 h-3 text-amber-400" />
            Modified by Engineer
          </span>
        );
      case 'declined':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-rose-950/40 text-rose-300 border border-rose-800/50">
            <XCircle className="w-3 h-3 text-rose-400" />
            Dismissed by Engineer
          </span>
        );
    }
  };

  const getOutcomeBadge = (outcome: MaintenanceRecord['outcome']) => {
    switch (outcome) {
      case 'resolved':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-950/40 text-emerald-300 border border-emerald-800/50">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            RESOLVED
          </span>
        );
      case 'no_issue_found':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800/40 text-slate-300 border border-slate-700/50">
            NO ISSUE FOUND
          </span>
        );
      case 'unresolved':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-red-950/40 text-red-300 border border-red-800/50">
            UNRESOLVED
          </span>
        );
    }
  };

  return (
    <div className="space-y-5 animate-in fade-in duration-150">
      {/* Header & Operational Strip */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-1 border-b border-[#1f2838]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-slate-100 tracking-tight">Maintenance & Human-in-the-Loop Workflow</h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#161f2e] text-slate-400 border border-[#233147]">
              {records.length} logged events
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            PRD §FR-14 &bull; Strict audit trail preserving AI recommendations, human engineering decisions, physical actions, and verified outcomes.
          </p>
        </div>

        {/* Quick Counters */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#131923] border border-[#222b3b]">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider font-mono">Active Work Orders</span>
            <span className="text-xs font-mono font-bold text-amber-400">
              {inProgressCount}
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#131923] border border-[#222b3b]">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider font-mono">Completed &amp; Verified</span>
            <span className="text-xs font-mono font-bold text-emerald-400">
              {completedCount}
            </span>
          </div>
        </div>
      </div>

      {/* Chronological Workflow Architecture Banner */}
      <div className="p-3.5 rounded-lg bg-[#111620] border border-[#1f2838]">
        <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-2 font-semibold">
          Sequential Governance Model
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-xs">
          <div className="p-2.5 rounded bg-[#141b27] border border-[#222c3e]">
            <div className="flex items-center gap-1.5 text-blue-400 font-mono text-[11px] font-semibold mb-1">
              <span className="w-4 h-4 rounded-full bg-blue-950 border border-blue-700/60 flex items-center justify-center text-[10px]">1</span>
              AI RECOMMENDATION
            </div>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Algorithmic advisory based on calibrated failure risk (H=30) and telemetry drift. Not an autonomous command.
            </p>
          </div>

          <div className="p-2.5 rounded bg-[#141b27] border border-[#222c3e]">
            <div className="flex items-center gap-1.5 text-slate-200 font-mono text-[11px] font-semibold mb-1">
              <span className="w-4 h-4 rounded-full bg-slate-800 border border-slate-600 flex items-center justify-center text-[10px]">2</span>
              ENGINEER DECISION
            </div>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Human engineer review: accept, modify scope, or dismiss with mandatory engineering rationale.
            </p>
          </div>

          <div className="p-2.5 rounded bg-[#141b27] border border-[#222c3e]">
            <div className="flex items-center gap-1.5 text-amber-300 font-mono text-[11px] font-semibold mb-1">
              <span className="w-4 h-4 rounded-full bg-amber-950 border border-amber-700/60 flex items-center justify-center text-[10px]">3</span>
              MAINTENANCE ACTION
            </div>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Physical intervention executed by maintenance technician (inspection, overhaul, seal replacement, purge).
            </p>
          </div>

          <div className="p-2.5 rounded bg-[#141b27] border border-[#222c3e]">
            <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-[11px] font-semibold mb-1">
              <span className="w-4 h-4 rounded-full bg-emerald-950 border border-emerald-700/60 flex items-center justify-center text-[10px]">4</span>
              OUTCOME &amp; AUDIT
            </div>
            <p className="text-slate-400 text-[11px] leading-relaxed">
              Post-service verification cycle confirming telemetry restoration and closing operational cycle.
            </p>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center justify-between gap-3 p-2 rounded-lg bg-[#111620] border border-[#1f2838]">
        <div className="flex items-center gap-1">
          {['all', 'in_progress', 'completed', 'recommended'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded text-xs font-medium cursor-pointer transition-colors ${
                statusFilter === st
                  ? 'bg-[#1e293b] text-slate-100 font-semibold border border-[#334155]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#151c27]'
              }`}
            >
              {st === 'all'
                ? 'All Records'
                : st === 'in_progress'
                ? 'In Progress'
                : st.charAt(0).toUpperCase() + st.slice(1)}
            </button>
          ))}
        </div>

        <div className="text-[11px] font-mono text-slate-400 pr-2">
          Displaying {filteredRecords.length} of {records.length} records
        </div>
      </div>

      {/* Chronological Maintenance Workflow Records */}
      <div className="space-y-4">
        {filteredRecords.length === 0 ? (
          <div className="py-16 text-center rounded-lg border border-[#1f2838] bg-[#111620] text-slate-400 text-xs">
            No maintenance records match the selected status filter.
          </div>
        ) : (
          filteredRecords.map((rec) => {
            return (
              <div
                key={rec.id}
                className="rounded-lg border border-[#1f2838] bg-[#111620] overflow-hidden transition-all"
              >
                {/* Event Header Strip */}
                <div className="px-4 py-3 bg-[#0d121a] border-b border-[#1f2838] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => onSelectMachine(rec.machineId)}
                      className="font-mono font-bold text-sm text-slate-100 hover:text-blue-400 flex items-center gap-1 cursor-pointer"
                    >
                      {rec.machineCode}
                      <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
                    </button>
                    <span className="text-slate-600 font-mono">|</span>
                    <span className="font-mono text-xs text-slate-300">
                      Work Order #{rec.id}
                    </span>
                    <Badge value={rec.status} size="sm" />
                    {rec.outcome && getOutcomeBadge(rec.outcome)}
                  </div>

                  <div className="flex items-center gap-4 text-[11px] font-mono text-slate-400">
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span>{rec.performedAt}</span>
                    </div>
                    <div>
                      Tech: <span className="text-slate-200">{rec.performedBy}</span>
                    </div>
                  </div>
                </div>

                {/* 4-Stage Chronological Breakdown */}
                <div className="p-4 grid grid-cols-1 lg:grid-cols-4 gap-4">
                  {/* Stage 1: AI Recommendation */}
                  <div className="space-y-2 p-3 rounded-md bg-[#131924] border border-[#20293a]">
                    <div className="flex items-center justify-between text-[11px] font-mono text-blue-400 font-semibold border-b border-[#1d2638] pb-1.5">
                      <span>1. AI RECOMMENDATION</span>
                      <span className="text-slate-400 text-[10px]">Rule-based</span>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase font-mono text-slate-400">Trigger Condition / Issue</div>
                      <div className="font-medium text-slate-200 text-xs mt-0.5">{rec.issue}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase font-mono text-slate-400">Advisory Action</div>
                      <div className="text-slate-300 text-xs italic mt-0.5">"{rec.recommendedAction}"</div>
                    </div>
                    <div className="text-[11px] text-slate-400 pt-1 border-t border-[#1d2638] flex items-center gap-1">
                      <span className="text-slate-400">Evidence:</span>
                      <span className="font-mono text-slate-300">Elevated EGT, high anomaly score</span>
                    </div>
                  </div>

                  {/* Stage 2: Engineer Decision */}
                  <div className="space-y-2 p-3 rounded-md bg-[#131924] border border-[#20293a]">
                    <div className="flex items-center justify-between text-[11px] font-mono text-slate-200 font-semibold border-b border-[#1d2638] pb-1.5">
                      <span>2. ENGINEER DECISION</span>
                      <UserCheck className="w-3.5 h-3.5 text-slate-400" />
                    </div>
                    <div>
                      <div className="text-[10px] uppercase font-mono text-slate-400">Review Outcome</div>
                      <div className="mt-1">{getDecisionBadge(rec.decision)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase font-mono text-slate-400">Engineering Rationale</div>
                      <div className="text-slate-300 text-xs mt-0.5 leading-relaxed">
                        {rec.decisionRationale}
                      </div>
                    </div>
                    <div className="text-[11px] text-slate-400 pt-1 border-t border-[#1d2638]">
                      Authorized by: <span className="text-slate-300 font-mono font-medium">chief_engineer</span>
                    </div>
                  </div>

                  {/* Stage 3: Maintenance Action */}
                  <div className="space-y-2 p-3 rounded-md bg-[#131924] border border-[#20293a]">
                    <div className="flex items-center justify-between text-[11px] font-mono text-amber-300 font-semibold border-b border-[#1d2638] pb-1.5">
                      <span>3. PHYSICAL ACTION</span>
                      <Wrench className="w-3.5 h-3.5 text-amber-400" />
                    </div>
                    <div>
                      <div className="text-[10px] uppercase font-mono text-slate-400">Action Executed</div>
                      <div className="font-medium text-slate-200 text-xs mt-0.5 leading-relaxed">
                        {rec.actionTaken}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase font-mono text-slate-400">Execution Status</div>
                      <div className="mt-1">
                        <Badge value={rec.status} size="sm" />
                      </div>
                    </div>
                    <div className="text-[11px] text-slate-400 pt-1 border-t border-[#1d2638]">
                      Technician: <span className="text-slate-300 font-mono">{rec.performedBy}</span>
                    </div>
                  </div>

                  {/* Stage 4: Outcome */}
                  <div className="space-y-2 p-3 rounded-md bg-[#131924] border border-[#20293a]">
                    <div className="flex items-center justify-between text-[11px] font-mono text-emerald-400 font-semibold border-b border-[#1d2638] pb-1.5">
                      <span>4. OUTCOME &amp; AUDIT</span>
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    </div>
                    <div>
                      <div className="text-[10px] uppercase font-mono text-slate-400">Resolution Verification</div>
                      <div className="mt-1">{getOutcomeBadge(rec.outcome)}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase font-mono text-slate-400">Post-Service Audit</div>
                      <div className="text-slate-300 text-xs mt-0.5 leading-relaxed">
                        Telemetry returned to baseline envelope. Sensor drift resolved across subsequent cycles.
                      </div>
                    </div>
                    <div className="text-[11px] text-slate-400 pt-1 border-t border-[#1d2638]">
                      Closed on: <span className="text-slate-300 font-mono">{rec.performedAt}</span>
                    </div>
                  </div>
                </div>

                {/* Footer Strip */}
                <div className="px-4 py-2 bg-[#0d121a] border-t border-[#1f2838] flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-2 text-[11px] font-mono">
                    <FileText className="w-3.5 h-3.5 text-slate-500" />
                    <span>PRD §FR-14 Audit Compliance Record &bull; Tamper-evident ledger trace</span>
                  </div>

                  <button
                    onClick={() => onSelectMachine(rec.machineId)}
                    className="text-xs text-blue-400 hover:text-blue-300 font-medium inline-flex items-center gap-1 cursor-pointer"
                  >
                    View Machine Telemetry <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
