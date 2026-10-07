import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

import { OverviewDashboardPage } from '../pages/OverviewDashboardPage';
import { FleetPage } from '../pages/FleetPage';
import { MachineDetailPage } from '../pages/MachineDetailPage';
import { AlertsPage } from '../pages/AlertsPage';
import { MaintenancePage } from '../pages/MaintenancePage';
import { DatasetsPage } from '../pages/DatasetsPage';
import { DatasetSchemaMappingPage } from '../pages/DatasetSchemaMappingPage';
import { ModelPerformancePage } from '../pages/ModelPerformancePage';
import { SettingsPage } from '../pages/SettingsPage';
import { LoginPage } from '../pages/LoginPage';
import type { Machine } from '../types';

// Mock recharts to avoid jsdom canvas issues
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

// Mock api hooks that fire inside components
vi.mock('../api', async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    useDashboardSummary: vi.fn(() => ({ data: null, isLoading: false })),
    useCurrentUser: vi.fn(() => ({ data: { id: 'usr-1', email: 'eng@predicore.internal', role: 'engineer' } })),
    useHealthConfig: vi.fn(() => ({ data: null, isLoading: false })),
    useUpdateHealthConfig: vi.fn(() => ({ mutate: vi.fn() })),
    useAlertRules: vi.fn(() => ({ data: [], isLoading: false })),
    useAuditLogs: vi.fn(() => ({ data: { items: [], total: 0 }, isLoading: false })),
    useSensorHistory: vi.fn(() => ({ data: { points: [] }, isLoading: false })),
    useCompatibilityReport: vi.fn(() => ({ data: null, isLoading: false })),
    useActiveModels: vi.fn(() => ({ data: [], isLoading: false })),
    useModelEvaluation: vi.fn(() => ({ data: null, isError: true })),
    useDemoReplayStatus: vi.fn(() => ({ data: { is_replaying: false, current_step: 0 } })),
    useStartReplay: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
    useStopReplay: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  };
});

const REMOVED_INVENTED_FALLBACKS = [
  'Test Cell',
  'RULE_DEFAULT',
  'Turbofan engine (simulated)',
  'Platt Sigmoid Calibrated',
  'Platt Scaling (Sigmoid)',
  'Platt Sigmoid',
  'Offline Evaluation',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  '13,096 cycles',
  '100 engines',
  'cmapss-fd001',
  'Perform standard engine inspection.',
  'Inspect engine sensors',
  'followed_recommendation',
  'Verified and resolved by engineering review.',
];

function assertNoRemovedValues(container: HTMLElement) {
  const text = container.textContent || '';
  for (const forbidden of REMOVED_INVENTED_FALLBACKS) {
    expect(text).not.toContain(forbidden);
  }
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('Empty and Partial API responses rendering tests (Requirement F)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders OverviewDashboardPage with empty API response without fallbacks', () => {
    const { container } = render(
      <OverviewDashboardPage
        machines={[]}
        alerts={[]}
        onSelectMachine={vi.fn()}
        onOpenAlerts={vi.fn()}
        onOpenOnboarding={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );
    assertNoRemovedValues(container);
    expect(screen.getByText(/No machines in registry/i)).toBeTruthy();
  });

  it('renders OverviewDashboardPage with unscored machine showing "No score yet"', () => {
    const partialMachine: Machine = {
      id: 'mach-unscored',
      machineCode: 'UNIT-UNSCORED',
      name: 'UNIT-UNSCORED',
      machineType: '—',
      location: '—',
      installDate: '2026-01-01',
      operationalStatus: 'active',
      healthIndicator: null,
      healthBand: null,
      healthComponents: { failureRiskPenalty: 0, anomalyPenalty: 0, trendPenalty: 0, otherPenalty: 0 },
      failureProbability: null,
      predictionHorizon: null,
      riskLevel: null,
      currentCycle: null,
      anomalySeverity: null,
      anomalyScore: null,
      anomalyStatus: 'normal',
      reliabilityStatus: 'ok',
      datasetBadge: 'Demo',
      lastUpdated: '2026-01-01T00:00:00Z',
      explanation: { headline: '', topContributingFeatures: [], trendFacts: [], summaryText: '' },
      recommendation: { ruleId: '—', text: '—', priority: 'low', rationale: '—' },
      lineage: {} as any,
    };

    const { container } = render(
      <OverviewDashboardPage
        machines={[partialMachine]}
        alerts={[]}
        onSelectMachine={vi.fn()}
        onOpenAlerts={vi.fn()}
        onOpenOnboarding={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );
    assertNoRemovedValues(container);
    const noScores = screen.getAllByText(/No score yet/i);
    expect(noScores.length).toBeGreaterThanOrEqual(1);
  });

  it('renders FleetPage with empty response and unscored machine showing "No score yet"', () => {
    const unscoredMachine: Machine = {
      id: 'm-empty',
      machineCode: 'UNIT-EMPTY',
      name: 'UNIT-EMPTY',
      machineType: '—',
      location: '—',
      installDate: '2026-01-01',
      operationalStatus: 'active',
      healthIndicator: null,
      healthBand: null,
      healthComponents: { failureRiskPenalty: 0, anomalyPenalty: 0, trendPenalty: 0, otherPenalty: 0 },
      failureProbability: null,
      predictionHorizon: null,
      riskLevel: null,
      currentCycle: null,
      anomalySeverity: null,
      anomalyScore: null,
      anomalyStatus: 'normal',
      reliabilityStatus: 'ok',
      datasetBadge: 'Demo',
      lastUpdated: '2026-01-01T00:00:00Z',
      explanation: { headline: '', topContributingFeatures: [], trendFacts: [], summaryText: '' },
      recommendation: { ruleId: '—', text: '—', priority: 'low', rationale: '—' },
      lineage: {} as any,
    };

    const { container } = render(
      <FleetPage machines={[unscoredMachine]} onSelectMachine={vi.fn()} />,
      { wrapper: createWrapper() }
    );
    assertNoRemovedValues(container);
    const noScores = screen.getAllByText(/No score yet/i);
    expect(noScores.length).toBeGreaterThanOrEqual(2);
  });

  it('renders MachineDetailPage with null health and failure probability as "No score yet"', () => {
    const unscoredMachine: Machine = {
      id: 'm-unscored-detail',
      machineCode: 'UNIT-DETAIL',
      name: 'UNIT-DETAIL',
      machineType: '—',
      location: '—',
      installDate: '2026-01-01',
      operationalStatus: 'active',
      healthIndicator: null,
      healthBand: null,
      healthComponents: { failureRiskPenalty: 0, anomalyPenalty: 0, trendPenalty: 0, otherPenalty: 0 },
      failureProbability: null,
      predictionHorizon: null,
      riskLevel: null,
      currentCycle: null,
      anomalySeverity: null,
      anomalyScore: null,
      anomalyStatus: 'normal',
      reliabilityStatus: 'ok',
      datasetBadge: 'Demo',
      lastUpdated: '2026-01-01T00:00:00Z',
      explanation: { headline: '', topContributingFeatures: [], trendFacts: [], summaryText: '' },
      recommendation: { ruleId: '—', text: '—', priority: 'low', rationale: '—' },
      lineage: {} as any,
    };

    const { container } = render(
      <MachineDetailPage
        machine={unscoredMachine}
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
    assertNoRemovedValues(container);
    const noScores = screen.getAllByText(/No score yet/i);
    expect(noScores.length).toBeGreaterThanOrEqual(2);
  });

  it('renders AlertsPage with empty list honestly', () => {
    const { container } = render(
      <AlertsPage
        alerts={[]}
        currentUserRole="engineer"
        onAcknowledgeAlert={vi.fn()}
        onResolveAlert={vi.fn()}
        onSelectMachine={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );
    assertNoRemovedValues(container);
    expect(screen.getByText(/No alert records match the active status\/severity filter/i)).toBeTruthy();
  });

  it('renders MaintenancePage with empty list honestly', () => {
    const { container } = render(
      <MaintenancePage
        records={[]}
        onSelectMachine={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );
    assertNoRemovedValues(container);
    expect(screen.getByText(/No maintenance records match/i)).toBeTruthy();
  });

  it('renders DatasetsPage with empty list honestly', () => {
    const { container } = render(
      <DatasetsPage
        datasets={[]}
        currentUserRole="engineer"
        onOpenUploadWizard={vi.fn()}
        onViewSchemaMapping={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );
    assertNoRemovedValues(container);
    expect(screen.getByText(/No registered datasets found in registry/i)).toBeTruthy();
  });

  it('renders DatasetSchemaMappingPage with partial response without fallbacks', () => {
    const { container } = render(
      <DatasetSchemaMappingPage
        initialDatasetId="ds-test"
        onBack={vi.fn()}
        onIngestSuccess={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );
    assertNoRemovedValues(container);
  });

  it('renders ModelPerformancePage with missing evaluation showing "Model evaluation not available."', () => {
    const { container } = render(
      <ModelPerformancePage evaluation={null as any} activeModels={[]} />,
      { wrapper: createWrapper() }
    );
    assertNoRemovedValues(container);
    expect(screen.getByText(/Model evaluation not available\./i)).toBeTruthy();
  });

  it('renders SettingsPage with empty healthConfig showing honest empty state', () => {
    const { container } = render(
      <SettingsPage currentUserRole="engineer" />,
      { wrapper: createWrapper() }
    );
    assertNoRemovedValues(container);
    expect(screen.getByText(/Health configuration not available\./i)).toBeTruthy();
  });

  it('renders LoginPage without fallbacks', () => {
    const { container } = render(
      <LoginPage onLogin={vi.fn()} />,
      { wrapper: createWrapper() }
    );
    assertNoRemovedValues(container);
  });
});
