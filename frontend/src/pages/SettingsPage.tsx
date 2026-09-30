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
  Shield
} from 'lucide-react';

interface SettingsPageProps {
  currentUserRole: Role;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({ currentUserRole }) => {
  const [activeSection, setActiveSection] = useState<
    'profile' | 'authentication' | 'notifications' | 'predictions' | 'health' | 'system'
  >('health');

  // Health indicator weights state
  const [wRisk, setWRisk] = useState(50);
  const [wAnom, setWAnom] = useState(30);
  const [wTrend, setWTrend] = useState(20);
  const [isSaved, setIsSaved] = useState(false);

  // Prediction settings
  const [consecutivePoints, setConsecutivePoints] = useState(5);
  const [criticalProbThreshold, setCriticalProbThreshold] = useState(0.80);
  const [defaultHorizon, setDefaultHorizon] = useState(30);

  const totalWeight = wRisk + wAnom + wTrend;
  const isWeightValid = totalWeight === 100;

  const handleSaveHealth = (e: React.FormEvent) => {
    e.preventDefault();
    if (isWeightValid) {
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 2500);
    }
  };

  const auditLogs = [
    { id: 1, action: 'Updated Health Indicator weights', user: 'admin@demo.internal', time: '2026-09-30 14:10:00 UTC', details: 'Weights set to 50 / 30 / 20' },
    { id: 2, action: 'Activated Model Version', user: 'admin@demo.internal', time: '2026-09-28 15:00:00 UTC', details: 'LightGBM-FD001-v1.2 set active' },
    { id: 3, action: 'Ingested Dataset Version', user: 'admin@demo.internal', time: '2026-09-28 12:00:00 UTC', details: 'NASA C-MAPSS FD001 v1.0 standard' },
  ];

  const sections = [
    { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
    { id: 'authentication', label: 'Authentication', icon: <Key className="w-4 h-4" /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell className="w-4 h-4" /> },
    { id: 'predictions', label: 'Prediction Settings', icon: <Cpu className="w-4 h-4" /> },
    { id: 'health', label: 'Health Indicator', icon: <Sliders className="w-4 h-4" /> },
    { id: 'system', label: 'System & Audit', icon: <Server className="w-4 h-4" /> },
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

      {/* Two-Column Layout: Left Nav + Content Area (Section 19) */}
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
                <span>{sec.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Area */}
        <div className="md:col-span-3 space-y-4">
          {/* PROFILE */}
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
                    value="Lead Reliability Engineer"
                    className="w-full px-3 py-1.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-slate-200 font-sans"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono text-slate-400 uppercase mb-1">Email Address</label>
                  <input
                    type="email"
                    disabled
                    value="engineer@predicore.internal"
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
                  <label className="block text-[11px] font-mono text-slate-400 uppercase mb-1">Assigned Facility</label>
                  <input
                    type="text"
                    disabled
                    value="Turbofan Test Cell #4 (NASA C-MAPSS)"
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
                <h3 className="font-semibold text-slate-100 text-sm">Authentication &amp; API Credentials</h3>
                <p className="text-[11px] text-slate-400">Tokens for offline Python model registration and telemetry scripts</p>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-[11px] font-mono text-slate-400 uppercase mb-1">Active CLI Ingest Token</label>
                  <div className="flex gap-2">
                    <input
                      type="password"
                      readOnly
                      value="predicore_live_79a3fc992bb1048e91024cd"
                      className="flex-1 px-3 py-1.5 rounded bg-[#0b1018] border border-[#253246] text-xs text-slate-300 font-mono"
                    />
                    <Button variant="outline" size="sm" onClick={() => alert('Token copied to clipboard')}>
                      Copy
                    </Button>
                  </div>
                  <span className="text-[10px] text-slate-400 mt-1 block">Used by `python -m app.cli` to push calibrated model artifacts.</span>
                </div>

                <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] space-y-1">
                  <span className="font-semibold text-slate-200 text-xs flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5 text-emerald-400" /> Session Security Policy
                  </span>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    Role-Based Access Control (RBAC) enforced across all endpoints. Engineer role can review alerts and record maintenance. Admin role required to mutate model registry or change formula scoring weights.
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

              <div className="space-y-3">
                <label className="flex items-center gap-3 p-3 rounded-md bg-[#131924] border border-[#222b3b] cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded accent-blue-600 w-4 h-4 cursor-pointer" />
                  <div>
                    <div className="font-semibold text-slate-200">Critical Failure Alerts (Probability &gt; 80%)</div>
                    <div className="text-[11px] text-slate-400">Immediate operational broadcast to console and on-duty engineer pager.</div>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 rounded-md bg-[#131924] border border-[#222b3b] cursor-pointer">
                  <input type="checkbox" defaultChecked className="rounded accent-blue-600 w-4 h-4 cursor-pointer" />
                  <div>
                    <div className="font-semibold text-slate-200">Severe Telemetry Anomaly Triggers (&gt; 5 consecutive cycles)</div>
                    <div className="text-[11px] text-slate-400">Flags unusual sensor covariance outside established flight envelopes.</div>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 rounded-md bg-[#131924] border border-[#222b3b] cursor-pointer">
                  <input type="checkbox" className="rounded accent-blue-600 w-4 h-4 cursor-pointer" />
                  <div>
                    <div className="font-semibold text-slate-200">Daily Fleet Health Summary Digest</div>
                    <div className="text-[11px] text-slate-400">Periodic shift report detailing newly acknowledged work orders.</div>
                  </div>
                </label>
              </div>
            </div>
          )}

          {/* PREDICTION SETTINGS */}
          {activeSection === 'predictions' && (
            <div className="p-5 rounded-lg border border-[#1f2838] bg-[#111620] space-y-4 text-xs">
              <div className="border-b border-[#1f2838] pb-2">
                <h3 className="font-semibold text-slate-100 text-sm">Prediction Horizon &amp; Anomaly Filters</h3>
                <p className="text-[11px] text-slate-400">PRD §FR-11 Parameters controlling inference and trigger sensitivity</p>
              </div>

              <div className="space-y-4 max-w-lg">
                <div>
                  <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1">
                    Prediction Horizon (H Cycles)
                  </label>
                  <input
                    type="number"
                    value={defaultHorizon}
                    onChange={(e) => setDefaultHorizon(Number(e.target.value))}
                    disabled={currentUserRole !== 'admin'}
                    className="w-full px-3 py-1.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-slate-100 font-mono"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block">
                    Fixed horizon at H=30 cycles. Governs binary classification target label.
                  </span>
                </div>

                <div>
                  <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1">
                    Consecutive Anomaly Cycles Threshold
                  </label>
                  <input
                    type="number"
                    value={consecutivePoints}
                    onChange={(e) => setConsecutivePoints(Number(e.target.value))}
                    disabled={currentUserRole !== 'admin'}
                    className="w-full px-3 py-1.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-slate-100 font-mono"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block">
                    Suppresses isolated single-point sensor noise. Requires N continuous out-of-envelope cycles before triggering warning.
                  </span>
                </div>

                <div>
                  <label className="block text-[11px] font-mono text-slate-300 font-semibold mb-1">
                    Critical Failure Probability Threshold (τ)
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    value={criticalProbThreshold}
                    onChange={(e) => setCriticalProbThreshold(Number(e.target.value))}
                    disabled={currentUserRole !== 'admin'}
                    className="w-full px-3 py-1.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-slate-100 font-mono"
                  />
                  <span className="text-[10px] text-slate-400 mt-1 block">
                    Calibrated probability at which an alert transitions to Critical severity.
                  </span>
                </div>

                {currentUserRole === 'admin' && (
                  <Button variant="primary" size="sm">
                    Save Prediction Parameters
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* HEALTH INDICATOR */}
          {activeSection === 'health' && (
            <div className="p-5 rounded-lg border border-[#1f2838] bg-[#111620] space-y-4 text-xs">
              <div className="border-b border-[#1f2838] pb-2">
                <h3 className="font-semibold text-slate-100 text-sm">Machine Health Indicator Weights (PRD §FR-10)</h3>
                <p className="text-[11px] text-slate-400">
                  Formula: Health = 100 - (W_risk × s_risk + W_anom × s_anom + W_trend × s_trend). Total sum must equal 100%.
                </p>
              </div>

              <form onSubmit={handleSaveHealth} className="space-y-5 max-w-xl">
                <div className="space-y-4">
                  {/* W_risk */}
                  <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b]">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="font-semibold text-slate-200">Failure Risk Weight (W_risk)</span>
                      <span className="font-mono text-blue-400 font-bold text-xs">{wRisk}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={wRisk}
                      disabled={currentUserRole !== 'admin'}
                      onChange={(e) => setWRisk(Number(e.target.value))}
                      className="w-full h-1.5 bg-[#1b2536] rounded appearance-none cursor-pointer accent-blue-500"
                    />
                    <div className="text-[10px] text-slate-400 mt-1">
                      Direct penalty from calibrated failure probability at horizon H=30.
                    </div>
                  </div>

                  {/* W_anom */}
                  <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b]">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="font-semibold text-slate-200">Anomaly Severity Weight (W_anom)</span>
                      <span className="font-mono text-amber-400 font-bold text-xs">{wAnom}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={wAnom}
                      disabled={currentUserRole !== 'admin'}
                      onChange={(e) => setWAnom(Number(e.target.value))}
                      className="w-full h-1.5 bg-[#1b2536] rounded appearance-none cursor-pointer accent-amber-500"
                    />
                    <div className="text-[10px] text-slate-400 mt-1">
                      Penalty derived from unsupervised reconstruction/distance error.
                    </div>
                  </div>

                  {/* W_trend */}
                  <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b]">
                    <div className="flex justify-between items-center mb-1.5">
                      <span className="font-semibold text-slate-200">Trend &amp; Degradation Slope (W_trend)</span>
                      <span className="font-mono text-slate-300 font-bold text-xs">{wTrend}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={wTrend}
                      disabled={currentUserRole !== 'admin'}
                      onChange={(e) => setWTrend(Number(e.target.value))}
                      className="w-full h-1.5 bg-[#1b2536] rounded appearance-none cursor-pointer accent-slate-400"
                    />
                    <div className="text-[10px] text-slate-400 mt-1">
                      Penalty based on monotonic telemetry drift over the rolling 20-cycle window.
                    </div>
                  </div>
                </div>

                {/* Sum Validation Indicator */}
                <div className="flex items-center justify-between p-3 rounded-md bg-[#0d121a] border border-[#1f2838]">
                  <span className="font-mono text-slate-300 text-xs">Total Weight Balance:</span>
                  <span
                    className={`font-mono font-bold text-xs ${
                      isWeightValid ? 'text-emerald-400' : 'text-red-400'
                    }`}
                  >
                    {totalWeight}% / 100% {isWeightValid ? '✓ (Valid)' : '✗ (Must equal exactly 100%)'}
                  </span>
                </div>

                {currentUserRole === 'admin' ? (
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    disabled={!isWeightValid}
                  >
                    {isSaved ? 'Weights Updated & Applied' : 'Save New Formula Weights'}
                  </Button>
                ) : (
                  <p className="text-slate-400 text-xs italic">
                    Read-only mode. Administrator privileges required to reconfigure health weights.
                  </p>
                )}
              </form>
            </div>
          )}

          {/* SYSTEM & AUDIT */}
          {activeSection === 'system' && (
            <div className="p-5 rounded-lg border border-[#1f2838] bg-[#111620] space-y-4 text-xs">
              <div className="border-b border-[#1f2838] pb-2">
                <h3 className="font-semibold text-slate-100 text-sm">System Audit Log &amp; Environment</h3>
                <p className="text-[11px] text-slate-400">Tamper-evident record of configuration changes and schema activations</p>
              </div>

              <div className="overflow-x-auto rounded border border-[#1f2838]">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[#1f2838] bg-[#0d121a] text-slate-400 font-mono text-[11px] uppercase">
                      <th className="py-2.5 px-3 font-semibold">Action</th>
                      <th className="py-2.5 px-3 font-semibold">Operator</th>
                      <th className="py-2.5 px-3 font-semibold">Timestamp</th>
                      <th className="py-2.5 px-3 font-semibold">Audit Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#172130]">
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-[#141b27]">
                        <td className="py-2.5 px-3 font-medium text-slate-200">{log.action}</td>
                        <td className="py-2.5 px-3 font-mono text-slate-300 text-[11px]">{log.user}</td>
                        <td className="py-2.5 px-3 font-mono text-slate-400 text-[11px]">{log.time}</td>
                        <td className="py-2.5 px-3 text-slate-300 text-[11px] font-mono">{log.details}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
