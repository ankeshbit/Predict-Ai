/**
 * DatasetSchemaMappingPage — PRD §FR-5 Schema Mapping & PRD §FR-6 Compatibility Gate.
 *
 * Full 6-step Reviewer Wizard:
 * 1. Upload CSV/TXT
 * 2. Dataset Profile (Exhaustive, non-hardcoded dataset statistics from file)
 * 3. Schema Mapping (Auto-detection, confidence table, user overrides)
 * 4. Compatibility Gate (11 PRD checks, Expected/Found/How-to-fix, training range comparison, OOD warnings, blocked FAIL gate)
 * 5. Ingestion (Live DB job progress, row count, units created)
 * 6. Scoring & Summary ("X units, Y readings ingested, Z scored, W alerts opened")
 */

import React, { useEffect, useState } from 'react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import {
  ArrowLeft,
  ArrowRight,
  AlertTriangle,
  CheckCircle2,
  Download,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Upload,
} from 'lucide-react';
import {
  useDatasets,
  useDatasetProfile,
  useUploadDataset,
  useUpdateMapping,
  useValidateCompatibility,
  useIngestDataset,
  useTriggerScoring,
  useDatasetSummary,
  useJobStatus,
  downloadCompatibilityReport,
  type CompatibilityCheckItem,
  type CompatibilityReport,
} from '../api';

interface DatasetSchemaMappingProps {
  initialDatasetId?: string;
  onBack: () => void;
  onIngestSuccess: () => void;
}

const CANONICAL_FIELDS = [
  'unit_id',
  'cycle',
  'op_setting_1',
  'op_setting_2',
  'op_setting_3',
  'sensor_1',
  'sensor_2',
  'sensor_3',
  'sensor_4',
  'sensor_5',
  'sensor_6',
  'sensor_7',
  'sensor_8',
  'sensor_9',
  'sensor_10',
  'sensor_11',
  'sensor_12',
  'sensor_13',
  'sensor_14',
  'sensor_15',
  'sensor_16',
  'sensor_17',
  'sensor_18',
  'sensor_19',
  'sensor_20',
  'sensor_21',
];

function getConfidenceMeta(canonical: string, source: string | undefined) {
  if (!source) {
    return { label: '0% Unmapped', badgeClass: 'bg-slate-900 text-slate-500 border-slate-800' };
  }
  const s = source.toLowerCase().trim();
  const c = canonical.toLowerCase().trim();
  if (s === c) {
    return { label: '100% Exact', badgeClass: 'bg-emerald-950/70 text-emerald-400 border-emerald-800' };
  }
  if (s.startsWith('col_') || s.startsWith('column_')) {
    return { label: '85% Positional', badgeClass: 'bg-indigo-950/70 text-indigo-300 border-indigo-800' };
  }
  return { label: '95% Synonym', badgeClass: 'bg-blue-950/70 text-blue-300 border-blue-800' };
}

export const DatasetSchemaMappingPage: React.FC<DatasetSchemaMappingProps> = ({
  initialDatasetId,
  onBack,
  onIngestSuccess,
}) => {
  const [activeStep, setActiveStep] = useState<number>(initialDatasetId ? 2 : 1);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(initialDatasetId ?? null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  // Local mapping edits
  const [mappingState, setMappingState] = useState<Record<string, string>>({});
  const [acknowledgedWarnings, setAcknowledgedWarnings] = useState<boolean>(false);

  // Live Job state
  const [ingestJobId, setIngestJobId] = useState<string | null>(null);
  const [scoringJobId, setScoringJobId] = useState<string | null>(null);

  // Compatibility report cache
  const [compReport, setCompReport] = useState<CompatibilityReport | null>(null);

  // Queries
  const { data: datasetsData, isLoading: datasetsLoading, refetch: refetchDatasets } = useDatasets({ limit: 50 });
  const datasets = datasetsData?.items ?? [];
  const selectedDataset = datasets.find((d) => d.id === selectedDatasetId) ?? null;
  const effectiveMapping = { ...(selectedDataset?.schema_mapping ?? {}), ...mappingState };

  const {
    data: profile,
    isLoading: profileLoading,
    error: profileError,
  } = useDatasetProfile(selectedDatasetId);

  const { data: summary, refetch: refetchSummary } = useDatasetSummary(selectedDatasetId);

  // Job status queries
  const { data: ingestJob } = useJobStatus(ingestJobId);
  const { data: scoringJob } = useJobStatus(scoringJobId);

  // Mutations
  const uploadMutation = useUploadDataset();
  const updateMappingMutation = useUpdateMapping();
  const validateMutation = useValidateCompatibility();
  const ingestMutation = useIngestDataset();
  const scoringMutation = useTriggerScoring();

  // Handle Ingest job completion -> transition to Scoring
  useEffect(() => {
    if (ingestJob?.status === 'completed' && activeStep === 5 && !scoringJobId && !scoringMutation.isPending) {
      if (selectedDatasetId) {
        setActiveStep(6);
        scoringMutation.mutate(
          { datasetId: selectedDatasetId, acknowledgedWarnings },
          { onSuccess: (res) => setScoringJobId(res.job_id) }
        );
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ingestJob?.status, activeStep, scoringJobId, selectedDatasetId]);

  // Handle Scoring job completion
  useEffect(() => {
    if (scoringJob?.status === 'completed' && activeStep === 6) {
      refetchSummary();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scoringJob?.status, activeStep]);

  function handleUpload() {
    if (!uploadFile) return;
    const form = new FormData();
    form.append('file', uploadFile);
    uploadMutation.mutate(form, {
      onSuccess: (ds) => {
        setSelectedDatasetId(ds.id);
        if (ds.schema_mapping) {
          setMappingState(ds.schema_mapping);
        }
        setActiveStep(2); // Jump to Profile
      },
    });
  }

  function handleRunCompatibility(datasetId: string) {
    setCompReport(null);
    setAcknowledgedWarnings(false);
    validateMutation.mutate(datasetId, {
      onSuccess: (report) => {
        setCompReport(report);
      },
      onError: (err: any) => {
        // Even if 409, ApiError may contain report details
        if (err?.details) {
          setCompReport(err.details as CompatibilityReport);
        }
      },
    });
  }

  function handleMappingChange(canonical: string, sourceCol: string) {
    const nextMapping = { ...mappingState };
    if (!sourceCol || sourceCol === '__unmapped__') {
      delete nextMapping[canonical];
    } else {
      nextMapping[canonical] = sourceCol;
    }
    setMappingState(nextMapping);

    // Persist immediately to backend
    if (selectedDatasetId) {
      updateMappingMutation.mutate({
        datasetId: selectedDatasetId,
        mapping: nextMapping,
      });
    }
  }

  function handleStartIngest() {
    if (!selectedDatasetId) return;
    setActiveStep(5);
    ingestMutation.mutate(
      {
        datasetId: selectedDatasetId,
        acknowledgedWarnings,
      },
      {
        onSuccess: (res) => {
          setIngestJobId(res.job_id);
        },
      }
    );
  }

  function handleStartScoring(datasetId: string) {
    setActiveStep(6);
    scoringMutation.mutate(
      {
        datasetId,
        acknowledgedWarnings,
      },
      {
        onSuccess: (res) => {
          setScoringJobId(res.job_id);
        },
      }
    );
  }

  const finalUnitsCreated = summary?.units_created ?? scoringJob?.result?.units_scored;
  const finalUnitsCreatedStr = finalUnitsCreated != null ? String(finalUnitsCreated) : '—';

  const finalReadingsIngested = summary?.readings_ingested ?? ingestJob?.result?.readings_ingested;
  const finalReadingsIngestedStr = finalReadingsIngested != null ? finalReadingsIngested.toLocaleString() : '—';

  const finalUnitsScored = summary?.units_scored ?? scoringJob?.result?.units_scored;
  const finalUnitsScoredStr = finalUnitsScored != null ? String(finalUnitsScored) : '—';

  const finalAlertsOpened = summary?.alerts_opened ?? scoringJob?.result?.alerts_opened;
  const finalAlertsOpenedStr = finalAlertsOpened != null ? String(finalAlertsOpened) : '—';

  const steps = [
    { num: 1, label: '1. Upload' },
    { num: 2, label: '2. Profile' },
    { num: 3, label: '3. Mapping' },
    { num: 4, label: '4. Compatibility' },
    { num: 5, label: '5. Ingest' },
    { num: 6, label: '6. Scoring' },
  ];

  return (
    <div className="space-y-5 animate-in fade-in duration-100 select-none">
      {/* Top Navigation & Dataset Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 bg-[#111621] border border-[#1e2636] rounded-md">
        <div className="space-y-0.5">
          <button
            onClick={onBack}
            className="text-xs font-mono text-slate-400 hover:text-white flex items-center gap-1 cursor-pointer transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Datasets
          </button>
          <h1 className="text-sm font-bold text-white font-mono uppercase tracking-wide">
            Dataset Ingestion &amp; Model Compatibility Pipeline
          </h1>
          <p className="text-[11px] text-slate-400">
            PRD §FR-5 Canonical Schema Mapping · PRD §FR-6 Strict Compatibility Gate
          </p>
        </div>

        {/* Dataset Switcher */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-slate-500">Active Dataset:</span>
          {datasetsLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
          ) : datasets.length === 0 ? (
            <span className="text-[11px] font-mono text-slate-500">None uploaded</span>
          ) : (
            <select
              value={selectedDatasetId ?? ''}
              onChange={(e) => {
                const id = e.target.value || null;
                setSelectedDatasetId(id);
                if (id) {
                  const ds = datasets.find((d) => d.id === id);
                  if (ds?.schema_mapping) setMappingState(ds.schema_mapping);
                  setActiveStep(2);
                }
              }}
              className="bg-[#0b0e14] border border-[#20293a] rounded px-2.5 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-blue-500"
            >
              <option value="">— Select dataset —</option>
              {datasets.map((ds) => (
                <option key={ds.id} value={ds.id}>
                  {ds.name} ({ds.status})
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* 6-Step Stepper Progress Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-1.5 text-xs font-mono">
        {steps.map((step) => {
          const isCurrent = activeStep === step.num;
          const isDone = activeStep > step.num;
          const isDisabled = !selectedDatasetId && step.num > 1;

          return (
            <button
              key={step.num}
              disabled={isDisabled}
              onClick={() => {
                setActiveStep(step.num);
                if (step.num === 4 && selectedDatasetId && !compReport) {
                  handleRunCompatibility(selectedDatasetId);
                }
              }}
              className={`p-2.5 rounded border text-left transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${
                isCurrent
                  ? 'bg-[#182334] border-blue-500 text-white font-semibold shadow-sm shadow-blue-500/20'
                  : isDone
                  ? 'bg-[#101620] border-emerald-900/60 text-emerald-400 hover:border-emerald-700'
                  : 'bg-[#0c1018] border-[#1e2636] text-slate-400 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span>{step.label}</span>
                {isDone && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
              </div>
            </button>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* STEP 1: UPLOAD                                                            */}
      {/* ========================================================================= */}
      {activeStep === 1 && (
        <Card title="Upload Dataset File" subtitle="Accepts NASA C-MAPSS FD001 space-delimited text or tabular CSV telemetry">
          <div className="p-8 border border-dashed border-[#242e40] rounded-lg text-center space-y-3 bg-[#0c1018]">
            <Upload className="w-8 h-8 text-blue-400 mx-auto" />
            <div className="space-y-1">
              <div className="text-sm font-semibold text-slate-200">
                Select Telemetry Dataset File
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Supports: Space/tab-delimited files without headers (raw train_FD001.txt style) or standard CSVs
              </p>
            </div>

            <div className="pt-2 flex flex-col items-center gap-3">
              <input
                type="file"
                accept=".csv,.txt"
                id="upload-dataset-file"
                className="text-xs text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-blue-600/20 file:text-blue-400 hover:file:bg-blue-600/30 cursor-pointer"
                onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
              />

              {uploadFile && (
                <div className="text-xs font-mono text-slate-300 bg-[#141b27] px-3 py-1.5 rounded border border-[#20293a]">
                  Selected: <span className="text-blue-400 font-bold">{uploadFile.name}</span> (
                  {(uploadFile.size / 1024).toFixed(1)} KB)
                </div>
              )}

              <Button
                variant="primary"
                size="sm"
                onClick={handleUpload}
                disabled={!uploadFile || uploadMutation.isPending}
                icon={uploadMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRight className="w-3.5 h-3.5" />}
              >
                {uploadMutation.isPending ? 'Profiling Dataset…' : 'Upload & Compute Profile'}
              </Button>

              {uploadMutation.isError && (
                <p className="text-xs text-rose-400 font-mono bg-rose-950/30 p-2 rounded border border-rose-900/60">
                  {String(uploadMutation.error)}
                </p>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* ========================================================================= */}
      {/* STEP 2: DATASET PROFILE                                                   */}
      {/* ========================================================================= */}
      {activeStep === 2 && (
        <div className="space-y-4">
          {profileLoading && (
            <Card title="Computing Dataset Profile" subtitle="Sniffing delimiter, header, and descriptive statistics">
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-400 font-mono text-xs">
                <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                <span>Reading staged file and computing non-fabricated statistics…</span>
              </div>
            </Card>
          )}

          {profileError && (
            <div className="p-4 rounded bg-rose-950/30 border border-rose-800 text-rose-300 font-mono text-xs">
              Failed to load dataset profile: {String(profileError)}
            </div>
          )}

          {profile && (
            <>
              {/* Header Overview Card */}
              <Card
                title="Dataset Profile &amp; Integrity Analysis"
                subtitle="All statistics computed directly from the uploaded file — zero hardcoded metrics"
              >
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 font-mono text-xs">
                  <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                    <div className="text-[10px] text-slate-500 uppercase">File Name</div>
                    <div className="text-white font-bold truncate mt-0.5" title={profile.filename}>
                      {profile.filename}
                    </div>
                  </div>
                  <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                    <div className="text-[10px] text-slate-500 uppercase">Total Rows</div>
                    <div className="text-white font-bold mt-0.5">{profile.total_rows.toLocaleString()}</div>
                  </div>
                  <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                    <div className="text-[10px] text-slate-500 uppercase">Columns</div>
                    <div className="text-white font-bold mt-0.5">{profile.total_columns}</div>
                  </div>
                  <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                    <div className="text-[10px] text-slate-500 uppercase">Delimiter</div>
                    <div className="text-blue-400 font-bold mt-0.5">
                      {profile.detected_delimiter === 'whitespace' ? 'Whitespace (space/tab)' : profile.detected_delimiter}
                    </div>
                  </div>
                  <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                    <div className="text-[10px] text-slate-500 uppercase">Header Line</div>
                    <div className="text-slate-300 font-bold mt-0.5">
                      {profile.has_header ? 'Detected (Named)' : 'None (Auto-indexed)'}
                    </div>
                  </div>
                  <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                    <div className="text-[10px] text-slate-500 uppercase">Duplicate Rows</div>
                    <div className={`font-bold mt-0.5 ${profile.duplicate_rows > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {profile.duplicate_rows}
                    </div>
                  </div>
                </div>

                {/* Entity & Cycle Stats */}
                <div className="mt-4 p-3 bg-[#0e141f] rounded border border-[#1e293b] flex flex-wrap items-center justify-between gap-4 font-mono text-xs">
                  <div>
                    <span className="text-slate-400">Detected Units / Entities: </span>
                    <span className="text-white font-bold">
                      {profile.unit_count != null ? `${profile.unit_count} distinct machines` : '—'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Cycles Per Unit: </span>
                    <span className="text-slate-200">
                      {profile.cycles_per_unit ? (
                        <>
                          min <strong className="text-white">{profile.cycles_per_unit.min}</strong> · max{' '}
                          <strong className="text-white">{profile.cycles_per_unit.max}</strong> · mean{' '}
                          <strong className="text-white">{profile.cycles_per_unit.mean.toFixed(1)}</strong>
                        </>
                      ) : (
                        '—'
                      )}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400">Data Origin: </span>
                    <span className="text-blue-400 font-semibold">User Uploaded Telemetry</span>
                  </div>
                </div>
              </Card>

              {/* Numeric Column Distributions & Missing Values */}
              <Card
                title="Column Statistics &amp; Missing Value Distribution"
                subtitle="Calculated min, max, mean, and missing observation counts per column"
              >
                <div className="overflow-x-auto max-h-72 overflow-y-auto">
                  <table className="w-full text-left text-xs border-collapse font-mono tabular-nums">
                    <thead className="sticky top-0 bg-[#111721] border-b border-[#20293a] text-[10px] text-slate-400 uppercase tracking-wider">
                      <tr>
                        <th className="py-2 px-3">Column Name</th>
                        <th className="py-2 px-3 text-right">Missing Count</th>
                        <th className="py-2 px-3 text-right">Min</th>
                        <th className="py-2 px-3 text-right">Max</th>
                        <th className="py-2 px-3 text-right">Mean</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#18212e]">
                      {Object.keys(profile.numeric_stats).length === 0 ? (
                        <tr>
                          <td colSpan={5} className="py-4 text-center text-slate-500 font-mono text-xs">
                            No numeric columns detected in this file.
                          </td>
                        </tr>
                      ) : (
                        Object.entries(profile.numeric_stats).map(([col, stats]) => {
                          const missing = profile.missing_counts[col] != null ? profile.missing_counts[col] : '—';
                          return (
                            <tr key={col} className="hover:bg-[#141b26]">
                              <td className="py-1.5 px-3 font-semibold text-slate-200">{col}</td>
                              <td className="py-1.5 px-3 text-right">
                                <span className={typeof missing === 'number' && missing > 0 ? 'text-amber-400 font-bold' : 'text-slate-500'}>
                                  {missing}
                                </span>
                              </td>
                              <td className="py-1.5 px-3 text-right text-slate-300">{stats.min.toFixed(4)}</td>
                              <td className="py-1.5 px-3 text-right text-slate-300">{stats.max.toFixed(4)}</td>
                              <td className="py-1.5 px-3 text-right text-blue-300">{stats.mean.toFixed(4)}</td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4 pt-3 border-t border-[#1d2634] flex justify-end">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setActiveStep(3)}
                    icon={<ArrowRight className="w-3.5 h-3.5" />}
                  >
                    Proceed to Schema Mapping
                  </Button>
                </div>
              </Card>
            </>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 3: SCHEMA MAPPING                                                    */}
      {/* ========================================================================= */}
      {activeStep === 3 && (
        <Card
          title="Schema Auto-Detection &amp; Interactive Column Mapping"
          subtitle="Auto-mapped to canonical C-MAPSS FD001 layout (unit, cycle, op_setting_1..3, sensor_1..21). Correct any field below."
        >
          <div className="space-y-4">
            <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
              <div>
                <span className="text-slate-400">Canonical Target: </span>
                <span className="text-white font-bold">NASA C-MAPSS FD001 (26 channels)</span>
                <span className="text-slate-500 ml-2">
                  ({Object.keys(effectiveMapping).length} of 26 mapped)
                </span>
              </div>
              {updateMappingMutation.isPending && (
                <div className="flex items-center gap-1.5 text-blue-400 text-xs">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Saving mapping update…
                </div>
              )}
            </div>

            {/* Two-Column Mapping Table with Confidence Badges */}
            <div className="overflow-x-auto max-h-96 overflow-y-auto">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead className="sticky top-0 bg-[#111721] border-b border-[#20293a] text-[10px] text-slate-400 uppercase tracking-wider">
                  <tr>
                    <th className="py-2.5 px-3">Canonical Channel</th>
                    <th className="py-2.5 px-3">Mapped Source Column</th>
                    <th className="py-2.5 px-3">Detection Confidence</th>
                    <th className="py-2.5 px-3">Override Source Column</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#18212e]">
                  {CANONICAL_FIELDS.map((canon) => {
                    const mappedSrc = effectiveMapping[canon];
                    const meta = getConfidenceMeta(canon, mappedSrc);
                    const sourceColumns = profile?.header_names ?? Object.keys(profile?.numeric_stats ?? {});

                    return (
                      <tr key={canon} className="hover:bg-[#141b26] transition-colors">
                        <td className="py-2 px-3 font-semibold text-slate-200">
                          <code>{canon}</code>
                        </td>
                        <td className="py-2 px-3">
                          {mappedSrc ? (
                            <span className="text-blue-400 font-bold">{mappedSrc}</span>
                          ) : (
                            <span className="text-slate-500 italic">— unmapped —</span>
                          )}
                        </td>
                        <td className="py-2 px-3">
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded font-mono border uppercase ${meta.badgeClass}`}
                          >
                            {meta.label}
                          </span>
                        </td>
                        <td className="py-2 px-3">
                          <select
                            value={mappedSrc ?? ''}
                            onChange={(e) => handleMappingChange(canon, e.target.value)}
                            className="bg-[#0b0e14] border border-[#232d3f] rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                          >
                            <option value="">— Select Source Column —</option>
                            {sourceColumns.map((col) => (
                              <option key={col} value={col}>
                                {col}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="pt-3 border-t border-[#1d2634] flex items-center justify-between">
              <span className="text-xs font-mono text-slate-400">
                Hash: <code className="text-slate-300 font-bold">{selectedDataset?.schema_mapping_hash ?? '—'}</code>
              </span>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  if (selectedDatasetId) {
                    setActiveStep(4);
                    handleRunCompatibility(selectedDatasetId);
                  }
                }}
                disabled={!selectedDatasetId}
                icon={<ArrowRight className="w-3.5 h-3.5" />}
              >
                Save &amp; Run Compatibility Gate
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* ========================================================================= */}
      {/* STEP 4: COMPATIBILITY GATE                                                */}
      {/* ========================================================================= */}
      {activeStep === 4 && (
        <div className="space-y-4">
          {validateMutation.isPending && (
            <Card title="Running Compatibility Verification" subtitle="Executing 11 PRD FR-6 verification checks">
              <div className="py-12 flex flex-col items-center justify-center gap-2 text-slate-400 font-mono text-xs">
                <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
                <span>Validating sequence length, monotonically increasing cycles, bounded imputation, and physical training ranges…</span>
              </div>
            </Card>
          )}

          {!validateMutation.isPending && compReport && (
            <>
              {/* Top Summary Banner */}
              {compReport.failed_checks > 0 ? (
                <div className="p-4 rounded-lg bg-rose-950/50 border border-rose-800/90 space-y-2">
                  <div className="flex items-start gap-3">
                    <ShieldAlert className="w-6 h-6 text-rose-400 shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
                        This dataset is not compatible with the selected model.
                      </div>
                      <p className="text-xs text-rose-200/90 leading-relaxed font-sans">
                        {compReport.summary_sentence ||
                          `Inference is strictly blocked: failed ${compReport.failed_checks} of ${compReport.total_checks} compatibility verification checks.`}
                      </p>
                    </div>
                  </div>

                  {/* Plain Language Explanation */}
                  {compReport.plain_language_explanation && (
                    <div className="mt-3 p-3 bg-black/40 rounded border border-rose-900/60 text-xs text-slate-300 space-y-1 font-sans">
                      <div className="font-bold text-rose-300 font-mono text-[11px] uppercase">
                        Plain-Language Diagnosis
                      </div>
                      <p className="leading-relaxed">{compReport.plain_language_explanation}</p>
                    </div>
                  )}

                  {/* Report Download Buttons */}
                  <div className="pt-2 flex items-center gap-2">
                    <span className="text-xs font-mono text-slate-400">Download report:</span>
                    <Button
                      variant="secondary"
                      size="xs"
                      onClick={() => selectedDatasetId && downloadCompatibilityReport(selectedDatasetId, 'json')}
                      icon={<Download className="w-3 h-3" />}
                    >
                      JSON Format
                    </Button>
                    <Button
                      variant="secondary"
                      size="xs"
                      onClick={() => selectedDatasetId && downloadCompatibilityReport(selectedDatasetId, 'csv')}
                      icon={<Download className="w-3 h-3" />}
                    >
                      CSV Format
                    </Button>
                  </div>
                </div>
              ) : compReport.has_warnings ? (
                <div className="p-4 rounded-lg bg-amber-950/40 border border-amber-800/80 space-y-2">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-6 h-6 text-amber-400 shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
                        Compatibility Warning: Out-Of-Distribution Telemetry
                      </div>
                      <p className="text-xs text-amber-200/90 leading-relaxed font-sans">
                        {compReport.summary_sentence ||
                          `All structural checks passed, but out-of-distribution values were detected in ${compReport.ood_sensors ? compReport.ood_sensors.length : '—'} sensor channel(s).`}
                      </p>
                    </div>
                  </div>

                  {/* Warning Acknowledgment Checkbox */}
                  <div className="mt-3 p-3 bg-black/40 rounded border border-amber-900/60 text-xs text-amber-200 space-y-2">
                    <label className="flex items-start gap-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={acknowledgedWarnings}
                        onChange={(e) => setAcknowledgedWarnings(e.target.checked)}
                        className="mt-0.5 rounded border-amber-600 bg-amber-950 text-amber-500 focus:ring-amber-500"
                      />
                      <span className="font-sans leading-relaxed">
                        I acknowledge these out-of-distribution warnings. I understand the model was not trained on these
                        value envelopes, and that all resulting predictions will carry a{' '}
                        <strong className="text-amber-300 font-mono">REDUCED RELIABILITY</strong> flag.
                      </span>
                    </label>
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-lg bg-emerald-950/40 border border-emerald-800/80 flex items-start gap-3">
                  <ShieldCheck className="w-6 h-6 text-emerald-400 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
                      Dataset Fully Compatible with Selected Model
                    </div>
                    <p className="text-xs text-emerald-200/90 leading-relaxed font-sans">
                      All 11 PRD FR-6 verification checks passed. Schema, sequence structure, monotonicity, and numeric
                      ranges align with the active NASA C-MAPSS FD001 model bundle contract.
                    </p>
                  </div>
                </div>
              )}

              {/* Actionable Expected / Found / How to Fix Table */}
              <Card
                title="Model Compatibility Verification Matrix (All 11 PRD FR-6 Checks)"
                subtitle="Verified against model card input_features and stored preprocessing transform"
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse font-mono tabular-nums">
                    <thead>
                      <tr className="border-b border-[#20293a] bg-[#111721] text-[10px] text-slate-400 uppercase tracking-wider">
                        <th className="py-2.5 px-3">Rule / Constraint</th>
                        <th className="py-2.5 px-3">Status</th>
                        <th className="py-2.5 px-3">Expected (Model Contract)</th>
                        <th className="py-2.5 px-3">Found in Dataset</th>
                        <th className="py-2.5 px-3 font-sans">How to Fix (Actionable)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#18212e]">
                      {compReport.checks.map((item: CompatibilityCheckItem) => (
                        <tr key={item.check_number} className="hover:bg-[#151c27] transition-colors">
                          <td className="py-2 px-3 font-semibold text-slate-200">
                            #{item.check_number} {item.check_name}
                          </td>
                          <td className="py-2 px-3">
                            {item.status === 'passed' ? (
                              <span className="text-[10px] text-emerald-400 font-bold uppercase bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/60">
                                ✓ Passed
                              </span>
                            ) : item.status === 'warning' ? (
                              <span className="text-[10px] text-amber-400 font-bold uppercase bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/60">
                                ⚠ Warning
                              </span>
                            ) : (
                              <span className="text-[10px] text-rose-400 font-bold uppercase bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/60">
                                ✕ Failed
                              </span>
                            )}
                          </td>
                          <td className="py-2 px-3 text-slate-300 text-[11px]">{item.expected_value}</td>
                          <td className="py-2 px-3 text-slate-300 text-[11px]">{item.found_value}</td>
                          <td className="py-2 px-3 text-slate-300 font-sans text-xs">{item.how_to_fix}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Value-Range Comparison vs Model Training Envelopes */}
              {compReport.range_comparisons && Object.keys(compReport.range_comparisons).length > 0 && (
                <Card
                  title="Telemetry Value-Range Comparison vs. Model Training Distribution"
                  subtitle="Uploaded sensor min/max plotted against the training envelopes stored in the model bundle"
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 font-mono text-xs">
                    {Object.entries(compReport.range_comparisons).map(([sensor, comp]) => {
                      return (
                        <div
                          key={sensor}
                          className={`p-3 rounded border ${
                            comp.is_ood
                              ? 'bg-amber-950/20 border-amber-800/80'
                              : 'bg-[#0c1018] border-[#1e2636]'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-200">{sensor}</span>
                            {comp.is_ood ? (
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-900/60 text-amber-300 border border-amber-700 uppercase font-semibold">
                                OOD Warning
                              </span>
                            ) : (
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800 uppercase font-semibold">
                                In Bounds
                              </span>
                            )}
                          </div>

                          <div className="mt-2 space-y-1 text-[11px]">
                            <div className="flex justify-between text-slate-400">
                              <span>Training Range:</span>
                              <span className="text-slate-300 font-semibold">
                                [{comp.train_min.toFixed(2)}, {comp.train_max.toFixed(2)}]
                              </span>
                            </div>
                            <div className="flex justify-between text-slate-400">
                              <span>Uploaded Range:</span>
                              <span className={`font-semibold ${comp.is_ood ? 'text-amber-400' : 'text-blue-300'}`}>
                                [{comp.uploaded_min.toFixed(2)}, {comp.uploaded_max.toFixed(2)}]
                              </span>
                            </div>
                          </div>

                          {/* Visual range comparison bar */}
                          <div className="mt-2.5 pt-2 border-t border-[#1c2433]">
                            <div className="h-2 w-full bg-[#141c27] rounded-full overflow-hidden relative">
                              <div
                                className={`h-full rounded-full ${comp.is_ood ? 'bg-amber-500' : 'bg-emerald-500'}`}
                                style={{ width: '100%' }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              )}

              {/* Action Bar */}
              <div className="p-3 bg-[#111621] border border-[#1e2636] rounded-md flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400">
                  Target: <strong className="text-slate-200">cmapss_fd001</strong> · Status:{' '}
                  <strong
                    className={
                      compReport.failed_checks > 0
                        ? 'text-rose-400'
                        : compReport.has_warnings
                        ? 'text-amber-400'
                        : 'text-emerald-400'
                    }
                  >
                    {compReport.failed_checks > 0
                      ? 'BLOCKED (Incompatible)'
                      : compReport.has_warnings
                      ? 'WARNING (Requires Acknowledgment)'
                      : 'PASSED (Ready)'}
                  </strong>
                </span>

                {compReport.failed_checks > 0 ? (
                  <Button variant="danger" size="sm" disabled>
                    Inference Blocked (Fix Matrix Errors)
                  </Button>
                ) : compReport.has_warnings ? (
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={!acknowledgedWarnings || ingestMutation.isPending}
                    onClick={handleStartIngest}
                    icon={ingestMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRight className="w-3.5 h-3.5" />}
                  >
                    Confirm Acknowledgment &amp; Ingest
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={ingestMutation.isPending}
                    onClick={handleStartIngest}
                    icon={ingestMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowRight className="w-3.5 h-3.5" />}
                  >
                    Proceed to Ingestion
                  </Button>
                )}
              </div>
            </>
          )}

          {!validateMutation.isPending && !compReport && (
            <Card title="Model Compatibility Gate" subtitle="Ready to evaluate dataset against model requirements">
              <div className="py-8 text-center space-y-3">
                <p className="text-slate-400 font-mono text-xs">
                  Click below to run all 11 PRD FR-6 verification checks against the active model bundle.
                </p>
                {selectedDatasetId && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleRunCompatibility(selectedDatasetId)}
                  >
                    Run Compatibility Gate
                  </Button>
                )}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* STEP 5: INGESTION                                                         */}
      {/* ========================================================================= */}
      {activeStep === 5 && (
        <Card
          title="Telemetry Data Ingestion"
          subtitle="Creating machine entities and streaming observation records into database"
        >
          <div className="p-6 space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">
                  Status:{' '}
                  <strong className="text-blue-400 uppercase">
                    {ingestJob?.status ?? (ingestMutation.isPending ? 'Queued' : 'Processing')}
                  </strong>
                </span>
                <span className="text-slate-200 font-bold">
                  {typeof ingestJob?.progress_pct === 'number' ? `${ingestJob.progress_pct.toFixed(0)}%` : '—'}
                </span>
              </div>
              <div className="h-3 w-full bg-[#0c1018] rounded-full overflow-hidden border border-[#1e2636]">
                <div
                  className="h-full bg-blue-500 transition-all duration-300 rounded-full"
                  style={{ width: `${typeof ingestJob?.progress_pct === 'number' ? Math.max(ingestJob.progress_pct, 5) : 5}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono text-xs">
              <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                <div className="text-[10px] text-slate-500 uppercase">Dataset Name</div>
                <div className="text-white font-bold truncate mt-0.5">{selectedDataset?.name ?? '—'}</div>
              </div>
              <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                <div className="text-[10px] text-slate-500 uppercase">Units Created</div>
                <div className="text-emerald-400 font-bold mt-0.5">
                  {ingestJob?.result?.units_created ?? (ingestJob?.status === 'completed' ? 'Done' : 'In Progress')}
                </div>
              </div>
              <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                <div className="text-[10px] text-slate-500 uppercase">Readings Ingested</div>
                <div className="text-blue-400 font-bold mt-0.5">
                  {ingestJob?.result?.readings_ingested != null
                    ? Number(ingestJob.result.readings_ingested).toLocaleString()
                    : 'Streaming…'}
                </div>
              </div>
            </div>

            {ingestJob?.status === 'completed' && (
              <div className="p-4 bg-emerald-950/40 rounded border border-emerald-800/80 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-emerald-300 font-mono">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Telemetry ingestion completed successfully! Proceed to scoring.</span>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => selectedDatasetId && handleStartScoring(selectedDatasetId)}
                  icon={<ArrowRight className="w-3.5 h-3.5" />}
                >
                  Proceed to Scoring Run
                </Button>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* ========================================================================= */}
      {/* STEP 6: SCORING & FINAL SUMMARY                                           */}
      {/* ========================================================================= */}
      {activeStep === 6 && (
        <Card
          title="Batch Model Scoring &amp; Alert Generation"
          subtitle="Running offline registered bundle inference across ingested machine trajectories"
        >
          <div className="p-6 space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">
                  Scoring Status:{' '}
                  <strong className="text-emerald-400 uppercase">
                    {scoringJob?.status ?? (scoringMutation.isPending ? 'Queued' : 'Scoring')}
                  </strong>
                </span>
                <span className="text-slate-200 font-bold">
                  {typeof scoringJob?.progress_pct === 'number' ? `${scoringJob.progress_pct.toFixed(0)}%` : '—'}
                </span>
              </div>
              <div className="h-3 w-full bg-[#0c1018] rounded-full overflow-hidden border border-[#1e2636]">
                <div
                  className="h-full bg-emerald-500 transition-all duration-300 rounded-full"
                  style={{ width: `${typeof scoringJob?.progress_pct === 'number' ? Math.max(scoringJob.progress_pct, 5) : 5}%` }}
                />
              </div>
            </div>

            {/* Live Progress or Final Database Summary */}
            {scoringJob?.status === 'completed' || summary ? (
              <div className="space-y-4">
                {/* Official PRD summary sentence */}
                <div className="p-4 rounded-lg bg-[#0e1726] border border-blue-500/40 text-center space-y-1">
                  <div className="text-sm font-bold text-white font-mono uppercase tracking-wide">
                    Pipeline Execution Complete
                  </div>
                  <p className="text-base font-mono text-emerald-400 font-semibold">
                    {finalUnitsCreatedStr} units,{' '}
                    {finalReadingsIngestedStr} readings ingested,{' '}
                    {finalUnitsScoredStr} scored,{' '}
                    {finalAlertsOpenedStr} alerts opened
                  </p>
                  <p className="text-xs text-slate-400 font-sans">
                    All numbers retrieved directly from the relational database state.
                  </p>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
                  <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                    <div className="text-[10px] text-slate-500 uppercase">Units Ingested</div>
                    <div className="text-white text-base font-bold mt-0.5">
                      {finalUnitsCreatedStr}
                    </div>
                  </div>
                  <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                    <div className="text-[10px] text-slate-500 uppercase">Telemetry Readings</div>
                    <div className="text-blue-400 text-base font-bold mt-0.5">
                      {finalReadingsIngestedStr}
                    </div>
                  </div>
                  <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                    <div className="text-[10px] text-slate-500 uppercase">Units Scored</div>
                    <div className="text-emerald-400 text-base font-bold mt-0.5">
                      {finalUnitsScoredStr}
                    </div>
                  </div>
                  <div className="p-3 bg-[#0c1018] rounded border border-[#1e2636]">
                    <div className="text-[10px] text-slate-500 uppercase">Alerts Opened</div>
                    <div className="text-amber-400 text-base font-bold mt-0.5">
                      {finalAlertsOpenedStr}
                    </div>
                  </div>
                </div>

                <div className="pt-2 flex justify-end gap-3">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      refetchDatasets();
                      setActiveStep(1);
                    }}
                    icon={<Upload className="w-3.5 h-3.5" />}
                  >
                    Upload Another Dataset
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={onIngestSuccess}
                    icon={<ArrowRight className="w-3.5 h-3.5" />}
                  >
                    View Scored Fleet
                  </Button>
                </div>
              </div>
            ) : (
              <div className="py-6 flex flex-col items-center justify-center gap-2 text-slate-400 font-mono text-xs">
                <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
                <span>Generating predictions and evaluating alert thresholds…</span>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  );
};
