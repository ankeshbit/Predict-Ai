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

interface CalibrationPlotProps {
  data: Array<{ meanPredictedValue: number; fractionOfPositives: number }>;
  brierScore: number;
}

export const CalibrationPlot: React.FC<CalibrationPlotProps> = ({ data, brierScore }) => {
  return (
    <div className="p-4 bg-[#111620] border border-[#1f2838] rounded-lg space-y-3">
      <div className="flex items-center justify-between text-xs">
        <div>
          <h4 className="font-semibold text-slate-100 font-mono">Calibration Curve (Reliability Diagram)</h4>
          <p className="text-[11px] text-slate-400">Mean Predicted Failure Probability vs Empirical Observed Fraction</p>
        </div>
        <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/60">
          Brier Score: {brierScore}
        </span>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 15, left: -15, bottom: 15 }}>
            <CartesianGrid strokeDasharray="2 2" stroke="#1c2534" />
            <XAxis
              dataKey="meanPredictedValue"
              stroke="#64748b"
              fontSize={10}
              domain={[0, 1]}
              tickLine={false}
              label={{ value: 'Mean Predicted Probability', position: 'insideBottom', offset: -10, fill: '#64748b', fontSize: 10 }}
            />
            <YAxis
              dataKey="fractionOfPositives"
              stroke="#64748b"
              fontSize={10}
              domain={[0, 1]}
              tickLine={false}
              label={{ value: 'Empirical Positives', angle: -90, position: 'insideLeft', offset: 20, fill: '#64748b', fontSize: 10 }}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  return (
                    <div className="bg-[#0b1018] border border-[#222d3f] p-2 rounded text-xs font-mono shadow-md">
                      <p className="text-slate-400 text-[10px]">Predicted: <strong className="text-slate-200">{d.meanPredictedValue}</strong></p>
                      <p className="text-emerald-400 text-[10px]">Observed: <strong className="text-slate-200">{d.fractionOfPositives}</strong></p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="#475569" strokeDasharray="3 3" />
            <Line
              type="monotone"
              dataKey="fractionOfPositives"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 3, fill: '#10b981' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
