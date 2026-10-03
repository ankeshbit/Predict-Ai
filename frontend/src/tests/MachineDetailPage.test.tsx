import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { MachineDetailPage } from '../pages/MachineDetailPage';
import type { Machine, Alert } from '../types';

vi.mock('../components/charts/SensorLineChart', () => ({
  SensorLineChart: () => <div data-testid="mock-sensor-chart" />,
}));

vi.mock('../components/charts/FeatureImportanceChart', () => ({
  FeatureImportanceChart: () => <div data-testid="mock-feature-chart" />,
}));

vi.mock('../components/charts/HealthGauge', () => ({
  HealthGauge: () => <div data-testid="mock-health-gauge" />,
}));

const mockMachine: Machine = {
  id: 'mach-demo-48',
  machineCode: 'ENGINE-048',
  name: 'Demo Engine 48',
  machineType: 'Turbofan engine (simulated)',
  location: 'Test Cell 2',
  installDate: '2023-01-15',
  operationalStatus: 'active',
  healthIndicator: 28.5,
  healthBand: 'Critical',
  healthComponents: {
    failureRiskPenalty: 50,
    anomalyPenalty: 15,
    trendPenalty: 6.5,
    otherPenalty: 0,
  },
  failureProbability: 0.82,
  predictionHorizon: 30,
  riskLevel: 'Critical',
  currentCycle: 142,
  anomalySeverity: 0.65,
  anomalyScore: 0.65,
  anomalyStatus: 'anomaly',
  reliabilityStatus: 'ok',
  datasetBadge: 'Demo / Simulated Data',
  lastUpdated: '2026-10-03T10:00:00Z',
  explanation: {
    headline: 'High degradation risk driven by sensor_11 and sensor_9 drift.',
    topContributingFeatures: [],
    trendFacts: [],
    summaryText: 'Degradation exceeds operating threshold.',
  },
  recommendation: {
    ruleId: 'REC-001',
    text: 'Perform borescope inspection of HP turbine and compressor stages.',
    priority: 'urgent',
    rationale: 'Calibrated failure probability exceeds critical threshold.',
  },
  lineage: {
    machineCode: 'ENGINE-048',
    datasetName: 'NASA C-MAPSS FD001',
    datasetVersion: '1.0',
    schemaMappingHash: '46cfb71d9c664326',
    featureConfigVersion: '1.0.0',
    preprocessingVersion: '1.0.0',
    failureModelVersion: 'fd001_xgboost_v1.0.0',
    anomalyModelVersion: 'fd001_isolation_forest_v1.0.0',
    predictionHorizon: 30,
    predictionHorizonUnit: 'cycles',
    asOfCycle: 142,
    predictedAt: '2026-10-03T10:00:00Z',
    inputWindowLength: 30,
  },
};

const mockAlerts: Alert[] = [
  {
    id: 'alt-048',
    machineId: 'mach-demo-48',
    machineCode: 'ENGINE-048',
    severity: 'critical',
    status: 'open',
    message: 'High Failure Probability (82.0%) within 30 cycles',
    timestamp: '2026-10-03T10:00:00Z',
    ruleId: 'REC-001',
  },
];

describe('MachineDetailPage Maintenance Form Validation', () => {
  it('enforces required decision rationale and physical action taken fields before submission', () => {
    const onRecordMaintenance = vi.fn();
    const onAcknowledgeAlert = vi.fn();
    const onBack = vi.fn();

    render(
      <MachineDetailPage
        machine={mockMachine}
        alerts={mockAlerts}
        maintenanceRecords={[]}
        sensorHistory={[]}
        onBack={onBack}
        currentUserRole="engineer"
        onAcknowledgeAlert={onAcknowledgeAlert}
        onRecordMaintenance={onRecordMaintenance}
      />
    );

    // 1. Open the maintenance modal
    const openModalBtn = screen.getByRole('button', { name: /Record Maintenance Action/i });
    fireEvent.click(openModalBtn);

    // 2. Verify modal opened
    expect(screen.getByText(/Record Engineer Intervention/i)).toBeDefined();

    // 3. Find the inputs
    const rationaleInput = screen.getByLabelText(/Decision Rationale/i) as HTMLInputElement;
    const actionInput = screen.getByLabelText(/Physical Action Taken/i) as HTMLInputElement;

    // 4. Assert required attribute is present
    expect(rationaleInput.required).toBe(true);
    expect(actionInput.required).toBe(true);

    // 5. Assert fields start completely empty (no pre-filled boilerplate)
    expect(rationaleInput.value).toBe('');
    expect(actionInput.value).toBe('');

    // 6. Attempt submission with both fields empty
    const saveBtn = screen.getByTestId('save-maintenance-btn');
    fireEvent.click(saveBtn);

    // 7. Verify onRecordMaintenance was NOT called
    expect(onRecordMaintenance).not.toHaveBeenCalled();

    // 8. Attempt submission with only rationale filled
    fireEvent.change(rationaleInput, {
      target: { value: 'Confirmed sensor drift across 30 cycle window.' },
    });
    fireEvent.click(saveBtn);
    expect(onRecordMaintenance).not.toHaveBeenCalled();

    // 9. Fill physical action taken as well
    fireEvent.change(actionInput, {
      target: { value: 'Conducted borescope inspection and replaced damaged stator vanes.' },
    });

    // 10. Submit with both required fields filled
    fireEvent.click(saveBtn);

    // 11. Assert onRecordMaintenance was called with explicit engineer input
    expect(onRecordMaintenance).toHaveBeenCalledTimes(1);
    expect(onRecordMaintenance).toHaveBeenCalledWith(
      expect.objectContaining({
        decisionRationale: 'Confirmed sensor drift across 30 cycle window.',
        actionTaken: 'Conducted borescope inspection and replaced damaged stator vanes.',
        machineId: 'mach-demo-48',
        machineCode: 'ENGINE-048',
      })
    );
  });
});
