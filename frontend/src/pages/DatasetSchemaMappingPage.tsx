import React, { useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import {
  ArrowLeft,
  CheckCircle2,
  Upload,
  ShieldAlert,
  FileCheck,
  ArrowRight,
} from 'lucide-react';

interface DatasetSchemaMappingProps {
  initialDatasetId?: string;
  onBack: () => void;
  onIngestSuccess: () => void;
}

export const DatasetSchemaMappingPage: React.FC<DatasetSchemaMappingProps> = ({
  initialDatasetId = 'ds-ai4i-sample',
  onBack,
  onIngestSuccess,
}) => {
  const [activeStep, setActiveStep] = useState<number>(initialDatasetId === 'ds-ai4i-sample' ? 4 : 2);
  const [selectedDataset, setSelectedDataset] = useState<string>(initialDatasetId);

  const isAI4I = selectedDataset === 'ds-ai4i-sample';

  // Compatibility matrix checks (Section 13)
  const compatibilityChecks = isAI4I
    ? [
        {
          check: 'Sequence Axis',
          status: 'error',
          expected: 'Integer cycle sequence axis per unit',
          found: 'Single static row index (no cycle axis)',
          howToFix: 'Ensure upload contains sequential run-to-failure cycle column.',
        },
        {
          check: 'Entity Identifier',
          status: 'error',
          expected: 'unit_id column grouping time series',
          found: 'UDI (synthetic record index)',
          howToFix: 'Map column representing physical machine instances.',
        },
        {
          check: 'Feature Schema Alignment',
          status: 'error',
          expected: '24 features matching model input_features (sensor_1..21)',
          found: 'Incompatible tabular format with unrecognized column headers',
          howToFix: 'Map headers to canonical sensor_1..21 or register a valid adapter.',
        },
        {
          check: 'Adapter Specification',
          status: 'error',
          expected: 'adapter_key = "cmapss_fd001_csv"',
          found: 'Tabular single-record format',
          howToFix: 'Use a compatible multi-variate run-to-failure adapter.',
        },
      ]
    : [
        {
          check: 'Sequence Axis',
          status: 'passed',
          expected: 'Integer cycle sequence axis present',
          found: 'cycle (1 to 362 continuous)',
          howToFix: 'Passed',
        },
        {
          check: 'Entity Identifier',
          status: 'passed',
          expected: 'unit_id grouping time series',
          found: 'unit_id present (100 engines)',
          howToFix: 'Passed',
        },
        {
          check: 'Feature Schema Alignment',
          status: 'passed',
          expected: '24 features matching model input_features',
          found: '24 matched canonical channels',
          howToFix: 'Passed',
        },
        {
          check: 'Training Baseline Ranges',
          status: 'passed',
          expected: 'Feature medians within training p1-p99',
          found: 'All channels within nominal reference boundaries',
          howToFix: 'Passed',
        },
      ];

  const hasErrors = compatibilityChecks.some((c) => c.status === 'error');

  const schemaColumns = [
    { datasetCol: 'unit_number', canonical: 'unit_id', type: 'integer', status: 'Mapped' },
    { datasetCol: 'time_in_cycles', canonical: 'cycle', type: 'integer (sequence)', status: 'Mapped' },
    { datasetCol: 'setting_1', canonical: 'op_setting_1', type: 'float', status: 'Mapped' },
    { datasetCol: 'setting_2', canonical: 'op_setting_2', type: 'float', status: 'Mapped' },
    { datasetCol: 'raw_col_2', canonical: 'sensor_2', type: 'float', status: 'Mapped' },
    { datasetCol: 'raw_col_11', canonical: 'sensor_11', type: 'float', status: 'Mapped' },
    { datasetCol: 'raw_col_4', canonical: 'sensor_4', type: 'float', status: 'Mapped' },
    { datasetCol: 'raw_col_9', canonical: 'sensor_9', type: 'float', status: 'Mapped' },
    { datasetCol: 'extra_col_aux', canonical: '—', type: 'unrecognized', status: 'Optional' },
  ];

  return (
    <div className="space-y-5 animate-in fade-in duration-100 select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-[#111621] border border-[#1e2636] rounded-md">
        <div className="space-y-0.5">
          <button
            onClick={onBack}
            className="text-xs font-mono text-slate-400 hover:text-white flex items-center gap-1 cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Datasets
          </button>
          <h1 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
            Dataset Ingestion & Compatibility Gate
          </h1>
          <p className="text-[11px] text-slate-400">
            PRD §FR-5 Schema Mapping &bull; PRD §FR-6 Compatibility Verification Matrix
          </p>
        </div>

        {/* Dataset sample selector */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-slate-500">Sample:</span>
          <select
            value={selectedDataset}
            onChange={(e) => {
              setSelectedDataset(e.target.value);
              setActiveStep(4);
            }}
            className="bg-[#0b0e14] border border-[#20293a] rounded px-2.5 py-1 text-xs font-mono text-slate-200"
          >
            <option value="ds-ai4i-sample">AI4I 2020 (Demonstrates Incompatible Blocking)</option>
            <option value="ds-fd001-demo">C-MAPSS FD001 (Compatible Time-Series)</option>
          </select>
        </div>
      </div>

      {/* Step Indicators: Upload → Validate → Map Schema → Preview → Confirm */}
      <div className="grid grid-cols-4 gap-1.5 text-xs font-mono">
        {[
          { num: 1, label: '1. Upload CSV' },
          { num: 2, label: '2. Schema Mapping' },
          { num: 3, label: '3. Data Validation' },
          { num: 4, label: '4. Compatibility Gate' },
        ].map((step) => {
          const isCurrent = activeStep === step.num;
          const isDone = activeStep > step.num;

          return (
            <button
              key={step.num}
              onClick={() => setActiveStep(step.num)}
              className={`p-2.5 rounded border text-left transition-colors cursor-pointer ${
                isCurrent
                  ? 'bg-[#182334] border-blue-500 text-white font-semibold'
                  : isDone
                  ? 'bg-[#101620] border-emerald-900/60 text-emerald-400'
                  : 'bg-[#0c1018] border-[#1e2636] text-slate-500'
              }`}
            >
              <div className="flex items-center justify-between">
                <span>{step.label}</span>
                {isDone && <span className="text-[10px] text-emerald-400">✓</span>}
              </div>
            </button>
          );
        })}
      </div>

      {/* Step 4: Compatibility Gate (Expected / Found / How to fix) */}
      {activeStep === 4 && (
        <div className="space-y-4">
          {hasErrors ? (
            <div className="p-3.5 rounded bg-rose-950/40 border border-rose-800/80 flex items-start gap-3">
              <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="space-y-1 text-xs">
                <div className="font-bold text-white font-mono uppercase">
                  This dataset is not compatible with the selected model (HTTP 409)
                </div>
                <p className="text-rose-200/90 leading-relaxed font-sans">
                  Inference is strictly blocked. The dataset cannot be scored against active model <code className="font-mono text-rose-300">LightGBM-FD001-v1.2</code> because structural time-series requirements failed.
                </p>
              </div>
            </div>
          ) : (
            <div className="p-3.5 rounded bg-emerald-950/40 border border-emerald-800/80 flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div className="space-y-1 text-xs">
                <div className="font-bold text-white font-mono uppercase">
                  Dataset Passed Compatibility Gate
                </div>
                <p className="text-emerald-200/90 leading-relaxed font-sans">
                  All 11 verification checks passed. Schema, sequence structure, and numeric reference boundaries match model specifications.
                </p>
              </div>
            </div>
          )}

          {/* Actionable Expected / Found / How to Fix Table */}
          <Card
            title="Model Compatibility Verification Matrix"
            subtitle="Verified against model card input_features and stored preprocessing transform"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse font-mono tabular-nums">
                <thead>
                  <tr className="border-b border-[#20293a] bg-[#111721] text-[10px] text-slate-400 uppercase tracking-wider">
                    <th className="py-2 px-3">Rule / Constraint</th>
                    <th className="py-2 px-3">Status</th>
                    <th className="py-2 px-3">Expected (Model Contract)</th>
                    <th className="py-2 px-3">Found in Dataset</th>
                    <th className="py-2 px-3 font-sans">How to Fix (Actionable)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#18212e]">
                  {compatibilityChecks.map((item, idx) => (
                    <tr key={idx} className="hover:bg-[#151c27] transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-slate-200">{item.check}</td>
                      <td className="py-2.5 px-3">
                        {item.status === 'passed' ? (
                          <span className="text-[10px] text-emerald-400 font-bold uppercase">
                            ✓ Passed
                          </span>
                        ) : (
                          <span className="text-[10px] text-rose-400 font-bold uppercase">
                            ✕ Failed
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 text-[11px]">{item.expected}</td>
                      <td className="py-2.5 px-3 text-slate-300 text-[11px]">{item.found}</td>
                      <td className="py-2.5 px-3 text-slate-300 font-sans text-xs">{item.howToFix}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 pt-3 border-t border-[#1d2634] flex items-center justify-between">
              <span className="text-[11px] font-mono text-slate-500">
                Target Adapter: <code className="text-slate-300 font-bold">cmapss_fd001_csv</code>
              </span>

              {hasErrors ? (
                <Button variant="danger" size="xs" disabled>
                  Inference Blocked (Fix Matrix Errors)
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="xs"
                  onClick={onIngestSuccess}
                  icon={<FileCheck className="w-3.5 h-3.5" />}
                >
                  Confirm Ingestion & Proceed to Fleet
                </Button>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Step 2: Two-Column Schema Mapping (Section 13) */}
      {activeStep === 2 && (
        <Card
          title="Two-Column Schema Mapping"
          subtitle="Dataset Column &darr; Canonical Adapter Field (Mapped, Missing, Invalid, Optional)"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse font-mono">
              <thead>
                <tr className="border-b border-[#20293a] bg-[#111721] text-[10px] text-slate-400 uppercase tracking-wider">
                  <th className="py-2 px-3">Source Dataset Column</th>
                  <th className="py-2 px-3">Canonical Field (Adapter)</th>
                  <th className="py-2 px-3">Data Type</th>
                  <th className="py-2 px-3">Mapping Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#18212e]">
                {schemaColumns.map((col, idx) => (
                  <tr key={idx} className="hover:bg-[#151c27]">
                    <td className="py-2 px-3 font-semibold text-slate-200">{col.datasetCol}</td>
                    <td className="py-2 px-3 text-blue-400 font-semibold">{col.canonical}</td>
                    <td className="py-2 px-3 text-slate-400 text-[11px]">{col.type}</td>
                    <td className="py-2 px-3">
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                          col.status === 'Mapped'
                            ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
                            : 'bg-slate-900 text-slate-400 border border-slate-700'
                        }`}
                      >
                        {col.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 pt-3 border-t border-[#1d2634] flex justify-end">
            <Button
              variant="primary"
              size="xs"
              onClick={() => setActiveStep(3)}
              icon={<ArrowRight className="w-3 h-3" />}
            >
              Save Mapping & Validate
            </Button>
          </div>
        </Card>
      )}

      {/* Step 3: Validation */}
      {activeStep === 3 && (
        <Card title="Pre-Ingestion Validation Report" subtitle="Integrity and format checks">
          <div className="space-y-3 text-xs">
            <div className="p-3 rounded bg-emerald-950/30 border border-emerald-800/40 text-emerald-300 font-mono text-[11px]">
              ✓ Verified: 20,631 records &bull; Zero NaN or infinite values &bull; Contiguous integer cycles 1..362
            </div>
            <div className="flex justify-end pt-2">
              <Button
                variant="primary"
                size="xs"
                onClick={() => setActiveStep(4)}
                icon={<ArrowRight className="w-3 h-3" />}
              >
                Run Model Compatibility Gate
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Step 1: Upload */}
      {activeStep === 1 && (
        <Card title="Upload Dataset File" subtitle="Accepts space-delimited C-MAPSS or standard tabular CSV">
          <div className="p-8 border border-dashed border-[#242e40] rounded text-center space-y-2 bg-[#0c1018]">
            <Upload className="w-6 h-6 text-slate-400 mx-auto" />
            <div className="text-xs font-semibold text-slate-200">
              Drag and drop telemetry CSV or select file
            </div>
            <p className="text-[11px] text-slate-500 font-mono">
              Accepted formats: NASA C-MAPSS FD001 space-separated values
            </p>
            <div className="pt-2">
              <Button variant="secondary" size="xs" onClick={() => setActiveStep(2)}>
                Load C-MAPSS FD001 Sample
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
