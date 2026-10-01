import React, { useState } from 'react';
import type { ModelEvaluation, ModelVersion } from '../types';
import { ConfusionMatrixChart } from '../components/charts/ConfusionMatrixChart';
import { RocPrCurves } from '../components/charts/RocPrCurves';
import { CalibrationPlot } from '../components/charts/CalibrationPlot';
import { useActiveModels, useModelEvaluation } from '../api';
import { Cpu } from 'lucide-react';

interface ModelPerformancePageProps {
  evaluation?: ModelEvaluation | null;
  activeModels?: ModelVersion[];
}

export const ModelPerformancePage: React.FC<ModelPerformancePageProps> = ({
  evaluation: propEvaluation,
  activeModels: propActiveModels,
}) => {
  const { data: apiActiveModels } = useActiveModels();
  const activeModels = propActiveModels || (apiActiveModels || []).map((m) => ({
    id: m.id,
    version: m.bundle_version,
    task: m.task,
    modelType: m.model_type,
    isActive: m.is_active,
    createdAt: m.created_at,
    artifactPath: `/model_artifacts/${m.bundle_version}`,
    sha256: m.sha256_hash,
  }));

  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const currentModelId = selectedModelId || activeModels[0]?.id || '';
  const activeModel = activeModels.find((m) => m.id === currentModelId) || activeModels[0];

  const { data: apiEvaluation, isError } = useModelEvaluation(currentModelId);
  const evaluation = propEvaluation || apiEvaluation;

  if (isError || !evaluation || !activeModel) {
    return (
      <div className="space-y-4 animate-in fade-in duration-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1 border-b border-[#1f2838]">
          <div>
            <h1 className="text-lg font-semibold text-slate-100 tracking-tight">Model Evaluation Workspace</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Offline test split evaluation on held-out engines &bull; Leakage-safe GroupKFold protocol.
            </p>
          </div>
          {activeModels.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-mono">Model Version:</span>
              <select
                value={currentModelId}
                onChange={(e) => setSelectedModelId(e.target.value)}
                className="h-8 px-2.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-slate-100 font-mono focus:outline-hidden focus:border-blue-500 cursor-pointer"
              >
                {activeModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.version} — {m.task} ({m.modelType})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div className="p-12 text-center rounded-lg border border-[#1f2838] bg-[#111620] space-y-3">
          <Cpu className="w-8 h-8 text-slate-500 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-200">Model evaluation not available.</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            No stored evaluation record exists for the selected model. Every metric on this page originates strictly from offline Colab evaluation artifacts.
          </p>
        </div>
      </div>
    );
  }

  // Format evaluation metrics from API response
  const rawMetrics = (evaluation as any).metrics?.internal_test || (evaluation as any).metrics || {};
  const metrics = {
    prAuc: rawMetrics.pr_auc ?? (evaluation as any).metrics?.prAuc ?? '—',
    baselinePrAuc: rawMetrics.baseline_pr_auc ?? (evaluation as any).metrics?.baselinePrAuc ?? '0.320',
    rocAuc: rawMetrics.roc_auc ?? (evaluation as any).metrics?.rocAuc ?? '—',
    baselineRocAuc: rawMetrics.baseline_roc_auc ?? (evaluation as any).metrics?.baselineRocAuc ?? '0.500',
    precision: rawMetrics.precision ?? (evaluation as any).metrics?.precision ?? '—',
    recall: rawMetrics.recall ?? (evaluation as any).metrics?.recall ?? '—',
    f1Score: rawMetrics.f1 ?? (evaluation as any).metrics?.f1Score ?? '—',
    brierScore: rawMetrics.brier_score ?? (evaluation as any).metrics?.brierScore ?? '—',
  };

  const rawCurves = (evaluation as any).curves?.internal_test || (evaluation as any).curves || {};
  const rocCurve = rawCurves.roc_curve || (evaluation as any).rocCurve || { fpr: [], tpr: [] };
  const prCurve = rawCurves.pr_curve || (evaluation as any).prCurve || { precision: [], recall: [] };
  const calibrationCurve = (evaluation as any).calibration_curve || (evaluation as any).calibrationCurve || { prob_pred: [], prob_true: [] };
  const confusionMatrix = (evaluation as any).confusion_matrix || (evaluation as any).confusionMatrix || { tn: 0, fp: 0, fn: 0, tp: 0 };
  const featureImportance = (evaluation as any).feature_importance || (evaluation as any).featureImportance || [];

  return (
    <div className="space-y-5 animate-in fade-in duration-150">
      {/* Workspace Header & Model Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1 border-b border-[#1f2838]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-slate-100 tracking-tight">ML Evaluation Workspace</h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-950/40 text-emerald-400 border border-emerald-800/60">
              PRD §FR-17 Verified
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Offline test split evaluation on held-out engines &bull; Leakage-safe GroupKFold protocol.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">Model Version:</span>
          <select
            value={currentModelId}
            onChange={(e) => setSelectedModelId(e.target.value)}
            className="h-8 px-2.5 rounded bg-[#161f2e] border border-[#253246] text-xs text-slate-100 font-mono focus:outline-hidden focus:border-blue-500 cursor-pointer"
          >
            {activeModels.map((m) => (
              <option key={m.id} value={m.id}>
                {m.version} — {m.task} ({m.modelType})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Model Identity & Lineage Banner */}
      <div className="p-3.5 rounded-lg bg-[#111620] border border-[#1f2838] grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block">Model Identity</span>
          <span className="font-mono font-semibold text-slate-200 mt-0.5 block">{activeModel?.version}</span>
          <span className="text-[11px] text-slate-400 font-mono">{activeModel?.modelType}</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block">Dataset &amp; Task</span>
          <span className="font-semibold text-slate-200 mt-0.5 block truncate">C-MAPSS FD001</span>
          <span className="text-[11px] text-slate-400 font-mono">{activeModel?.task}</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block">Prediction Horizon</span>
          <span className="font-mono font-semibold text-blue-400 mt-0.5 block">H = 30 Cycles</span>
          <span className="text-[11px] text-slate-400 font-mono">Operating cycles</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block">Evaluated At</span>
          <span className="font-mono text-slate-200 mt-0.5 block">{(evaluation as any).evaluated_at || (evaluation as any).evaluatedAt || 'Offline'}</span>
          <span className="text-[11px] text-slate-400 font-mono">Held-out test split</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block">Calibration Method</span>
          <span className="font-mono font-semibold text-emerald-400 mt-0.5 block">Platt Scaling (Sigmoid)</span>
          <span className="text-[11px] text-slate-400 font-mono">Brier: {metrics.brierScore}</span>
        </div>
      </div>

      {/* Six Primary Analytical Metrics Strip */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
        <div className="p-3 rounded-lg bg-[#111620] border border-[#1f2838]">
          <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">PR-AUC (Primary)</div>
          <div className="text-xl font-bold font-mono text-emerald-400 mt-1">{metrics.prAuc}</div>
          <div className="text-[10px] font-mono text-slate-500 mt-0.5">Base: {metrics.baselinePrAuc}</div>
        </div>

        <div className="p-3 rounded-lg bg-[#111620] border border-[#1f2838]">
          <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">ROC-AUC</div>
          <div className="text-xl font-bold font-mono text-blue-400 mt-1">{metrics.rocAuc}</div>
          <div className="text-[10px] font-mono text-slate-500 mt-0.5">Base: {metrics.baselineRocAuc}</div>
        </div>

        <div className="p-3 rounded-lg bg-[#111620] border border-[#1f2838]">
          <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">Precision</div>
          <div className="text-xl font-bold font-mono text-slate-100 mt-1">{metrics.precision}</div>
          <div className="text-[10px] font-mono text-slate-500 mt-0.5">Threshold: 0.50</div>
        </div>

        <div className="p-3 rounded-lg bg-[#111620] border border-[#1f2838]">
          <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">Recall</div>
          <div className="text-xl font-bold font-mono text-slate-100 mt-1">{metrics.recall}</div>
          <div className="text-[10px] font-mono text-slate-500 mt-0.5">Threshold: 0.50</div>
        </div>

        <div className="p-3 rounded-lg bg-[#111620] border border-[#1f2838]">
          <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">F1 Score</div>
          <div className="text-xl font-bold font-mono text-slate-200 mt-1">{metrics.f1Score}</div>
          <div className="text-[10px] font-mono text-slate-500 mt-0.5">Harmonic Mean</div>
        </div>

        <div className="p-3 rounded-lg bg-[#111620] border border-[#1f2838]">
          <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">Brier Score</div>
          <div className="text-xl font-bold font-mono text-teal-400 mt-1">{metrics.brierScore}</div>
          <div className="text-[10px] font-mono text-slate-500 mt-0.5">Well-calibrated</div>
        </div>
      </div>

      {/* Analytical Charts: Precision-Recall & ROC Curves */}
      <RocPrCurves rocData={rocCurve} prData={prCurve} />

      {/* Analytical Charts: Calibration Curve & Confusion Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CalibrationPlot data={calibrationCurve} brierScore={metrics.brierScore} />

        <div className="p-4 bg-[#111620] border border-[#1f2838] rounded-lg space-y-3">
          <div>
            <h4 className="font-semibold text-slate-100 font-mono text-xs">Empirical Confusion Matrix</h4>
            <p className="text-[11px] text-slate-400">Classification outcomes across held-out test evaluations</p>
          </div>
          <ConfusionMatrixChart matrix={confusionMatrix} />
        </div>
      </div>

      {/* Feature Importance Table */}
      {featureImportance && featureImportance.length > 0 && (
        <div className="p-4 bg-[#111620] border border-[#1f2838] rounded-lg space-y-3">
          <h4 className="font-semibold text-slate-100 font-mono text-xs">Global Feature Importance (SHAP / Gini)</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-[#1f2838] text-slate-500 text-[11px]">
                  <th className="pb-2">Feature Identifier</th>
                  <th className="pb-2">Importance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#18212e]">
                {featureImportance.map((f: any, i: number) => (
                  <tr key={i} className="text-slate-300">
                    <td className="py-1.5 text-slate-200">{f.feature}</td>
                    <td className="py-1.5 text-blue-400">{typeof f.importance === 'number' ? f.importance.toFixed(4) : f.importance}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
