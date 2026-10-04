/**
 * Demo Fleet API hooks.
 *
 * useResetDemo — POST /demo/reset (admin only, invalidates everything).
 * useReplayStatus — GET /demo/replay/status (polled every POLL_INTERVAL_MS, admin only).
 * useStartReplay — POST /demo/replay/start (admin only, advances one cycle).
 * useStopReplay — POST /demo/replay/stop (admin only).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch, POLL_INTERVAL_MS } from './client';

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
  return useQuery({
    queryKey: ['demo', 'replay', 'status'],
    queryFn: () => apiFetch<DemoReplayStatus>('/demo/replay/status'),
    enabled: isAdmin,
    refetchInterval: POLL_INTERVAL_MS,
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
