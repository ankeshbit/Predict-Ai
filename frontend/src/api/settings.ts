import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export interface HealthConfig {
  id: string;
  version: string;
  anomaly_weight: number;
  data_quality_penalty: Record<string, number>;
  trend_enabled: boolean;
  is_active: boolean;
  created_at: string;
}

export interface RiskBands {
  low_max: number;
  medium_max: number;
  high_max: number;
}

export interface AlertRule {
  id: string;
  rule_id: string;
  alert_type: string;
  failure_probability_threshold: number;
  anomaly_severity_threshold: string;
  consecutive_cycles: number;
  is_active: boolean;
}

export interface ReliabilityConfig {
  max_missing_fraction: number;
  max_out_of_range_fraction: number;
  max_z_shift: number;
  min_window_length: number;
  description: string;
}

export interface RecommendationRules {
  version: string;
  domain: string;
  disclaimer: string;
  rules: Array<{
    rule_id: string;
    condition: string;
    category: string;
    action: string;
  }>;
}

export interface AuditLogItem {
  id: number;
  user_id?: string | null;
  action: string;
  resource_type: string;
  resource_id?: string | null;
  details?: Record<string, any> | null;
  ip_address?: string | null;
  created_at: string;
}

export function useHealthConfig() {
  return useQuery({
    queryKey: ['settings', 'health-indicator'],
    queryFn: () => apiFetch<HealthConfig>('/settings/health-indicator'),
  });
}

export function useUpdateHealthConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<HealthConfig>) =>
      apiFetch<HealthConfig>('/settings/health-indicator', {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings', 'health-indicator'] });
    },
  });
}

export function useRiskBands() {
  return useQuery({
    queryKey: ['settings', 'risk-bands'],
    queryFn: () => apiFetch<RiskBands>('/settings/risk-bands'),
  });
}

export function useUpdateRiskBands() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RiskBands) =>
      apiFetch<RiskBands>('/settings/risk-bands', {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings', 'risk-bands'] });
    },
  });
}

export function useAlertRules() {
  return useQuery({
    queryKey: ['settings', 'alert-rules'],
    queryFn: () => apiFetch<AlertRule[]>('/settings/alert-rules'),
  });
}

export function useUpdateAlertRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, body }: { ruleId: string; body: Partial<AlertRule> }) =>
      apiFetch<AlertRule>(`/settings/alert-rules/${ruleId}`, {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['settings', 'alert-rules'] });
    },
  });
}

export function useReliabilityConfig() {
  return useQuery({
    queryKey: ['settings', 'reliability'],
    queryFn: () => apiFetch<ReliabilityConfig>('/settings/reliability'),
  });
}

export function useRecommendationRules() {
  return useQuery({
    queryKey: ['settings', 'recommendation-rules'],
    queryFn: () => apiFetch<RecommendationRules>('/settings/recommendation-rules'),
  });
}

export function useAuditLog(action?: string) {
  return useQuery({
    queryKey: ['admin', 'audit-log', action],
    queryFn: () => {
      const url = action ? `/admin/audit-log?action=${action}` : '/admin/audit-log';
      return apiFetch<{ items: AuditLogItem[]; total: number }>(url);
    },
  });
}
