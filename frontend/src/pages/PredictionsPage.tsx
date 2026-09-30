import React, { useState } from 'react';
import type { Machine, Role } from '../types';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Play, ArrowRight, Filter } from 'lucide-react';

interface PredictionsPageProps {
  machines: Machine[];
  currentUserRole: Role;
  onSelectMachine: (machineId: string) => void;
}

export const PredictionsPage: React.FC<PredictionsPageProps> = ({
  machines,
  currentUserRole,
  onSelectMachine,
}) => {
  const [isScoringRunning, setIsScoringRunning] = useState(false);
  const [scoringProgress, setScoringProgress] = useState(100);
  const [selectedRisk, setSelectedRisk] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');

  const handleTriggerScoring = () => {
    setIsScoringRunning(true);
    setScoringProgress(20);
    setTimeout(() => setScoringProgress(60), 300);
    setTimeout(() => setScoringProgress(90), 600);
    setTimeout(() => {
      setScoringProgress(100);
      setIsScoringRunning(false);
    }, 900);
  };

  const filtered = machines.filter((m) => {
    const matchesRisk = selectedRisk === 'all' || m.riskLevel === selectedRisk;
    const matchesStatus = selectedStatus === 'all' || m.operationalStatus === selectedStatus;
    return matchesRisk && matchesStatus;
  });

  return (
    <div className="space-y-5 animate-in fade-in duration-100 select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-[#111621] border border-[#1e2636] rounded-md">
        <div>
          <h1 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
            Model Inference & Prediction Logs
          </h1>
          <p className="text-[11px] text-slate-400">
            PRD §FR-7 Background Scoring Runs &bull; Calibrated binary failure forecasts (Horizon H = 30)
          </p>
        </div>

        {currentUserRole === 'admin' && (
          <Button
            variant="primary"
            size="xs"
            onClick={handleTriggerScoring}
            isLoading={isScoringRunning}
            icon={<Play className="w-3 h-3 fill-current" />}
          >
            {isScoringRunning ? `Scoring (${scoringProgress}%)...` : 'Execute Scoring Run'}
          </Button>
        )}
      </div>

      {/* Scoring Progress Banner */}
      {isScoringRunning && (
        <div className="p-3 rounded bg-[#101928] border border-blue-900/60 space-y-1.5 text-xs font-mono">
          <div className="flex justify-between text-blue-300">
            <span>Executing inference on active models...</span>
            <span>{scoringProgress}%</span>
          </div>
          <div className="h-1.5 w-full bg-[#0b0e14] rounded-xs overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-xs transition-all duration-300"
              style={{ width: `${scoringProgress}%` }}
            />
          </div>
        </div>
      )}

      {/* Analytical Filter Strip */}
      <div className="p-2.5 bg-[#111621] border border-[#1e2636] rounded-md flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-slate-500 flex items-center gap-1 text-[11px]">
            <Filter className="w-3 h-3" /> Risk:
          </span>
          {['all', 'Low', 'Medium', 'High', 'Critical'].map((risk) => (
            <button
              key={risk}
              onClick={() => setSelectedRisk(risk)}
              className={`px-2 py-0.5 rounded text-[11px] border transition-colors cursor-pointer ${
                selectedRisk === risk
                  ? 'bg-[#1b2536] text-white border-blue-500 font-semibold'
                  : 'bg-[#0c1018] text-slate-400 border-[#1f2838] hover:text-slate-200'
              }`}
            >
              {risk}
            </button>
          ))}

          <span className="text-slate-500 ml-2 text-[11px]">Status:</span>
          {['all', 'active', 'maintenance'].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-2 py-0.5 rounded text-[11px] uppercase border transition-colors cursor-pointer ${
                selectedStatus === st
                  ? 'bg-[#1b2536] text-white border-blue-500 font-semibold'
                  : 'bg-[#0c1018] text-slate-400 border-[#1f2838] hover:text-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <span className="text-[11px] text-slate-500">
          Showing {filtered.length} of {machines.length} scored machines
        </span>
      </div>

      {/* Dense Analytical Predictions Table */}
      <Card
        title="Persisted Predictions Log"
        subtitle="Idempotent scored records &bull; Verified feature inputs &bull; Full lineage hash"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse font-mono tabular-nums">
            <thead>
              <tr className="border-b border-[#20293a] bg-[#111721] text-[10px] text-slate-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">Machine Code</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Health Ind.</th>
                <th className="py-2.5 px-3">Failure Prob. [H=30]</th>
                <th className="py-2.5 px-3">Risk Level</th>
                <th className="py-2.5 px-3">Anomaly Severity</th>
                <th className="py-2.5 px-3">Reliability</th>
                <th className="py-2.5 px-3">Cycle Axis</th>
                <th className="py-2.5 px-3 text-right">Lineage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#18212e]">
              {filtered.map((m) => (
                <tr
                  key={m.id}
                  onClick={() => onSelectMachine(m.id)}
                  className="hover:bg-[#161d29] transition-colors cursor-pointer"
                >
                  <td className="py-2.5 px-3 font-bold text-slate-100">{m.machineCode}</td>
                  <td className="py-2.5 px-3"><Badge value={m.operationalStatus} size="xs" /></td>
                  <td className="py-2.5 px-3">
                    <span className="text-slate-200 font-bold">{m.healthIndicator}</span>
                    <span className="text-slate-500 text-[10px]"> /100</span>
                  </td>
                  <td className="py-2.5 px-3 font-bold text-slate-100">
                    <span className={m.failureProbability >= 0.5 ? 'text-rose-400' : 'text-slate-200'}>
                      {(m.failureProbability * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="py-2.5 px-3"><Badge value={m.riskLevel} size="xs" /></td>
                  <td className="py-2.5 px-3 text-slate-400">{(m.anomalySeverity * 100).toFixed(0)}%</td>
                  <td className="py-2.5 px-3"><Badge value={m.reliabilityStatus} size="xs" /></td>
                  <td className="py-2.5 px-3 text-slate-400">as of c{m.currentCycle}</td>
                  <td className="py-2.5 px-3 text-right">
                    <span className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1 text-[11px]">
                      View <ArrowRight className="w-3 h-3" />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
