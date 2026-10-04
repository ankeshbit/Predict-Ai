/**
 * Demo Fleet API hooks.
 *
 * useResetDemo — POST /demo/reset (admin only, invalidates everything).
 * useReplayStatus — GET /demo/replay/status (polled every POLL_INTERVAL_MS, admin only).
 * useStartReplay — POST /demo/replay/start (admin only, advances one cycle).
 * useStopReplay — POST /demo/replay/stop (admin only).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export interface DemoResetResult {
  status: string;
  message: string;
  demo_units: Record<string, {
    machine_code: string;
    cutoff_cycle: number;
    readings_count: number;
    health_indicator: number;
  }>;
}

export interface DemoReplayStatus {
  running: boolean;
  completed?: boolean;
  current_machine_cycles: Record<string, number>;
  message: string;
}

export function useResetDemo() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<DemoResetResult>('/demo/reset', { method: 'POST' }),
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
