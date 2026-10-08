import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

import { FleetPage } from '../pages/FleetPage';
import { MachineDetailPage } from '../pages/MachineDetailPage';
import { DatasetsPage } from '../pages/DatasetsPage';
import { ModelPerformancePage } from '../pages/ModelPerformancePage';
import { OnboardingModal } from '../pages/OnboardingModal';
import { HealthGauge } from '../components/charts/HealthGauge';
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
        confusion_matrix: {},
        calibration_curve: {},
        feature_importance: [],
        methodology: 'Held-out test split',
        limitations: [],
      },
      isLoading: false,
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
  healthComponents: { failureRiskPenalty: null, anomalyPenalty: null, trendPenalty: null, otherPenalty: null },
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

describe('Verification tests for Items 1, 2, 3, 5, and 6', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockModelCardReturn.mockReturnValue({ data: null, isLoading: false, isError: false });
    mockMachinesReturn.mockReturnValue({ data: null, isLoading: false });
  });

  // ── Item 1: Health penalties missing renders "—" and never 0, risk level derivation deleted ─
  it('Item 1: Renders "—" when penalties or risk_level are missing, never rendering 0 pts', () => {
    // HealthGauge with null penalties
    const { container, unmount } = render(
      <HealthGauge
        score={80}
        band="Healthy"
        components={{ failureRiskPenalty: null, anomalyPenalty: null, trendPenalty: null, otherPenalty: null }}
      />
    );
    expect(container.textContent).not.toContain('-0 pts');
    expect(container.textContent).toContain('—');
    unmount();

    // MachineDetailPage
    const { unmount: unmountDetail } = render(
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
    unmountDetail();

    // FleetPage
    render(
      <FleetPage machines={[baseMachine]} onSelectMachine={vi.fn()} />,
      { wrapper: createWrapper() }
    );
    expect(screen.queryByText('(Critical)')).toBeNull();
    expect(screen.getByText('(—)')).toBeDefined();
  });

  // ── Item 2: ruleId is from API or "—", never RULE_NOMINAL ─
  it('Item 2: Machine recommendation ruleId renders API value or "—", never hardcoded RULE_NOMINAL', () => {
    const machineWithNominal: Machine = {
      ...baseMachine,
      recommendation: {
        ruleId: '—',
        text: 'Telemetry evaluated.',
        priority: 'low',
        rationale: 'Evaluated against operational envelope.',
      },
    };

    const { container } = render(
      <MachineDetailPage
        machine={machineWithNominal}
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

    expect(container.textContent).not.toContain('RULE_NOMINAL');
    expect(container.textContent).toContain('Rule ID: —');
  });

  // ── Item 3: ModelPerformancePage renders gitCommit from metadata or "—", never hardcoded HEAD ─
  it('Item 3: ModelPerformancePage renders gitCommit from model metadata or "—", never hardcoded HEAD', () => {
    mockModelCardReturn.mockReturnValue({
      data: {
        intended_use: ['Operational support'],
        known_limitations: ['Simulated envelope'],
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
      gitCommit: '—',
      modelCard: {
        targetDefinition: '—',
        calibrationInfo: '—',
        featuresUsed: [],
        intendedUse: '',
        limitations: '',
      },
    };

    const { container } = render(
      <ModelPerformancePage activeModels={[activeModel]} />,
      { wrapper: createWrapper() }
    );

    expect(container.textContent).not.toContain('Commit: HEAD');
    expect(container.textContent).toContain('Commit: —');
  });

  // ── Item 5: OnboardingModal renders "—" when count is missing, zero hardcoded "Eight" or metric numbers ─
  it('Item 5: OnboardingModal renders "—" when demo count is missing and has zero hardcoded metric numbers', () => {
    mockMachinesReturn.mockReturnValue({ data: null, isLoading: true });

    const { container } = render(
      <OnboardingModal isOpen={true} onClose={vi.fn()} onStartDemoJourney={vi.fn()} />,
      { wrapper: createWrapper() }
    );

    const modalText = container.textContent || '';
    expect(modalText).not.toContain('Eight simulated');
    expect(modalText).toContain('— simulated turbofan engines');
    expect(modalText).not.toContain('94/100');
    expect(modalText).not.toContain('64/100');
    expect(modalText).not.toContain('Unit #3');
  });

  // ── Item 6: Dataset isDemo derives from API field is_demo, not from name containing demo ─
  it('Item 6: DatasetsPage distinguishes demo status via isDemo boolean from API, not name matching', () => {
    const demoDatasetWithoutDemoName: Dataset = {
      id: 'ds-demo-1',
      name: 'Fleet Run Alpha',
      version: 'v1.0',
      adapterKey: 'cmapss_fd001',
      adapterVersion: '1.0',
      dataOrigin: 'simulated' as any,
      isDemo: true, // API is_demo is true even without 'demo' in name
      status: 'validated',
      checksumSha256: 'sha256-hash',
      rowCount: 1000,
      unitCount: 10,
      uploadedBy: 'admin@predicore.io',
      uploadedAt: '2026-01-01T00:00:00Z',
    };

    const nonDemoDatasetWithDemoName: Dataset = {
      id: 'ds-nondemo-1',
      name: 'demo_simulation_raw',
      version: 'v1.0',
      adapterKey: 'cmapss_fd001',
      adapterVersion: '1.0',
      dataOrigin: 'simulated' as any,
      isDemo: false, // API is_demo is false even though name contains 'demo'
      status: 'validated',
      checksumSha256: 'sha256-hash-2',
      rowCount: 500,
      unitCount: 5,
      uploadedBy: 'eng@predicore.io',
      uploadedAt: '2026-01-02T00:00:00Z',
    };

    render(
      <DatasetsPage
        datasets={[demoDatasetWithoutDemoName, nonDemoDatasetWithDemoName]}
        currentUserRole="engineer"
        onOpenUploadWizard={vi.fn()}
        onViewSchemaMapping={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    // demoDatasetWithoutDemoName should render Demo badge
    expect(screen.getAllByText('Demo').length).toBe(1);
  });
});
