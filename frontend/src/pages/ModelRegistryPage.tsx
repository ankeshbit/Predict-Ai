import React, { useState } from 'react';
import type { ModelVersion } from '../types';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Drawer } from '../components/ui/Drawer';
import {
  Terminal,
  CheckCircle2,
  ArrowRight,
  ChevronRight,
  GitBranch
} from 'lucide-react';

interface ModelRegistryPageProps {
  models: ModelVersion[];
  onViewModelPerformance: () => void;
}

export const ModelRegistryPage: React.FC<ModelRegistryPageProps> = ({
  models,
  onViewModelPerformance,
}) => {
  const [selectedModel, setSelectedModel] = useState<ModelVersion | null>(null);

  return (
    <div className="space-y-5 animate-in fade-in duration-150">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1 border-b border-[#1f2838]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-slate-100 tracking-tight">Model Registry</h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#161f2e] text-slate-400 border border-[#233147]">
              {models.length} registered models
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            PRD §FR-16 Model metadata, deterministic versioning &amp; lineage &bull; Safeguards against ad-hoc client-side training.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={onViewModelPerformance}
          className="text-xs"
        >
          Open ML Evaluation Workspace <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
        </Button>
      </div>

      {/* Operational Protocol Banner */}
      <div className="p-3.5 rounded-lg bg-[#111620] border border-[#1f2838] flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
        <div className="flex items-start gap-2.5">
          <Terminal className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <div className="font-mono text-slate-200 font-semibold text-xs">
              Offline Registration &amp; Promotion Protocol
            </div>
            <p className="text-slate-400 text-[11px]">
              Models are compiled and evaluated strictly in Python environments and registered via authenticated CLI artifacts.
            </p>
          </div>
        </div>

        <code className="text-[11px] font-mono bg-[#0c121b] px-2.5 py-1 rounded text-slate-300 border border-[#1f2b3e] shrink-0">
          python -m app.cli register-model --bundle /artifacts/lgbm_fd001.pkl
        </code>
      </div>

      {/* Professional Model Registry Table (PRD §FR-16 & Section 18) */}
      <div className="rounded-lg border border-[#1f2838] bg-[#111620] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#1f2838] bg-[#0d121a] text-[11px] font-mono text-slate-400 uppercase tracking-wider">
                <th className="py-2.5 px-4 font-semibold">Model Version</th>
                <th className="py-2.5 px-4 font-semibold">Algorithm</th>
                <th className="py-2.5 px-4 font-semibold">Dataset</th>
                <th className="py-2.5 px-4 font-semibold">Dataset Version</th>
                <th className="py-2.5 px-4 font-semibold">Features</th>
                <th className="py-2.5 px-4 font-semibold">Prediction Horizon</th>
                <th className="py-2.5 px-4 font-semibold">Status</th>
                <th className="py-2.5 px-4 font-semibold">Created</th>
                <th className="py-2.5 px-4 font-semibold">Activated</th>
                <th className="py-2.5 px-4 font-semibold text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#182130]">
              {models.map((mod) => {
                const isActive = mod.status === 'active';

                return (
                  <tr
                    key={mod.id}
                    onClick={() => setSelectedModel(mod)}
                    className={`group cursor-pointer transition-colors ${
                      isActive ? 'bg-[#121926] hover:bg-[#151f30]' : 'hover:bg-[#141b27]'
                    }`}
                  >
                    {/* Model Version */}
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-slate-100 group-hover:text-blue-400 transition-colors">
                          {mod.version}
                        </span>
                        {isActive && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-blue-950/80 text-blue-300 border border-blue-700/60 uppercase">
                            ACTIVE
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 font-sans mt-0.5">{mod.name}</div>
                    </td>

                    {/* Algorithm */}
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-300">
                      {mod.modelType}
                    </td>

                    {/* Dataset */}
                    <td className="py-3 px-4 whitespace-nowrap text-slate-300">
                      {mod.trainingDataset}
                    </td>

                    {/* Dataset Version */}
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-400">
                      v1.0 (FD001)
                    </td>

                    {/* Features Count */}
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-300">
                      {mod.modelCard.featuresUsed.length} channels
                    </td>

                    {/* Prediction Horizon */}
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-blue-400 font-medium">
                      {mod.horizon ? `H = ${mod.horizon} ${mod.horizonUnit}` : 'N/A (Anomaly)'}
                    </td>

                    {/* Status */}
                    <td className="py-3 px-4 whitespace-nowrap">
                      <Badge value={mod.status} size="sm" />
                    </td>

                    {/* Created */}
                    <td className="py-3 px-4 whitespace-nowrap font-mono text-slate-400 text-[11px]">
                      {mod.trainingDate}
                    </td>

                    {/* Activated */}
                    <td className="py-3 px-4 whitespace-nowrap">
                      {isActive ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Serving
                        </span>
                      ) : (
                        <span className="text-[11px] font-mono text-slate-400">
                          Standby
                        </span>
                      )}
                    </td>

                    {/* Action */}
                    <td className="py-3 px-4 whitespace-nowrap text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedModel(mod)}
                        className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-[#1f2b3e] cursor-pointer"
                        title="View Model Card"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Model Detail & Model Card Drawer */}
      <Drawer
        isOpen={Boolean(selectedModel)}
        onClose={() => setSelectedModel(null)}
        title="Model Card & Lineage Specifications"
        subtitle={selectedModel ? `${selectedModel.version} — ${selectedModel.name}` : undefined}
        width="md"
      >
        {selectedModel && (
          <div className="space-y-4 text-xs text-slate-300">
            {/* Header info */}
            <div className="p-3 rounded-lg bg-[#0d121a] border border-[#1f2838] flex items-center justify-between">
              <div>
                <span className="text-[10px] font-mono text-slate-400 uppercase">Architecture</span>
                <div className="font-mono font-semibold text-slate-100 text-sm">{selectedModel.modelType}</div>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-mono text-slate-400 uppercase">Production Status</span>
                <div><Badge value={selectedModel.status} size="sm" /></div>
              </div>
            </div>

            {/* Lineage & Git Info */}
            <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] space-y-2 font-mono text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 flex items-center gap-1">
                  <GitBranch className="w-3 h-3 text-slate-400" /> Git Commit:
                </span>
                <span className="text-slate-200">{selectedModel.gitCommit}</span>
              </div>
              <div className="flex items-center justify-between pt-1 border-t border-[#1d2636]">
                <span className="text-slate-400">Decision Threshold:</span>
                <span className="text-blue-400 font-bold">τ = {selectedModel.decisionThreshold}</span>
              </div>
              <div className="flex items-center justify-between pt-1 border-t border-[#1d2636]">
                <span className="text-slate-400">Training Dataset:</span>
                <span className="text-slate-200">{selectedModel.trainingDataset}</span>
              </div>
              <div className="flex items-center justify-between pt-1 border-t border-[#1d2636]">
                <span className="text-slate-400">Registration Date:</span>
                <span className="text-slate-300">{selectedModel.trainingDate}</span>
              </div>
            </div>

            {/* Features Used */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-mono font-semibold text-slate-400 uppercase tracking-wider">
                Input Features ({selectedModel.modelCard.featuresUsed.length})
              </span>
              <div className="p-2.5 rounded-md bg-[#131924] border border-[#222b3b] flex flex-wrap gap-1.5">
                {selectedModel.modelCard.featuresUsed.map((feat) => (
                  <span
                    key={feat}
                    className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#162030] text-slate-300 border border-[#24334a]"
                  >
                    {feat}
                  </span>
                ))}
              </div>
            </div>

            {/* Intended Use & Target Definition */}
            <div className="space-y-2">
              <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] space-y-1">
                <span className="text-[10px] uppercase font-mono text-slate-400 font-semibold">Target Definition</span>
                <p className="text-slate-300 font-sans leading-relaxed">{selectedModel.modelCard.targetDefinition}</p>
              </div>

              <div className="p-3 rounded-md bg-[#131924] border border-[#222b3b] space-y-1">
                <span className="text-[10px] uppercase font-mono text-slate-400 font-semibold">Intended Operational Scope</span>
                <p className="text-slate-300 font-sans leading-relaxed">{selectedModel.modelCard.intendedUse}</p>
              </div>

              <div className="p-3 rounded-md bg-[#18151c] border border-amber-900/40 space-y-1 text-amber-200">
                <span className="text-[10px] uppercase font-mono text-amber-400 font-semibold">Operational Limitations</span>
                <p className="text-slate-300 text-xs font-sans leading-relaxed">{selectedModel.modelCard.limitations}</p>
              </div>
            </div>

            <div className="pt-2 border-t border-[#1f2838] flex justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSelectedModel(null);
                  onViewModelPerformance();
                }}
              >
                Inspect Performance Metrics <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
              </Button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
