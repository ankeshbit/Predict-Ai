/**
 * SettingsPage — PRD §FR-10 Health Indicator Weights · PRD §FR-11 Prediction Parameters.
 *
 * All displayed values (weights, thresholds, audit log) come from API hooks.
 * No hardcoded model names, timestamps, usernames, or metric values.
 * Profile section shows real user data from useCurrentUser().
 * The fake token field has been removed (no tokens are stored in the frontend).
 * Audit log comes from GET /admin/audit-log.
 */

import React, { useState } from 'react';
import type { Role } from '../types';
import { Button } from '../components/ui/Button';
import {
  User,
  Key,
  Bell,
  Cpu,
  Sliders,
  Server,
  Shield,
  Loader2,
} from 'lucide-react';
import {
  useHealthConfig,
  useUpdateHealthConfig,
  useAlertRules,
  useAuditLog,
} from '../api';
import { useCurrentUser } from '../api';

interface SettingsPageProps {
  currentUserRole: Role;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ currentUserRole }) => {
  const [activeSection, setActiveSection] = useState<
    'profile' | 'authentication' | 'notifications' | 'predictions' | 'health' | 'system'
  >('health');

  // Health indicator weights — from API
  const { data: healthConfig, isLoading: healthLoading } = useHealthConfig();
  const updateHealth = useUpdateHealthConfig();

  const [overrideWAnom, setWAnom] = useState<number | null>(null);
  const [overrideTrendEnabled, setTrendEnabled] = useState<boolean | null>(null);
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const wAnom = overrideWAnom != null
    ? overrideWAnom
    : (healthConfig && typeof healthConfig.anomaly_weight === 'number'
      ? Math.round(healthConfig.anomaly_weight * 100)
      : null);
  const trendEnabled = overrideTrendEnabled != null
    ? overrideTrendEnabled
    : (healthConfig && typeof healthConfig.trend_enabled === 'boolean'
      ? healthConfig.trend_enabled
      : false);

  const wRisk = wAnom != null ? 100 - wAnom : null;

  const handleSaveHealth = (e: React.FormEvent) => {
    e.preventDefault();
    if (wAnom == null) return;
    updateHealth.mutate(
      { anomaly_weight: wAnom / 100, trend_enabled: trendEnabled },
      {
        onSuccess: () => {
          setSaveMsg('Weights saved successfully.');
          setTimeout(() => setSaveMsg(null), 2500);
        },
      }
    );
  };

  // Alert rules from API
  const { data: alertRules, isLoading: rulesLoading } = useAlertRules();

  // Audit log from API (admin only)
  const { data: auditLogData, isLoading: auditLoading } = useAuditLog();
  const auditLogs = auditLogData?.items ?? [];

  // Current user profile from API
  const { data: currentUser } = useCurrentUser();

  const sections = [
    { id: 'profile',        label: 'Profile',             icon: <User className="w-4 h-4" /> },
    { id: 'authentication', label: 'Authentication',       icon: <Key className="w-4 h-4" /> },
    { id: 'notifications',  label: 'Notifications',        icon: <Bell className="w-4 h-4" /> },
    { id: 'predictions',    label: 'Prediction Settings',  icon: <Cpu className="w-4 h-4" /> },
    { id: 'health',         label: 'Health Indicator',     icon: <Sliders className="w-4 h-4" /> },
    { id: 'system',         label: 'System &amp; Audit',        icon: <Server className="w-4 h-4" /> },
  ] as const;

  return (
    <div className="space-y-5 animate-in fade-in duration-150">
      {/* Header */}
      <div className="pb-1 border-b border-[#1f2838]">
        <div className="flex items-center gap-2">
          <h1 className="text-lg font-semibold text-slate-100 tracking-tight">Platform Configuration &amp; Settings</h1>
          <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#161f2e] text-slate-400 border border-[#233147]">
            {currentUserRole === 'admin' ? 'Admin Access' : 'Engineer (Read-Only Mode)'}
          </span>
        </div>
        <p className="text-xs text-slate-400 mt-0.5">
          Deterministic scoring parameters, operational thresholds, telemetry ingest limits, and administrative controls.
        </p>
      </div>

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        {/* Left Settings Navigation */}
        <div className="space-y-1">
          {sections.map((sec) => {
            const isActive = activeSection === sec.id;
            return (
              <button
                key={sec.id}
                onClick={() => setActiveSection(sec.id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium cursor-pointer transition-colors text-left ${
                  isActive
                    ? 'bg-[#1a2333] text-blue-400 font-semibold border border-blue-900/60'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#131923]'
                }`}
              >
                <span className={isActive ? 'text-blue-400' : 'text-slate-400'}>{sec.icon}</span>
                <span dangerouslySetInnerHTML={{ __html: sec.label }} />
              </button>
            );
          })}
        </div>

        {/* Content Area */}
        <div className="md:col-span-3 space-y-4">

          {/* PROFILE — from useCurrentUser() */}
          {activeSection === 'profile' && (
            <div className="p-5 rounded-lg border border-[#1f2838] bg-[#111620] space-y-4 text-xs">
              <div className="border-b border-[#1f2838] pb-2">
                <h3 className="font-semibold text-slate-100 text-sm">Operator Profile</h3>
                <p className="text-[11px] text-slate-400">Current active user credentials and session permissions</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-mono text-slate-400 uppercase mb-1">Full Name</label>
                  <input
                    type="text"
                    disabled
                    value={currentUser?.fullName ?? '—'}
                    className="w-full px-3 py-1.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-slate-200 font-sans"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-slate-400 uppercase mb-1">Email Address</label>
                  <input
                    type="email"
                    disabled
                    value={currentUser?.email ?? '—'}
                    className="w-full px-3 py-1.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-slate-200 font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-slate-400 uppercase mb-1">Assigned Role</label>
                  <input
                    type="text"
                    disabled
                    value={currentUserRole.toUpperCase()}
                    className="w-full px-3 py-1.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-blue-400 font-mono font-bold"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-slate-400 uppercase mb-1">Dataset Domain</label>
                  <input
                    type="text"
                    disabled
                    value="NASA C-MAPSS FD001 (Simulated)"
                    className="w-full px-3 py-1.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-slate-200 font-sans"
                  />
                </div>
              </div>
            </div>
          )}

          {/* AUTHENTICATION */}
          {activeSection === 'authentication' && (
            <div className="p-5 rounded-lg border border-[#1f2838] bg-[#111620] space-y-4 text-xs">
              <div className="border-b border-[#1f2838] pb-2">
                <h3 className="font-semibold text-slate-100 text-sm">Authentication &amp; Session Policy</h3>
                <p className="text-[11px] text-slate-400">JWT-based session management and RBAC enforcement</p>
              </div>

              <div className="space-y-3">
                <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] space-y-1">
                  <span className="font-semibold text-slate-200 text-xs flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-emerald-400" /> Session Security Policy
                  </span>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Role-Based Access Control (RBAC) enforced across all endpoints. Engineer role can review alerts and
                    record maintenance decisions. Admin role required to mutate model registry or reconfigure health
                    indicator formula weights.
                  </p>
                </div>
                <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] space-y-1">
                  <span className="font-semibold text-slate-200 text-xs">Token Management</span>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    API tokens for offline model registration are issued server-side and transmitted only once.
                    Contact your system administrator to rotate or issue a new CLI token.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* NOTIFICATIONS */}
          {activeSection === 'notifications' && (
            <div className="p-5 rounded-lg border border-[#1f2838] bg-[#111620] space-y-4 text-xs">
              <div className="border-b border-[#1f2838] pb-2">
                <h3 className="font-semibold text-slate-100 text-sm">Alert Routing &amp; Notification Channels</h3>
                <p className="text-[11px] text-slate-400">Operational delivery rules for critical events</p>
              </div>

              {rulesLoading ? (
                <div className="flex items-center gap-2 text-slate-400 font-mono text-xs">
                  <Loader2 className="w-4 h-4 animate-spin" /> Loading alert rules…
                </div>
              ) : alertRules && alertRules.length > 0 ? (
                <div className="space-y-3">
                  {alertRules.map((rule) => (
                    <div key={rule.id} className="p-3 rounded-md bg-[#131924] border border-[#222b3b]">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="font-semibold text-slate-200">{rule.rule_id}</div>
                          <div className="text-[11px] text-slate-400 mt-0.5">
                            Type: <span className="font-mono text-slate-300">{rule.alert_type}</span>
                            {' '}· P(Failure) threshold: <span className="font-mono text-slate-300">{(rule.failure_probability_threshold * 100).toFixed(0)}%</span>
                            {' '}· Consecutive cycles: <span className="font-mono text-slate-300">{rule.consecutive_cycles}</span>
                          </div>
                        </div>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold ${rule.is_active ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60' : 'bg-slate-900 text-slate-500 border border-slate-700'}`}>
                          {rule.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 font-mono text-xs py-4 text-center">
                  No alert rules configured. Configure alert rules via admin panel.
                </p>
              )}
            </div>
          )}

          {/* PREDICTION SETTINGS — from alert rules & health config */}
          {activeSection === 'predictions' && (
            <div className="p-5 rounded-lg border border-[#1f2838] bg-[#111620] space-y-4 text-xs">
              <div className="border-b border-[#1f2838] pb-2">
                <h3 className="font-semibold text-slate-100 text-sm">Prediction Horizon &amp; Anomaly Filters</h3>
                <p className="text-[11px] text-slate-400">PRD §FR-11 Parameters controlling inference and trigger sensitivity</p>
              </div>

              {rulesLoading ? (
                <div className="flex items-center gap-2 text-slate-400 font-mono text-xs">
                  <Loader2 className="w-4 h-4 animate-spin" /> Loading prediction parameters…
                </div>
              ) : alertRules && alertRules.length > 0 ? (
                <div className="space-y-4 max-w-lg">
                  {alertRules.map((rule) => (
                    <div key={rule.id} className="p-3 rounded-md bg-[#131924] border border-[#222b3b]">
                      <div className="font-semibold text-slate-200 mb-2">{rule.rule_id}</div>
                      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
                        <span>Failure Probability τ</span>
                        <span className="text-slate-200 font-bold">{(rule.failure_probability_threshold * 100).toFixed(0)}%</span>
                        <span>Consecutive Cycles</span>
                        <span className="text-slate-200 font-bold">{rule.consecutive_cycles}</span>
                        <span>Anomaly Severity</span>
                        <span className="text-slate-200 font-bold">{rule.anomaly_severity_threshold}</span>
                        <span>Status</span>
                        <span className={rule.is_active ? 'text-emerald-400' : 'text-slate-500'}>
                          {rule.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>
                  ))}
                  {currentUserRole !== 'admin' && (
                    <p className="text-slate-400 text-xs italic">
                      Read-only mode. Administrator privileges required to reconfigure prediction thresholds.
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-slate-500 font-mono text-xs py-4 text-center">
                  Model evaluation not available. No alert rules found.
                </p>
              )}
            </div>
          )}

          {/* HEALTH INDICATOR — from useHealthConfig() */}
          {activeSection === 'health' && (
            <div className="p-5 rounded-lg border border-[#1f2838] bg-[#111620] space-y-4 text-xs">
              <div className="border-b border-[#1f2838] pb-2">
                <h3 className="font-semibold text-slate-100 text-sm">Machine Health Indicator Weights (PRD §FR-10)</h3>
                <p className="text-[11px] text-slate-400">
                  Formula: Health = 100 − (W_risk × s_risk + W_anom × s_anom + W_trend × s_trend). Total sum must equal 100%.
                </p>
              </div>

              {healthLoading ? (
                <div className="flex items-center gap-2 text-slate-400 font-mono text-xs">
                  <Loader2 className="w-4 h-4 animate-spin" /> Loading health config…
                </div>
              ) : !healthConfig || wAnom == null ? (
                <p className="text-slate-500 font-mono text-xs py-4 text-center">
                  Health configuration not available.
                </p>
              ) : (
                <form onSubmit={handleSaveHealth} className="space-y-5 max-w-xl">
                  <div className="space-y-4">
                    {/* W_risk (derived = 100 - wAnom) */}
                    <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b]">
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="font-semibold text-slate-200">Failure Risk Weight (W_risk)</span>
                        <span className="font-mono text-blue-400 font-bold text-xs">{wRisk != null ? `${wRisk}%` : '—'}</span>
                      </div>
                      <div className="h-1.5 w-full bg-[#1b2536] rounded overflow-hidden">
                        <div className="h-full bg-blue-500 rounded transition-all" style={{ width: `${wRisk != null ? wRisk : 0}%` }} />
                      </div>
                      <div className="text-[10px] text-slate-400 mt-1">
                        Direct penalty from calibrated failure probability at horizon H.
                        Derived automatically as 100% − W_anom.
                      </div>
                    </div>

                    {/* W_anom (editable) */}
                    <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b]">
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="font-semibold text-slate-200">Anomaly Severity Weight (W_anom)</span>
                        <span className="font-mono text-amber-400 font-bold text-xs">{wAnom != null ? `${wAnom}%` : '—'}</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={wAnom != null ? wAnom : 0}
                        disabled={currentUserRole !== 'admin'}
                        onChange={(e) => setWAnom(Number(e.target.value))}
                        className="w-full h-1.5 bg-[#1b2536] rounded appearance-none cursor-pointer accent-amber-500"
                      />
                      <div className="text-[10px] text-slate-400 mt-1">
                        Penalty derived from unsupervised reconstruction/distance error.
                      </div>
                    </div>

                    {/* Trend toggle */}
                    <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b]">
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="font-semibold text-slate-200">Trend &amp; Degradation Slope (W_trend)</span>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={trendEnabled}
                            disabled={currentUserRole !== 'admin'}
                            onChange={(e) => setTrendEnabled(e.target.checked)}
                            className="rounded accent-blue-600 w-4 h-4 cursor-pointer"
                          />
                          <span className="font-mono text-slate-300 font-bold text-xs">{trendEnabled ? 'Enabled' : 'Disabled'}</span>
                        </label>
                      </div>
                      <div className="text-[10px] text-slate-400 mt-1">
                        Penalty based on monotonic telemetry drift over rolling window. Toggle activates/deactivates component.
                      </div>
                    </div>
                  </div>

                  {/* Active config from API */}
                  {healthConfig && (
                    <div className="flex items-center justify-between p-3 rounded-md bg-[#0d121a] border border-[#1f2838]">
                      <span className="font-mono text-slate-300 text-xs">Active Config Version:</span>
                      <span className="font-mono text-blue-400 font-bold text-xs">{healthConfig.version}</span>
                    </div>
                  )}

                  {currentUserRole === 'admin' ? (
                    <div className="flex items-center gap-3">
                      <Button
                        type="submit"
                        variant="primary"
                        size="sm"
                        disabled={updateHealth.isPending}
                      >
                        {updateHealth.isPending ? (
                          <Loader2 className="w-3 h-3 animate-spin inline mr-1" />
                        ) : null}
                        Save New Formula Weights
                      </Button>
                      {saveMsg && <span className="text-emerald-400 font-mono text-xs">{saveMsg}</span>}
                      {updateHealth.isError && (
                        <span className="text-rose-400 font-mono text-xs">Save failed. {String(updateHealth.error)}</span>
                      )}
                    </div>
                  ) : (
                    <p className="text-slate-400 text-xs italic">
                      Read-only mode. Administrator privileges required to reconfigure health weights.
                    </p>
                  )}
                </form>
              )}
            </div>
          )}

          {/* SYSTEM & AUDIT — from useAuditLog() */}
          {activeSection === 'system' && (
            <div className="p-5 rounded-lg border border-[#1f2838] bg-[#111620] space-y-4 text-xs">
              <div className="border-b border-[#1f2838] pb-2">
                <h3 className="font-semibold text-slate-100 text-sm">System Audit Log &amp; Environment</h3>
                <p className="text-[11px] text-slate-400">Tamper-evident record of configuration changes and schema activations</p>
              </div>

              {currentUserRole !== 'admin' ? (
                <p className="text-slate-500 font-mono text-xs py-4 text-center">
                  Admin access required to view the system audit log.
                </p>
              ) : auditLoading ? (
                <div className="flex items-center gap-2 text-slate-400 font-mono text-xs">
                  <Loader2 className="w-4 h-4 animate-spin" /> Loading audit log…
                </div>
              ) : auditLogs.length === 0 ? (
                <p className="text-slate-500 font-mono text-xs py-4 text-center">
                  No audit log entries recorded yet.
                </p>
              ) : (
                <div className="overflow-x-auto rounded border border-[#1f2838]">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-[#1f2838] bg-[#0d121a] text-slate-400 font-mono text-[11px] uppercase">
                        <th className="py-2.5 px-3 font-semibold">Action</th>
                        <th className="py-2.5 px-3 font-semibold">Resource</th>
                        <th className="py-2.5 px-3 font-semibold">Timestamp (UTC)</th>
                        <th className="py-2.5 px-3 font-semibold">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#172130]">
                      {auditLogs.map((log) => (
                        <tr key={log.id} className="hover:bg-[#141b27]">
                          <td className="py-2.5 px-3 font-medium text-slate-200">{log.action}</td>
                          <td className="py-2.5 px-3 font-mono text-slate-300 text-[11px]">
                            {log.resource_type}{log.resource_id ? ` / ${log.resource_id.slice(0, 8)}…` : ''}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-slate-400 text-[11px]">
                            {new Date(log.created_at).toISOString().replace('T', ' ').slice(0, 19)} UTC
                          </td>
                          <td className="py-2.5 px-3 text-slate-300 text-[11px] font-mono">
                            {log.details ? JSON.stringify(log.details).slice(0, 80) : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
