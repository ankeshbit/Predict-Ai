import React, { useState } from 'react';
import type { Machine, Alert, MaintenanceRecord, SensorReading, Role } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { HealthGauge } from '../components/charts/HealthGauge';
import { SensorLineChart } from '../components/charts/SensorLineChart';
import { FeatureImportanceChart } from '../components/charts/FeatureImportanceChart';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import {
  ArrowLeft,
  Wrench,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

interface MachineDetailPageProps {
  machine: Machine;
  alerts: Alert[];
  maintenanceRecords: MaintenanceRecord[];
  sensorHistory: SensorReading[];
  onBack: () => void;
  currentUserRole: Role;
  onAcknowledgeAlert: (alertId: string) => void;
  onRecordMaintenance: (record: Omit<MaintenanceRecord, 'id' | 'performedAt'>) => void;
}

export const MachineDetailPage: React.FC<MachineDetailPageProps> = ({
  machine,
  alerts,
  maintenanceRecords,
  sensorHistory,
  onBack,
  currentUserRole: _currentUserRole,
  onAcknowledgeAlert,
  onRecordMaintenance,
}) => {
  const [isMaintenanceModalOpen, setIsMaintenanceModalOpen] = useState(false);
  const [decision, setDecision] = useState<'followed_recommendation' | 'modified' | 'declined'>('followed_recommendation');
  const [decisionRationale, setDecisionRationale] = useState('');
  const [actionTaken, setActionTaken] = useState('');
  const [maintenanceOutcome, setMaintenanceOutcome] = useState<'resolved' | 'unresolved' | 'no_issue_found'>('resolved');
  const [notes, setNotes] = useState('');

  // Machine alerts and latest alert
  const machineAlerts = alerts.filter((a) => a.machineId === machine.id);
  const activeAlert = machineAlerts.find((a) => a.status === 'open' || a.status === 'acknowledged');
  const latestAlert = activeAlert || machineAlerts[0];

  // Submit maintenance record
  const handleSaveMaintenance = (e: React.FormEvent) => {
    e.preventDefault();
    if (!decisionRationale.trim() || !actionTaken.trim()) {
      return;
    }
    onRecordMaintenance({
      machineId: machine.id,
      machineCode: machine.machineCode,
      alertId: activeAlert?.id || latestAlert?.id,
      issue: (activeAlert || latestAlert) ? (activeAlert || latestAlert).message : 'Condition assessment inspection',
      recommendedAction: machine.recommendation.text,
      decision,
      decisionRationale: decisionRationale.trim(),
      actionTaken: actionTaken.trim(),
      performedBy: '',  // populated server-side from JWT subject
      status: maintenanceOutcome === 'unresolved' ? 'in_progress' : 'completed',
      outcome: maintenanceOutcome,
      notes: notes.trim(),
    });
    setDecisionRationale('');
    setActionTaken('');
    setNotes('');
    setIsMaintenanceModalOpen(false);
  };

  return (
    <div className="space-y-5 animate-in fade-in duration-100 select-none">
      {/* 1. Engineering Workstation Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3 bg-[#111621] border border-[#1e2636] rounded-md">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <button
              onClick={onBack}
              className="text-xs font-mono text-slate-400 hover:text-white flex items-center gap-1 cursor-pointer mr-2"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Fleet
            </button>
            <span className="text-slate-600">/</span>
            <span className="text-base font-bold font-mono text-white tracking-tight">
              {machine.machineCode}
            </span>
            <Badge value={machine.operationalStatus} size="xs" />
            <Badge value={machine.healthBand} size="xs" />
          </div>

          <div className="text-xs text-slate-400 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono">
            <span>Name: <strong className="text-slate-200 font-sans">{machine.name}</strong></span>
            <span>Location: <strong className="text-slate-200">{machine.location}</strong></span>
            <span>Cycle: <strong className="text-blue-400">{machine.currentCycle}</strong></span>
            <span>Install: <strong className="text-slate-300">{machine.installDate}</strong></span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsMaintenanceModalOpen(true)}
            icon={<Wrench className="w-3.5 h-3.5" />}
          >
            Record Maintenance Action
          </Button>
        </div>
      </div>

      {/* Reduced Reliability Warning Notice (PRD §FR-15) */}
      {machine.reliabilityStatus === 'reduced' && (
        <div className="p-3 rounded bg-amber-950/40 border border-amber-700/60 flex items-start gap-2.5 text-xs">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <div className="font-semibold text-white font-mono uppercase text-[11px]">
              Prediction Reliability Reduced
            </div>
            <p className="text-amber-200/90 leading-relaxed font-sans">
              Input data differs from the model's training reference statistics. Low probability does not guarantee safety.
            </p>
            {machine.reliabilityWarningReason && (
              <p className="text-[11px] font-mono text-amber-300">
                Diagnostic: {machine.reliabilityWarningReason}
              </p>
            )}
          </div>
        </div>
      )}

      {/* 2. Analytical Summary Grid (Health Indicator & Calibrated Probability) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Machine Health Indicator */}
        <HealthGauge
          score={machine.healthIndicator ?? 100}
          band={machine.healthBand}
          components={machine.healthComponents || { failureRiskPenalty: 0, anomalyPenalty: 0, trendPenalty: 0, otherPenalty: 0 }}
          currentCycle={machine.currentCycle ?? 1}
        />

        {/* Calibrated Failure Probability (Compact analytical presentation - Section 10) */}
        <div className="p-4 rounded-md bg-[#131923] border border-[#222b3b] flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-start justify-between text-xs font-mono">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                  Failure Probability (Calibrated)
                </div>
                <div className="flex items-baseline gap-2.5 mt-1">
                  <span className="text-3xl font-mono font-bold text-white tabular-nums">
                    {(machine.failureProbability * 100).toFixed(0)}%
                  </span>
                  <Badge value={machine.riskLevel} size="sm" />
                </div>
              </div>

              <div className="text-right text-[11px] text-slate-500 font-mono">
                <div>Horizon H</div>
                <div className="text-slate-300 font-semibold">{machine.predictionHorizon} cycles</div>
              </div>
            </div>

            {/* Subtle Probability Visualization */}
            <div className="mt-2.5 space-y-1">
              <div className="h-2 w-full bg-[#1b2332] rounded-xs overflow-hidden flex">
                <div
                  className={`h-full ${
                    machine.failureProbability >= 0.5 ? 'bg-rose-500' : 'bg-blue-500'
                  }`}
                  style={{ width: `${machine.failureProbability * 100}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-slate-500">
                <span>0% (Low)</span>
                <span>20% (Med)</span>
                <span>50% (High)</span>
                <span>80% (Crit)</span>
                <span>100%</span>
              </div>
            </div>

            <p className="text-xs text-slate-300 font-sans mt-2.5 leading-relaxed">
              Calibrated estimate of mechanical failure occurring within the next {machine.predictionHorizon} cycles based on active run-to-failure model.
            </p>
          </div>

          <div className="pt-2.5 border-t border-[#1d2634] grid grid-cols-3 gap-2 text-xs font-mono text-slate-400">
            <div>
              <div className="text-[10px] text-slate-500">Model Version</div>
              <div className="text-slate-200 font-semibold truncate">{machine.lineage?.failureModelVersion ?? '—'}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500">Anomaly Severity</div>
              <div className="text-amber-400 font-semibold">
                {machine.anomalySeverity != null ? `${(machine.anomalySeverity * 100).toFixed(0)}%` : '—'}
              </div>
            </div>
            <div>
              <div className="text-[10px] text-slate-500">Reliability</div>
              <Badge value={machine.reliabilityStatus} size="xs" />
            </div>
          </div>
        </div>
      </div>

      {/* 3. Centerpiece Telemetry Visualization (Section 8: Visual Centerpiece) */}
      <Card
        title="Time-Series Multivariate Telemetry"
        subtitle="Historical operating cycles &bull; Monitored physical channels &bull; Anomaly episode highlight"
      >
        <SensorLineChart data={sensorHistory} />
      </Card>

      {/* 4. AI Engineering Analysis & Feature Explainability */}
      <Card
        title="AI Engineering Analysis & Explainability (Tree SHAP)"
        subtitle="Attributed local feature contributions to the failure risk score with empirical cycle drift rates"
      >
        <FeatureImportanceChart explanation={machine.explanation} />
      </Card>

      {/* 5. Clearly Distinguished Human-in-the-Loop Workflow (Section 8 & 16) */}
      <div className="space-y-3">
        <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
          Human-in-the-Loop Maintenance Lifecycle (PRD §FR-14)
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Card 1: AI Recommendation (Distinct decision support style) */}
          <div className="p-4 rounded-md bg-[#0f1520] border-l-2 border-indigo-500 border-t border-r border-b border-[#1f2838] space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-indigo-400">
                1. AI Recommendation (Decision Support)
              </span>
              <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800 font-bold uppercase">
                Priority: {machine.recommendation.priority}
              </span>
            </div>

            <p className="text-xs font-semibold text-slate-100 font-sans leading-relaxed">
              "{machine.recommendation.text}"
            </p>

            <div className="text-[11px] text-slate-400 font-sans space-y-1">
              <div><strong>Rule ID:</strong> <code className="font-mono text-slate-300">{machine.recommendation.ruleId}</code></div>
              <div><strong>Rationale:</strong> {machine.recommendation.rationale}</div>
            </div>

            <div className="text-[10px] font-mono text-slate-500 border-t border-[#1a2333] pt-2">
              Note: AI-generated recommendation, not a confirmed diagnosis. Verification required.
            </div>

            {/* Alert Status Lifecycle: Open -> Acknowledged -> Resolved */}
            {latestAlert && latestAlert.status === 'open' && (
              <div data-testid="alert-status-open" className="pt-2 flex items-center justify-between border-t border-[#1a2333]">
                <span className="text-xs text-rose-400 font-mono flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" /> Open Alert Pending Action
                </span>
                <Button
                  data-testid="acknowledge-alert-btn"
                  variant="primary"
                  size="xs"
                  onClick={() => onAcknowledgeAlert(latestAlert.id)}
                  icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                >
                  Acknowledge Alert
                </Button>
              </div>
            )}
            {latestAlert && latestAlert.status === 'acknowledged' && (
              <div data-testid="alert-status-acknowledged" className="p-2 rounded bg-amber-950/30 border border-amber-800/40 text-xs font-mono text-amber-300 flex items-center justify-between">
                <span>Acknowledged by {latestAlert.acknowledgedBy}</span>
                <Button
                  data-testid="record-work-btn"
                  variant="secondary"
                  size="xs"
                  onClick={() => setIsMaintenanceModalOpen(true)}
                  icon={<Wrench className="w-3.5 h-3.5" />}
                >
                  Record Work
                </Button>
              </div>
            )}
            {latestAlert && latestAlert.status === 'resolved' && (
              <div data-testid="alert-status-resolved" className="p-2 rounded bg-emerald-950/30 border border-emerald-800/40 text-xs font-mono text-emerald-300 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Alert Resolved &amp; Verified
                </span>
                <span className="text-[10px] text-emerald-400">Maintenance Completed</span>
              </div>
            )}
          </div>

          {/* Card 2: Engineer Decision & Maintenance Action (Distinct human authority style) */}
          <div className="p-4 rounded-md bg-[#0f141d] border-l-2 border-emerald-500 border-t border-r border-b border-[#1f2838] space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                2. Engineer Decision & Maintenance Action
              </span>
              <span className="text-[10px] font-mono text-slate-500">
                {maintenanceRecords.length} Records Logged
              </span>
            </div>

            {maintenanceRecords.length === 0 ? (
              <p className="text-xs text-slate-500 font-mono py-6 text-center">
                No physical maintenance action logged for this unit yet.
              </p>
            ) : (
              <div className="space-y-2.5">
                {maintenanceRecords.slice(0, 2).map((rec) => (
                  <div
                    key={rec.id}
                    className="p-2.5 rounded bg-[#0b0e14] border border-[#1b2332] space-y-1.5 text-xs font-sans"
                  >
                    <div className="flex items-center justify-between font-mono text-[11px]">
                      <span className="font-semibold text-slate-200 capitalize">
                        {rec.decision.replace(/_/g, ' ')}
                      </span>
                      <Badge value={rec.outcome} size="xs" />
                    </div>
                    <p className="text-slate-300">{rec.actionTaken}</p>
                    {rec.decisionRationale && (
                      <p className="text-slate-400 text-[11px] font-mono">Rationale: {rec.decisionRationale}</p>
                    )}
                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pt-1 border-t border-[#17202e]">
                      <span>By: {rec.performedBy}</span>
                      <span>Status: <strong className="text-slate-300 uppercase">{rec.status}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 6. Machine Lineage Trace (Audit Metadata) */}
      <Card
        title="Prediction Lineage Trace"
        subtitle="End-to-end data, schema, model, and cycle provenance (PRD §FR-16)"
      >
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 text-xs font-mono">
          <div className="p-2 rounded bg-[#0d121a] border border-[#1b2332]">
            <div className="text-[10px] text-slate-500">Dataset</div>
            <div className="text-slate-200 font-semibold truncate">{machine.lineage.datasetName}</div>
          </div>
          <div className="p-2 rounded bg-[#0d121a] border border-[#1b2332]">
            <div className="text-[10px] text-slate-500">Schema Hash</div>
            <div className="text-slate-200 font-semibold truncate">{machine.lineage.schemaMappingHash}</div>
          </div>
          <div className="p-2 rounded bg-[#0d121a] border border-[#1b2332]">
            <div className="text-[10px] text-slate-500">Feature Config</div>
            <div className="text-slate-200 font-semibold truncate">{machine.lineage.featureConfigVersion}</div>
          </div>
          <div className="p-2 rounded bg-[#0d121a] border border-[#1b2332]">
            <div className="text-[10px] text-slate-500">Failure Model</div>
            <div className="text-blue-400 font-semibold truncate">{machine.lineage.failureModelVersion}</div>
          </div>
          <div className="p-2 rounded bg-[#0d121a] border border-[#1b2332]">
            <div className="text-[10px] text-slate-500">Anomaly Model</div>
            <div className="text-indigo-400 font-semibold truncate">{machine.lineage.anomalyModelVersion}</div>
          </div>
          <div className="p-2 rounded bg-[#0d121a] border border-[#1b2332]">
            <div className="text-[10px] text-slate-500">Predicted At</div>
            <div className="text-slate-300 font-semibold truncate">{machine.lineage.predictedAt}</div>
          </div>
        </div>
      </Card>

      {/* Record Maintenance Action Modal */}
      <Modal
        isOpen={isMaintenanceModalOpen}
        onClose={() => setIsMaintenanceModalOpen(false)}
        title="Record Engineer Intervention"
        description={`Audit record for ${machine.machineCode} (PRD §FR-14)`}
        maxWidth="md"
      >
        <form onSubmit={handleSaveMaintenance} className="space-y-4 text-xs">
          <Select
            label="Engineer Decision"
            value={decision}
            onChange={(e) => setDecision(e.target.value as any)}
            options={[
              { label: 'Followed AI Recommendation', value: 'followed_recommendation' },
              { label: 'Modified Action (Based on physical observation)', value: 'modified' },
              { label: 'Declined Action (False alarm / Not required)', value: 'declined' },
            ]}
          />

          <Input
            label="Decision Rationale"
            placeholder="Explain why this decision was reached..."
            value={decisionRationale}
            onChange={(e) => setDecisionRationale(e.target.value)}
            required
          />

          <Input
            label="Physical Action Taken"
            placeholder="Detailed description of inspection or repair..."
            value={actionTaken}
            onChange={(e) => setActionTaken(e.target.value)}
            required
          />

          <Select
            label="Maintenance Outcome"
            data-testid="outcome-select"
            id="outcome-select"
            value={maintenanceOutcome}
            onChange={(e) => setMaintenanceOutcome(e.target.value as any)}
            options={[
              { label: 'Resolved (Restores operational status to Active)', value: 'resolved' },
              { label: 'Unresolved / In Progress (Status remains Maintenance)', value: 'unresolved' },
              { label: 'No Issue Found (False alarm)', value: 'no_issue_found' },
            ]}
          />

          <Input
            label="Additional Notes"
            placeholder="Optional follow-up observations..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />

          <div className="p-2.5 rounded bg-[#0c1018] border border-[#1e2636] text-[11px] text-slate-400">
            Submitting will update the machine's operational status to <code className="text-blue-300">maintenance</code> while in progress, or restore to <code className="text-emerald-300">active</code> if resolved.
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="xs" type="button" onClick={() => setIsMaintenanceModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="xs" type="submit" data-testid="save-maintenance-btn">
              Save Record
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
