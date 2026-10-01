import { useMutation, useQueryClient } from '@tanstack/react-query';
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
