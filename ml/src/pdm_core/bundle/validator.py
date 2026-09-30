"""
Validation engine for pdm_core model bundles.
Enforces the PRD v3.0 Bundle Contract, schema completeness, and SHA-256 cryptographic integrity.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd
import yaml
from pydantic import ValidationError

from pdm_core.bundle.hasher import compute_file_sha256
from pdm_core.schemas.bundle_schemas import (
    EvaluationSchema,
    ManifestSchema,
    ModelCardSchema,
)


@dataclass
class ValidationResult:
    valid: bool
    path: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    manifest: Optional[ManifestSchema] = None
    model_card: Optional[ModelCardSchema] = None
    evaluation: Optional[EvaluationSchema] = None

    def add_error(self, msg: str):
        self.errors.append(msg)
        self.valid = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)


def validate_sub_bundle(sub_dir: Path, expected_task: Optional[str] = None) -> ValidationResult:
    """
    Validates a task-specific sub-bundle directory (e.g. failure_risk or anomaly).
    """
    result = ValidationResult(valid=True, path=str(sub_dir))

    if not sub_dir.is_dir():
        result.add_error(f"Directory not found: {sub_dir}")
        return result

    manifest_path = sub_dir / "manifest.json"
    if not manifest_path.is_file():
        result.add_error("Missing required file: manifest.json")
        return result

    # 1. Parse & validate manifest.json
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        manifest = ManifestSchema(**manifest_data)
        result.manifest = manifest
    except (json.JSONDecodeError, ValidationError) as e:
        result.add_error(f"Invalid manifest.json schema: {e}")
        return result

    if expected_task and manifest.task != expected_task:
        result.add_error(f"Task mismatch in manifest: expected '{expected_task}', got '{manifest.task}'")

    # 2. Check required files per task
    if manifest.task == "failure_risk":
        required_files = [
            "preprocessing.joblib",
            "calibrator.joblib",
            "reference_stats.json",
            "explainer_config.json",
            "model_card.json",
            "evaluation.json",
        ]
        # Check model file (model.joblib or model.json or model.ubj)
        model_candidates = ["model.joblib", "model.json", "model.ubj"]
        if not any((sub_dir / m).is_file() for m in model_candidates):
            result.add_error(f"Missing model artifact. Expected one of: {model_candidates}")
    elif manifest.task == "anomaly":
        required_files = [
            "preprocessing.joblib",
            "healthy_score_quantiles.json",
            "baseline_stats.json",
            "reference_stats.json",
            "model_card.json",
            "evaluation.json",
        ]
        if not (sub_dir / "model.joblib").is_file():
            result.add_error("Missing model artifact: model.joblib")
    else:
        result.add_error(f"Unknown task type in manifest: '{manifest.task}'")
        return result

    for rf in required_files:
        if not (sub_dir / rf).is_file():
            result.add_error(f"Missing required task file: {rf}")

    # 3. Validate model_card.json
    mc_path = sub_dir / "model_card.json"
    if mc_path.is_file():
        try:
            with open(mc_path, "r", encoding="utf-8") as f:
                mc_data = json.load(f)
            result.model_card = ModelCardSchema(**mc_data)
            if not result.model_card.operational_limitations:
                result.add_warning("Model card does not list any operational limitations")
        except (json.JSONDecodeError, ValidationError) as e:
            result.add_error(f"Invalid model_card.json schema: {e}")

    # 4. Validate evaluation.json
    eval_path = sub_dir / "evaluation.json"
    if eval_path.is_file():
        try:
            with open(eval_path, "r", encoding="utf-8") as f:
                eval_data = json.load(f)
            result.evaluation = EvaluationSchema(**eval_data)

            # Check curve downsampling constraints (<= 50 points per PRD)
            roc_pts = len(result.evaluation.curves.roc_curve.x)
            pr_pts = len(result.evaluation.curves.pr_curve.x)
            if roc_pts > 50:
                result.add_error(f"ROC curve points exceed PRD maximum 50: found {roc_pts}")
            if pr_pts > 50:
                result.add_error(f"PR curve points exceed PRD maximum 50: found {pr_pts}")
        except (json.JSONDecodeError, ValidationError) as e:
            result.add_error(f"Invalid evaluation.json schema: {e}")

    # 5. Cryptographic SHA-256 validation
    for rel_path, expected_hash in manifest.file_sha256.items():
        target_file = sub_dir / rel_path
        if not target_file.is_file():
            result.add_error(f"File listed in manifest hash table is missing from bundle: {rel_path}")
            continue
        actual_hash = compute_file_sha256(target_file)
        if actual_hash.lower() != expected_hash.lower():
            result.add_error(
                f"SHA-256 mismatch for {rel_path}: expected {expected_hash}, found {actual_hash}"
            )

    return result


def validate_model_bundle(bundle_path: Union[str, Path]) -> ValidationResult:
    """
    Validates a model bundle (either a complete root bundle_<version>/ directory
    or a specific task sub-bundle like failure_risk).
    """
    p = Path(bundle_path)
    if not p.exists():
        return ValidationResult(valid=False, path=str(p), errors=[f"Path does not exist: {p}"])

    # If pointing directly to a task sub-bundle with manifest.json
    if (p / "manifest.json").is_file():
        return validate_sub_bundle(p)

    # Otherwise validate root bundle package
    root_result = ValidationResult(valid=True, path=str(p))

    # Check root required files
    feature_cfg_path = p / "feature_config.yaml"
    if not feature_cfg_path.is_file():
        root_result.add_error("Missing required bundle file: feature_config.yaml")
    else:
        try:
            with open(feature_cfg_path, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except Exception as e:
            root_result.add_error(f"Corrupt feature_config.yaml: {e}")

    demo_cand_path = p / "demo_candidates.csv"
    if not demo_cand_path.is_file():
        root_result.add_error("Missing required bundle file: demo_candidates.csv")
    else:
        try:
            demo_df = pd.read_csv(demo_cand_path, nrows=5)
            if "unit_id" not in demo_df.columns or "cycle" not in demo_df.columns:
                root_result.add_error("demo_candidates.csv missing required C-MAPSS columns: unit_id, cycle")
        except Exception as e:
            root_result.add_error(f"Cannot read demo_candidates.csv: {e}")

    export_readme_path = p / "EXPORT_README.md"
    if not export_readme_path.is_file():
        root_result.add_warning("Missing EXPORT_README.md in bundle root")

    # Check sub-bundles
    failure_risk_dir = p / "failure_risk"
    if not failure_risk_dir.is_dir():
        root_result.add_error("Missing required sub-bundle directory: failure_risk/")
    else:
        sub_res = validate_sub_bundle(failure_risk_dir, expected_task="failure_risk")
        if not sub_res.valid:
            root_result.valid = False
            root_result.errors.extend([f"failure_risk/{e}" for e in sub_res.errors])
        root_result.warnings.extend([f"failure_risk/{w}" for w in sub_res.warnings])
        root_result.manifest = sub_res.manifest
        root_result.model_card = sub_res.model_card
        root_result.evaluation = sub_res.evaluation

    anomaly_dir = p / "anomaly"
    if anomaly_dir.is_dir():
        anom_res = validate_sub_bundle(anomaly_dir, expected_task="anomaly")
        if not anom_res.valid:
            root_result.valid = False
            root_result.errors.extend([f"anomaly/{e}" for e in anom_res.errors])
        root_result.warnings.extend([f"anomaly/{w}" for w in anom_res.warnings])

    return root_result
