import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

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
  checks: CompatibilityCheckItem[];
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
    mutationFn: (datasetId: string) =>
      apiFetch<{ job_id: string; dataset_id: string; status: string; message: string }>(
        `/datasets/${datasetId}/ingest`,
        { method: 'POST' }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
      queryClient.invalidateQueries({ queryKey: ['machines'] });
    },
  });
}
