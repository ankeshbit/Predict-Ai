"""
Canonical schema definitions for pdm_core
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConfusionMatrixSchema(BaseModel):
    threshold: float = 0.5
    tp: int
    fp: int
    tn: int
    fn: int


class CalibrationCurveSchema(BaseModel):
    prob_pred: List[float]
    prob_true: List[float]
    bin_counts: List[int]


class CurvePointSchema(BaseModel):
    x: List[float]
    y: List[float]
    thresholds: Optional[List[float]] = None


class CurvesSchema(BaseModel):
    roc_curve: CurvePointSchema
    pr_curve: CurvePointSchema


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


class EvaluationMetricsSchema(BaseModel):
    pr_auc: float
    roc_auc: float
    precision: float
    recall: float
    f1_score: float
    brier_score: float
    expected_calibration_error: float


class EvaluationSchema(BaseModel):
    task: str = Field(..., description="'failure_risk' or 'anomaly'")
    model_name: str
    model_version: str
    evaluation_date: str
    metrics: EvaluationMetricsSchema
    confusion_matrix: ConfusionMatrixSchema
    calibration_curve: CalibrationCurveSchema
    curves: CurvesSchema
    feature_importance: List[FeatureImportanceItem]
    methodology: str
    limitations: List[str]


class ModelCardSchema(BaseModel):
    model_name: str
    version: str
    description: str
    model_type: str
    intended_use: str
    domain: str = "Simulated Turbofan Degradation (NASA C-MAPSS FD001)"
    training_dataset: str = "NASA C-MAPSS FD001 Train"
    evaluation_dataset: str = "NASA C-MAPSS FD001 Test"
    feature_summary: List[str]
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    operational_limitations: List[str] = Field(default_factory=list)
    ethical_considerations: List[str] = Field(default_factory=list)
    author: str
    created_at: str


class ManifestSchema(BaseModel):
    bundle_version: str
    task: str = Field(..., description="'failure_risk' or 'anomaly'")
    model_type: str
    adapter_key: str = "cmapss_fd001"
    feature_config_version: str
    preprocessing_version: str
    input_features: List[str]
    horizon: Optional[int] = None
    horizon_unit: Optional[str] = None
    decision_threshold: Optional[float] = None
    created_at: str
    git_commit: Optional[str] = None
    python_version: str
    library_versions: Dict[str, str]
    file_sha256: Dict[str, str]
