/**
 * Dashboard API hooks with real-time polling.
 *
 * All query hooks use refetchInterval so the UI stays current without manual refresh.
 * refetchIntervalInBackground: false — polling pauses when the tab is hidden (battery-friendly).
 * POLL_INTERVAL_MS defaults to 7 s and is configurable via VITE_POLL_INTERVAL_MS.
 */

import { useQuery } from '@tanstack/react-query';
import { apiFetch, POLL_INTERVAL_MS } from './client';

export interface DashboardSummary {
  total_machines: number;
  healthy_count: number;
  warning_count: number;
  critical_count: number;
  average_health_indicator: number;
  open_alerts_count: number;
  dataset_banner_text: string;
  dataset_badge_text: string;
  health_band_counts: Record<string, number>;
  operational_counts: Record<string, number>;
  active_count: number;
  maintenance_count: number;
  server_time?: string | null;
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
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
  });
}

export function usePriorityMachines(limit = 5) {
  return useQuery({
    queryKey: ['dashboard', 'priority-machines', limit],
    queryFn: () => apiFetch<PriorityMachine[]>(`/dashboard/priority-machines?limit=${limit}`),
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
  });
}

export function useRecentAnomalies(limit = 5) {
  return useQuery({
    queryKey: ['dashboard', 'recent-anomalies', limit],
    queryFn: () => apiFetch<RecentAnomaly[]>(`/dashboard/recent-anomalies?limit=${limit}`),
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
  });
}

export function useRecentAlerts(limit = 5) {
  return useQuery({
    queryKey: ['dashboard', 'recent-alerts', limit],
    queryFn: () => apiFetch<RecentAlert[]>(`/dashboard/recent-alerts?limit=${limit}`),
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
  });
}

export function useProbabilityDistribution() {
  return useQuery({
    queryKey: ['dashboard', 'probability-distribution'],
    queryFn: () => apiFetch<ProbabilityDistribution>('/dashboard/probability-distribution'),
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: false,
  });
}
