"""
Bundle packaging and serialization for pdm_core.
Serializes model artifacts, preprocessors, reference stats, model cards, evaluations,
computes SHA-256 digests, and generates manifest.json and EXPORT_README.md.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import pandas as pd
import yaml

from pdm_core.bundle.hasher import compute_dir_hashes
from pdm_core.schemas.bundle_schemas import (
    EvaluationSchema,
    ManifestSchema,
    ModelCardSchema,
)


def get_current_library_versions() -> Dict[str, str]:
    """Captures installed versions of core ML dependencies."""
    packages = ["numpy", "pandas", "scipy", "scikit-learn", "xgboost", "shap", "joblib", "pyyaml", "pydantic"]
    versions = {}
    for pkg in packages:
        try:
            mod_name = pkg.replace("-", "_")
            mod = __import__(mod_name)
            versions[pkg] = getattr(mod, "__version__", "unknown")
        except ImportError:
            versions[pkg] = "not_installed"
    return versions


def write_failure_risk_bundle(
    target_dir: Union[str, Path],
    bundle_version: str,
    model: Any,
    preprocessing: Any,
    calibrator: Any,
    reference_stats: Dict[str, Any],
    explainer_config: Dict[str, Any],
    model_card: Union[ModelCardSchema, Dict[str, Any]],
    evaluation: Union[EvaluationSchema, Dict[str, Any]],
    input_features: List[str],
    horizon: int = 30,
    decision_threshold: float = 0.50,
    model_type: str = "xgboost",
    feature_config_version: str = "1.0.0",
    adapter_key: str = "cmapss_fd001",
) -> Path:
    """
    Serializes a complete failure_risk task bundle directory.
    """
    out = Path(target_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Model artifact
    model_path = out / "model.joblib"
    joblib.dump(model, model_path)

    # 2. Preprocessing
    preproc_path = out / "preprocessing.joblib"
    joblib.dump(preprocessing, preproc_path)

    # 3. Calibrator
    calib_path = out / "calibrator.joblib"
    joblib.dump(calibrator, calib_path)

    # 4. Reference stats
    with open(out / "reference_stats.json", "w", encoding="utf-8") as f:
        json.dump(reference_stats, f, indent=2)

    # 5. Explainer config
    with open(out / "explainer_config.json", "w", encoding="utf-8") as f:
        json.dump(explainer_config, f, indent=2)

    # 6. Model card
    if isinstance(model_card, dict):
        mc_obj = ModelCardSchema(**model_card)
    else:
        mc_obj = model_card
    with open(out / "model_card.json", "w", encoding="utf-8") as f:
        f.write(mc_obj.model_dump_json(indent=2))

    # 7. Evaluation
    if isinstance(evaluation, dict):
        eval_obj = EvaluationSchema(**evaluation)
    else:
        eval_obj = evaluation
    with open(out / "evaluation.json", "w", encoding="utf-8") as f:
        f.write(eval_obj.model_dump_json(indent=2))

    # 8. Compute hashes for all serialized artifacts
    file_hashes = compute_dir_hashes(out, exclude_manifest=True)

    # 9. Write manifest.json
    manifest = ManifestSchema(
        bundle_version=bundle_version,
        task="failure_risk",
        model_type=model_type,
        adapter_key=adapter_key,
        feature_config_version=feature_config_version,
        preprocessing_version=file_hashes.get("preprocessing.joblib", "unknown")[:16],
        input_features=input_features,
        horizon=horizon,
        horizon_unit="cycles",
        decision_threshold=decision_threshold,
        created_at=datetime.now(timezone.utc).isoformat(),
        python_version=sys.version.split()[0],
        library_versions=get_current_library_versions(),
        file_sha256=file_hashes,
    )

    with open(out / "manifest.json", "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    return out


def write_anomaly_bundle(
    target_dir: Union[str, Path],
    bundle_version: str,
    model: Any,
    preprocessing: Any,
    healthy_score_quantiles: Dict[str, float],
    baseline_stats: Dict[str, Any],
    reference_stats: Dict[str, Any],
    model_card: Union[ModelCardSchema, Dict[str, Any]],
    evaluation: Union[EvaluationSchema, Dict[str, Any]],
    input_features: List[str],
    model_type: str = "isolation_forest",
    feature_config_version: str = "1.0.0",
    adapter_key: str = "cmapss_fd001",
) -> Path:
    """
    Serializes a complete anomaly task bundle directory.
    """
    out = Path(target_dir)
    out.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, out / "model.joblib")
    joblib.dump(preprocessing, out / "preprocessing.joblib")

    with open(out / "healthy_score_quantiles.json", "w", encoding="utf-8") as f:
        json.dump(healthy_score_quantiles, f, indent=2)

    with open(out / "baseline_stats.json", "w", encoding="utf-8") as f:
        json.dump(baseline_stats, f, indent=2)

    with open(out / "reference_stats.json", "w", encoding="utf-8") as f:
        json.dump(reference_stats, f, indent=2)

    if isinstance(model_card, dict):
        mc_obj = ModelCardSchema(**model_card)
    else:
        mc_obj = model_card
    with open(out / "model_card.json", "w", encoding="utf-8") as f:
        f.write(mc_obj.model_dump_json(indent=2))

    if isinstance(evaluation, dict):
        eval_obj = EvaluationSchema(**evaluation)
    else:
        eval_obj = evaluation
    with open(out / "evaluation.json", "w", encoding="utf-8") as f:
        f.write(eval_obj.model_dump_json(indent=2))

    file_hashes = compute_dir_hashes(out, exclude_manifest=True)

    manifest = ManifestSchema(
        bundle_version=bundle_version,
        task="anomaly",
        model_type=model_type,
        adapter_key=adapter_key,
        feature_config_version=feature_config_version,
        preprocessing_version=file_hashes.get("preprocessing.joblib", "unknown")[:16],
        input_features=input_features,
        horizon=None,
        horizon_unit=None,
        decision_threshold=None,
        created_at=datetime.now(timezone.utc).isoformat(),
        python_version=sys.version.split()[0],
        library_versions=get_current_library_versions(),
        file_sha256=file_hashes,
    )

    with open(out / "manifest.json", "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    return out


def generate_export_readme(bundle_dir: Path, version: str) -> str:
    """Generates EXPORT_README.md documentation for registering the bundle."""
    return f"""# Model Bundle {version} Export Documentation

This bundle was generated offline (Google Colab / pdm_core) and conforms to the Predict-Ai PRD v3.0 Bundle Contract.

## Contents
- `feature_config.yaml`: Feature engineering pipeline configuration.
- `demo_candidates.csv`: Held-out C-MAPSS FD001 engines for deterministic demo mode seeding.
- `failure_risk/`: Calibrated classification model for $P(\\text{{Fail}} \\le H)$.
- `anomaly/`: Unsupervised anomaly detection model and baseline score quantiles.

## Registration Instructions
To validate and register this bundle into the Predict-Ai platform:

```bash
# 1. Validate bundle integrity and contracts
python -m pdm_core.bundle validate {bundle_dir.as_posix()}

# 2. Register into backend database (Phase 4 CLI)
python -m app.cli register-model --bundle-dir {bundle_dir.as_posix()} --activate
```
"""


def write_complete_bundle(
    target_root: Union[str, Path],
    version: str,
    feature_config_content: Union[str, Path, Dict[str, Any]],
    demo_candidates_df: pd.DataFrame,
    failure_risk_kwargs: Dict[str, Any],
    anomaly_kwargs: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Assembles a complete bundle_<version> package adhering to the PRD §5 contract.
    """
    root = Path(target_root) / f"bundle_{version}"
    root.mkdir(parents=True, exist_ok=True)

    # 1. feature_config.yaml
    if isinstance(feature_config_content, (str, Path)) and Path(feature_config_content).is_file():
        with open(feature_config_content, "r", encoding="utf-8") as src, open(
            root / "feature_config.yaml", "w", encoding="utf-8"
        ) as dst:
            dst.write(src.read())
    elif isinstance(feature_config_content, dict):
        with open(root / "feature_config.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(feature_config_content, f)
    else:
        with open(root / "feature_config.yaml", "w", encoding="utf-8") as f:
            f.write(str(feature_config_content))

    # 2. demo_candidates.csv
    demo_candidates_df.to_csv(root / "demo_candidates.csv", index=False)

    # 3. failure_risk sub-bundle
    write_failure_risk_bundle(
        target_dir=root / "failure_risk",
        bundle_version=version,
        **failure_risk_kwargs,
    )

    # 4. anomaly sub-bundle (if supplied)
    if anomaly_kwargs is not None:
        write_anomaly_bundle(
            target_dir=root / "anomaly",
            bundle_version=version,
            **anomaly_kwargs,
        )

    # 5. EXPORT_README.md
    with open(root / "EXPORT_README.md", "w", encoding="utf-8") as f:
        f.write(generate_export_readme(root, version))

    return root
