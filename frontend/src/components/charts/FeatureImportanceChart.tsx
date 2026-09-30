import React from 'react';
import type { PredictionExplanation } from '../../types';

interface FeatureImportanceChartProps {
  explanation: PredictionExplanation;
}

export const FeatureImportanceChart: React.FC<FeatureImportanceChartProps> = ({ explanation }) => {
  return (
    <div className="space-y-4">
      {/* Narrative Headline */}
      <div className="p-3 rounded bg-[#0f1520] border-l-2 border-blue-500 text-xs text-slate-300 leading-relaxed font-sans">
        <span className="font-mono text-[10px] text-blue-400 font-bold uppercase tracking-wider block mb-1">
          Model Inference Explanation
        </span>
        {explanation.headline}
      </div>

      {/* SHAP Feature Contribution Bars */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pb-1 border-b border-[#1e2636]">
          <span>Attributed Features (Original C-MAPSS Identifiers)</span>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-rose-400">
              <span className="w-2 h-2 rounded-xs bg-rose-500" />
              Elevates Failure Risk
            </span>
            <span className="flex items-center gap-1.5 text-blue-400">
              <span className="w-2 h-2 rounded-xs bg-blue-500" />
              Attenuates Risk
            </span>
          </div>
        </div>

        <div className="space-y-1.5 font-mono text-xs">
          {explanation.topContributingFeatures.map((item, idx) => {
            const isRaises = item.direction === 'raises';
            const percentWidth = Math.min(100, Math.abs(item.weight) * 200);

            return (
              <div
                key={idx}
                className="p-2 rounded bg-[#0e131b] border border-[#1c2433] hover:border-[#27354b] transition-colors"
              >
                <div className="flex items-center justify-between text-xs mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-200">{item.feature}</span>
                    <span className="text-[11px] text-slate-500 font-normal">
                      observed: <strong className="text-slate-300 tabular-nums">{item.value}</strong>
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-[11px]">
                    <span className="text-slate-500">Ref: [{item.baselineRef}]</span>
                    <span className={`font-bold tabular-nums ${isRaises ? 'text-rose-400' : 'text-blue-400'}`}>
                      {isRaises ? '+' : ''}{(item.weight * 100).toFixed(1)}% weight
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="h-1.5 w-full bg-[#18202d] rounded-xs overflow-hidden flex">
                  <div
                    className={`h-full ${isRaises ? 'bg-rose-500' : 'bg-blue-500'}`}
                    style={{ width: `${percentWidth}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Empirical Trend Facts */}
      <div className="p-3 rounded bg-[#0f141d] border border-[#1e2636] space-y-2">
        <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
          Empirical Trend Facts (Last 20 Cycles)
        </div>
        <ul className="space-y-1 text-xs text-slate-300 font-sans">
          {explanation.trendFacts.map((fact, idx) => (
            <li key={idx} className="flex items-start gap-2">
              <span className="text-blue-400 font-mono font-bold shrink-0">&rsaquo;</span>
              <span>{fact}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};
