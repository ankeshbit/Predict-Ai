import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceArea,
} from 'recharts';
import type { SensorReading } from '../../types';

interface SensorLineChartProps {
  data: SensorReading[];
  availableSensors?: Array<{ id: keyof SensorReading; label: string; unit: string; color: string }>;
}

const DEFAULT_SENSORS: Array<{ id: keyof SensorReading; label: string; unit: string; color: string }> = [
  { id: 'sensor_11', label: 'sensor_11', unit: 'HPC Outlet Temp (°R)', color: '#38bdf8' },
  { id: 'sensor_9', label: 'sensor_9', unit: 'Physical Core Speed (rpm)', color: '#fbbf24' },
  { id: 'sensor_4', label: 'sensor_4', unit: 'LPT Outlet Temp (°R)', color: '#f472b6' },
  { id: 'sensor_12', label: 'sensor_12', unit: 'Corrected Core Speed (rpm)', color: '#34d399' },
  { id: 'sensor_2', label: 'sensor_2', unit: 'LPC Outlet Temp (°R)', color: '#a78bfa' },
  { id: 'sensor_7', label: 'sensor_7', unit: 'HPT Coolant Bleed (psia)', color: '#fb923c' },
];

export const SensorLineChart: React.FC<SensorLineChartProps> = ({
  data = [],
  availableSensors = DEFAULT_SENSORS,
}) => {
  const [selectedSensor, setSelectedSensor] = useState<keyof SensorReading>('sensor_11');

  const activeSensor = availableSensors.find((s) => s.id === selectedSensor) || availableSensors[0];

  // Anomaly episode boundaries
  const anomalyPoints = data.filter((d) => d.isAnomaly);
  const anomalyStart = anomalyPoints.length > 0 ? anomalyPoints[0].cycle : null;
  const anomalyEnd = anomalyPoints.length > 0 ? anomalyPoints[anomalyPoints.length - 1].cycle : null;

  return (
    <div className="space-y-3">
      {/* Sensor Channel Selectors & Legend */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold mr-1">
            Channels:
          </span>
          {availableSensors.map((sensor) => {
            const isSelected = selectedSensor === sensor.id;
            return (
              <button
                key={sensor.id as string}
                onClick={() => setSelectedSensor(sensor.id)}
                className={`px-2 py-1 text-xs font-mono rounded transition-colors cursor-pointer border ${
                  isSelected
                    ? 'bg-[#1b2537] text-white border-blue-500 font-semibold'
                    : 'bg-[#10151f] text-slate-400 border-[#20293a] hover:text-slate-200 hover:border-slate-600'
                }`}
              >
                <span
                  className="inline-block w-2 h-2 rounded-xs mr-1.5"
                  style={{ backgroundColor: sensor.color }}
                />
                {sensor.id as string}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-4 text-[11px] font-mono text-slate-400">
          {anomalyStart && (
            <div className="flex items-center gap-1.5 text-rose-400">
              <span className="w-2.5 h-2.5 rounded-xs bg-rose-950 border border-rose-500/80" />
              <span>Anomaly Window (C{anomalyStart}–C{anomalyEnd})</span>
            </div>
          )}
          <div className="flex items-center gap-1.5 text-amber-400">
            <span className="w-2 h-2 rotate-45 bg-amber-400" />
            <span>Imputed (Missing)</span>
          </div>
        </div>
      </div>

      {/* Main Analytical Chart */}
      <div className="h-80 w-full p-3 bg-[#0d121a] border border-[#20293a] rounded-md">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 12, right: 15, left: 10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="2 2" stroke="#192230" vertical={false} />
            <XAxis
              dataKey="cycle"
              stroke="#475569"
              fontSize={11}
              tickLine={false}
              tick={{ fill: '#64748b', fontFamily: 'monospace' }}
              label={{
                value: 'Operating Cycles (Contiguous Time-Series)',
                position: 'insideBottom',
                offset: -12,
                fill: '#64748b',
                fontSize: 11,
                fontFamily: 'monospace',
              }}
            />
            <YAxis
              stroke="#475569"
              fontSize={11}
              tickLine={false}
              tick={{ fill: '#64748b', fontFamily: 'monospace' }}
              domain={['auto', 'auto']}
              label={{
                value: `${activeSensor.label} [${activeSensor.unit}]`,
                angle: -90,
                position: 'insideLeft',
                fill: '#64748b',
                fontSize: 11,
                fontFamily: 'monospace',
              }}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  const item = payload[0].payload as SensorReading;
                  return (
                    <div className="bg-[#121824] border border-[#273448] p-2.5 rounded shadow-xl text-xs space-y-1 font-mono">
                      <div className="text-slate-400 font-semibold border-b border-[#20293a] pb-1">
                        Cycle {label}
                      </div>
                      <div className="text-slate-200">
                        {String(selectedSensor)}:{' '}
                        <strong className="text-white tabular-nums">{payload[0].value}</strong>
                      </div>
                      {item.isAnomaly && (
                        <div className="text-rose-400 text-[10px] font-bold">
                          ● Flagged Anomaly Point
                        </div>
                      )}
                      {item.isImputed && (
                        <div className="text-amber-400 text-[10px] font-bold">
                          ◆ Imputed Reading (Linear)
                        </div>
                      )}
                    </div>
                  );
                }
                return null;
              }}
            />

            {/* Anomaly Episode Background Reference Area */}
            {anomalyStart && anomalyEnd && (
              <ReferenceArea
                x1={anomalyStart}
                x2={anomalyEnd}
                fill="#be123c"
                fillOpacity={0.12}
                stroke="#e11d48"
                strokeOpacity={0.3}
              />
            )}

            <Line
              type="monotone"
              dataKey={selectedSensor as string}
              stroke={activeSensor.color}
              strokeWidth={1.5}
              isAnimationActive={false}
              dot={(props: any) => {
                const { cx, cy, payload } = props;
                if (payload.isImputed) {
                  return (
                    <polygon
                      key={`imp-${props.index}`}
                      points={`${cx},${cy - 4} ${cx + 4},${cy} ${cx},${cy + 4} ${cx - 4},${cy}`}
                      fill="#f59e0b"
                      stroke="#78350f"
                    />
                  );
                }
                if (payload.isAnomaly) {
                  return (
                    <circle
                      key={`anom-${props.index}`}
                      cx={cx}
                      cy={cy}
                      r={3}
                      fill="#ef4444"
                      stroke="#7f1d1d"
                      strokeWidth={1}
                    />
                  );
                }
                return null;
              }}
              activeDot={{ r: 4, fill: activeSensor.color }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
