import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, getAuthToken } from './client';

export interface BackendDataset {
  id: string;
  name: string;
  slug: string;
  filename: string;
  file_size_bytes: number;
  row_count?: number | null;
  unit_count?: number | null;
  schema_mapping?: Record<string, string> | null;
  schema_mapping_hash?: string | null;
  version?: string | null;
  adapter_key?: string | null;
  adapter_version?: string | null;
  data_origin?: string | null;
  is_demo?: boolean;
  uploaded_by?: string | null;
  status: string;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DatasetProfile {
  filename: string;
  total_rows: number;
  total_columns: number;
  detected_delimiter: string;
  has_header: boolean;
  header_names?: string[];
  unit_count?: number | null;
  cycles_per_unit?: { min: number; max: number; mean: number } | null;
  duplicate_rows: number;
  missing_counts: Record<string, number>;
  numeric_stats: Record<string, { min: number; max: number; mean: number }>;
}

export interface UpdateMappingResponse {
  dataset_id: string;
  schema_mapping: Record<string, string>;
  schema_mapping_hash: string;
  unmapped_columns: string[];
  is_valid: boolean;
  message: string;
}

export interface CompatibilityCheckItem {
  check_number: number;
  check_name: string;
  status: 'passed' | 'failed' | 'warning';
  expected_value: string;
  found_value: string;
  how_to_fix: string;
  details?: Record<string, any> | null;
}

export interface CompatibilityReport {
  dataset_id: string;
  passed: boolean;
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  warning_checks?: number;
  has_warnings?: boolean;
  summary_sentence?: string;
  plain_language_explanation?: string;
  ood_sensors?: string[];
  range_comparisons?: Record<
    string,
    {
      train_min: number;
      train_max: number;
      uploaded_min: number;
      uploaded_max: number;
      is_ood: boolean;
    }
  >;
  checks: CompatibilityCheckItem[];
}

export interface DatasetSummary {
  dataset_id: string;
  name: string;
  status: string;
  units_created: number;
  readings_ingested: number;
  units_scored: number;
  alerts_opened: number;
  has_warnings: boolean;
}

export function useDatasets(params?: { status?: string; limit?: number; offset?: number }) {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.set('status', params.status);
  if (params?.limit) queryParams.set('limit', String(params.limit));
  if (params?.offset) queryParams.set('offset', String(params.offset));

  const queryStr = queryParams.toString() ? `?${queryParams.toString()}` : '';

  return useQuery({
    queryKey: ['datasets', params],
    queryFn: () => apiFetch<{ items: BackendDataset[]; total: number }>(`/datasets${queryStr}`),
  });
}

export function useDatasetProfile(datasetId: string | null) {
  return useQuery({
    queryKey: ['datasets', datasetId, 'profile'],
    queryFn: () => apiFetch<DatasetProfile>(`/datasets/${datasetId}/profile`),
    enabled: Boolean(datasetId),
  });
}

export function useUploadDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) =>
      apiFetch<BackendDataset>('/datasets/upload', {
        method: 'POST',
        body: formData,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useUpdateMapping() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ datasetId, mapping }: { datasetId: string; mapping: Record<string, string> }) =>
      apiFetch<UpdateMappingResponse>(`/datasets/${datasetId}/mapping`, {
        method: 'PUT',
        body: JSON.stringify({ mapping }),
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      queryClient.invalidateQueries({ queryKey: ['datasets', variables.datasetId, 'profile'] });
    },
  });
}

export function useValidateCompatibility() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datasetId: string) =>
      apiFetch<CompatibilityReport>(`/datasets/${datasetId}/compatibility`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useIngestDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      datasetId,
      acknowledgedWarnings = false,
    }: {
      datasetId: string;
      acknowledgedWarnings?: boolean;
    }) =>
      apiFetch<{ job_id: string; dataset_id: string; status: string; message: string }>(
        `/datasets/${datasetId}/ingest`,
        {
          method: 'POST',
          body: JSON.stringify({ acknowledged_warnings: acknowledgedWarnings }),
        }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
}

export function useTriggerScoring() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      datasetId,
      acknowledgedWarnings = false,
    }: {
      datasetId: string;
      acknowledgedWarnings?: boolean;
    }) =>
      apiFetch<{ job_id: string; status: string; message: string }>('/scoring/run', {
        method: 'POST',
        body: JSON.stringify({
          dataset_id: datasetId,
          acknowledged_warnings: acknowledgedWarnings,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}

export function useDatasetSummary(datasetId: string | null) {
  return useQuery({
    queryKey: ['datasets', datasetId, 'summary'],
    queryFn: () => apiFetch<DatasetSummary>(`/datasets/${datasetId}/summary`),
    enabled: Boolean(datasetId),
  });
}

export async function downloadCompatibilityReport(
  datasetId: string,
  format: 'json' | 'csv'
): Promise<void> {
  const token = getAuthToken();
  const url = `/api/v1/datasets/${datasetId}/compatibility/download?format=${format}`;
  const response = await fetch(url, {
    headers: {
      Accept: format === 'json' ? 'application/json' : 'text/csv',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to download report: ${response.statusText}`);
  }

  const blob = await response.blob();
  const downloadUrl = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `compatibility_report_${datasetId}.${format}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(downloadUrl);
}
