import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';

interface CurveProps {
  rocData: Array<{ fpr: number; tpr: number }>;
  prData: Array<{ recall: number; precision: number }>;
}

export const RocPrCurves: React.FC<CurveProps> = ({ rocData, prData }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Precision-Recall Curve (Primary Metric for Imbalanced Data) */}
      <div className="p-4 bg-[#111620] border border-[#1f2838] rounded-lg space-y-3">
        <div className="flex items-center justify-between text-xs">
          <div>
            <h4 className="font-semibold text-slate-100 font-mono">Precision-Recall Curve (PR-AUC: 0.892)</h4>
            <p className="text-[11px] text-slate-400">Primary metric for class-imbalanced run-to-failure degradation</p>
          </div>
          <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/60">
            Baseline: 0.320
          </span>
        </div>

        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={prData} margin={{ top: 10, right: 15, left: -15, bottom: 15 }}>
              <CartesianGrid strokeDasharray="2 2" stroke="#1c2534" />
              <XAxis
                dataKey="recall"
                stroke="#64748b"
                fontSize={10}
                domain={[0, 1]}
                tickLine={false}
                label={{ value: 'Recall', position: 'insideBottom', offset: -10, fill: '#64748b', fontSize: 10 }}
              />
              <YAxis
                dataKey="precision"
                stroke="#64748b"
                fontSize={10}
                domain={[0, 1]}
                tickLine={false}
                label={{ value: 'Precision', angle: -90, position: 'insideLeft', offset: 20, fill: '#64748b', fontSize: 10 }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    return (
                      <div className="bg-[#0b1018] border border-[#222d3f] p-2 rounded text-xs font-mono shadow-md">
                        <p className="text-slate-400 text-[10px]">Recall: <strong className="text-slate-200">{d.recall}</strong></p>
                        <p className="text-blue-400 text-[10px]">Precision: <strong className="text-slate-200">{d.precision}</strong></p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine y={0.32} stroke="#475569" strokeDasharray="3 3" />
              <Line type="monotone" dataKey="precision" stroke="#2563eb" strokeWidth={2} dot={{ r: 2.5, fill: '#2563eb' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ROC Curve */}
      <div className="p-4 bg-[#111620] border border-[#1f2838] rounded-lg space-y-3">
        <div className="flex items-center justify-between text-xs">
          <div>
            <h4 className="font-semibold text-slate-100 font-mono">ROC Curve (ROC-AUC: 0.946)</h4>
            <p className="text-[11px] text-slate-400">Sensitivity (TPR) vs 1 - Specificity (FPR)</p>
          </div>
          <span className="text-[11px] font-mono text-blue-400 bg-blue-950/40 px-2 py-0.5 rounded border border-blue-800/60">
            Baseline: 0.500
          </span>
        </div>

        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={rocData} margin={{ top: 10, right: 15, left: -15, bottom: 15 }}>
              <CartesianGrid strokeDasharray="2 2" stroke="#1c2534" />
              <XAxis
                dataKey="fpr"
                stroke="#64748b"
                fontSize={10}
                domain={[0, 1]}
                tickLine={false}
                label={{ value: 'False Positive Rate (FPR)', position: 'insideBottom', offset: -10, fill: '#64748b', fontSize: 10 }}
              />
              <YAxis
                dataKey="tpr"
                stroke="#64748b"
                fontSize={10}
                domain={[0, 1]}
                tickLine={false}
                label={{ value: 'True Positive Rate (TPR)', angle: -90, position: 'insideLeft', offset: 20, fill: '#64748b', fontSize: 10 }}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    return (
                      <div className="bg-[#0b1018] border border-[#222d3f] p-2 rounded text-xs font-mono shadow-md">
                        <p className="text-slate-400 text-[10px]">FPR: <strong className="text-slate-200">{d.fpr}</strong></p>
                        <p className="text-blue-400 text-[10px]">TPR: <strong className="text-slate-200">{d.tpr}</strong></p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#475569" strokeDasharray="3 3" />
              <Line type="monotone" dataKey="tpr" stroke="#3b82f6" strokeWidth={2} dot={{ r: 2.5, fill: '#3b82f6' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};
