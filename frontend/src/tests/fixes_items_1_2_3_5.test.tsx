import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

import { FleetPage } from '../pages/FleetPage';
import { MachineDetailPage } from '../pages/MachineDetailPage';
import { DatasetsPage } from '../pages/DatasetsPage';
import { ModelPerformancePage } from '../pages/ModelPerformancePage';
import { OnboardingModal } from '../pages/OnboardingModal';
import type { Machine, Dataset, ModelVersion } from '../types';

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
const mockModelCardReturn = vi.fn();
const mockMachinesReturn = vi.fn();

vi.mock('../api', async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    useActiveModels: vi.fn(() => ({ data: [], isLoading: false })),
    useModelEvaluation: vi.fn(() => ({
      data: {
        id: 'eval-1',
        metrics: {
          internal_test: { pr_auc: 0.85, precision: 0.8, recall: 0.8, f1: 0.8, roc_auc: 0.9, brier_score: 0.05, accuracy: 0.85 },
        },
        curves: {},
        feature_importance: [],
        methodology: 'GroupKFold',
        limitations: [],
        evaluated_at: '2026-10-01T00:00:00Z',
      },
      isError: false,
    })),
    useModelCard: (...args: any[]) => mockModelCardReturn(...args),
    useMachines: (...args: any[]) => mockMachinesReturn(...args),
    useSensorHistory: vi.fn(() => ({ data: { points: [] }, isLoading: false })),
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
  id: 'mach-fix-1',
  machineCode: 'UNIT-FIX-1',
  name: 'Unit Fix 1',
  machineType: 'Turbofan',
  location: 'Cell-1',
  installDate: '2026-01-01',
  operationalStatus: 'active',
  healthIndicator: 80,
  healthBand: 'Healthy',
  healthComponents: { failureRiskPenalty: 0, anomalyPenalty: 0, trendPenalty: 0, otherPenalty: 0 },
  failureProbability: 0.85, // High failure probability (>= 0.7)
  predictionHorizon: 30,
  riskLevel: null, // Missing risk_level from API
  currentCycle: 10,
  anomalySeverity: null,
  anomalyScore: 0.25,
  anomalyStatus: null, // Missing is_anomaly from API
  isAnomaly: null,
  reliabilityStatus: 'ok',
  isDemo: false,
  datasetBadge: null,
  lastUpdated: '2026-01-01T00:00:00Z',
  explanation: { headline: '', topContributingFeatures: [], trendFacts: [], summaryText: '' },
  recommendation: { ruleId: '—', text: '—', priority: 'low', rationale: '—' },
  lineage: {} as any,
};

describe('Verification tests for Items 1, 2, 3, and 5', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockModelCardReturn.mockReturnValue({ data: null, isLoading: false, isError: false });
    mockMachinesReturn.mockReturnValue({ data: null, isLoading: false });
  });

  // ── Item 1: Risk Level derivation deleted, missing risk_level renders "—" ─
  it('Item 1: Renders "—" when risk_level is missing, without deriving Critical from failureProbability 0.85', () => {
    // MachineDetailPage
    const { unmount } = render(
      <MachineDetailPage
        machine={baseMachine}
        alerts={[]}
        maintenanceRecords={[]}
        sensorHistory={[]}
        onBack={vi.fn()}
        currentUserRole="engineer"
        onAcknowledgeAlert={vi.fn()}
        onRecordMaintenance={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );
    // Should NOT derive "Critical" on the frontend
    expect(screen.queryByText('Critical')).toBeNull();
    // Should render dash "—" in Badge for riskLevel
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1);
    unmount();

    // FleetPage
    render(
      <FleetPage machines={[baseMachine]} onSelectMachine={vi.fn()} />,
      { wrapper: createWrapper() }
    );
    expect(screen.queryByText('(Critical)')).toBeNull();
    expect(screen.getByText('(—)')).toBeDefined();
  });

  // ── Item 2: data_origin missing renders "—", anomalyStatus missing renders "—" ─
  it('Item 2: Renders "—" for missing dataOrigin on DatasetsPage and missing anomalyStatus on FleetPage', () => {
    const datasetWithMissingOrigin: Dataset = {
      id: 'ds-missing-origin',
      name: 'Test Dataset Missing Origin',
      version: 'v1.0',
      adapterKey: 'cmapss_fd001',
      adapterVersion: '1.0',
      dataOrigin: '—' as any, // missing from API
      isDemo: false,
      status: 'validated',
      checksumSha256: 'sha256-hash',
      rowCount: 1000,
      unitCount: 10,
      uploadedBy: 'eng@predicore.io',
      uploadedAt: '2026-01-01T00:00:00Z',
    };

    const { unmount } = render(
      <DatasetsPage datasets={[datasetWithMissingOrigin]} onUploadSuccess={vi.fn()} onOpenMapping={vi.fn()} />,
      { wrapper: createWrapper() }
    );
    // Should NOT render 'simulated' as fallback
    expect(screen.queryByText('simulated')).toBeNull();
    expect(screen.getByText('—')).toBeDefined();
    unmount();

    // FleetPage with missing is_anomaly
    render(
      <FleetPage machines={[baseMachine]} onSelectMachine={vi.fn()} />,
      { wrapper: createWrapper() }
    );
    // Should NOT render 'normal' fallback for anomaly status
    expect(screen.queryByText('• normal')).toBeNull();
    expect(screen.getByText('• —')).toBeDefined();
  });

  // ── Item 3: ModelPerformancePage reads from stored model card, shows "Model card not available." when absent ─
  it('Item 3: ModelPerformancePage shows "Model card not available." when absent from API', () => {
    mockModelCardReturn.mockReturnValue({ data: null, isLoading: false, isError: false });

    const activeModel: ModelVersion = {
      id: 'mod-1',
      name: 'Active Model',
      task: 'failure_risk',
      modelType: 'LightGBM Classifier',
      version: 'cmapss-fd001-v1',
      adapterKey: 'cmapss_fd001',
      status: 'active',
      horizon: 30,
      horizonUnit: 'cycles',
      decisionThreshold: 0.10,
      trainingDataset: 'NASA C-MAPSS FD001',
      trainingDate: '2026-10-01',
      gitCommit: 'HEAD',
      modelCard: {
        targetDefinition: '—',
        calibrationInfo: '—',
        featuresUsed: [],
        intendedUse: '',
        limitations: '',
      },
    };

    render(
      <ModelPerformancePage activeModels={[activeModel]} />,
      { wrapper: createWrapper() }
    );

    // Stated empty text per requirement: "Model card not available."
    expect(screen.getByText('Model card not available.')).toBeDefined();
    // Zero hardcoded strings
    expect(screen.queryByText('Simulated fleet risk screening')).toBeNull();
    expect(screen.queryByText('Trained exclusively on C-MAPSS FD001 simulation run-to-failure.')).toBeNull();
  });

  it('Item 3: ModelPerformancePage renders intendedUse and limitations from stored model card via API', () => {
    mockModelCardReturn.mockReturnValue({
      data: {
        intended_use: ['Decision support on C-MAPSS-style multivariate run-to-failure data'],
        known_limitations: ['Trained exclusively on SIMULATED single-operating-condition dataset'],
      },
      isLoading: false,
      isError: false,
    });

    const activeModel: ModelVersion = {
      id: 'mod-1',
      name: 'Active Model',
      task: 'failure_risk',
      modelType: 'LightGBM Classifier',
      version: 'cmapss-fd001-v1',
      adapterKey: 'cmapss_fd001',
      status: 'active',
      horizon: 30,
      horizonUnit: 'cycles',
      decisionThreshold: 0.10,
      trainingDataset: 'NASA C-MAPSS FD001',
      trainingDate: '2026-10-01',
      gitCommit: 'HEAD',
      modelCard: {
        targetDefinition: '—',
        calibrationInfo: '—',
        featuresUsed: [],
        intendedUse: '',
        limitations: '',
      },
    };

    render(
      <ModelPerformancePage activeModels={[activeModel]} />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/Decision support on C-MAPSS-style multivariate run-to-failure data/)).toBeDefined();
    expect(screen.getByText(/Trained exclusively on SIMULATED single-operating-condition dataset/)).toBeDefined();
  });

  // ── Item 5: OnboardingModal renders "—" when count is missing, zero hardcoded "Eight" or metric numbers ─
  it('Item 5: OnboardingModal renders "—" when demo count is missing and has zero hardcoded metric numbers', () => {
    mockMachinesReturn.mockReturnValue({ data: null, isLoading: true });

    const { container } = render(
      <OnboardingModal isOpen={true} onClose={vi.fn()} onStartDemoJourney={vi.fn()} />,
      { wrapper: createWrapper() }
    );

    // Must NOT contain hardcoded "Eight" engines
    const modalText = container.textContent || '';
    expect(modalText).not.toContain('Eight simulated');
    expect(modalText).toContain('— simulated turbofan engines');

    // Must NOT contain fabricated metric literals (94/100, 6%, 64/100, 42%, 34/100, 82%)
    expect(modalText).not.toContain('94/100');
    expect(modalText).not.toContain('(6%)');
    expect(modalText).not.toContain('64/100');
    expect(modalText).not.toContain('42%');
    expect(modalText).not.toContain('34/100');
    expect(modalText).not.toContain('82%');
    expect(modalText).not.toContain('Unit #3');
  });
});
