export type Role = 'admin' | 'engineer';

export type MachineStatus = 'active' | 'maintenance' | 'archived';
export type HealthBand = 'Critical' | 'Poor' | 'Warning' | 'Healthy' | 'Excellent';
export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical';
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AlertStatus = 'open' | 'acknowledged' | 'resolved';
export type ReliabilityStatus = 'ok' | 'reduced';
export type MaintenanceStatus = 'recommended' | 'in_progress' | 'completed' | 'cancelled';
export type MaintenanceOutcome = 'resolved' | 'unresolved' | 'no_issue_found';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: Role;
}

export interface HealthComponents {
  failureRiskPenalty: number; // e.g. 50 * s_risk
  anomalyPenalty: number;     // e.g. 30 * s_anom
  trendPenalty: number;       // e.g. 20 * s_trend
  otherPenalty: number;
}

export interface PredictionLineage {
  machineCode: string;
  datasetName: string;
  datasetVersion: string | null;
  schemaMappingHash: string | null;
  featureConfigVersion: string | null;
  preprocessingVersion: string | null;
  failureModelVersion: string | null;
  anomalyModelVersion: string | null;
  predictionHorizon: number | null;
  predictionHorizonUnit: string | null;
  asOfCycle: number | null;
  predictedAt: string;
  inputWindowLength: number | null;
}

export interface PredictionExplanation {
  headline: string;
  topContributingFeatures: Array<{
    feature: string; // e.g. "sensor_11", "sensor_9"
    direction: 'raises' | 'lowers';
    weight: number;
    value: number;
    baselineRef: string;
  }>;
  trendFacts: string[];
  summaryText: string;
}

export interface Machine {
  id: string;
  machineCode: string;
  name: string;
  machineType: string;
  location: string;
  installDate: string;
  operationalStatus: MachineStatus;
  healthIndicator: number | null;
  healthBand: HealthBand;
  healthComponents: HealthComponents;
  failureProbability: number;   // 0.0 until first score, then real value
  predictionHorizon: number | null;
  riskLevel: RiskLevel;
  currentCycle: number | null;
  anomalySeverity: number | null;
  anomalyScore: number | null;
  anomalyStatus: 'normal' | 'warning' | 'anomaly';
  reliabilityStatus: ReliabilityStatus;
  reliabilityWarningReason?: string;
  datasetBadge: string;
  lastUpdated: string;
  explanation: PredictionExplanation;
  recommendation: {
    ruleId: string;
    text: string;
    priority: 'low' | 'medium' | 'high' | 'urgent';
    rationale: string;
  };
  lineage: PredictionLineage;
}

export interface SensorReading {
  cycle: number;
  sensor_1?: number;
  sensor_2?: number;
  sensor_3?: number;
  sensor_4?: number;
  sensor_7?: number;
  sensor_8?: number;
  sensor_9?: number;
  sensor_11?: number;
  sensor_12?: number;
  sensor_13?: number;
  sensor_14?: number;
  sensor_15?: number;
  sensor_17?: number;
  sensor_20?: number;
  sensor_21?: number;
  op_setting_1?: number;
  op_setting_2?: number;
  op_setting_3?: number;
  isAnomaly?: boolean;
  isImputed?: boolean;
}

export interface Alert {
  id: string;
  machineId: string;
  machineCode: string;
  machineName: string;
  type: 'high_failure_risk' | 'severe_anomaly' | 'rapid_deterioration';
  severity: AlertSeverity;
  status: AlertStatus;
  asOfCycle: number;
  triggeredAt: string;
  message: string;
  reliabilityStatus: ReliabilityStatus;
  recommendationText: string;
  recommendationRuleId: string;
  acknowledgedBy?: string;
  acknowledgedAt?: string;
  resolvedBy?: string;
  resolvedAt?: string;
  resolutionNote?: string;
  resolutionType?: 'issue_resolved' | 'false_alarm' | 'no_action_needed';
}

export interface MaintenanceRecord {
  id: string;
  machineId: string;
  machineCode: string;
  alertId?: string;
  issue: string;
  recommendedAction: string;
  decision: 'followed_recommendation' | 'modified' | 'declined';
  decisionRationale: string;
  actionTaken: string;
  performedBy: string;
  performedAt: string;
  status: MaintenanceStatus;
  outcome: MaintenanceOutcome;
  notes: string;
}

export interface Dataset {
  id: string;
  name: string;
  version: string;
  adapterKey: string;
  adapterVersion: string;
  dataOrigin: 'simulated' | 'synthetic' | 'real';
  isDemo: boolean;
  status: 'uploaded' | 'validated' | 'ingested' | 'rejected_incompatible';
  checksumSha256: string;
  rowCount: number;
  unitCount: number;
  uploadedBy: string;
  uploadedAt: string;
}

export interface CompatibilityCheckItem {
  rule: string;
  severity: 'error' | 'warning';
  expected: string;
  found: string;
  howToFix: string;
  passed: boolean;
}

export interface ModelVersion {
  id: string;
  name: string;
  task: 'failure_risk' | 'anomaly';
  modelType: string; // e.g. "LightGBM Classifier", "Isolation Forest"
  version: string;
  adapterKey: string;
  status: 'active' | 'registered' | 'retired';
  horizon: number | null;
  horizonUnit: string | null;
  decisionThreshold: number;
  trainingDataset: string;
  trainingDate: string;
  gitCommit: string;
  modelCard: {
    targetDefinition: string;
    calibrationInfo: string;
    featuresUsed: string[];
    intendedUse: string;
    limitations: string;
  };
}

export interface ModelEvaluation {
  modelId: string;
  modelVersion: string;
  evaluatedAt: string;
  evaluationDataset: string;
  splitProtocol: string;
  metrics: {
    prAuc: number;
    rocAuc: number;
    precision: number;
    recall: number;
    f1Score: number;
    brierScore: number;
    baselinePrAuc: number;
    baselineRocAuc: number;
  };
  confusionMatrix: {
    tp: number;
    fp: number;
    fn: number;
    tn: number;
  };
  prCurve: Array<{ recall: number; precision: number }>;
  rocCurve: Array<{ fpr: number; tpr: number }>;
  calibrationCurve: Array<{ meanPredictedValue: number; fractionOfPositives: number }>;
  featureImportance: Array<{ feature: string; importance: number }>;
}
