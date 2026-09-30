import React, { useState } from 'react';
import type { Alert, AlertSeverity, Role } from '../types';
import { Button } from '../components/ui/Button';
import { Drawer } from '../components/ui/Drawer';
import { Select } from '../components/ui/Select';
import {
  CheckCircle2,
  Clock,
  ExternalLink,
  SlidersHorizontal,
  ChevronRight,
  Info,
  Check,
  CheckCheck
} from 'lucide-react';

interface AlertsPageProps {
  alerts: Alert[];
  currentUserRole?: Role;
  onAcknowledgeAlert: (alertId: string) => void;
  onResolveAlert: (alertId: string, resolutionType: any, note: string) => void;
  onSelectMachine: (machineId: string) => void;
}

export const AlertsPage: React.FC<AlertsPageProps> = ({
  alerts,
  onAcknowledgeAlert,
  onResolveAlert,
  onSelectMachine,
}) => {
  const [statusFilter, setStatusFilter] = useState<'all' | 'open' | 'acknowledged' | 'resolved'>('all');
  const [severityFilter, setSeverityFilter] = useState<'all' | AlertSeverity>('all');
  const [selectedAlertForDetail, setSelectedAlertForDetail] = useState<Alert | null>(null);
  const [selectedAlertForResolve, setSelectedAlertForResolve] = useState<Alert | null>(null);
  const [resolutionType, setResolutionType] = useState<'issue_resolved' | 'false_alarm' | 'no_action_needed'>('issue_resolved');
  const [resolutionNote, setResolutionNote] = useState('');

  const openCount = alerts.filter(a => a.status === 'open').length;
  const acknowledgedCount = alerts.filter(a => a.status === 'acknowledged').length;
  const criticalCount = alerts.filter(a => a.severity === 'critical' && a.status !== 'resolved').length;

  const filtered = alerts.filter((a) => {
    if (statusFilter !== 'all' && a.status !== statusFilter) return false;
    if (severityFilter !== 'all' && a.severity !== severityFilter) return false;
    return true;
  });

  const handleResolveSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedAlertForResolve) {
      onResolveAlert(
        selectedAlertForResolve.id,
        resolutionType,
        resolutionNote.trim() || 'Verified and resolved by engineering review.'
      );
      setSelectedAlertForResolve(null);
      if (selectedAlertForDetail?.id === selectedAlertForResolve.id) {
        setSelectedAlertForDetail(null);
      }
    }
  };

  const getSeverityBadge = (severity: AlertSeverity) => {
    switch (severity) {
      case 'critical':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-red-950/40 text-red-400 border border-red-800/50">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
            CRITICAL
          </span>
        );
      case 'high':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-950/40 text-amber-400 border border-amber-800/50">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            HIGH
          </span>
        );
      case 'medium':
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-800/60 text-slate-300 border border-slate-700/60">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            MEDIUM
          </span>
        );
      case 'low':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-800/40 text-slate-400 border border-slate-700/40">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            LOW
          </span>
        );
    }
  };

  const getStatusBadge = (status: Alert['status']) => {
    switch (status) {
      case 'open':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-red-950/30 text-red-400 border border-red-900/40">
            ACTIVE
          </span>
        );
      case 'acknowledged':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-amber-950/30 text-amber-300 border border-amber-900/40">
            ACKNOWLEDGED
          </span>
        );
      case 'resolved':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-950/30 text-emerald-400 border border-emerald-900/40">
            RESOLVED
          </span>
        );
    }
  };

  return (
    <div className="space-y-5 animate-in fade-in duration-150">
      {/* Page Title & Operational Metric Strip */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-1 border-b border-[#1f2838]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-slate-100 tracking-tight">Operational Alerts</h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#161f2e] text-slate-400 border border-[#233147]">
              {alerts.length} total events
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time threshold breaches, anomaly triggers, and calibrated failure risk notifications.
          </p>
        </div>

        {/* Operational Status Badges */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#131923] border border-[#222b3b]">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider font-mono">Critical Active</span>
            <span className={`text-xs font-mono font-bold ${criticalCount > 0 ? 'text-red-400' : 'text-slate-400'}`}>
              {criticalCount}
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#131923] border border-[#222b3b]">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider font-mono">Unacknowledged</span>
            <span className={`text-xs font-mono font-bold ${openCount > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
              {openCount}
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-[#131923] border border-[#222b3b]">
            <span className="text-[11px] text-slate-400 uppercase tracking-wider font-mono">In Review</span>
            <span className="text-xs font-mono font-bold text-slate-300">
              {acknowledgedCount}
            </span>
          </div>
        </div>
      </div>

      {/* Filter and Control Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-2 rounded-lg bg-[#111620] border border-[#1f2838]">
        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1">
          {(['all', 'open', 'acknowledged', 'resolved'] as const).map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded text-xs font-medium cursor-pointer transition-colors ${
                statusFilter === st
                  ? 'bg-[#1e293b] text-slate-100 font-semibold border border-[#334155]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#151c27]'
              }`}
            >
              {st === 'all' ? 'All Alerts' : st === 'open' ? 'Active' : st.charAt(0).toUpperCase() + st.slice(1)}
              {st === 'open' && openCount > 0 && (
                <span className="ml-1.5 px-1 py-0.2 rounded text-[10px] bg-red-950/80 text-red-300 font-mono">
                  {openCount}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Severity Filter */}
        <div className="flex items-center gap-2 self-end sm:self-auto">
          <span className="text-[11px] text-slate-400 font-mono uppercase flex items-center gap-1">
            <SlidersHorizontal className="w-3 h-3 text-slate-400" />
            Severity:
          </span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as any)}
            className="h-7 px-2.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-slate-200 focus:outline-hidden focus:border-blue-500 font-mono cursor-pointer"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Operational Alert Table */}
      <div className="rounded-lg border border-[#1f2838] bg-[#111620] overflow-hidden">
        {filtered.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <CheckCheck className="w-8 h-8 text-emerald-500/60 mx-auto" />
            <p className="text-sm font-medium text-slate-300">All machines are currently within configured alert thresholds.</p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              No alert records match the active status/severity filter. Real-time telemetry monitoring remains active.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#1f2838] bg-[#0d121a] text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  <th className="py-2.5 px-4 font-semibold w-28">Severity</th>
                  <th className="py-2.5 px-4 font-semibold w-32">Machine</th>
                  <th className="py-2.5 px-4 font-semibold">Alert Condition</th>
                  <th className="py-2.5 px-4 font-semibold w-32">Trigger Cycle</th>
                  <th className="py-2.5 px-4 font-semibold w-36">Timestamp</th>
                  <th className="py-2.5 px-4 font-semibold w-28">Status</th>
                  <th className="py-2.5 px-4 font-semibold w-40 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#182130]">
                {filtered.map((alert) => {
                  const isOpen = alert.status === 'open';
                  const isCritical = alert.severity === 'critical';

                  return (
                    <tr
                      key={alert.id}
                      onClick={() => setSelectedAlertForDetail(alert)}
                      className={`group cursor-pointer transition-colors ${
                        isOpen && isCritical
                          ? 'bg-red-950/10 hover:bg-red-950/20'
                          : 'hover:bg-[#141b27]'
                      }`}
                    >
                      {/* Severity */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        {getSeverityBadge(alert.severity)}
                      </td>

                      {/* Machine */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectMachine(alert.machineId);
                          }}
                          className="font-mono font-semibold text-slate-200 hover:text-blue-400 flex items-center gap-1 group-hover:underline text-left cursor-pointer"
                        >
                          {alert.machineCode}
                          <ExternalLink className="w-3 h-3 text-slate-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </button>
                        <div className="text-[11px] text-slate-400 truncate max-w-[120px]">
                          {alert.machineName}
                        </div>
                      </td>

                      {/* Alert Message & Recommendation */}
                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-200 leading-snug line-clamp-1">
                          {alert.message}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono mt-0.5 flex items-center gap-2">
                          <span>Rule: {alert.recommendationRuleId}</span>
                          <span className="text-slate-600">&bull;</span>
                          <span className="text-slate-400 truncate max-w-md italic">
                            "{alert.recommendationText}"
                          </span>
                        </div>
                      </td>

                      {/* Trigger Cycle */}
                      <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-300">
                        Cycle #{alert.asOfCycle}
                      </td>

                      {/* Timestamp */}
                      <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-400 text-[11px]">
                        {alert.triggeredAt}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        {getStatusBadge(alert.status)}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1.5">
                          {isOpen && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => onAcknowledgeAlert(alert.id)}
                              className="h-6.5 text-[11px] px-2 py-0 border-amber-800/60 text-amber-300 hover:bg-amber-950/40"
                              title="Acknowledge alert and take ownership"
                            >
                              <Check className="w-3 h-3 mr-1" />
                              Acknowledge
                            </Button>
                          )}
                          {alert.status === 'acknowledged' && (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => setSelectedAlertForResolve(alert)}
                              className="h-6.5 text-[11px] px-2 py-0 text-emerald-400 border-emerald-800/50 hover:bg-emerald-950/30"
                              title="Close alert and document resolution"
                            >
                              <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-400" />
                              Resolve
                            </Button>
                          )}
                          {alert.status === 'resolved' && (
                            <span className="text-[11px] font-mono text-slate-400 pr-2">
                              Archived
                            </span>
                          )}
                          <button
                            type="button"
                            onClick={() => setSelectedAlertForDetail(alert)}
                            className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-[#1e293b] cursor-pointer"
                            title="View details"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Alert Detail Drawer */}
      <Drawer
        isOpen={Boolean(selectedAlertForDetail)}
        onClose={() => setSelectedAlertForDetail(null)}
        title="Alert Telemetry & Investigation"
        subtitle={selectedAlertForDetail ? `${selectedAlertForDetail.machineCode} — Event #${selectedAlertForDetail.id}` : undefined}
        width="md"
      >
        {selectedAlertForDetail && (
          <div className="space-y-5 text-xs text-slate-300">
            {/* Header Status Strip */}
            <div className="p-3 rounded-lg bg-[#0e141f] border border-[#1f2838] flex items-center justify-between">
              <div className="space-y-0.5">
                <span className="text-[11px] font-mono text-slate-400 uppercase">Alert Severity</span>
                <div>{getSeverityBadge(selectedAlertForDetail.severity)}</div>
              </div>
              <div className="space-y-0.5 text-right">
                <span className="text-[11px] font-mono text-slate-400 uppercase">Lifecycle Status</span>
                <div>{getStatusBadge(selectedAlertForDetail.status)}</div>
              </div>
            </div>

            {/* Condition & Context */}
            <div className="space-y-2">
              <div className="text-[11px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
                Event Description
              </div>
              <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] space-y-2">
                <p className="text-slate-100 font-medium text-sm leading-relaxed">
                  {selectedAlertForDetail.message}
                </p>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#1d2636] font-mono text-[11px] text-slate-400">
                  <div>
                    <span className="text-slate-400">Machine:</span>{' '}
                    <span className="text-slate-200 font-semibold">{selectedAlertForDetail.machineCode}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Trigger Cycle:</span>{' '}
                    <span className="text-slate-200 font-semibold">#{selectedAlertForDetail.asOfCycle}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Timestamp:</span>{' '}
                    <span className="text-slate-200">{selectedAlertForDetail.triggeredAt}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Data Reliability:</span>{' '}
                    <span className="text-emerald-400">{selectedAlertForDetail.reliabilityStatus.toUpperCase()}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Recommendation Context */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[11px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
                <span>AI Recommendation</span>
                <span className="text-blue-400 font-mono">Rule: {selectedAlertForDetail.recommendationRuleId}</span>
              </div>
              <div className="p-3 rounded-md bg-[#0d1422] border border-blue-900/40 space-y-2">
                <p className="text-slate-200 leading-relaxed italic">
                  "{selectedAlertForDetail.recommendationText}"
                </p>
                <div className="p-2 rounded bg-[#090d15] border border-[#1b2536] text-[11px] text-slate-400 flex items-start gap-2">
                  <Info className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
                  <span>
                    Deterministic guidance from calibrated prediction horizon (H=30). Requires human engineer verification prior to work order execution.
                  </span>
                </div>
              </div>
            </div>

            {/* Audit Trail / Resolution History */}
            <div className="space-y-2">
              <div className="text-[11px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
                Audit Log & Ownership
              </div>
              <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] space-y-2.5 font-mono text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Clock className="w-3 h-3 text-slate-400" /> Triggered:
                  </span>
                  <span className="text-slate-300">{selectedAlertForDetail.triggeredAt}</span>
                </div>
                {selectedAlertForDetail.acknowledgedBy ? (
                  <div className="flex items-center justify-between pt-1 border-t border-[#1d2636]">
                    <span className="text-amber-400 flex items-center gap-1.5">
                      <Check className="w-3 h-3" /> Acknowledged by:
                    </span>
                    <span className="text-slate-200">{selectedAlertForDetail.acknowledgedBy}</span>
                  </div>
                ) : (
                  <div className="text-slate-400 pt-1 border-t border-[#1d2636] italic">
                    Awaiting engineer acknowledgment
                  </div>
                )}
                {selectedAlertForDetail.resolvedBy && (
                  <div className="pt-2 border-t border-[#1d2636] space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-emerald-400 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3 h-3" /> Resolved by:
                      </span>
                      <span className="text-slate-200">{selectedAlertForDetail.resolvedBy}</span>
                    </div>
                    {selectedAlertForDetail.resolutionType && (
                      <div className="text-slate-400 text-[10px]">
                        Type: <span className="text-slate-300 uppercase">{selectedAlertForDetail.resolutionType.replace(/_/g, ' ')}</span>
                      </div>
                    )}
                    {selectedAlertForDetail.resolutionNote && (
                      <div className="p-2 rounded bg-[#0b1018] text-slate-300 text-xs font-sans mt-1">
                        "{selectedAlertForDetail.resolutionNote}"
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Action Buttons in Drawer */}
            <div className="pt-3 border-t border-[#1f2838] flex items-center justify-between gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSelectedAlertForDetail(null);
                  onSelectMachine(selectedAlertForDetail.machineId);
                }}
                className="text-xs"
              >
                Inspect Telemetry <ExternalLink className="w-3 h-3 ml-1.5" />
              </Button>

              <div className="flex items-center gap-2">
                {selectedAlertForDetail.status === 'open' && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      onAcknowledgeAlert(selectedAlertForDetail.id);
                      setSelectedAlertForDetail({
                        ...selectedAlertForDetail,
                        status: 'acknowledged',
                        acknowledgedBy: 'current_user',
                      });
                    }}
                  >
                    Acknowledge
                  </Button>
                )}
                {selectedAlertForDetail.status === 'acknowledged' && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setSelectedAlertForResolve(selectedAlertForDetail)}
                    className="bg-emerald-600 hover:bg-emerald-500 border-emerald-500"
                  >
                    Resolve Alert
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}
      </Drawer>

      {/* Resolve Alert Modal Dialog */}
      <Drawer
        isOpen={Boolean(selectedAlertForResolve)}
        onClose={() => setSelectedAlertForResolve(null)}
        title="Resolve Maintenance Alert"
        subtitle={selectedAlertForResolve ? `${selectedAlertForResolve.machineCode} — Event #${selectedAlertForResolve.id}` : undefined}
        width="sm"
      >
        <form onSubmit={handleResolveSubmit} className="space-y-4 text-xs">
          <Select
            label="Resolution Classification (PRD §FR-14)"
            value={resolutionType}
            onChange={(e) => setResolutionType(e.target.value as any)}
            options={[
              { label: 'Issue Resolved — Work order verified and complete', value: 'issue_resolved' },
              { label: 'False Alarm — Sensor telemetry within acceptable tolerance', value: 'false_alarm' },
              { label: 'No Action Needed — Operational run scheduled for phase retirement', value: 'no_action_needed' },
            ]}
          />

          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-slate-300">
              Resolution Note &amp; Verification Details <span className="text-red-400">*</span>
            </label>
            <textarea
              rows={3}
              value={resolutionNote}
              onChange={(e) => setResolutionNote(e.target.value)}
              placeholder="Record findings, replaced components, or calibration details..."
              className="w-full px-3 py-2 rounded-md bg-[#161f2e] border border-[#253246] text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-blue-500 font-sans"
              required
            />
          </div>

          <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] text-slate-400 text-[11px] leading-relaxed">
            Submitting this resolution moves this alert to archived history and records your identity in the audit trail.
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-[#1f2838]">
            <Button
              variant="secondary"
              size="sm"
              type="button"
              onClick={() => setSelectedAlertForResolve(null)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              type="submit"
              className="bg-emerald-600 hover:bg-emerald-500 border-emerald-500"
            >
              Confirm Resolution
            </Button>
          </div>
        </form>
      </Drawer>
    </div>
  );
};
