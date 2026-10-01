import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export interface DashboardSummary {
  total_machines: number;
  operational_counts: Record<string, number>;
  health_band_counts: Record<string, number>;
  average_health_indicator: number;
  open_alerts_count: number;
  dataset_banner_text: string;
  is_demo: boolean;
}

export interface PriorityMachine {
  id: string;
  machine_code: string;
  failure_probability: number;
  horizon: number;
  health_indicator: number;
  health_band: string;
  operational_status: string;
  open_alerts_count: number;
}

export interface RecentAnomaly {
  id: string;
  machine_id: string;
  cycle: number;
  anomaly_score: number;
  severity: string;
  detected_at: string;
}

export interface RecentAlert {
  id: string;
  machine_id: string;
  alert_type: string;
  severity: string;
  status: string;
  trigger_cycle: number;
  trigger_score: number;
  recommendation_text: string;
  created_at: string;
}

export interface ProbabilityDistribution {
  bins: Array<{
    bin_start: number;
    bin_end: number;
    count: number;
  }>;
  total: number;
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => apiFetch<DashboardSummary>('/dashboard/summary'),
  });
}

export function usePriorityMachines(limit = 5) {
  return useQuery({
    queryKey: ['dashboard', 'priority-machines', limit],
    queryFn: () => apiFetch<PriorityMachine[]>(`/dashboard/priority-machines?limit=${limit}`),
  });
}

export function useRecentAnomalies(limit = 5) {
  return useQuery({
    queryKey: ['dashboard', 'recent-anomalies', limit],
    queryFn: () => apiFetch<RecentAnomaly[]>(`/dashboard/recent-anomalies?limit=${limit}`),
  });
}

export function useRecentAlerts(limit = 5) {
  return useQuery({
    queryKey: ['dashboard', 'recent-alerts', limit],
    queryFn: () => apiFetch<RecentAlert[]>(`/dashboard/recent-alerts?limit=${limit}`),
  });
}

export function useProbabilityDistribution() {
  return useQuery({
    queryKey: ['dashboard', 'probability-distribution'],
    queryFn: () => apiFetch<ProbabilityDistribution>('/dashboard/probability-distribution'),
  });
}
