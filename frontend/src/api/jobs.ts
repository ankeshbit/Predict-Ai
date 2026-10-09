import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export interface BackendJob {
  id: string;
  job_type: string;
  status: 'pending' | 'queued' | 'running' | 'completed' | 'failed';
  progress_pct: number;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  result?: Record<string, any> | null;
  created_at: string;
}

export function useJobStatus(jobId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['jobs', jobId],
    queryFn: () => apiFetch<BackendJob>(`/jobs/${jobId}`),
    enabled: Boolean(jobId) && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 1000;
    },
    refetchIntervalInBackground: false,
  });
}
