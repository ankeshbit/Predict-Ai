import React, { useState } from 'react';
import type { Machine } from '../types';
import { Badge } from '../components/ui/Badge';
import { Search, LayoutGrid, List, ArrowRight, SlidersHorizontal, ExternalLink } from 'lucide-react';

interface FleetPageProps {
  machines: Machine[];
  onSelectMachine: (machineId: string) => void;
}

export const FleetPage: React.FC<FleetPageProps> = ({ machines, onSelectMachine }) => {
  const [search, setSearch] = useState('');
  const [selectedHealthBand, setSelectedHealthBand] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');

  const filteredMachines = machines.filter((m) => {
    const matchesSearch =
      m.machineCode.toLowerCase().includes(search.toLowerCase()) ||
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.location.toLowerCase().includes(search.toLowerCase());
    const matchesBand = selectedHealthBand === 'all' || m.healthBand === selectedHealthBand;
    const matchesStatus = selectedStatus === 'all' || m.operationalStatus === selectedStatus;
    return matchesSearch && matchesBand && matchesStatus;
  });

  return (
    <div className="space-y-5 animate-in fade-in duration-150">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1 border-b border-[#1f2838]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-slate-100 tracking-tight">Fleet Asset Inventory</h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#161f2e] text-slate-400 border border-[#233147]">
              {machines.length} monitored turbofans
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Active telemetry streaming, rolling anomaly detection, and calibrated failure risk across all units.
          </p>
        </div>

        {/* View Switcher */}
        <div className="flex items-center gap-1 p-1 bg-[#111620] border border-[#1f2838] rounded-md self-start sm:self-auto">
          <button
            onClick={() => setViewMode('table')}
            className={`px-2.5 py-1 rounded text-xs font-mono font-medium flex items-center gap-1.5 cursor-pointer transition-colors ${
              viewMode === 'table'
                ? 'bg-[#1e293b] text-slate-100 border border-[#334155]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <List className="w-3.5 h-3.5" /> Table
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={`px-2.5 py-1 rounded text-xs font-mono font-medium flex items-center gap-1.5 cursor-pointer transition-colors ${
              viewMode === 'grid'
                ? 'bg-[#1e293b] text-slate-100 border border-[#334155]'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <LayoutGrid className="w-3.5 h-3.5" /> Grid
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-2.5 bg-[#111620] border border-[#1f2838] rounded-lg flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between text-xs">
        <div className="relative w-full md:w-80">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Filter by engine code, cell, or type..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8.5 pr-3 py-1.5 rounded-md bg-[#161f2e] border border-[#253246] text-xs text-slate-100 placeholder-slate-500 focus:outline-hidden focus:border-blue-500 font-sans"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-mono text-slate-400 uppercase flex items-center gap-1">
            <SlidersHorizontal className="w-3 h-3 text-slate-500" /> Band:
          </span>
          {['all', 'Excellent', 'Healthy', 'Warning', 'Poor', 'Critical'].map((band) => (
            <button
              key={band}
              onClick={() => setSelectedHealthBand(band)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono border transition-colors cursor-pointer ${
                selectedHealthBand === band
                  ? 'bg-blue-950/60 text-blue-300 border-blue-700/60 font-semibold'
                  : 'bg-[#141b27] text-slate-400 border-[#222c3e] hover:text-slate-200'
              }`}
            >
              {band === 'all' ? 'All' : band}
            </button>
          ))}

          <span className="text-[11px] font-mono text-slate-400 uppercase ml-2">Status:</span>
          {['all', 'active', 'maintenance'].map((status) => (
            <button
              key={status}
              onClick={() => setSelectedStatus(status)}
              className={`px-2 py-0.5 rounded text-[11px] font-mono border uppercase transition-colors cursor-pointer ${
                selectedStatus === status
                  ? 'bg-blue-950/60 text-blue-300 border-blue-700/60 font-semibold'
                  : 'bg-[#141b27] text-slate-400 border-[#222c3e] hover:text-slate-200'
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Main Display: Table or Grid */}
      {viewMode === 'table' ? (
        <div className="rounded-lg border border-[#1f2838] bg-[#111620] overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#1f2838] bg-[#0d121a] text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                  <th className="py-2.5 px-4 font-semibold">Machine ID</th>
                  <th className="py-2.5 px-4 font-semibold">Asset Name &amp; Cell</th>
                  <th className="py-2.5 px-4 font-semibold">Status</th>
                  <th className="py-2.5 px-4 font-semibold w-40">Health Indicator</th>
                  <th className="py-2.5 px-4 font-semibold">P(Fail) H=30</th>
                  <th className="py-2.5 px-4 font-semibold">Anomaly Score</th>
                  <th className="py-2.5 px-4 font-semibold">Current Cycle</th>
                  <th className="py-2.5 px-4 font-semibold">Reliability</th>
                  <th className="py-2.5 px-4 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#182130]">
                {filteredMachines.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="py-12 text-center text-slate-500 font-mono text-xs">
                      No machines found in fleet registry.
                    </td>
                  </tr>
                ) : (
                  filteredMachines.map((m) => {
                    const isCritical = m.riskLevel === 'Critical';

                    return (
                      <tr
                        key={m.id}
                        onClick={() => onSelectMachine(m.id)}
                        className={`group cursor-pointer transition-colors ${
                          isCritical ? 'bg-red-950/10 hover:bg-red-950/20' : 'hover:bg-[#141b27]'
                        }`}
                      >
                        <td className="py-3 px-4 whitespace-nowrap font-mono font-semibold text-slate-100 group-hover:text-blue-400 transition-colors">
                          {m.machineCode}
                        </td>

                        <td className="py-3 px-4">
                          <div className="text-slate-200 font-medium">{m.name}</div>
                          <div className="text-[11px] text-slate-400 font-mono">{m.location}</div>
                        </td>

                        <td className="py-3 px-4 whitespace-nowrap">
                          <Badge value={m.operationalStatus} size="sm" />
                        </td>

                        <td className="py-3 px-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-slate-100">
                              {m.healthIndicator != null ? m.healthIndicator : '—'}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">/ 100</span>
                            <Badge value={m.healthBand} size="sm" />
                          </div>
                          <div className="w-28 h-1 bg-[#1a2333] rounded-full mt-1.5 overflow-hidden">
                            <div
                              className={`h-full ${
                                (m.healthIndicator ?? 0) >= 80
                                  ? 'bg-emerald-500'
                                  : (m.healthIndicator ?? 0) >= 60
                                  ? 'bg-amber-500'
                                  : 'bg-red-500'
                              }`}
                              style={{ width: `${Math.max(0, Math.min(100, m.healthIndicator ?? 0))}%` }}
                            />
                          </div>
                        </td>

                        <td className="py-3 px-4 whitespace-nowrap font-mono font-bold text-blue-400">
                          {m.failureProbability != null ? `${(m.failureProbability * 100).toFixed(0)}%` : '—'}
                          <span className="text-[10px] text-slate-400 font-normal ml-1 font-mono">
                            ({m.riskLevel})
                          </span>
                        </td>

                        <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-300">
                          {m.anomalyScore != null ? m.anomalyScore.toFixed(3) : '—'}
                          <span className={`ml-1 text-[10px] ${m.anomalyStatus === 'anomaly' ? 'text-red-400' : 'text-slate-400'}`}>
                            &bull; {m.anomalyStatus}
                          </span>
                        </td>

                        <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-300">
                          #{m.currentCycle != null ? m.currentCycle : '—'}
                        </td>

                        <td className="py-3 px-4 whitespace-nowrap">
                          <Badge value={m.reliabilityStatus} size="sm" />
                        </td>

                        <td className="py-3 px-4 whitespace-nowrap text-right">
                          <button
                            type="button"
                            onClick={() => onSelectMachine(m.id)}
                            className="text-xs text-blue-400 hover:text-blue-300 font-medium inline-flex items-center gap-1 cursor-pointer"
                          >
                            Workstation <ExternalLink className="w-3 h-3" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : filteredMachines.length === 0 ? (
        <div className="py-12 text-center rounded-lg border border-[#1f2838] bg-[#111620] text-slate-500 font-mono text-xs">
          No machines found in fleet registry.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {filteredMachines.map((m) => {
            const isCritical = m.riskLevel === 'Critical';

            return (
              <div
                key={m.id}
                onClick={() => onSelectMachine(m.id)}
                className={`p-3.5 rounded-lg border transition-all cursor-pointer flex flex-col justify-between ${
                  isCritical
                    ? 'border-red-900/60 bg-red-950/15 hover:border-red-700'
                    : 'border-[#1f2838] bg-[#111620] hover:border-[#2b3a50] hover:bg-[#141b27]'
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-mono font-bold text-sm text-slate-100">{m.machineCode}</div>
                      <div className="text-[11px] text-slate-400 line-clamp-1">{m.name}</div>
                    </div>
                    <Badge value={m.operationalStatus} size="sm" />
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#1d2638] text-xs">
                    <div className="p-2 rounded bg-[#0e141f] border border-[#1b2536]">
                      <div className="text-[10px] text-slate-400 uppercase font-mono">Health Score</div>
                      <div className="font-mono font-bold text-base text-slate-100 mt-0.5">
                        {m.healthIndicator != null ? m.healthIndicator : '—'}{' '}
                        <span className="text-[10px] text-slate-400 font-normal">/100</span>
                      </div>
                      <Badge value={m.healthBand} size="sm" className="mt-1" />
                    </div>

                    <div className="p-2 rounded bg-[#0e141f] border border-[#1b2536]">
                      <div className="text-[10px] text-slate-400 uppercase font-mono">P(Fail) H=30</div>
                      <div className="font-mono font-bold text-base text-blue-400 mt-0.5">
                        {m.failureProbability != null ? `${(m.failureProbability * 100).toFixed(0)}%` : '—'}
                      </div>
                      <Badge value={m.riskLevel} size="sm" className="mt-1" />
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1">
                    <span>Cycle: #{m.currentCycle != null ? m.currentCycle : '—'}</span>
                    <Badge value={m.reliabilityStatus} size="sm" />
                  </div>
                </div>

                <div className="mt-3 pt-2.5 border-t border-[#1d2638] flex items-center justify-between text-xs">
                  <span className="text-slate-400 text-[11px] font-mono truncate max-w-[120px]">{m.location}</span>
                  <span className="text-blue-400 hover:text-blue-300 font-medium inline-flex items-center gap-1">
                    Inspect <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
