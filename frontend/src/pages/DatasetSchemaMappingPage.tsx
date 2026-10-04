/**
 * DatasetSchemaMappingPage — PRD §FR-5 Schema Mapping · PRD §FR-6 Compatibility Gate.
 *
 * All dataset options come from GET /datasets.
 * The compatibility matrix comes from POST /datasets/{id}/compatibility (real backend check).
 * No hardcoded dataset IDs, model names, record counts, or check results.
 */

import React, { useEffect, useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import {
  ArrowLeft,
  CheckCircle2,
  Upload,
  ShieldAlert,
  FileCheck,
  ArrowRight,
  Loader2,
} from 'lucide-react';
import {
  useDatasets,
  useUploadDataset,
  useValidateCompatibility,
  useIngestDataset,
  type CompatibilityCheckItem,
} from '../api';

interface DatasetSchemaMappingProps {
  initialDatasetId?: string;
  onBack: () => void;
  onIngestSuccess: () => void;
}

export const DatasetSchemaMappingPage: React.FC<DatasetSchemaMappingProps> = ({
  initialDatasetId,
  onBack,
  onIngestSuccess,
}) => {
  const [activeStep, setActiveStep] = useState<number>(initialDatasetId ? 4 : 1);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(initialDatasetId ?? null);
  const [compatibilityChecks, setCompatibilityChecks] = useState<CompatibilityCheckItem[] | null>(null);
  const [compatibilityPassed, setCompatibilityPassed] = useState<boolean | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const { data: datasetsData, isLoading: datasetsLoading } = useDatasets({ limit: 50 });
  const datasets = datasetsData?.items ?? [];

  const uploadMutation = useUploadDataset();
  const validateMutation = useValidateCompatibility();
  const ingestMutation = useIngestDataset();

  const selectedDataset = datasets.find((d) => d.id === selectedDatasetId) ?? null;

  // Auto-jump to step 4 if a pre-selected dataset comes in and was already validated
  useEffect(() => {
    if (initialDatasetId && datasets.length > 0) {
      const ds = datasets.find((d) => d.id === initialDatasetId);
      if (ds) {
        setSelectedDatasetId(ds.id);
        setActiveStep(4);
        handleRunCompatibility(ds.id);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialDatasetId, datasets.length]);

  function handleRunCompatibility(datasetId: string) {
    setCompatibilityChecks(null);
    setCompatibilityPassed(null);
    validateMutation.mutate(datasetId, {
      onSuccess: (report) => {
        setCompatibilityChecks(report.checks);
        setCompatibilityPassed(report.passed);
        setActiveStep(4);
      },
      onError: () => {
        setCompatibilityChecks([]);
        setCompatibilityPassed(false);
      },
    });
  }

  function handleUpload() {
    if (!uploadFile) return;
    const form = new FormData();
    form.append('file', uploadFile);
    uploadMutation.mutate(form, {
      onSuccess: (ds) => {
        setSelectedDatasetId(ds.id);
        setActiveStep(2);
      },
    });
  }

  function handleIngest() {
    if (!selectedDatasetId) return;
    ingestMutation.mutate(selectedDatasetId, {
      onSuccess: () => {
        onIngestSuccess();
      },
    });
  }

  const schemaMapping = selectedDataset?.schema_mapping ?? null;

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
            Dataset Ingestion &amp; Compatibility Gate
          </h1>
          <p className="text-[11px] text-slate-400">
            PRD §FR-5 Schema Mapping · PRD §FR-6 Compatibility Verification Matrix
          </p>
        </div>

        {/* Dataset selector from API */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-slate-500">Dataset:</span>
          {datasetsLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
          ) : datasets.length === 0 ? (
            <span className="text-[11px] font-mono text-slate-500">No datasets uploaded yet</span>
          ) : (
            <select
              value={selectedDatasetId ?? ''}
              onChange={(e) => {
                const id = e.target.value;
                setSelectedDatasetId(id || null);
                if (id) {
                  setActiveStep(4);
                  handleRunCompatibility(id);
                }
              }}
              className="bg-[#0b0e14] border border-[#20293a] rounded px-2.5 py-1 text-xs font-mono text-slate-200"
            >
              <option value="">— Select a dataset —</option>
              {datasets.map((ds) => (
                <option key={ds.id} value={ds.id}>
                  {ds.name} ({ds.status})
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Step Indicators */}
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
            <div className="pt-2 space-y-2">
              <input
                type="file"
                accept=".csv,.txt"
                id="upload-csv-input"
                className="text-xs text-slate-300"
                onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              />
              <Button
                variant="secondary"
                size="xs"
                onClick={handleUpload}
                disabled={!uploadFile || uploadMutation.isPending}
              >
                {uploadMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin inline mr-1" />
                ) : null}
                Upload &amp; Continue
              </Button>
              {uploadMutation.isError && (
                <p className="text-xs text-rose-400 font-mono">{String(uploadMutation.error)}</p>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Step 2: Schema Mapping */}
      {activeStep === 2 && (
        <Card
          title="Two-Column Schema Mapping"
          subtitle="Dataset Column → Canonical Adapter Field (Mapped, Missing, Invalid, Optional)"
        >
          {!schemaMapping ? (
            <div className="py-8 text-center text-slate-500 font-mono text-xs">
              Schema mapping not available for this dataset. Upload a valid CSV file first.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead>
                  <tr className="border-b border-[#20293a] bg-[#111721] text-[10px] text-slate-400 uppercase tracking-wider">
                    <th className="py-2 px-3">Source Dataset Column</th>
                    <th className="py-2 px-3">Canonical Field (Adapter)</th>
                    <th className="py-2 px-3">Mapping Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#18212e]">
                  {Object.entries(schemaMapping).map(([src, canonical]) => (
                    <tr key={src} className="hover:bg-[#151c27]">
                      <td className="py-2 px-3 font-semibold text-slate-200">{src}</td>
                      <td className="py-2 px-3 text-blue-400 font-semibold">{canonical || '—'}</td>
                      <td className="py-2 px-3">
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                            canonical
                              ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/60'
                              : 'bg-slate-900 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {canonical ? 'Mapped' : 'Optional / Unmapped'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="mt-4 pt-3 border-t border-[#1d2634] flex justify-end">
            <Button
              variant="primary"
              size="xs"
              onClick={() => setActiveStep(3)}
              icon={<ArrowRight className="w-3 h-3" />}
            >
              Save Mapping &amp; Validate
            </Button>
          </div>
        </Card>
      )}

      {/* Step 3: Validation */}
      {activeStep === 3 && (
        <Card title="Pre-Ingestion Validation Report" subtitle="Integrity and format checks">
          <div className="space-y-3 text-xs">
            {selectedDataset ? (
              <div className="p-3 rounded bg-emerald-950/30 border border-emerald-800/40 text-emerald-300 font-mono text-[11px]">
                ✓ Dataset: <span className="text-white font-bold">{selectedDataset.name}</span>
                {selectedDataset.row_count != null && <> · {selectedDataset.row_count.toLocaleString()} records</>}
                {selectedDataset.unit_count != null && <> · {selectedDataset.unit_count} units</>}
                {' '}· Status: {selectedDataset.status}
              </div>
            ) : (
              <div className="text-slate-500 font-mono text-xs py-4 text-center">
                No dataset selected. Go back to Step 1 to upload.
              </div>
            )}
            <div className="flex justify-end pt-2">
              <Button
                variant="primary"
                size="xs"
                onClick={() => {
                  if (selectedDatasetId) handleRunCompatibility(selectedDatasetId);
                }}
                disabled={!selectedDatasetId || validateMutation.isPending}
                icon={<ArrowRight className="w-3 h-3" />}
              >
                {validateMutation.isPending ? (
                  <Loader2 className="w-3 h-3 animate-spin inline mr-1" />
                ) : null}
                Run Model Compatibility Gate
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Step 4: Compatibility Gate — real backend check results */}
      {activeStep === 4 && (
        <div className="space-y-4">
          {validateMutation.isPending && (
            <div className="p-4 rounded bg-[#131923] border border-[#20293a] text-slate-400 font-mono text-xs flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Running compatibility checks against registered model contract…
            </div>
          )}

          {!validateMutation.isPending && compatibilityChecks != null && (
            <>
              {!compatibilityPassed ? (
                <div className="p-3.5 rounded bg-rose-950/40 border border-rose-800/80 flex items-start gap-3">
                  <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                  <div className="space-y-1 text-xs">
                    <div className="font-bold text-white font-mono uppercase">
                      This dataset is not compatible with the selected model.
                    </div>
                    <p className="text-rose-200/90 leading-relaxed font-sans">
                      Inference is strictly blocked until all failed checks are resolved (HTTP 409 DATASET_INCOMPATIBLE).
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
                      All {compatibilityChecks.filter((c) => c.status === 'passed').length} verification checks passed.
                      Schema, sequence structure, and numeric reference boundaries match model specifications.
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
                      {compatibilityChecks.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="py-6 text-center text-slate-500 font-mono text-xs">
                            No compatibility checks returned by the backend.
                          </td>
                        </tr>
                      ) : (
                        compatibilityChecks.map((item, idx) => (
                          <tr key={idx} className="hover:bg-[#151c27] transition-colors">
                            <td className="py-2.5 px-3 font-semibold text-slate-200">{item.check_name}</td>
                            <td className="py-2.5 px-3">
                              {item.status === 'passed' ? (
                                <span className="text-[10px] text-emerald-400 font-bold uppercase">✓ Passed</span>
                              ) : item.status === 'warning' ? (
                                <span className="text-[10px] text-amber-400 font-bold uppercase">⚠ Warning</span>
                              ) : (
                                <span className="text-[10px] text-rose-400 font-bold uppercase">✕ Failed</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3 text-slate-300 text-[11px]">{item.expected_value}</td>
                            <td className="py-2.5 px-3 text-slate-300 text-[11px]">{item.found_value}</td>
                            <td className="py-2.5 px-3 text-slate-300 font-sans text-xs">{item.how_to_fix}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4 pt-3 border-t border-[#1d2634] flex items-center justify-between">
                  <span className="text-[11px] font-mono text-slate-500">
                    Target Adapter: <code className="text-slate-300 font-bold">cmapss_fd001</code>
                  </span>

                  {!compatibilityPassed ? (
                    <Button variant="danger" size="xs" disabled>
                      Inference Blocked (Fix Matrix Errors)
                    </Button>
                  ) : (
                    <Button
                      variant="primary"
                      size="xs"
                      onClick={handleIngest}
                      disabled={ingestMutation.isPending}
                      icon={<FileCheck className="w-3.5 h-3.5" />}
                    >
                      {ingestMutation.isPending ? (
                        <Loader2 className="w-3 h-3 animate-spin inline mr-1" />
                      ) : null}
                      Confirm Ingestion &amp; Proceed to Fleet
                    </Button>
                  )}
                </div>
              </Card>
            </>
          )}

          {!validateMutation.isPending && compatibilityChecks == null && (
            <Card title="Model Compatibility Verification Matrix" subtitle="">
              <div className="py-8 text-center space-y-3">
                <p className="text-slate-400 font-mono text-xs">
                  {selectedDatasetId
                    ? 'Select a dataset and click "Run Compatibility Gate" to see results.'
                    : 'No dataset selected. Use the Dataset selector above or upload a new file.'}
                </p>
                {selectedDatasetId && (
                  <Button
                    variant="secondary"
                    size="xs"
                    onClick={() => handleRunCompatibility(selectedDatasetId)}
                    disabled={validateMutation.isPending}
                  >
                    Run Compatibility Gate
                  </Button>
                )}
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};
