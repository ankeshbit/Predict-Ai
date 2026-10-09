/**
 * Demo Fleet API hooks.
 *
 * useResetDemo — POST /demo/reset (admin only, invalidates everything).
 * useResetDemoPreview — GET /demo/reset/preview (shows what will be deleted).
 * useReplayStatus — GET /demo/replay/status (polled every POLL_INTERVAL_MS, admin only).
 * useStartReplay — POST /demo/replay/start (admin only, advances one cycle).
 * useStopReplay — POST /demo/replay/stop (admin only).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export interface DemoResetResult {
  status: string;
  message: string;
  demo_units: Record<
    string,
    {
      machine_code: string;
      cutoff_cycle: number;
      readings_count: number;
      health_indicator: number;
    }
  >;
}

export interface ResetDemoPreviewResponse {
  demo_machines_to_reset: number;
  user_machines_to_delete: number;
  user_datasets_to_delete: number;
  user_dataset_names: string[];
  user_predictions_to_delete: number;
  user_alerts_to_delete: number;
}

export interface DemoReplayStatus {
  running: boolean;
  completed?: boolean;
  current_machine_cycles: Record<string, number>;
  message: string;
}

export function useResetDemoPreview(enabled = true) {
  return useQuery({
    queryKey: ['demo', 'reset', 'preview'],
    queryFn: () => apiFetch<ResetDemoPreviewResponse>('/demo/reset/preview'),
    enabled,
  });
}

export function useResetDemo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (variables?: { clearUserDatasets?: boolean }) => {
      const clearUser = variables?.clearUserDatasets ? 'true' : 'false';
      return apiFetch<DemoResetResult>(`/demo/reset?clear_user_datasets=${clearUser}`, {
        method: 'POST',
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });
}

export function useDemoReplayStatus(isAdmin: boolean) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ['demo', 'replay', 'status'],
    queryFn: async () => {
      const res = await apiFetch<DemoReplayStatus>('/demo/replay/status');
      if (res.running) {
        queryClient.invalidateQueries({ queryKey: ['machines'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      }
      return res;
    },
    enabled: isAdmin,
    refetchInterval: (query) => {
      return query.state.data?.running ? 1500 : 3000;
    },
    refetchIntervalInBackground: false,
  });
}

export function useStartReplay() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ status: string; message: string }>('/demo/replay/start', { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['machines'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      queryClient.invalidateQueries({ queryKey: ['demo', 'replay', 'status'] });
    },
  });
}

export function useStopReplay() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ status: string; message: string }>('/demo/replay/stop', { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo', 'replay', 'status'] });
    },
  });
}
