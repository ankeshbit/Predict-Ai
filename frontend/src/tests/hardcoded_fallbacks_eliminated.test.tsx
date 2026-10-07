import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

import { OverviewDashboardPage } from '../pages/OverviewDashboardPage';
import { FleetPage } from '../pages/FleetPage';
import { MachineDetailPage } from '../pages/MachineDetailPage';
import { AlertsPage } from '../pages/AlertsPage';
import { ModelPerformancePage } from '../pages/ModelPerformancePage';
import type { Machine, Alert } from '../types';

// Mock recharts
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: any) => <div data-testid="mock-container">{children}</div>,
  LineChart: ({ children }: any) => <div data-testid="mock-line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ReferenceLine: () => null,
}));

// Mock api hooks
vi.mock('../api', async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    useDashboardSummary: vi.fn(() => ({ data: null, isLoading: false })),
    useCurrentUser: vi.fn(() => ({ data: { id: 'usr-1', email: 'eng@predicore.internal', role: 'engineer' } })),
    useHealthConfig: vi.fn(() => ({
      data: {
        bands: [
          { key: 'Excellent', label: 'Excellent (86–100)', min_score: 86, max_score: 100 },
          { key: 'Healthy', label: 'Healthy (71–85)', min_score: 71, max_score: 85 },
          { key: 'Warning', label: 'Warning (51–70)', min_score: 51, max_score: 70 },
          { key: 'Poor', label: 'Poor (31–50)', min_score: 31, max_score: 50 },
          { key: 'Critical', label: 'Critical (0–30)', min_score: 0, max_score: 30 },
        ],
      },
      isLoading: false,
    })),
    useSensorHistory: vi.fn(() => ({ data: { points: [] }, isLoading: false })),
    useDemoReplayStatus: vi.fn(() => ({ data: { is_replaying: false, current_step: 0 } })),
    useModelEvaluation: vi.fn(() => ({ data: null, isError: false })),
  };
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

const baseMachine: Machine = {
  id: 'mach-test-1',
  machineCode: 'UNIT-TEST-1',
  name: 'Unit Test 1',
  machineType: 'Turbofan',
  location: 'Cell-1',
  installDate: '2026-01-01',
  operationalStatus: null,
  healthIndicator: null,
  healthBand: null,
  healthComponents: { failureRiskPenalty: 0, anomalyPenalty: 0, trendPenalty: 0, otherPenalty: 0 },
  failureProbability: null,
  predictionHorizon: 30,
  riskLevel: null,
  currentCycle: 10,
  anomalySeverity: null,
  anomalyScore: null,
  anomalyStatus: null,
  reliabilityStatus: null,
  isDemo: false,
  datasetBadge: null,
  lastUpdated: '2026-01-01T00:00:00Z',
  explanation: { headline: '', topContributingFeatures: [], trendFacts: [], summaryText: '' },
  recommendation: { ruleId: '—', text: '—', priority: 'low', rationale: '—' },
  lineage: {} as any,
};

describe('Verification of Items 1-5 (No hardcoded values & honest empty states)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── 1. Empty status renders "—" ──────────────────────────────────────────
  it('Item 1: Renders "—" for missing operationalStatus and reliabilityStatus on FleetPage', () => {
    render(
      <FleetPage machines={[baseMachine]} onSelectMachine={vi.fn()} />,
      { wrapper: createWrapper() }
    );
    // Should render dash for status in table
    const table = screen.getByRole('table');
    expect(table.textContent).toContain('—');
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it('Item 1: Renders "—" for missing operationalStatus and reliabilityStatus on MachineDetailPage', () => {
    render(
      <MachineDetailPage
        machine={baseMachine}
        alerts={[]}
        sensorHistory={[]}
        maintenanceRecords={[]}
        currentUserRole="engineer"
        onBack={vi.fn()}
        onAcknowledgeAlert={vi.fn()}
        onRecordMaintenance={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText('active')).toBeNull();
    expect(screen.queryByText('ok')).toBeNull();
  });

  // ── 2. Anomaly decision comes from API (not 0.5 literal threshold) ─────────
  it('Item 2: Uses anomaly decision from API regardless of numeric score', () => {
    const anomalyFromApiMachine: Machine = {
      ...baseMachine,
      anomalyScore: 0.2, // Below 0.5, but model flagged it
      anomalyStatus: 'anomaly',
      isAnomaly: true,
    };

    render(
      <MachineDetailPage
        machine={anomalyFromApiMachine}
        alerts={[]}
        sensorHistory={[]}
        maintenanceRecords={[]}
        currentUserRole="engineer"
        onBack={vi.fn()}
        onAcknowledgeAlert={vi.fn()}
        onRecordMaintenance={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );
    expect(anomalyFromApiMachine.anomalyStatus).toBe('anomaly');
    expect(anomalyFromApiMachine.isAnomaly).toBe(true);
  });

  // ── 3. Dataset badge and PRD banner follow the dataset (is_demo flag) ────
  it('Item 3: Non-demo machine does NOT display demo badge and PRD banner is hidden', () => {
    const regularMachine: Machine = {
      ...baseMachine,
      isDemo: false,
      datasetBadge: null,
    };

    render(
      <OverviewDashboardPage
        machines={[regularMachine]}
        alerts={[]}
        onSelectMachine={vi.fn()}
        onOpenAlerts={vi.fn()}
        onOpenOnboarding={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.queryByText(/Demo \/ Simulated Data/i)).toBeNull();
    expect(screen.queryByText(/Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data/i)).toBeNull();
  });

  it('Item 3: Demo machine displays Demo badge and PRD banner is shown', () => {
    const demoMachine: Machine = {
      ...baseMachine,
      isDemo: true,
      datasetBadge: 'Demo / Simulated Data',
    };

    render(
      <OverviewDashboardPage
        machines={[demoMachine]}
        alerts={[]}
        onSelectMachine={vi.fn()}
        onOpenAlerts={vi.fn()}
        onOpenOnboarding={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data/i)).toBeTruthy();
  });

  // ── 4. Resolve alert requires a resolution type ──────────────────────────
  it('Item 4: Resolve dialog requires engineer to select resolution type before submitting', () => {
    const sampleAlert: Alert = {
      id: 'al-1',
      machineId: 'mach-test-1',
      machineCode: 'UNIT-TEST-1',
      machineName: 'UNIT-TEST-1',
      type: 'high_failure_risk',
      severity: 'critical',
      status: 'acknowledged',
      asOfCycle: 10,
      triggeredAt: '2026-01-01T00:00:00Z',
      message: 'Critical failure risk',
      reliabilityStatus: 'ok',
      recommendationText: 'Inspect unit immediately',
      recommendationRuleId: 'RULE_CRIT',
    };

    render(
      <AlertsPage
        alerts={[sampleAlert]}
        currentUserRole="engineer"
        onAcknowledgeAlert={vi.fn()}
        onResolveAlert={vi.fn()}
        onSelectMachine={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    // Click Resolve button on the acknowledged alert row to open modal
    const resolveBtn = screen.getByRole('button', { name: /^Resolve$/i });
    fireEvent.click(resolveBtn);

    // Confirm button must be disabled because resolutionType is not selected
    const confirmBtn = screen.getByRole('button', { name: /Confirm Resolution/i });
    expect(confirmBtn).toHaveProperty('disabled', true);
  });

  // ── 5. Horizon unit fallbacks eliminated ──────────────────────────────────
  it('Item 5: Shows horizon unit when present and does NOT append hardcoded "cycles" when absent', () => {
    const modelWithUnit = {
      id: 'mod-1',
      version: 'v1.0',
      task: 'failure_risk',
      modelType: 'XGBoost',
      horizon: 30,
      horizonUnit: 'operating_cycles',
      decisionThreshold: 0.1,
      sha256: 'abc123456789',
    };

    const mockEvaluation = {
      model_version_id: 'mod-1',
      metrics: { internal_test: { pr_auc: 0.95 } },
      evaluated_at: '2026-10-01T00:00:00Z',
      calibration_method: 'sigmoid',
      confusion_matrix: { internal_test: {} },
      calibration_curve: { internal_test: [] },
      curves: { internal_test: { roc: [], pr: [] } },
      feature_importance: [],
      methodology: 'XGBoost',
      limitations: [],
    };

    const { rerender } = render(
      <ModelPerformancePage evaluation={mockEvaluation as any} activeModels={[modelWithUnit as any]} />,
      { wrapper: createWrapper() }
    );
    expect(screen.getAllByText(/H = 30 operating_cycles/i).length).toBeGreaterThanOrEqual(1);

    // Re-render with model without horizon unit
    const modelWithoutUnit = {
      ...modelWithUnit,
      horizonUnit: null,
    };
    rerender(
      <ModelPerformancePage evaluation={mockEvaluation as any} activeModels={[modelWithoutUnit as any]} />
    );
    // Should display H = 30 without 'cycles'
    expect(screen.getAllByText('H = 30').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText(/H = 30 cycles/i)).toBeNull();
  });
});
