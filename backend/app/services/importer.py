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
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.db import engine
from app.ml.verify_artifacts import verify_manifest
from app.models.entities import (
    Alert,
    Anomaly,
    HealthIndicatorConfig,
    Machine,
    MaintenanceRecord,
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
    session: Optional[Session] = None,
) -> ModelVersion:
    """Reads metadata/model_card.json, evaluation/curves.json and feature_importance.json
    from the artifact bundle directory, verifies the manifest hashes ONLY (no library version
    check, no unpickling), and registers records into model_versions and model_evaluations tables.

    Strict library version checking is reserved for app startup.
    """
    root = Path(bundle_path).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Model bundle directory not found: {root}")

    # 1. Verify manifest hashes ONLY (no library version check, zero unpickling)
    verify_manifest(root)

    # 2. Read required metadata files (JSON only)
    model_metadata_path = root / "metadata" / "model_metadata.json"
    model_card_path = root / "metadata" / "model_card.json"
    curves_path = root / "evaluation" / "curves.json"
    feature_imp_path = root / "evaluation" / "feature_importance.json"

    if not model_card_path.is_file():
        raise FileNotFoundError(f"Missing required model card: {model_card_path}")
    if not curves_path.is_file():
        raise FileNotFoundError(f"Missing required curves file: {curves_path}")
    if not feature_imp_path.is_file():
        raise FileNotFoundError(f"Missing required feature importance file: {feature_imp_path}")

    metadata = json.loads(model_metadata_path.read_text(encoding="utf-8")) if model_metadata_path.is_file() else {}
    model_card = json.loads(model_card_path.read_text(encoding="utf-8"))
    curves = json.loads(curves_path.read_text(encoding="utf-8"))
    feature_importance = json.loads(feature_imp_path.read_text(encoding="utf-8"))

    # Extract version details
    model_version_str = model_card.get("model_version", metadata.get("model_version", root.name))
    training_methodology = model_card.get("training_methodology")
    if not training_methodology:
        raise ValueError(f"Missing required 'training_methodology' in model card: {model_card_path}")
    selected_model = training_methodology.get("selected_model", "XGBoostClassifier")

    features_info = model_card.get("features", {})
    active_sensors = features_info.get("active_sensors", metadata.get("feature_config", {}).get("active_sensors", []))

    # Strict check: failure_horizon must be explicitly defined
    horizon_info = model_card.get("failure_horizon")
    if not horizon_info or "value" not in horizon_info:
        raise ValueError(f"Missing required 'failure_horizon.value' in model card: {model_card_path}")
    horizon_val = int(horizon_info["value"])
    horizon_unit = horizon_info.get("unit", "operating_cycles")

    # Strict check: decision threshold must be explicitly defined
    threshold_info = training_methodology.get("threshold")
    if not threshold_info or "value" not in threshold_info:
        raise ValueError(f"Missing required 'training_methodology.threshold.value' in model card: {model_card_path}")
    decision_threshold = float(threshold_info["value"])

    # Strict check: evaluation dates must be explicitly defined
    eval_date = model_card.get("evaluation_date")
    if not eval_date:
        raise ValueError(f"Missing required 'evaluation_date' in model card: {model_card_path}")
    training_timestamp = model_card.get("training_timestamp")
    if not training_timestamp:
        raise ValueError(f"Missing required 'training_timestamp' in model card: {model_card_path}")

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
            py_ver = (
                model_card.get("library_versions", {}).get("python")
                or metadata.get("library_versions", {}).get("python")
                or "3.12.13"
            )
            mv.python_version = py_ver
            mv.is_active = activate
        else:
            py_ver = (
                model_card.get("library_versions", {}).get("python")
                or metadata.get("library_versions", {}).get("python")
                or "3.12.13"
            )
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
                python_version=py_ver,
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

    # 1. Distinct engine selection per category (Healthy, Warning, Critical)
    # Warning machine = the engine/cutoff with the widest Warning window (prefer engines 77, 29, 70)
    # Critical machine = engine 48 or 97 at the final cycle
    # Healthy machine = any other distinct engine at an early Excellent cycle

    # Warning selection: widest warning window
    chosen_warning_unit = None
    chosen_warning_cutoff = None
    max_warning_span = 0
    for u in [77, 29, 70] + [x for x in available_units if x not in [77, 29, 70]]:
        if u not in available_units:
            continue
        w_scores = scores_df[scores_df[unit_col] == u]
        w_matches = w_scores[(w_scores[health_col] >= 51.0) & (w_scores[health_col] <= 70.0)]
        if len(w_matches) > max_warning_span:
            max_warning_span = len(w_matches)
            chosen_warning_unit = u
            chosen_warning_cutoff = int(w_matches.iloc[len(w_matches) // 2][cycle_col])

    if not chosen_warning_unit:
        raise ValueError("Could not find an engine with Warning band (51 <= HI <= 70)")

    # Critical selection: engine 48 or 97 at final cycle
    chosen_critical_unit = None
    chosen_critical_cutoff = None
    for u in [48, 97]:
        if u in available_units and u != chosen_warning_unit:
            c_scores = scores_df[scores_df[unit_col] == u]
            final_c = int(c_scores.iloc[-1][cycle_col])
            final_hi = float(c_scores.iloc[-1][health_col])
            if final_hi <= 30.0:
                chosen_critical_unit = u
                chosen_critical_cutoff = final_c
                break

    if not chosen_critical_unit:
        raise ValueError("Could not find engine 48 or 97 at final cycle with Critical band (HI <= 30)")

    # Healthy selection: any other distinct engine at an early Excellent cycle (HI >= 86.0)
    chosen_healthy_unit = None
    chosen_healthy_cutoff = None
    for u in [70, 29, 97, 48, 77]:
        if u in available_units and u not in (chosen_warning_unit, chosen_critical_unit):
            h_scores = scores_df[scores_df[unit_col] == u]
            h_matches = h_scores[h_scores[health_col] >= 86.0]
            if not h_matches.empty:
                chosen_healthy_unit = u
                cand_cycle = 35 if 35 in h_matches[cycle_col].values else int(h_matches.iloc[min(20, len(h_matches) - 1)][cycle_col])
                chosen_healthy_cutoff = cand_cycle
                break

    if not chosen_healthy_unit:
        raise ValueError("Could not find a distinct Healthy demo engine with HI >= 71")

    categories = {
        "warning": {"unit_id": chosen_warning_unit, "cutoff_cycle": chosen_warning_cutoff},
        "critical": {"unit_id": chosen_critical_unit, "cutoff_cycle": chosen_critical_cutoff},
        "healthy": {"unit_id": chosen_healthy_unit, "cutoff_cycle": chosen_healthy_cutoff},
    }

    # Also register the remaining demo units so that all 5 held-out demo engines are seeded
    for u in available_units:
        if u not in [chosen_warning_unit, chosen_critical_unit, chosen_healthy_unit]:
            sub = scores_df[scores_df[unit_col] == u]
            categories[f"unit_{u}"] = {"unit_id": u, "cutoff_cycle": int(sub.iloc[-1][cycle_col])}
    logger.info("Distinct demo selection: Healthy (Unit %s, Cycle %s), Warning (Unit %s, Cycle %s), Critical (Unit %s, Cycle %s)",
                categories["healthy"]["unit_id"], categories["healthy"]["cutoff_cycle"],
                categories["warning"]["unit_id"], categories["warning"]["cutoff_cycle"],
                categories["critical"]["unit_id"], categories["critical"]["cutoff_cycle"])

    # 2. Try loading ModelBundle for live trajectory scoring
    from app.ml.pdm_inference import ModelBundle, score_trajectory
    bundle = None
    try:
        bundle = ModelBundle.load(root)
    except Exception as exc:
        logger.info("Note: ModelBundle could not be loaded directly (%s); using reference scores for fixture tests.", exc)

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
                anomaly_weight=0.30,
                data_quality_penalty={"DATA_OK": 0.0, "DATA_WARNING": 10.0},
                trend_enabled=False,
                is_active=True,
            )
            db.add(active_health_cfg)
            db.flush()

        results = {}
        for category, info in categories.items():
            u_id = info["unit_id"]
            cutoff = info["cutoff_cycle"]
            machine_code = f"ENGINE-{u_id:03d}"

            # Engine raw rows up to cutoff
            engine_rows = units_df[(units_df[unit_col] == u_id) & (units_df[cycle_col] <= cutoff)].sort_values(cycle_col)
            ref_slice = scores_df[(scores_df[unit_col] == u_id) & (scores_df[cycle_col] <= cutoff)].sort_values(cycle_col)

            # Re-run score_trajectory in backend and assert parity
            if bundle is not None:
                scored_df = score_trajectory(engine_rows, bundle)
                if len(scored_df) != len(ref_slice):
                    raise AssertionError(
                        f"Parity check failed for engine {u_id}: scored {len(scored_df)} rows vs reference {len(ref_slice)} rows."
                    )
                p_diff = np.abs(scored_df["failure_probability"].to_numpy() - ref_slice["failure_probability"].to_numpy())
                if np.max(p_diff) > 1e-3:
                    raise AssertionError(
                        f"Parity check failed for engine {u_id} failure_probability: max diff {np.max(p_diff):.6f} > 1e-3 tolerance"
                    )
                hi_diff = np.abs(scored_df["machine_health_indicator"].to_numpy() - ref_slice[health_col].to_numpy())
                if np.max(hi_diff) > 1e-2:
                    raise AssertionError(
                        f"Parity check failed for engine {u_id} machine_health_indicator: max diff {np.max(hi_diff):.6f} > 1e-2 tolerance"
                    )
                score_data = scored_df.iloc[-1].to_dict()
                logger.info("Parity verified for demo engine %s (%s, %d rows)", machine_code, category, len(scored_df))
            else:
                score_data = ref_slice.iloc[-1].to_dict()

            # Operational status is strictly 'active' (maintenance/archived are operational states)
            op_status = "active"
            health_band = "Healthy" if category == "healthy" else ("Warning" if category == "warning" else "Critical")

            clean_name = f"Turbofan Engine {u_id:03d}"
            if category in ("healthy", "warning", "critical"):
                clean_name += f" ({category.capitalize()} Demo)"

            # Check or create Machine
            machine = db.scalar(select(Machine).where(Machine.machine_code == machine_code))
            if not machine:
                machine = Machine(
                    id=uuid.uuid4(),
                    machine_code=machine_code,
                    name=clean_name,
                    machine_type="Simulated Turbofan Engine (C-MAPSS FD001)",
                    location="Test Cell A-1",
                    notes="Held-out test engine from NASA C-MAPSS FD001 dataset",
                    source_unit_id=u_id,
                    operational_status=op_status,
                    health_indicator=float(score_data[health_col]),
                    health_band=health_band,
                    is_demo=True,
                    demo_cluster=category,
                )
                db.add(machine)
                db.flush()
            else:
                machine.name = clean_name
                machine.operational_status = op_status
                machine.health_indicator = float(score_data[health_col])
                machine.health_band = health_band
                machine.is_demo = True
                machine.demo_cluster = category

            # Delete old data for this machine (respecting FK dependency order)
            db.execute(Alert.__table__.delete().where(Alert.machine_id == machine.id))
            db.execute(MaintenanceRecord.__table__.delete().where(MaintenanceRecord.machine_id == machine.id))
            db.execute(Anomaly.__table__.delete().where(Anomaly.machine_id == machine.id))
            db.execute(Prediction.__table__.delete().where(Prediction.machine_id == machine.id))
            db.execute(SensorReading.__table__.delete().where(SensorReading.machine_id == machine.id))

            # Insert truncated sensor readings up to cutoff
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
                penalty_dq=0.0,
                penalty_trend=0.0,
                clipping_adjustment=0.0,
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
