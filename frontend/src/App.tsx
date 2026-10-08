import { useState } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import type { Machine, Alert, MaintenanceRecord, Dataset } from './types';
import { AppLayout } from './components/layout/AppLayout';
import type { NavPage } from './components/layout/Sidebar';
import { LoginPage } from './pages/LoginPage';
import { OnboardingModal } from './pages/OnboardingModal';
import { OverviewDashboardPage } from './pages/OverviewDashboardPage';
import { FleetPage } from './pages/FleetPage';
import { MachineDetailPage } from './pages/MachineDetailPage';
import { DatasetsPage } from './pages/DatasetsPage';
import { DatasetSchemaMappingPage } from './pages/DatasetSchemaMappingPage';
import { AlertsPage } from './pages/AlertsPage';
import { MaintenancePage } from './pages/MaintenancePage';
import { ModelPerformancePage } from './pages/ModelPerformancePage';
import { SettingsPage } from './pages/SettingsPage';

import {
  setAuthToken,
  useAcknowledgeAlert,
  useAlerts,
  useCurrentUser,
  useDatasets,
  useMachines,
  useMaintenanceRecords,
  useResetDemo,
  useResolveAlert,
  useCreateMaintenance,
  useSensorHistory,
} from './api';
import { Loader2 } from 'lucide-react';

function mapBackendMachineToMachine(bm: any): Machine {
  const failureProb: number | null = bm.failure_probability != null ? bm.failure_probability : null;

  return {
    id: bm.id,
    machineCode: bm.machine_code,
    name: bm.name || bm.machine_code,
    machineType: bm.machine_type || '—',
    location: bm.location || '—',
    installDate: bm.install_date ?? bm.created_at,
    operationalStatus: bm.operational_status ?? null,
    healthIndicator: bm.health_indicator ?? null,
    healthBand: bm.health_band ?? null,
    healthComponents: {
      failureRiskPenalty: 0,
      anomalyPenalty: 0,
      trendPenalty: 0,
      otherPenalty: 0,
    },
    failureProbability: failureProb,
    predictionHorizon: bm.prediction_horizon ?? null,
    riskLevel: bm.risk_level ?? null,
    currentCycle: bm.current_cycle ?? null,
    anomalySeverity: bm.anomaly_severity ?? null,
    anomalyScore: bm.anomaly_score ?? null,
    anomalyStatus: bm.is_anomaly != null ? (bm.is_anomaly ? 'anomaly' : 'normal') : null,
    isAnomaly: bm.is_anomaly ?? null,
    anomalyThreshold: bm.anomaly_threshold ?? null,
    reliabilityStatus: bm.reliability_status ?? null,
    isDemo: Boolean(bm.is_demo),
    datasetBadge: bm.is_demo ? 'Demo / Simulated Data' : null,
    lastUpdated: bm.updated_at,
    explanation: {
      headline: `Unit ${bm.machine_code} status`,
      topContributingFeatures: [],
      trendFacts: [],
      summaryText: bm.current_cycle != null
        ? `Latest scored at cycle ${bm.current_cycle}.`
        : 'No prediction available yet. Score the machine to see results.',
    },
    recommendation: {
      ruleId: 'RULE_NOMINAL',
      text: 'Standard operational schedule.',
      priority: 'low',
      rationale: 'Telemetry within nominal threshold.',
    },
    lineage: {
      machineCode: bm.machine_code,
      datasetName: 'NASA C-MAPSS FD001',
      datasetVersion: '1.0',
      schemaMappingHash: bm.schema_mapping_hash ?? null,
      featureConfigVersion: bm.feature_config_version ?? null,
      preprocessingVersion: bm.preprocessing_version ?? null,
      failureModelVersion: bm.failure_model_version_id ?? null,
      anomalyModelVersion: bm.anomaly_model_version_id ?? null,
      predictionHorizon: bm.prediction_horizon ?? null,
      predictionHorizonUnit: bm.prediction_horizon_unit ?? null,
      asOfCycle: bm.current_cycle ?? null,
      predictedAt: bm.updated_at,
      inputWindowLength: null,
    },
  };
}


function mapBackendAlertToAlert(ba: any, machineCode = 'FD001-Unit'): Alert {
  return {
    id: ba.id,
    machineId: ba.machine_id,
    machineCode,
    machineName: machineCode,
    type: ba.alert_type as any,
    severity: ba.severity as any,
    status: ba.status as any,
    asOfCycle: ba.trigger_cycle != null ? ba.trigger_cycle : null,
    triggeredAt: ba.created_at,
    message: ba.alert_type ? `Operational alert: ${String(ba.alert_type).replace(/_/g, ' ')}` : 'Operational alert: —',
    reliabilityStatus: ba.reliability_status ?? null,
    recommendationText: ba.recommendation_text || '—',
    recommendationRuleId: ba.recommendation_rule_id || '—',
    acknowledgedAt: ba.acknowledged_at,
    acknowledgedBy: ba.acknowledged_by_user_id,
    resolvedAt: ba.resolved_at,
    resolvedBy: ba.resolved_by_user_id,
  };
}

function mapBackendMaintenanceToRecord(bm: any, machineCode = 'FD001-Unit'): MaintenanceRecord {
  return {
    id: bm.id,
    machineId: bm.machine_id,
    machineCode,
    alertId: bm.alert_id,
    issue: bm.issue || bm.action_type || '—',
    recommendedAction: bm.recommended_action || '—',
    decision: bm.decision || '—',
    decisionRationale: bm.decision_rationale || '—',
    actionTaken: bm.action_taken || '—',
    performedAt: bm.started_at,
    performedBy: bm.performed_by_user_id,
    status: bm.status || '—',
    outcome: bm.outcome,
    notes: bm.engineer_notes || '—',
  };
}

export function App() {
  const { data: currentUser, isLoading: isAuthLoading, refetch: refetchUser } = useCurrentUser();
  const resetDemoMutation = useResetDemo();
  const acknowledgeAlertMutation = useAcknowledgeAlert();
  const resolveAlertMutation = useResolveAlert();
  const createMaintenanceMutation = useCreateMaintenance();

  const { data: backendMachinesData } = useMachines();
  const { data: backendAlertsData } = useAlerts();
  const { data: backendMaintData } = useMaintenanceRecords();
  const { data: backendDatasetsData } = useDatasets();

  const navigate = useNavigate();
  const location = useLocation();

  const getPageFromPath = (path: string): NavPage => {
    if (path.startsWith('/fleet')) return 'fleet';
    if (path.startsWith('/machines')) return 'machines';
    if (path.startsWith('/datasets')) return 'datasets';
    if (path.startsWith('/alerts')) return 'alerts';
    if (path.startsWith('/maintenance')) return 'maintenance';
    if (path.startsWith('/performance') || path.startsWith('/model-performance')) return 'model-performance';
    if (path.startsWith('/settings')) return 'settings';
    return 'overview';
  };

  const currentPage = getPageFromPath(location.pathname);

  const handleNavigate = (page: NavPage) => {
    if (page === 'overview') navigate('/');
    else navigate(`/${page}`);
  };

  const [selectedMachineId, setSelectedMachineId] = useState<string>('');
  const [isOnboardingOpen, setIsOnboardingOpen] = useState<boolean>(false);
  const [schemaMappingDatasetId, setSchemaMappingDatasetId] = useState<string>('');

  // Transform backend entities to UI types
  const machines: Machine[] = (backendMachinesData?.items || []).map(mapBackendMachineToMachine);
  const alerts: Alert[] = (backendAlertsData?.items || []).map((a) => {
    const matchedMachine = machines.find((m) => m.id === a.machine_id);
    return mapBackendAlertToAlert(a, matchedMachine?.machineCode);
  });
  const maintenanceRecords: MaintenanceRecord[] = (backendMaintData?.items || []).map((m) => {
    const matchedMachine = machines.find((mach) => mach.id === m.machine_id);
    return mapBackendMaintenanceToRecord(m, matchedMachine?.machineCode);
  });

  const datasets: Dataset[] = (backendDatasetsData?.items || []).map((d) => ({
    id: d.id,
    name: d.name,
    version: d.version || '—',
    adapterKey: d.adapter_key || '—',
    adapterVersion: d.adapter_version || '—',
    dataOrigin: (d.data_origin || '—') as any,
    isDemo: Boolean(d.name.toLowerCase().includes('demo') || d.slug?.includes('demo')),
    status: (d.status === 'incompatible' ? 'rejected_incompatible' : d.status) as any,
    checksumSha256: d.schema_mapping_hash || '—',
    rowCount: d.row_count != null ? d.row_count : 0,
    unitCount: d.unit_count != null ? d.unit_count : 0,
    uploadedBy: d.uploaded_by || '—',
    uploadedAt: d.created_at,
  }));

  // Resolve selected machine
  const effectiveSelectedId = selectedMachineId || machines[0]?.id || '';
  const selectedMachine = machines.find((m) => m.id === effectiveSelectedId) || machines[0];

  const { data: sensorHistoryData } = useSensorHistory(effectiveSelectedId, { downsample_to: 100 });
  const rawPoints = sensorHistoryData?.points || (sensorHistoryData as any)?.readings || [];
  const sensorHistory = rawPoints.map((r: any) => ({
    cycle: r.cycle,
    sensor_1: r.sensors?.sensor_1,
    sensor_2: r.sensors?.sensor_2,
    sensor_3: r.sensors?.sensor_3,
    sensor_4: r.sensors?.sensor_4,
    sensor_7: r.sensors?.sensor_7,
    sensor_8: r.sensors?.sensor_8,
    sensor_9: r.sensors?.sensor_9,
    sensor_11: r.sensors?.sensor_11,
    sensor_12: r.sensors?.sensor_12,
    sensor_13: r.sensors?.sensor_13,
    sensor_14: r.sensors?.sensor_14,
    sensor_15: r.sensors?.sensor_15,
    sensor_17: r.sensors?.sensor_17,
    sensor_20: r.sensors?.sensor_20,
    sensor_21: r.sensors?.sensor_21,
    op_setting_1: r.op_setting_1,
    op_setting_2: r.op_setting_2,
  }));

  const handleLogout = () => {
    setAuthToken(null);
    refetchUser();
  };

  const handleResetDemo = () => {
    resetDemoMutation.mutate();
  };

  const handleAcknowledgeAlert = (alertId: string) => {
    acknowledgeAlertMutation.mutate({ alertId });
  };

  const handleResolveAlert = (
    alertId: string,
    resolutionType: 'issue_resolved' | 'false_alarm' | 'no_action_needed',
    note: string
  ) => {
    resolveAlertMutation.mutate({ alertId, resolutionType, resolutionNote: note });
  };

  const handleRecordMaintenance = (
    recordData: Omit<MaintenanceRecord, 'id' | 'performedAt'>
  ) => {
    createMaintenanceMutation.mutate({
      machine_id: recordData.machineId,
      alert_id: recordData.alertId,
      issue: recordData.issue,
      recommended_action: recordData.recommendedAction,
      decision: recordData.decision,
      decision_rationale: recordData.decisionRationale,
      action_taken: recordData.actionTaken,
      status: recordData.status,
      outcome: recordData.outcome,
      notes: recordData.notes,
    });

  };

  const handleSelectMachine = (machineId: string) => {
    setSelectedMachineId(machineId);
    navigate('/machines');
  };

  const handleViewSchemaMapping = (datasetId: string) => {
    setSchemaMappingDatasetId(datasetId);
    navigate('/datasets');
  };

  const handleIngestSuccess = () => {
    navigate('/');
  };

  // Route Guard: Loading
  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-[#0a0e16] flex items-center justify-center text-slate-400 font-mono text-xs">
        <Loader2 className="w-5 h-5 animate-spin mr-2 text-blue-500" />
        Verifying station authentication...
      </div>
    );
  }

  // Route Guard: Unauthenticated -> render real LoginPage
  if (!currentUser) {
    return <LoginPage onLogin={() => refetchUser()} />;
  }

  const openAlertsCount = alerts.filter((a) => a.status === 'open').length;

  return (
    <AppLayout
      currentPage={currentPage}
      onNavigate={handleNavigate}
      currentUser={currentUser}
      openAlertCount={openAlertsCount}
      onResetDemo={handleResetDemo}
      onLogout={handleLogout}
    >
      <Routes>
        <Route
          path="/"
          element={
            <OverviewDashboardPage
              machines={machines}
              alerts={alerts}
              onSelectMachine={handleSelectMachine}
              onOpenAlerts={() => navigate('/alerts')}
              onOpenOnboarding={() => setIsOnboardingOpen(true)}
            />
          }
        />
        <Route
          path="/overview"
          element={
            <OverviewDashboardPage
              machines={machines}
              alerts={alerts}
              onSelectMachine={handleSelectMachine}
              onOpenAlerts={() => navigate('/alerts')}
              onOpenOnboarding={() => setIsOnboardingOpen(true)}
            />
          }
        />

        <Route
          path="/fleet"
          element={
            <FleetPage
              machines={machines}
              onSelectMachine={handleSelectMachine}
            />
          }
        />

        <Route
          path="/machines"
          element={
            selectedMachine ? (
              <MachineDetailPage
                machine={selectedMachine}
                alerts={alerts}
                maintenanceRecords={maintenanceRecords.filter((r) => r.machineId === selectedMachine.id)}
                sensorHistory={sensorHistory}
                onBack={() => navigate('/fleet')}
                currentUserRole={currentUser.role}
                onAcknowledgeAlert={handleAcknowledgeAlert}
                onRecordMaintenance={handleRecordMaintenance}
              />
            ) : (
              <FleetPage
                machines={machines}
                onSelectMachine={handleSelectMachine}
              />
            )
          }
        />

        <Route
          path="/datasets"
          element={
            schemaMappingDatasetId ? (
              <DatasetSchemaMappingPage
                initialDatasetId={schemaMappingDatasetId}
                onBack={() => setSchemaMappingDatasetId('')}
                onIngestSuccess={handleIngestSuccess}
              />
            ) : (
              <DatasetsPage
                datasets={datasets}
                currentUserRole={currentUser.role}
                onOpenUploadWizard={() => {
                  const firstDs = datasets[0]?.id ? datasets[0].id : '';
                  setSchemaMappingDatasetId(firstDs);
                }}
                onViewSchemaMapping={handleViewSchemaMapping}
              />
            )
          }
        />

        <Route
          path="/alerts"
          element={
            <AlertsPage
              alerts={alerts}
              currentUserRole={currentUser.role}
              onAcknowledgeAlert={handleAcknowledgeAlert}
              onResolveAlert={handleResolveAlert}
              onSelectMachine={handleSelectMachine}
            />
          }
        />

        <Route
          path="/maintenance"
          element={
            <MaintenancePage
              records={maintenanceRecords}
              onSelectMachine={handleSelectMachine}
            />
          }
        />

        <Route
          path="/model-performance"
          element={<ModelPerformancePage />}
        />
        <Route
          path="/performance"
          element={<ModelPerformancePage />}
        />

        <Route
          path="/settings"
          element={<SettingsPage currentUserRole={currentUser.role} />}
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {/* Onboarding Tour Modal */}
      <OnboardingModal
        isOpen={isOnboardingOpen}
        onClose={() => setIsOnboardingOpen(false)}
        onStartDemoJourney={() => {
          setIsOnboardingOpen(false);
          if (machines.length > 0) {
            handleSelectMachine(machines[0].id);
          }
        }}
      />
    </AppLayout>
  );
}

export default App;
