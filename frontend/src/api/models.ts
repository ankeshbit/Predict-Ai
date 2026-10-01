import { useQuery } from '@tanstack/react-query';
import { apiFetch } from './client';

export interface BackendModelVersion {
  id: string;
  bundle_version: string;
  task: string;
  model_type: string;
  adapter_key: string;
  feature_config_version: string;
  preprocessing_version: string;
  input_features: string[];
  horizon?: number | null;
  horizon_unit?: string | null;
  decision_threshold?: number | null;
  is_active: boolean;
  model_card_complete: boolean;
  sha256_hash: string;
  python_version: string;
  created_at: string;
}

export interface BackendModelEvaluation {
  id: string;
  model_version_id: string;
  task: string;
  metrics: {
    internal_test?: Record<string, number>;
    official_test?: Record<string, number>;
    [key: string]: any;
  };
  confusion_matrix: Record<string, any>;
  calibration_curve: Record<string, any>;
  curves: {
    internal_test?: {
      roc_curve?: { fpr: number[]; tpr: number[] };
      pr_curve?: { precision: number[]; recall: number[] };
    };
    official_test?: {
      roc_curve?: { fpr: number[]; tpr: number[] };
      pr_curve?: { precision: number[]; recall: number[] };
    };
    [key: string]: any;
  };
  feature_importance: Array<{
    feature: string;
    importance: number;
    sensor?: string;
  }>;
  methodology: string;
  limitations: string[];
  evaluated_at: string;
}

export function useModels() {
  return useQuery({
    queryKey: ['models'],
    queryFn: () => apiFetch<BackendModelVersion[]>('/models'),
  });
}

export function useActiveModel() {
  return useQuery({
    queryKey: ['activeModel'],
    queryFn: () => apiFetch<BackendModelVersion>('/models/active'),
  });
}

export function useModelEvaluation(modelId?: string) {
  return useQuery({
    queryKey: ['modelEvaluation', modelId],
    queryFn: () => apiFetch<BackendModelEvaluation>(`/models/${modelId}/evaluation`),
    enabled: !!modelId,
    retry: false,
  });
}
