import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export interface BackendMaintenanceRecord {
  id: string;
  machine_id: string;
  alert_id?: string | null;
  issue?: string | null;
  recommended_action?: string | null;
  decision?: 'followed_recommendation' | 'modified' | 'declined' | null;
  decision_rationale?: string | null;
  action_taken?: string | null;
  action_type: string;
  status: 'recommended' | 'in_progress' | 'completed' | 'cancelled';
  outcome?: 'resolved' | 'no_issue_found' | 'unresolved' | null;
  engineer_notes: string;
  performed_by_user_id: string;
  started_at: string;
  completed_at?: string | null;
}

export interface MaintenanceListResponse {
  items: BackendMaintenanceRecord[];
  total: number;
}

export interface MaintenanceFilterParams {
  machine_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}

export interface CreateMaintenanceInput {
  machine_id: string;
  alert_id?: string | null;
  issue?: string | null;
  recommended_action?: string | null;
  decision: 'followed_recommendation' | 'modified' | 'declined';
  decision_rationale: string;
  action_taken: string;
  action_type?: string;
  notes?: string;
}

export interface CompleteMaintenanceInput {
  recordId: string;
  outcome: 'resolved' | 'no_issue_found' | 'unresolved';
  engineer_notes?: string;
}

export function useMaintenanceRecords(params?: MaintenanceFilterParams) {
  const queryParams = new URLSearchParams();
  if (params?.machine_id) queryParams.set('machine_id', params.machine_id);
  if (params?.status) queryParams.set('status', params.status);
  if (params?.limit) queryParams.set('limit', String(params.limit));
  if (params?.offset) queryParams.set('offset', String(params.offset));

  const queryStr = queryParams.toString() ? `?${queryParams.toString()}` : '';

  return useQuery({
    queryKey: ['maintenance', params],
    queryFn: () => apiFetch<MaintenanceListResponse>(`/maintenance${queryStr}`),
  });
}

export function useCreateMaintenance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateMaintenanceInput) =>
      apiFetch<BackendMaintenanceRecord>('/maintenance', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['maintenance'] });
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['machine', variables.machine_id] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
}

export function useCompleteMaintenance() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ recordId, outcome, engineer_notes }: CompleteMaintenanceInput) =>
      apiFetch<BackendMaintenanceRecord>(`/maintenance/${recordId}/complete`, {
        method: 'POST',
        body: JSON.stringify({ outcome, engineer_notes: engineer_notes || '' }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['maintenance'] });
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
}
