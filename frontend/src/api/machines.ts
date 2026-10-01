import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export interface BackendMachine {
  id: string;
  machine_code: string;
  operational_status: 'active' | 'maintenance' | 'archived';
  health_indicator: number;
  health_band: 'Critical' | 'Poor' | 'Warning' | 'Healthy' | 'Excellent';
  is_demo: boolean;
  demo_cluster?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MachineListResponse {
  items: BackendMachine[];
  total: number;
}

export interface SensorTelemetryPoint {
  cycle: number;
  op_setting_1?: number | null;
  op_setting_2?: number | null;
  op_setting_3?: number | null;
  sensor_1?: number | null;
  sensor_2?: number | null;
  sensor_3?: number | null;
  sensor_4?: number | null;
  sensor_5?: number | null;
  sensor_6?: number | null;
  sensor_7?: number | null;
  sensor_8?: number | null;
  sensor_9?: number | null;
  sensor_10?: number | null;
  sensor_11?: number | null;
  sensor_12?: number | null;
  sensor_13?: number | null;
  sensor_14?: number | null;
  sensor_15?: number | null;
  sensor_16?: number | null;
  sensor_17?: number | null;
  sensor_18?: number | null;
  sensor_19?: number | null;
  sensor_20?: number | null;
  sensor_21?: number | null;
}

export interface SensorHistoryResponse {
  machine_id: string;
  downsampled: boolean;
  total_available: number;
  returned_count: number;
  points: SensorTelemetryPoint[];
}

export interface PredictionResponse {
  id: string;
  machine_id: string;
  cycle: number;
  as_of_index: number;
  predicted_at: string;
  failure_probability: number;
  risk_level: string;
  health_indicator: number;
  health_band: string;
  additive_breakdown: {
    base_score: number;
    penalty_risk: number;
    penalty_anomaly: number;
    penalty_dq: number;
    penalty_trend: number;
    clipping_adjustment: number;
    final_health_indicator: number;
  };
  lineage: {
    dataset_version: string;
    schema_mapping_hash: string;
    feature_config_version: string;
    preprocessing_version: string;
    failure_model_version_id: string;
    anomaly_model_version_id?: string | null;
    health_config_id: string;
    horizon: number;
    horizon_unit: string;
    input_window_start: number;
    input_window_end: number;
  };
  reliability_flags: Record<string, any>;
}

export interface MachineFilterParams {
  operational_status?: string;
  health_band?: string;
  is_demo?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}

export function useMachines(params?: MachineFilterParams) {
  const queryParams = new URLSearchParams();
  if (params?.operational_status) queryParams.set('operational_status', params.operational_status);
  if (params?.health_band) queryParams.set('health_band', params.health_band);
  if (params?.is_demo !== undefined) queryParams.set('is_demo', String(params.is_demo));
  if (params?.search) queryParams.set('search', params.search);
  if (params?.limit) queryParams.set('limit', String(params.limit));
  if (params?.offset) queryParams.set('offset', String(params.offset));

  const queryStr = queryParams.toString() ? `?${queryParams.toString()}` : '';

  return useQuery({
    queryKey: ['machines', params],
    queryFn: () => apiFetch<MachineListResponse>(`/machines${queryStr}`),
  });
}

export function useMachine(id?: string) {
  return useQuery({
    queryKey: ['machine', id],
    queryFn: () => apiFetch<BackendMachine>(`/machines/${id}`),
    enabled: !!id,
  });
}

export function useSensorHistory(
  id?: string,
  params?: { from_cycle?: number; to_cycle?: number; downsample_to?: number; channels?: string }
) {
  const queryParams = new URLSearchParams();
  if (params?.from_cycle) queryParams.set('from_cycle', String(params.from_cycle));
  if (params?.to_cycle) queryParams.set('to_cycle', String(params.to_cycle));
  if (params?.downsample_to) queryParams.set('downsample_to', String(params.downsample_to));
  if (params?.channels) queryParams.set('channels', params.channels);

  const queryStr = queryParams.toString() ? `?${queryParams.toString()}` : '';

  return useQuery({
    queryKey: ['sensorHistory', id, params],
    queryFn: () => apiFetch<any>(`/machines/${id}/sensors${queryStr}`),
    enabled: !!id,
  });
}

export function useMachineTelemetry(
  id?: string,
  params?: { start_cycle?: number; end_cycle?: number; downsample_limit?: number }
) {
  const queryParams = new URLSearchParams();
  if (params?.start_cycle) queryParams.set('from_cycle', String(params.start_cycle));
  if (params?.end_cycle) queryParams.set('to_cycle', String(params.end_cycle));
  if (params?.downsample_limit) queryParams.set('downsample_to', String(params.downsample_limit));

  const queryStr = queryParams.toString() ? `?${queryParams.toString()}` : '';

  return useQuery({
    queryKey: ['machineTelemetry', id, params],
    queryFn: () => apiFetch<any>(`/machines/${id}/sensors${queryStr}`),
    enabled: !!id,
  });
}

export function useMachinePredictions(id?: string, limit = 50) {
  return useQuery({
    queryKey: ['machinePredictions', id, limit],
    queryFn: () => apiFetch<{ items: PredictionResponse[]; total: number }>(`/machines/${id}/predictions?limit=${limit}`),
    enabled: !!id,
  });
}

export function useScoreMachine() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (machineId: string) =>
      apiFetch<Record<string, any>>(`/machines/${machineId}/score`, { method: 'POST' }),
    onSuccess: (_, machineId) => {
      queryClient.invalidateQueries({ queryKey: ['machine', machineId] });
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['machinePredictions', machineId] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
}
