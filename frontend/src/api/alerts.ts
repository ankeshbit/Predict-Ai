import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export interface BackendAlert {
  id: string;
  machine_id: string;
  alert_type: string;
  status: 'open' | 'acknowledged' | 'resolved';
  severity: 'warning' | 'critical';
  trigger_cycle: number;
  trigger_score: number;
  recommendation_text: string;
  recommendation_rule_id: string;
  acknowledged_at?: string | null;
  acknowledged_by_user_id?: string | null;
  resolved_at?: string | null;
  resolved_by_user_id?: string | null;
  created_at: string;
}

export interface AlertListResponse {
  items: BackendAlert[];
  total: number;
}

export interface AlertFilterParams {
  status?: string;
  severity?: string;
  machine_id?: string;
  limit?: number;
  offset?: number;
}

export function useAlerts(params?: AlertFilterParams) {
  const queryParams = new URLSearchParams();
  if (params?.status) queryParams.set('status', params.status);
  if (params?.severity) queryParams.set('severity', params.severity);
  if (params?.machine_id) queryParams.set('machine_id', params.machine_id);
  if (params?.limit) queryParams.set('limit', String(params.limit));
  if (params?.offset) queryParams.set('offset', String(params.offset));

  const queryStr = queryParams.toString() ? `?${queryParams.toString()}` : '';

  return useQuery({
    queryKey: ['alerts', params],
    queryFn: () => apiFetch<AlertListResponse>(`/alerts${queryStr}`),
  });
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ alertId, note }: { alertId: string; note?: string }) =>
      apiFetch<BackendAlert>(`/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        body: JSON.stringify({ note }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
}

export function useResolveAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      alertId,
      resolutionType,
      resolutionNote,
    }: {
      alertId: string;
      resolutionType?: string;
      resolutionNote?: string;
    }) =>
      apiFetch<BackendAlert>(`/alerts/${alertId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({
          resolution_type: resolutionType || 'issue_resolved',
          resolution_note: resolutionNote,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['machines'] });
    },
  });
}
