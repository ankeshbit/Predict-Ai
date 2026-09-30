import React from 'react';

interface ConfusionMatrixProps {
  matrix: {
    tp: number;
    fp: number;
    fn: number;
    tn: number;
  };
}

export const ConfusionMatrixChart: React.FC<ConfusionMatrixProps> = ({ matrix }) => {
  const total = matrix.tp + matrix.fp + matrix.fn + matrix.tn;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
        <span>Decision Threshold: <strong className="text-slate-200">τ = 0.50</strong></span>
        <span>Evaluations: <strong className="text-slate-200">{total}</strong></span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-center text-xs">
        {/* TP */}
        <div className="p-3.5 rounded-md bg-[#111c1b] border border-emerald-900/50 flex flex-col items-center justify-center">
          <span className="text-[10px] text-emerald-400 font-mono uppercase tracking-wider font-semibold">
            True Positive (TP)
          </span>
          <span className="text-2xl font-bold font-mono text-slate-100 mt-1">{matrix.tp}</span>
          <span className="text-[10px] font-mono text-slate-400 mt-0.5">
            {((matrix.tp / total) * 100).toFixed(1)}% &bull; True Deterioration
          </span>
        </div>

        {/* FP */}
        <div className="p-3.5 rounded-md bg-[#1c1417] border border-amber-900/40 flex flex-col items-center justify-center">
          <span className="text-[10px] text-amber-400 font-mono uppercase tracking-wider font-semibold">
            False Positive (FP)
          </span>
          <span className="text-2xl font-bold font-mono text-slate-100 mt-1">{matrix.fp}</span>
          <span className="text-[10px] font-mono text-slate-400 mt-0.5">
            {((matrix.fp / total) * 100).toFixed(1)}% &bull; False Alarm
          </span>
        </div>

        {/* FN */}
        <div className="p-3.5 rounded-md bg-[#1f1214] border border-red-900/60 flex flex-col items-center justify-center">
          <span className="text-[10px] text-red-400 font-mono uppercase tracking-wider font-semibold">
            False Negative (FN)
          </span>
          <span className="text-2xl font-bold font-mono text-slate-100 mt-1">{matrix.fn}</span>
          <span className="text-[10px] font-mono text-slate-400 mt-0.5">
            {((matrix.fn / total) * 100).toFixed(1)}% &bull; Missed Event
          </span>
        </div>

        {/* TN */}
        <div className="p-3.5 rounded-md bg-[#131924] border border-[#222b3b] flex flex-col items-center justify-center">
          <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider font-semibold">
            True Negative (TN)
          </span>
          <span className="text-2xl font-bold font-mono text-slate-100 mt-1">{matrix.tn}</span>
          <span className="text-[10px] font-mono text-slate-400 mt-0.5">
            {((matrix.tn / total) * 100).toFixed(1)}% &bull; Normal Operation
          </span>
        </div>
      </div>
    </div>
  );
};
