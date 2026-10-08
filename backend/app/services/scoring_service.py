"""
Scoring and Telemetry Inference Engine Service for Predict-Ai (PrediCore).

Executes idempotent trajectory scoring using the registered, active ML model bundle.
Generates:
1. Calibrated failure probabilities P(Fail | H=30)
2. Rolling unsupervised anomaly scores and severity classifications
3. Machine Health Indicators with additive breakdown points
4. Alert rule evaluation with consecutive cycle filtering
5. AI recommendations with mandatory non-diagnostic disclaimers
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.errors import ConflictError, NotFoundError
from app.ml.pdm_health import health_breakdown
from app.ml.pdm_inference import ModelBundle, score_trajectory
from app.ml.pdm_recommendation import recommend_maintenance
from app.models.entities import (
    Anomaly,
    Dataset,
    HealthIndicatorConfig,
    Job,
    Machine,
    ModelVersion,
    Prediction,
    SensorReading,
    Setting,
)
from app.services.alert_service import evaluate_trajectory_alerts

logger = logging.getLogger(__name__)


def determine_health_band(score: float, bands: Optional[List[Dict[str, Any]]] = None) -> str:
    """Assigns health band based on configured bands from Setting (ordered by min_score desc)."""
    if bands:
        for b in sorted(bands, key=lambda x: float(x.get("min_score", 0)), reverse=True):
            if score >= float(b.get("min_score", 0)):
                return b.get("key", "Healthy")
        return bands[-1].get("key", "Critical")
    return (
        "Excellent" if score >= 86.0
        else ("Healthy" if score >= 71.0
        else ("Warning" if score >= 51.0
        else ("Poor" if score >= 31.0 else "Critical")))
    )


def score_machine_trajectory(
    machine_id: uuid.UUID,
    db: Session,
    bundle_path: Optional[str | Path] = None,
    commit: bool = True,
) -> Dict[str, Any]:
    """Scores historical sensor readings for a machine using the active model bundle."""
    machine = db.get(Machine, machine_id)
    if not machine:
        raise NotFoundError(message=f"Machine {machine_id} not found")

    # 1. Fetch active model
    active_model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.adapter_key == "cmapss_fd001",
            ModelVersion.task == "failure_risk",
            ModelVersion.is_active.is_(True),
        )
    )
    if not active_model:
        raise ConflictError(message="No active failure risk model is registered. Cannot score telemetry.")

    active_anomaly_model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.adapter_key == "cmapss_fd001",
            ModelVersion.task == "anomaly",
            ModelVersion.is_active.is_(True),
        )
    )
    anomaly_model_version_id = active_anomaly_model.id if active_anomaly_model else None

    # Fetch dataset lineage from dataset row or canonical adapter (no literal strings)
    from app.adapters.cmapss_fd001 import CmapssFd001Adapter
    dataset_version = "1.0"
    schema_mapping_hash = None
    if machine.dataset_id:
        dataset = db.get(Dataset, machine.dataset_id)
        if dataset:
            dataset_version = dataset.version
            schema_mapping_hash = dataset.schema_mapping_hash
    if not schema_mapping_hash:
        mapping = {col: col for col in CmapssFd001Adapter.canonical_columns}
        schema_mapping_hash = CmapssFd001Adapter.compute_mapping_hash(mapping)

    # 2. Load model bundle
    artifact_path = Path(bundle_path or active_model.artifact_path)
    if not artifact_path.is_dir():
        raise ConflictError(message=f"Model bundle artifact directory {artifact_path} does not exist.")

    bundle = ModelBundle.load(artifact_path)

    # 3. Fetch sensor readings
    readings = db.scalars(
        select(SensorReading)
        .where(SensorReading.machine_id == machine_id)
        .order_by(SensorReading.cycle_index.asc())
    ).all()

    if not readings:
        raise ConflictError(message="No sensor readings available for this machine.")

    # Build dataframe for scoring
    rows = []
    for r in readings:
        row_dict = {
            "unit_id": 1,
            "cycle": r.cycle,
            "op_setting_1": r.op_setting_1 or 0.0,
            "op_setting_2": r.op_setting_2 or 0.0,
            "op_setting_3": r.op_setting_3 or 0.0,
            "operating_setting_1": r.op_setting_1 or 0.0,
            "operating_setting_2": r.op_setting_2 or 0.0,
            "operating_setting_3": r.op_setting_3 or 0.0,
        }
        for s in range(1, 22):
            val = getattr(r, f"sensor_{s}", None)
            row_dict[f"sensor_{s}"] = val if val is not None else 0.0
        rows.append(row_dict)

    df = pd.DataFrame(rows)

    # 4. Fetch active health config
    health_cfg = db.scalar(
        select(HealthIndicatorConfig).where(HealthIndicatorConfig.is_active.is_(True))
    )
    cfg_dict = {
        "anomaly_weight": health_cfg.anomaly_weight if health_cfg else 0.30,
        "data_quality_penalty": health_cfg.data_quality_penalty if health_cfg else {"DATA_OK": 0.0, "DATA_WARNING": 10.0},
    }

    # 5. Run inference via vendored pdm_inference
    scored_df = score_trajectory(df, bundle)

    # 6. Delete previous anomalies and predictions for this machine (child table first)
    db.execute(Anomaly.__table__.delete().where(Anomaly.machine_id == machine_id))
    db.execute(Prediction.__table__.delete().where(Prediction.machine_id == machine_id))

    # Query risk band settings (PRD §14.8 default low_max=0.10 aligned with decision_threshold)
    risk_setting = db.scalar(select(Setting).where(Setting.key == "risk_bands"))
    low_max = float(risk_setting.value.get("low_max", 0.10)) if risk_setting and risk_setting.value else 0.10
    medium_max = float(risk_setting.value.get("medium_max", 0.50)) if risk_setting and risk_setting.value else 0.50
    high_max = float(risk_setting.value.get("high_max", 0.80)) if risk_setting and risk_setting.value else 0.80

    # Query health bands setting (PRD §FR-10 configured bands)
    bands_setting = db.scalar(select(Setting).where(Setting.key == "health_bands"))
    configured_bands = bands_setting.value.get("bands", []) if bands_setting and bands_setting.value else []

    new_predictions: List[Prediction] = []
    new_anomalies: List[Anomaly] = []

    for _, row in scored_df.iterrows():
        cycle_val = int(row["cycle"])
        p_fail = float(row["failure_probability"])
        s_anom = float(row["anomaly_score"])
        hi_val = float(row["machine_health_indicator"])
        dq_status = row.get("data_quality_status", "DATA_OK")

        # Breakdown points
        bd = health_breakdown(p_fail, s_anom, dq_status, config=cfg_dict)
        risk_penalty = bd["failure_risk_points"] if bd else round(100.0 * p_fail, 2)
        anom_penalty = bd["anomaly_points"] if bd else round(100.0 * (1.0 - p_fail) * cfg_dict["anomaly_weight"] * s_anom, 2)
        dq_penalty = bd["data_quality_points"] if bd else 0.0
        clip_adj = bd["clipping_adjustment_points"] if bd else 0.0

        # Aligned with decision threshold: >= low_max (0.10) is at least Medium
        risk_level = (
            "Critical" if p_fail >= high_max
            else ("High" if p_fail >= medium_max
            else ("Medium" if p_fail >= low_max else "Low"))
        )
        health_band = determine_health_band(hi_val, configured_bands)

        pred_id = uuid.uuid4()
        pred = Prediction(
            id=pred_id,
            machine_id=machine_id,
            cycle=cycle_val,
            as_of_index=cycle_val,
            dataset_version=dataset_version,
            schema_mapping_hash=schema_mapping_hash,
            feature_config_version=active_model.feature_config_version,
            preprocessing_version=active_model.preprocessing_version,
            failure_model_version_id=active_model.id,
            anomaly_model_version_id=anomaly_model_version_id,
            health_config_id=health_cfg.id if health_cfg else uuid.uuid4(),
            horizon=active_model.horizon or 30,
            horizon_unit=active_model.horizon_unit or "cycles",
            failure_probability=p_fail,
            risk_level=risk_level,
            health_indicator=hi_val,
            health_band=health_band,
            penalty_risk=risk_penalty,
            penalty_anomaly=anom_penalty,
            penalty_dq=dq_penalty,
            penalty_trend=0.0,
            clipping_adjustment=clip_adj,
            input_window_start=max(1, cycle_val - 30),
            input_window_end=cycle_val,
            reliability_flags={"data_quality": dq_status},
        )
        new_predictions.append(pred)

        # Anomaly record
        is_anom = bool(row.get("anomaly_flag", False))
        severity = "critical" if s_anom >= 0.80 else ("warning" if s_anom >= 0.50 else "low")
        anom = Anomaly(
            id=uuid.uuid4(),
            machine_id=machine_id,
            cycle=cycle_val,
            prediction_id=pred_id,
            anomaly_score=s_anom,
            severity=severity,
            is_anomaly=is_anom,
            detected_at=datetime.now(timezone.utc),
        )
        new_anomalies.append(anom)

    db.add_all(new_predictions)
    db.flush()
    db.add_all(new_anomalies)

    # 7. Update Machine health indicator & health band from latest prediction
    latest_row = scored_df.iloc[-1]
    latest_hi = float(latest_row["machine_health_indicator"])
    latest_fail = float(latest_row["failure_probability"])
    latest_band = determine_health_band(latest_hi, configured_bands)

    machine.health_indicator = latest_hi
    machine.health_band = latest_band

    # 8. Alert Rule Evaluation (respecting uq_open_alert_per_type and data order)
    rec = recommend_maintenance(
        failure_probability=latest_fail,
        anomaly_flag=bool(latest_row.get("anomaly_flag", False)),
        health_indicator=latest_hi,
        data_quality_status=str(latest_row.get("data_quality_status", "DATA_OK")),
        decision_threshold=float(active_model.decision_threshold or 0.10),
    )

    evaluate_trajectory_alerts(
        df=scored_df,
        db=db,
        machine_id=machine_id,
        decision_threshold=float(active_model.decision_threshold or 0.10),
        check_severe_anomaly=True,
        persist=True,
    )

    if commit:
        db.commit()
        db.refresh(machine)
    else:
        db.flush()

    return {
        "machine_id": str(machine_id),
        "machine_code": machine.machine_code,
        "scored_cycles": len(scored_df),
        "health_indicator": latest_hi,
        "health_band": latest_band,
        "failure_probability": latest_fail,
        "recommendation": rec,
    }


def run_scoring_job(
    job_id: uuid.UUID,
    dataset_id: uuid.UUID,
    machine_ids: Optional[List[uuid.UUID]] = None,
    bundle_path: Optional[str | Path] = None,
    _db: Optional[Session] = None,
):
    """
    Background worker task for scoring run (PRD FR-7).
    Executes in a background thread/task using its own isolated database session,
    OR uses the provided _db session (for synchronous test execution).
    """
    own_session = _db is None
    db: Session = _db if _db is not None else SessionLocal()
    job = None
    try:
        job = db.get(Job, job_id)
        dataset = db.get(Dataset, dataset_id)
        if not job or not dataset:
            logger.error(f"Scoring job {job_id} or dataset {dataset_id} not found.")
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.progress_pct = 5.0
        db.commit()

        # Fetch machines associated with this dataset
        stmt = select(Machine).where(Machine.dataset_id == dataset_id)
        if machine_ids:
            stmt = stmt.where(Machine.id.in_(machine_ids))

        machines = db.scalars(stmt).all()
        total_machines = len(machines)

        if total_machines == 0:
            job.status = "completed"
            job.progress_pct = 100.0
            job.completed_at = datetime.now(timezone.utc)
            job.result = {"scored_machines": 0, "message": "No machines found to score"}
            db.commit()
            return

        scored_count = 0
        for i, machine in enumerate(machines):
            try:
                score_machine_trajectory(machine.id, db, bundle_path=bundle_path)
                scored_count += 1
            except Exception as e:
                logger.warning(f"Error scoring machine {machine.id}: {e}")

            progress = 5.0 + 90.0 * (i + 1) / total_machines
            job.progress_pct = round(progress, 1)
            db.commit()

        job.status = "completed"
        job.progress_pct = 100.0
        job.completed_at = datetime.now(timezone.utc)
        job.result = {
            "dataset_id": str(dataset_id),
            "total_machines": total_machines,
            "scored_machines": scored_count,
            "status": "completed",
        }
        db.commit()
    except Exception as e:
        logger.exception(f"Scoring job {job_id} failed: {e}")
        if job:
            db.rollback()
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        if own_session:
            db.close()

