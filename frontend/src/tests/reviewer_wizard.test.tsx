import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { DatasetSchemaMappingPage } from '../pages/DatasetSchemaMappingPage';
import * as api from '../api';

vi.mock('../api', async (importOriginal) => {
  const actual: any = await importOriginal();
  return {
    ...actual,
    useDatasets: vi.fn(),
    useDatasetProfile: vi.fn(),
    useUploadDataset: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
    useUpdateMapping: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
    useValidateCompatibility: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
    useIngestDataset: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
    useTriggerScoring: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
    useDatasetSummary: vi.fn(() => ({ data: null, refetch: vi.fn() })),
    useJobStatus: vi.fn(() => ({ data: null })),
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

describe('DatasetSchemaMappingPage Reviewer Wizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.useDatasets as any).mockReturnValue({
      data: {
        items: [
          {
            id: 'ds-100',
            name: 'telemetry_sample.csv',
            status: 'valid',
            schema_mapping: { unit_id: 'unit_id', cycle: 'cycle' },
          },
        ],
        total: 1,
      },
      isLoading: false,
      refetch: vi.fn(),
    });
  });

  it('renders all 6 steps in the reviewer stepper', () => {
    (api.useDatasetProfile as any).mockReturnValue({
      data: null,
      isLoading: false,
    });

    render(
      <DatasetSchemaMappingPage
        onBack={vi.fn()}
        onIngestSuccess={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('1. Upload')).toBeTruthy();
    expect(screen.getByText('2. Profile')).toBeTruthy();
    expect(screen.getByText('3. Mapping')).toBeTruthy();
    expect(screen.getByText('4. Compatibility')).toBeTruthy();
    expect(screen.getByText('5. Ingest')).toBeTruthy();
    expect(screen.getByText('6. Scoring')).toBeTruthy();
  });

  it('displays computed dataset profile statistics without hardcoded values', () => {
    (api.useDatasetProfile as any).mockReturnValue({
      data: {
        filename: 'custom_telemetry.csv',
        total_rows: 15420,
        total_columns: 26,
        detected_delimiter: 'comma',
        has_header: true,
        header_names: ['unit_id', 'cycle', 'sensor_2'],
        unit_count: 50,
        cycles_per_unit: { min: 45, max: 210, mean: 125.4 },
        duplicate_rows: 0,
        missing_counts: { sensor_2: 0 },
        numeric_stats: {
          sensor_2: { min: 641.5, max: 644.2, mean: 642.8 },
        },
      },
      isLoading: false,
    });

    render(
      <DatasetSchemaMappingPage
        initialDatasetId="ds-100"
        onBack={vi.fn()}
        onIngestSuccess={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('custom_telemetry.csv')).toBeTruthy();
    expect(screen.getByText('15,420')).toBeTruthy();
    expect(screen.getByText('26')).toBeTruthy();
    expect(screen.getByText('50 distinct machines')).toBeTruthy();
  });

  it('strictly blocks incompatible dataset with PRD message and displays plain language diagnosis', () => {
    const mockValidate = vi.fn((_id, options) => {
      options?.onSuccess?.({
        dataset_id: 'ds-incompatible',
        passed: false,
        total_checks: 11,
        passed_checks: 1,
        failed_checks: 10,
        summary_sentence: 'This dataset is not compatible with the selected model. Failed 10 of 11 compatibility checks.',
        plain_language_explanation: 'The active model bundle was trained exclusively on NASA C-MAPSS FD001 data.',
        checks: [
          {
            check_number: 1,
            check_name: 'Column Completeness',
            status: 'failed',
            expected_value: 'All 26 channels',
            found_value: '0 mapped',
            how_to_fix: 'Upload a compatible C-MAPSS FD001 dataset.',
          },
        ],
      });
    });

    (api.useValidateCompatibility as any).mockReturnValue({
      mutate: mockValidate,
      isPending: false,
    });

    (api.useDatasetProfile as any).mockReturnValue({
      data: {
        filename: 'incompatible.csv',
        total_rows: 100,
        total_columns: 5,
        detected_delimiter: 'comma',
        has_header: true,
        duplicate_rows: 0,
        missing_counts: {},
        numeric_stats: {},
      },
      isLoading: false,
    });

    render(
      <DatasetSchemaMappingPage
        initialDatasetId="ds-100"
        onBack={vi.fn()}
        onIngestSuccess={vi.fn()}
      />,
      { wrapper: createWrapper() }
    );

    // Click step 4 (Compatibility)
    fireEvent.click(screen.getByText('4. Compatibility'));

    // Assert exact PRD message
    expect(screen.getByText('This dataset is not compatible with the selected model.')).toBeTruthy();
    expect(screen.getByText(/Inference Blocked/i)).toBeTruthy();
    expect(screen.getByText(/Plain-Language Diagnosis/i)).toBeTruthy();
  });
});
