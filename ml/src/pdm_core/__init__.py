"""
pdm_core - Shared Predictive Maintenance ML Library
Shared identically between Google Colab offline training and FastAPI backend runtime.
"""

from pdm_core.bundle import (
    ValidationResult,
    validate_model_bundle,
    write_anomaly_bundle,
    write_complete_bundle,
    write_failure_risk_bundle,
)
from pdm_core.data import (
    CANONICAL_COLUMNS,
    CYCLE_COL,
    UNIT_COL,
    compute_test_rul,
    compute_train_rul,
    load_fd001_raw,
)
from pdm_core.evaluation import compute_evaluation, save_evaluation_json
from pdm_core.explain import (
    compute_feature_attributions,
    compute_linear_contribution,
    compute_tree_shap,
)
from pdm_core.features import (
    extract_features,
    get_feature_names,
    load_feature_config,
)
from pdm_core.labels import assign_binary_labels
from pdm_core.schemas import (
    EvaluationSchema,
    ManifestSchema,
    ModelCardSchema,
)
from pdm_core.splits import engine_grouped_split, get_engine_split_ids

__version__ = "0.1.0"

__all__ = [
    "CANONICAL_COLUMNS",
    "CYCLE_COL",
    "EvaluationSchema",
    "ManifestSchema",
    "ModelCardSchema",
    "UNIT_COL",
    "ValidationResult",
    "assign_binary_labels",
    "compute_evaluation",
    "compute_feature_attributions",
    "compute_linear_contribution",
    "compute_test_rul",
    "compute_train_rul",
    "compute_tree_shap",
    "engine_grouped_split",
    "extract_features",
    "get_engine_split_ids",
    "get_feature_names",
    "load_fd001_raw",
    "load_feature_config",
    "save_evaluation_json",
    "validate_model_bundle",
    "write_anomaly_bundle",
    "write_complete_bundle",
    "write_failure_risk_bundle",
]
