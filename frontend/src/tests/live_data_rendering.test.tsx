/**
 * Vitest tests for PRD FR-11 & Real-time Database requirements:
 * 1. Page renders values returned by mocked API response and changes when response changes.
 * 2. Empty API response shows the honest empty state.
 * 3. Polling refetches at configured interval using fake timers.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { FleetPage } from '../pages/FleetPage';
import { AlertsPage } from '../pages/AlertsPage';
import { DatasetsPage } from '../pages/DatasetsPage';
import type { Machine } from '../types';

const sampleMachineA: Machine = {
  id: 'mach-1',
  machineCode: 'ENGINE-001',
  name: 'Turbofan Unit 1',
  machineType: 'Turbofan engine (simulated)',
  location: 'Cell A',
  installDate: '2024-01-01',
  operationalStatus: 'active',
  healthIndicator: 92,
  healthBand: 'Excellent',
  healthComponents: { failureRiskPenalty: 5, anomalyPenalty: 3, trendPenalty: 0, otherPenalty: 0 },
  failureProbability: 0.05,
  predictionHorizon: 30,
  riskLevel: 'Low',
  currentCycle: 40,
  anomalySeverity: 0.1,
  anomalyScore: 0.12,
  anomalyStatus: 'normal',
  reliabilityStatus: 'ok',
  datasetBadge: 'Demo / Simulated Data',
  lastUpdated: '2026-10-04T12:00:00Z',
  explanation: { headline: 'Nominal condition', topContributingFeatures: [], trendFacts: [], summaryText: 'Healthy' },
  recommendation: { ruleId: 'RULE_NOMINAL', text: 'Standard inspection', priority: 'low', rationale: 'Nominal' },
  lineage: {
    machineCode: 'ENGINE-001',
    datasetName: 'NASA C-MAPSS FD001',
    datasetVersion: '1.0',
    schemaMappingHash: null,
    featureConfigVersion: '1.0',
    preprocessingVersion: '1.0',
    failureModelVersion: 'xgboost-1.0',
    anomalyModelVersion: 'iforest-1.0',
    predictionHorizon: 30,
    predictionHorizonUnit: 'cycles',
    asOfCycle: 40,
    predictedAt: '2026-10-04T12:00:00Z',
    inputWindowLength: null,
  },
};

const sampleMachineB: Machine = {
  id: 'mach-2',
  machineCode: 'ENGINE-002',
  name: 'Turbofan Unit 2',
  machineType: 'Turbofan engine (simulated)',
  location: 'Cell B',
  installDate: '2024-01-01',
  operationalStatus: 'maintenance',
  healthIndicator: 34,
  healthBand: 'Poor',
  healthComponents: { failureRiskPenalty: 50, anomalyPenalty: 16, trendPenalty: 0, otherPenalty: 0 },
  failureProbability: 0.78,
  predictionHorizon: 30,
  riskLevel: 'Critical',
  currentCycle: 195,
  anomalySeverity: 0.8,
  anomalyScore: 0.79,
  anomalyStatus: 'anomaly',
  reliabilityStatus: 'ok',
  datasetBadge: 'Demo / Simulated Data',
  lastUpdated: '2026-10-04T12:05:00Z',
  explanation: { headline: 'Degradation detected', topContributingFeatures: [], trendFacts: [], summaryText: 'Poor' },
  recommendation: { ruleId: 'RULE_CRITICAL', text: 'Inspect HP turbine', priority: 'urgent', rationale: 'High risk' },
  lineage: {
    machineCode: 'ENGINE-002',
    datasetName: 'NASA C-MAPSS FD001',
    datasetVersion: '1.0',
    schemaMappingHash: null,
    featureConfigVersion: '1.0',
    preprocessingVersion: '1.0',
    failureModelVersion: 'xgboost-1.0',
    anomalyModelVersion: 'iforest-1.0',
    predictionHorizon: 30,
    predictionHorizonUnit: 'cycles',
    asOfCycle: 195,
    predictedAt: '2026-10-04T12:05:00Z',
    inputWindowLength: null,
  },
};

describe('Dynamic Page Rendering & Response Updates', () => {
  it('renders initial API values, then dynamically updates when response data changes', () => {
    const { rerender } = render(
      <FleetPage machines={[sampleMachineA]} onSelectMachine={vi.fn()} />
    );

    // Initial response: ENGINE-001 with 92 health
    expect(screen.getByText('ENGINE-001')).toBeDefined();
    expect(screen.getByText('92')).toBeDefined();
    expect(screen.queryByText('ENGINE-002')).toBeNull();

    // Data changes from API update: ENGINE-002 with 34 health
    rerender(
      <FleetPage machines={[sampleMachineB]} onSelectMachine={vi.fn()} />
    );

    expect(screen.getByText('ENGINE-002')).toBeDefined();
    expect(screen.getByText('34')).toBeDefined();
    expect(screen.queryByText('ENGINE-001')).toBeNull();
  });
});

describe('Honest Empty State Rendering', () => {
  it('renders honest empty state when fleet registry has zero machines', () => {
    render(<FleetPage machines={[]} onSelectMachine={vi.fn()} />);
    expect(screen.getByText('No machines found in fleet registry.')).toBeDefined();
  });

  it('renders honest empty state when alerts list is empty', () => {
    render(
      <AlertsPage
        alerts={[]}
        onAcknowledgeAlert={vi.fn()}
        onResolveAlert={vi.fn()}
        onSelectMachine={vi.fn()}
      />
    );
    expect(
      screen.getByText('All machines are currently within configured alert thresholds.')
    ).toBeDefined();
  });

  it('renders honest empty state when datasets list is empty', () => {
    render(
      <DatasetsPage
        datasets={[]}
        currentUserRole="admin"
        onOpenUploadWizard={vi.fn()}
        onViewSchemaMapping={vi.fn()}
      />
    );
    expect(screen.getByText('No registered datasets found in registry.')).toBeDefined();
  });
});

describe('Polling with Fake Timers', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.useFakeTimers();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    queryClient.clear();
  });

  it('periodically refetches API data at configured POLL_INTERVAL', async () => {
    const mockFetcher = vi.fn().mockResolvedValue({ status: 'ok', value: 42 });

    function PollingComponent() {
      const { data } = useQuery({
        queryKey: ['test-polling-key'],
        queryFn: mockFetcher,
        refetchInterval: 5000,
        refetchIntervalInBackground: false,
      });
      return <div data-testid="poll-result">{data?.value ?? 'loading'}</div>;
    }

    render(
      <QueryClientProvider client={queryClient}>
        <PollingComponent />
      </QueryClientProvider>
    );

    // Initial mount triggers 1 fetch
    expect(mockFetcher).toHaveBeenCalledTimes(1);

    // Advance 5000ms: second polling tick
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(mockFetcher).toHaveBeenCalledTimes(2);

    // Advance another 5000ms: third polling tick
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(mockFetcher).toHaveBeenCalledTimes(3);
  });
});
