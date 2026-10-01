"""
Model Artifact and Demo Fleet Importer Service for Predict-Ai (PrediCore).

Handles:
1. Importing model bundles into model_versions and model_evaluations
2. Verifying bundle manifest and runtime library compatibility
3. Seeding the held-out demo engines from demo_units.csv and demo_reference_scores.csv
   into Healthy, Warning, and Critical demo machines.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

import numpy as np
import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.db import engine
from app.ml.verify_artifacts import ArtifactVerificationError, verify_all
from app.models.entities import (
    HealthIndicatorConfig,
    Machine,
    ModelEvaluation,
    ModelVersion,
    Prediction,
    SensorReading,
)

logger = logging.getLogger(__name__)


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def register_model_bundle(
    bundle_path: str | Path,
    activate: bool = True,
    strict_versions: bool = False,
    session: Optional[Session] = None,
) -> ModelVersion:
    """Reads metadata/model_card.json, evaluation/curves.json and feature_importance.json

    from the artifact bundle directory, verifies the manifest and library versions,
    and registers records into model_versions and model_evaluations tables.
    """
    root = Path(bundle_path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Model bundle directory not found: {root}")

    # 1. Run full manifest + library verification
    metadata = verify_all(root, strict_versions=strict_versions)

    # 2. Read required metadata files
    model_card_path = root / "metadata" / "model_card.json"
    curves_path = root / "evaluation" / "curves.json"
    feature_imp_path = root / "evaluation" / "feature_importance.json"

    if not model_card_path.is_file():
        raise FileNotFoundError(f"Missing required model card: {model_card_path}")
    if not curves_path.is_file():
        raise FileNotFoundError(f"Missing required curves file: {curves_path}")
    if not feature_imp_path.is_file():
        raise FileNotFoundError(f"Missing required feature importance file: {feature_imp_path}")

    model_card = json.loads(model_card_path.read_text(encoding="utf-8"))
    curves = json.loads(curves_path.read_text(encoding="utf-8"))
    feature_importance = json.loads(feature_imp_path.read_text(encoding="utf-8"))

    # Extract version details
    model_version_str = model_card.get("model_version", metadata.get("model_version", root.name))
    training_methodology = model_card.get("training_methodology", {})
    selected_model = training_methodology.get("selected_model", "XGBoostClassifier")
    features_info = model_card.get("features", {})
    active_sensors = features_info.get("active_sensors", metadata.get("feature_config", {}).get("active_sensors", []))
    horizon_info = model_card.get("failure_horizon", {})
    horizon_val = horizon_info.get("value", 30)
    horizon_unit = horizon_info.get("unit", "operating_cycles")
    threshold_info = training_methodology.get("threshold", {})
    decision_threshold = threshold_info.get("value", 0.50)
    metrics_data = model_card.get("metrics", {})
    limitations_data = model_card.get("limitations", [])

    # Methodology string representation
    methodology_text = json.dumps(
        {
            "training_methodology": training_methodology,
            "evaluation_methodology": model_card.get("evaluation_methodology", []),
        },
        indent=2,
    )

    # Confusion matrix and calibration from internal_test or fallback
    internal_test_curves = curves.get("internal_test", {})
    confusion_matrix_data = internal_test_curves.get("confusion_matrix", {})
    calibration_curve_data = internal_test_curves.get("calibration", {})

    features_list = feature_importance.get("features", [])

    # Bundle hash (manifest sha256 or folder signature)
    manifest_path = root / "metadata" / "artifact_manifest.json"
    bundle_hash = compute_sha256(manifest_path) if manifest_path.is_file() else "unknown"

    def _execute_import(db: Session) -> ModelVersion:
        # Check if already registered
        existing = db.scalar(
            select(ModelVersion).where(ModelVersion.bundle_version == model_version_str)
        )

        if activate:
            # Deactivate previous active model for this adapter and task
            db.execute(
                update(ModelVersion)
                .where(
                    ModelVersion.adapter_key == "cmapss_fd001",
                    ModelVersion.task == "failure_risk",
                    ModelVersion.is_active.is_(True),
                )
                .values(is_active=False)
            )

        if existing:
            mv = existing
            mv.model_type = selected_model
            mv.input_features = active_sensors
            mv.horizon = horizon_val
            mv.horizon_unit = horizon_unit
            mv.decision_threshold = decision_threshold
            mv.model_card_complete = True
            mv.artifact_path = str(root)
            mv.sha256_hash = bundle_hash
            mv.python_version = metadata.get("library_versions", {}).get("python", "3.10.0")
            mv.is_active = activate
        else:
            mv = ModelVersion(
                id=uuid.uuid4(),
                bundle_version=model_version_str,
                task="failure_risk",
                model_type=selected_model,
                adapter_key="cmapss_fd001",
                feature_config_version="v1.0",
                preprocessing_version="v1.0",
                input_features=active_sensors,
                horizon=horizon_val,
                horizon_unit=horizon_unit,
                decision_threshold=decision_threshold,
                is_active=activate,
                model_card_complete=True,
                artifact_path=str(root),
                sha256_hash=bundle_hash,
                python_version=metadata.get("library_versions", {}).get("python", "3.10.0"),
            )
            db.add(mv)
            db.flush()

        # Update or create ModelEvaluation
        existing_eval = db.scalar(
            select(ModelEvaluation).where(ModelEvaluation.model_version_id == mv.id)
        )
        if existing_eval:
            me = existing_eval
            me.metrics = metrics_data
            me.confusion_matrix = confusion_matrix_data
            me.calibration_curve = calibration_curve_data
            me.curves = curves
            me.feature_importance = features_list
            me.methodology = methodology_text
            me.limitations = limitations_data
        else:
            me = ModelEvaluation(
                id=uuid.uuid4(),
                model_version_id=mv.id,
                task="failure_risk",
                metrics=metrics_data,
                confusion_matrix=confusion_matrix_data,
                calibration_curve=calibration_curve_data,
                curves=curves,
                feature_importance=features_list,
                methodology=methodology_text,
                limitations=limitations_data,
            )
            db.add(me)

        db.commit()
        db.refresh(mv)
        logger.info("Successfully registered model version: %s (active=%s)", mv.bundle_version, mv.is_active)
        return mv

    if session:
        return _execute_import(session)
    with Session(engine) as db:
        return _execute_import(db)


def seed_demo_engines(
    bundle_path: str | Path,
    session: Optional[Session] = None,
) -> Dict[str, Any]:
    """Seeds demo fleet from demo/demo_units.csv and demo/demo_reference_scores.csv

    by choosing engine trajectories truncated at cutoffs corresponding to:
    - Healthy (Health Indicator >= 71)
    - Warning (51 <= Health Indicator <= 70)
    - Critical (Health Indicator <= 30)

    Fails loudly if any of the three categories cannot be produced.
    """
    root = Path(bundle_path).resolve()
    demo_units_path = root / "demo" / "demo_units.csv"
    demo_scores_path = root / "demo" / "demo_reference_scores.csv"

    if not demo_units_path.is_file():
        raise FileNotFoundError(f"Missing demo units CSV: {demo_units_path}")
    if not demo_scores_path.is_file():
        raise FileNotFoundError(f"Missing demo reference scores CSV: {demo_scores_path}")

    units_df = pd.read_csv(demo_units_path)
    scores_df = pd.read_csv(demo_scores_path)

    # Standardize column naming if needed
    unit_col = "unit_id" if "unit_id" in scores_df.columns else "unit"
    cycle_col = "cycle" if "cycle" in scores_df.columns else "cycle_index"

    health_col = None
    for cand in ["machine_health_indicator", "health_indicator", "hi"]:
        if cand in scores_df.columns:
            health_col = cand
            break
    if not health_col:
        raise ValueError(f"Could not find health indicator column in {demo_scores_path}. Columns: {list(scores_df.columns)}")

    available_units = sorted(scores_df[unit_col].unique())
    logger.info("Found %d demo units in reference scores: %s", len(available_units), available_units)

    # Find cutoff cycles for Healthy, Warning, and Critical
    # Requirements:
    # Healthy: health >= 71 (e.g. early life)
    # Warning: 51 <= health <= 70 (degradation initiated)
    # Critical: health <= 30 (failure imminent within H)
    categories = {"healthy": None, "warning": None, "critical": None}

    # Strategy: pick distinct units if possible for the 3 demo machines
    for u in available_units:
        u_scores = scores_df[scores_df[unit_col] == u].sort_values(cycle_col)

        # Look for critical near the end of life
        crit_rows = u_scores[u_scores[health_col] <= 30.0]
        if not crit_rows.empty and categories["critical"] is None:
            cutoff = int(crit_rows.iloc[-1][cycle_col])
            categories["critical"] = {"unit_id": u, "cutoff_cycle": cutoff, "score_row": crit_rows.iloc[-1].to_dict()}
            continue

        # Look for warning
        warn_rows = u_scores[(u_scores[health_col] >= 51.0) & (u_scores[health_col] <= 70.0)]
        if not warn_rows.empty and categories["warning"] is None:
            cutoff = int(warn_rows.iloc[-1][cycle_col])
            categories["warning"] = {"unit_id": u, "cutoff_cycle": cutoff, "score_row": warn_rows.iloc[-1].to_dict()}
            continue

        # Look for healthy
        health_rows = u_scores[u_scores[health_col] >= 75.0]
        if not health_rows.empty and categories["healthy"] is None:
            cutoff = int(min(health_rows.iloc[-1][cycle_col], 50))  # Healthy early run
            categories["healthy"] = {"unit_id": u, "cutoff_cycle": cutoff, "score_row": health_rows[health_rows[cycle_col] == cutoff].iloc[0].to_dict()}
            continue

    # If any category is missing, do a second pass across all units to find any cycle cutoff that matches
    for cat_name, condition in [
        ("healthy", lambda s: s[health_col] >= 71.0),
        ("warning", lambda s: (s[health_col] >= 51.0) & (s[health_col] <= 70.0)),
        ("critical", lambda s: s[health_col] <= 30.0),
    ]:
        if categories[cat_name] is None:
            matching = scores_df[condition(scores_df)]
            if matching.empty:
                raise ValueError(
                    f"FATAL: Demo fleet seeding cannot proceed: No engine cycle satisfies condition for '{cat_name.upper()}'. "
                    f"Healthy requires HI >= 71, Warning requires 51 <= HI <= 70, Critical requires HI <= 30."
                )
            chosen_row = matching.iloc[len(matching) // 2]
            categories[cat_name] = {
                "unit_id": int(chosen_row[unit_col]),
                "cutoff_cycle": int(chosen_row[cycle_col]),
                "score_row": chosen_row.to_dict(),
            }

    # Verify all three exist
    for k, v in categories.items():
        if v is None:
            raise ValueError(f"FATAL: Missing required demo machine category: '{k.upper()}'. All three (Healthy, Warning, Critical) are mandatory.")

    logger.info("Demo selection: Healthy (Unit %s, Cycle %s), Warning (Unit %s, Cycle %s), Critical (Unit %s, Cycle %s)",
                categories["healthy"]["unit_id"], categories["healthy"]["cutoff_cycle"],
                categories["warning"]["unit_id"], categories["warning"]["cutoff_cycle"],
                categories["critical"]["unit_id"], categories["critical"]["cutoff_cycle"])

    def _execute_seed(db: Session) -> Dict[str, Any]:
        # Get active model and active health config
        active_model = db.scalar(
            select(ModelVersion).where(
                ModelVersion.adapter_key == "cmapss_fd001",
                ModelVersion.task == "failure_risk",
                ModelVersion.is_active.is_(True),
            )
        )
        if not active_model:
            raise ValueError("No active failure_risk model found in database. Register and activate a model before seeding demo.")

        active_health_cfg = db.scalar(
            select(HealthIndicatorConfig).where(HealthIndicatorConfig.is_active.is_(True))
        )
        if not active_health_cfg:
            active_health_cfg = HealthIndicatorConfig(
                version="v1.0",
                weight_risk=50.0,
                weight_anomaly=30.0,
                weight_trend=20.0,
                trend_window=20,
                is_active=True,
            )
            db.add(active_health_cfg)
            db.flush()

        results = {}
        for category, info in categories.items():
            u_id = info["unit_id"]
            cutoff = info["cutoff_cycle"]
            score_data = info["score_row"]
            machine_code = f"ENGINE-{u_id:03d}"

            # Operational status mapping
            op_status = "active" if category == "healthy" else ("warning" if category == "warning" else "critical")
            health_band = "Healthy" if category == "healthy" else ("Warning" if category == "warning" else "Critical")

            # Check or create Machine
            machine = db.scalar(select(Machine).where(Machine.machine_code == machine_code))
            if not machine:
                machine = Machine(
                    id=uuid.uuid4(),
                    machine_code=machine_code,
                    operational_status=op_status,
                    health_indicator=float(score_data[health_col]),
                    health_band=health_band,
                    is_demo=True,
                    demo_cluster=category,
                )
                db.add(machine)
                db.flush()
            else:
                machine.operational_status = op_status
                machine.health_indicator = float(score_data[health_col])
                machine.health_band = health_band
                machine.is_demo = True
                machine.demo_cluster = category

            # Delete old readings for this machine
            db.execute(
                SensorReading.__table__.delete().where(SensorReading.machine_id == machine.id)
            )
            db.execute(
                Prediction.__table__.delete().where(Prediction.machine_id == machine.id)
            )

            # Insert truncated sensor readings up to cutoff
            engine_rows = units_df[(units_df[unit_col] == u_id) & (units_df[cycle_col] <= cutoff)].sort_values(cycle_col)
            readings_to_add = []
            for _, r in engine_rows.iterrows():
                readings_to_add.append(
                    SensorReading(
                        machine_id=machine.id,
                        dataset_id=None,
                        cycle_index=int(r[cycle_col]),
                        op_setting_1=float(r["op_setting_1"]) if "op_setting_1" in r else None,
                        op_setting_2=float(r["op_setting_2"]) if "op_setting_2" in r else None,
                        op_setting_3=float(r["op_setting_3"]) if "op_setting_3" in r else None,
                        sensor_1=float(r["sensor_1"]) if "sensor_1" in r else None,
                        sensor_2=float(r["sensor_2"]) if "sensor_2" in r else None,
                        sensor_3=float(r["sensor_3"]) if "sensor_3" in r else None,
                        sensor_4=float(r["sensor_4"]) if "sensor_4" in r else None,
                        sensor_5=float(r["sensor_5"]) if "sensor_5" in r else None,
                        sensor_6=float(r["sensor_6"]) if "sensor_6" in r else None,
                        sensor_7=float(r["sensor_7"]) if "sensor_7" in r else None,
                        sensor_8=float(r["sensor_8"]) if "sensor_8" in r else None,
                        sensor_9=float(r["sensor_9"]) if "sensor_9" in r else None,
                        sensor_10=float(r["sensor_10"]) if "sensor_10" in r else None,
                        sensor_11=float(r["sensor_11"]) if "sensor_11" in r else None,
                        sensor_12=float(r["sensor_12"]) if "sensor_12" in r else None,
                        sensor_13=float(r["sensor_13"]) if "sensor_13" in r else None,
                        sensor_14=float(r["sensor_14"]) if "sensor_14" in r else None,
                        sensor_15=float(r["sensor_15"]) if "sensor_15" in r else None,
                        sensor_16=float(r["sensor_16"]) if "sensor_16" in r else None,
                        sensor_17=float(r["sensor_17"]) if "sensor_17" in r else None,
                        sensor_18=float(r["sensor_18"]) if "sensor_18" in r else None,
                        sensor_19=float(r["sensor_19"]) if "sensor_19" in r else None,
                        sensor_20=float(r["sensor_20"]) if "sensor_20" in r else None,
                        sensor_21=float(r["sensor_21"]) if "sensor_21" in r else None,
                    )
                )
            db.add_all(readings_to_add)

            # Insert latest prediction with complete lineage
            fail_prob = float(score_data.get("failure_probability", 0.0))
            anom_score = float(score_data.get("anomaly_score", 0.0))
            pred = Prediction(
                id=uuid.uuid4(),
                machine_id=machine.id,
                cycle=cutoff,
                as_of_index=cutoff,
                dataset_version="cmapss-fd001-heldout",
                schema_mapping_hash="fd001-canonical-sha256",
                feature_config_version=active_model.feature_config_version,
                preprocessing_version=active_model.preprocessing_version,
                failure_model_version_id=active_model.id,
                anomaly_model_version_id=None,
                health_config_id=active_health_cfg.id,
                horizon=active_model.horizon or 30,
                horizon_unit=active_model.horizon_unit or "cycles",
                failure_probability=fail_prob,
                risk_level="High" if fail_prob >= 0.50 else ("Medium" if fail_prob >= 0.20 else "Low"),
                health_indicator=float(score_data[health_col]),
                health_band=health_band,
                penalty_risk=round(100.0 * fail_prob, 2),
                penalty_anomaly=round(100.0 * (1.0 - fail_prob) * 0.30 * anom_score, 2),
                penalty_trend=0.0,
                input_window_start=max(1, cutoff - 30),
                input_window_end=cutoff,
                reliability_flags={"data_quality": score_data.get("data_quality_status", "DATA_OK")},
            )
            db.add(pred)

            results[category] = {
                "machine_code": machine_code,
                "cutoff_cycle": cutoff,
                "readings_count": len(readings_to_add),
                "health_indicator": float(score_data[health_col]),
            }

        db.commit()
        return results

    if session:
        return _execute_seed(session)
    with Session(engine) as db:
        return _execute_seed(db)
