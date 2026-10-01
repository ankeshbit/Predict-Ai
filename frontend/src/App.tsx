import { useState } from 'react';
import type { User, Role, Machine, Alert, MaintenanceRecord } from './types';
import {
  INITIAL_MACHINES,
  INITIAL_ALERTS,
  INITIAL_MAINTENANCE_RECORDS,
  INITIAL_DATASETS,
  INITIAL_MODELS,
  INITIAL_EVALUATION,
  generateSensorHistory,
} from './mockData/demoData';

import { AppLayout } from './components/layout/AppLayout';
import type { NavPage } from './components/layout/Sidebar';
import { LoginPage } from './pages/LoginPage';
import { OnboardingModal } from './pages/OnboardingModal';
import { OverviewDashboardPage } from './pages/OverviewDashboardPage';
import { FleetPage } from './pages/FleetPage';
import { MachineDetailPage } from './pages/MachineDetailPage';
import { DatasetsPage } from './pages/DatasetsPage';
import { DatasetSchemaMappingPage } from './pages/DatasetSchemaMappingPage';
import { PredictionsPage } from './pages/PredictionsPage';
import { AlertsPage } from './pages/AlertsPage';
import { MaintenancePage } from './pages/MaintenancePage';
import { ModelPerformancePage } from './pages/ModelPerformancePage';
import { ModelRegistryPage } from './pages/ModelRegistryPage';
import { SettingsPage } from './pages/SettingsPage';

import { useResetDemo } from './api';

export function App() {
  const resetDemoMutation = useResetDemo();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(true);
  const [currentUser, setCurrentUser] = useState<User>({
    id: 'usr-eng-01',
    email: 'engineer@demo.internal',
    fullName: 'Alex Vance (Engineer)',
    role: 'engineer',
  });

  const [currentPage, setCurrentPage] = useState<NavPage>('overview');
  const [selectedMachineId, setSelectedMachineId] = useState<string>('m-fd001-03');
  const [isOnboardingOpen, setIsOnboardingOpen] = useState<boolean>(false);

  // Core application entities (seeded demo state)
  const [machines, setMachines] = useState<Machine[]>(INITIAL_MACHINES);
  const [alerts, setAlerts] = useState<Alert[]>(INITIAL_ALERTS);
  const [maintenanceRecords, setMaintenanceRecords] = useState<MaintenanceRecord[]>(INITIAL_MAINTENANCE_RECORDS);
  const [datasets, setDatasets] = useState(INITIAL_DATASETS);
  const [schemaMappingDatasetId, setSchemaMappingDatasetId] = useState<string>('ds-ai4i-sample');

  // Login handler
  const handleLogin = (role: Role) => {
    setCurrentUser({
      id: role === 'admin' ? 'usr-adm-01' : 'usr-eng-01',
      email: role === 'admin' ? 'admin@demo.internal' : 'engineer@demo.internal',
      fullName: role === 'admin' ? 'Chief Administrator' : 'Demo Reliability Engineer',
      role,
    });
    setIsAuthenticated(true);
    setCurrentPage('overview');
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
  };

  const handleSwitchRole = (role: Role) => {
    setCurrentUser((prev) => ({
      ...prev,
      role,
      fullName: role === 'admin' ? 'Chief Administrator' : 'Demo Reliability Engineer',
      email: role === 'admin' ? 'admin@demo.internal' : 'engineer@demo.internal',
    }));
  };

  // PRD §FR-2 & FR-11 Reset Demo Data action
  const handleResetDemo = () => {
    setMachines(INITIAL_MACHINES);
    setAlerts(INITIAL_ALERTS);
    setMaintenanceRecords(INITIAL_MAINTENANCE_RECORDS);
    setDatasets(INITIAL_DATASETS);
    resetDemoMutation.mutate(undefined, {
      onError: (err) => {
        console.warn('Backend demo reset skipped or unavailable:', err);
      },
    });
  };

  // Alert acknowledgment
  const handleAcknowledgeAlert = (alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === alertId
          ? {
              ...a,
              status: 'acknowledged',
              acknowledgedBy: currentUser.email,
              acknowledgedAt: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
            }
          : a
      )
    );
  };

  // Alert resolution
  const handleResolveAlert = (
    alertId: string,
    resolutionType: 'issue_resolved' | 'false_alarm' | 'no_action_needed',
    note: string
  ) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === alertId
          ? {
              ...a,
              status: 'resolved',
              resolutionType,
              resolutionNote: note,
              resolvedBy: currentUser.email,
              resolvedAt: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
            }
          : a
      )
    );
  };

  // Record maintenance action & synchronize machine operational status (PRD §FR-14)
  const handleRecordMaintenance = (
    recordData: Omit<MaintenanceRecord, 'id' | 'performedAt'>
  ) => {
    const newRecord: MaintenanceRecord = {
      ...recordData,
      id: `maint-${Date.now()}`,
      performedAt: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
    };

    setMaintenanceRecords((prev) => [newRecord, ...prev]);

    // Machine status side-effect per PRD §FR-14:
    // in_progress sets operational_status to maintenance
    // completed with resolved or no_issue_found returns it to active
    setMachines((prev) =>
      prev.map((m) => {
        if (m.id === recordData.machineId) {
          const nextStatus =
            recordData.status === 'in_progress'
              ? 'maintenance'
              : recordData.outcome === 'resolved' || recordData.outcome === 'no_issue_found'
              ? 'active'
              : m.operationalStatus;
          return {
            ...m,
            operationalStatus: nextStatus,
          };
        }
        return m;
      })
    );

    // If related alert exists and outcome is resolved, auto-resolve alert
    if (recordData.alertId && (recordData.outcome === 'resolved' || recordData.outcome === 'no_issue_found')) {
      handleResolveAlert(recordData.alertId, 'issue_resolved', recordData.actionTaken);
    }
  };

  // Open machine detail page
  const handleSelectMachine = (machineId: string) => {
    setSelectedMachineId(machineId);
    setCurrentPage('machines');
  };

  // Open schema mapping page for a dataset
  const handleViewSchemaMapping = (datasetId: string) => {
    setSchemaMappingDatasetId(datasetId);
    setCurrentPage('datasets');
  };

  // Ingestion success simulation
  const handleIngestSuccess = () => {
    setCurrentPage('overview');
  };

  const selectedMachine =
    machines.find((m) => m.id === selectedMachineId) || machines[0];
  const openAlertsCount = alerts.filter((a) => a.status === 'open').length;

  // Unauthenticated screen
  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <AppLayout
      currentPage={currentPage}
      onNavigate={setCurrentPage}
      currentUser={currentUser}
      onSwitchRole={handleSwitchRole}
      openAlertCount={openAlertsCount}
      onResetDemo={handleResetDemo}
      onLogout={handleLogout}
    >
      {/* Overview Dashboard */}
      {currentPage === 'overview' && (
        <OverviewDashboardPage
          machines={machines}
          alerts={alerts}
          onSelectMachine={handleSelectMachine}
          onOpenAlerts={() => setCurrentPage('alerts')}
          onOpenOnboarding={() => setIsOnboardingOpen(true)}
        />
      )}

      {/* Fleet List / Grid */}
      {currentPage === 'fleet' && (
        <FleetPage
          machines={machines}
          onSelectMachine={handleSelectMachine}
        />
      )}

      {/* Machine Details */}
      {currentPage === 'machines' && (
        <MachineDetailPage
          machine={selectedMachine}
          alerts={alerts}
          maintenanceRecords={maintenanceRecords.filter(
            (r) => r.machineId === selectedMachine.id
          )}
          sensorHistory={generateSensorHistory(
            selectedMachine.id,
            selectedMachine.currentCycle
          )}
          onBack={() => setCurrentPage('fleet')}
          currentUserRole={currentUser.role}
          onAcknowledgeAlert={handleAcknowledgeAlert}
          onRecordMaintenance={handleRecordMaintenance}
        />
      )}

      {/* Datasets List or Schema Mapping Wizard */}
      {currentPage === 'datasets' && (
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
              setSchemaMappingDatasetId('ds-fd001-demo');
            }}
            onViewSchemaMapping={handleViewSchemaMapping}
          />
        )
      )}

      {/* Predictions & Scoring Runs */}
      {currentPage === 'predictions' && (
        <PredictionsPage
          machines={machines}
          currentUserRole={currentUser.role}
          onSelectMachine={handleSelectMachine}
        />
      )}

      {/* Alerts */}
      {currentPage === 'alerts' && (
        <AlertsPage
          alerts={alerts}
          currentUserRole={currentUser.role}
          onAcknowledgeAlert={handleAcknowledgeAlert}
          onResolveAlert={handleResolveAlert}
          onSelectMachine={handleSelectMachine}
        />
      )}

      {/* Maintenance */}
      {currentPage === 'maintenance' && (
        <MaintenancePage
          records={maintenanceRecords}
          onSelectMachine={handleSelectMachine}
        />
      )}

      {/* Model Performance */}
      {currentPage === 'model-performance' && (
        <ModelPerformancePage
          evaluation={INITIAL_EVALUATION}
          activeModels={INITIAL_MODELS}
        />
      )}

      {/* Model Registry */}
      {currentPage === 'models' && (
        <ModelRegistryPage
          models={INITIAL_MODELS}
          onViewModelPerformance={() => setCurrentPage('model-performance')}
        />
      )}

      {/* Settings */}
      {currentPage === 'settings' && (
        <SettingsPage currentUserRole={currentUser.role} />
      )}

      {/* First-Run Onboarding Acceptance Modal */}
      <OnboardingModal
        isOpen={isOnboardingOpen}
        onClose={() => setIsOnboardingOpen(false)}
        onStartDemoJourney={() => {
          setIsOnboardingOpen(false);
          handleSelectMachine('m-fd001-03');
        }}
      />
    </AppLayout>
  );
}

export default App;
