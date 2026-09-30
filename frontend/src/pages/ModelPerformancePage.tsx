import React, { useState } from 'react';
import type { ModelEvaluation, ModelVersion } from '../types';
import { ConfusionMatrixChart } from '../components/charts/ConfusionMatrixChart';
import { RocPrCurves } from '../components/charts/RocPrCurves';
import { CalibrationPlot } from '../components/charts/CalibrationPlot';
import { Cpu, ShieldCheck, Info } from 'lucide-react';

interface ModelPerformancePageProps {
  evaluation: ModelEvaluation | null;
  activeModels: ModelVersion[];
}

export const ModelPerformancePage: React.FC<ModelPerformancePageProps> = ({
  evaluation,
  activeModels,
}) => {
  const [selectedModelId, setSelectedModelId] = useState<string>(activeModels[0]?.id || '');
  const activeModel = activeModels.find((m) => m.id === selectedModelId) || activeModels[0];

  if (!evaluation) {
    return (
      <div className="space-y-4">
        <h1 className="text-lg font-semibold text-slate-100 tracking-tight">Model Evaluation Workspace</h1>
        <div className="p-12 text-center rounded-lg border border-[#1f2838] bg-[#111620] space-y-2">
          <Cpu className="w-8 h-8 text-slate-500 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-200">No Model Evaluation Artifacts Loaded</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Run the offline evaluation pipeline (`python -m ml.evaluate`) to export evaluation metrics, ROC/PR curves, and calibration tables.
          </p>
        </div>
      </div>
    );
  }

  const { metrics, confusionMatrix, prCurve, rocCurve, calibrationCurve, featureImportance } = evaluation;

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
            value={selectedModelId}
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

      {/* Model Identity & Lineage Banner (Section 17 Structure) */}
      <div className="p-3.5 rounded-lg bg-[#111620] border border-[#1f2838] grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block">Model Identity</span>
          <span className="font-mono font-semibold text-slate-200 mt-0.5 block">{activeModel?.version || 'failure_lgb_v2.1'}</span>
          <span className="text-[11px] text-slate-400 font-mono">{activeModel?.modelType || 'LightGBM Classifier'}</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block">Dataset &amp; Split</span>
          <span className="font-semibold text-slate-200 mt-0.5 block truncate">{evaluation.evaluationDataset}</span>
          <span className="text-[11px] text-slate-400 font-mono">{evaluation.splitProtocol}</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block">Prediction Horizon</span>
          <span className="font-mono font-semibold text-blue-400 mt-0.5 block">H = 30 Operating Cycles</span>
          <span className="text-[11px] text-slate-400 font-mono">Binary degradation</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block">Evaluated At</span>
          <span className="font-mono text-slate-200 mt-0.5 block">{evaluation.evaluatedAt}</span>
          <span className="text-[11px] text-slate-400 font-mono">920 test engine windows</span>
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
            <p className="text-[11px] text-slate-400">Classification outcomes across 920 test window evaluations</p>
          </div>
          <ConfusionMatrixChart matrix={confusionMatrix} />
        </div>
      </div>

      {/* Feature Importance & SHAP Attribution */}
      <div className="p-4 bg-[#111620] border border-[#1f2838] rounded-lg space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-[#1f2838]">
          <div>
            <h4 className="font-semibold text-slate-100 font-mono text-xs">Global Feature Importance (SHAP Mean Absolute Attribution)</h4>
            <p className="text-[11px] text-slate-400">Contribution of standardized C-MAPSS sensor features to degradation probability</p>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Top 7 explanatory channels
          </span>
        </div>

        <div className="space-y-2.5 text-xs">
          {featureImportance.map((item, idx) => (
            <div key={idx} className="space-y-1">
              <div className="flex justify-between items-center text-slate-300 font-mono text-xs">
                <span className="font-semibold">{item.feature}</span>
                <span className="text-slate-400 text-[11px]">
                  Importance: <strong className="text-blue-400 font-mono">{(item.importance * 100).toFixed(1)}%</strong>
                </span>
              </div>
              <div className="h-1.5 w-full bg-[#161f2d] rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 rounded-full"
                  style={{ width: `${item.importance * 300}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Model Card & Operational Boundary */}
      <div className="p-4 bg-[#111620] border border-[#1f2838] rounded-lg space-y-3 text-xs">
        <div className="flex items-center gap-2 text-slate-200 font-semibold font-mono text-xs">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Model Card &amp; Engineering Specifications</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-slate-300">
          <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] space-y-1">
            <span className="font-mono text-[11px] text-slate-400 uppercase">Target Definition</span>
            <p className="text-slate-300 leading-relaxed font-sans">{activeModel.modelCard.targetDefinition}</p>
          </div>

          <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] space-y-1">
            <span className="font-mono text-[11px] text-slate-400 uppercase">Probability Calibration Protocol</span>
            <p className="text-slate-300 leading-relaxed font-sans">{activeModel.modelCard.calibrationInfo}</p>
          </div>
        </div>

        <div className="p-3 rounded-md bg-[#17161b] border border-amber-900/40 text-amber-200 text-xs flex items-start gap-2.5">
          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-amber-300 block font-mono text-[11px] uppercase">
              Stated Operational Limitations
            </span>
            <p className="text-slate-300 text-xs mt-0.5 font-sans leading-relaxed">
              {activeModel.modelCard.limitations}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
