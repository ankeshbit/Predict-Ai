"""Unified Alert Evaluation Service for Predict-Ai (PrediCore).

PRD §14.8 & §FR-14:
- Evaluates telemetry trajectories in strict chronological data order.
- Queries active alert_rules (default: high_failure_risk threshold 0.50, N=3 consecutive cycles).
- Identifies trigger_cycle and trigger_score at the exact cycle the rule first fires.
- Generates recommendation snapshots maintaining AI vs Human authority boundaries.
- Respects DB unique constraint uq_open_alert_per_type (at most one open/acknowledged alert per machine & type).
- Used identically by seed_demo_engines and scoring_service.score_machine_trajectory.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from app.ml.pdm_recommendation import recommend_maintenance
from app.models.entities import Alert, AlertRule
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger("predicore.alerts")


def find_high_failure_risk_trigger(
    df: pd.DataFrame,
    threshold: float = 0.50,
    consecutive_n: int = 3,
    cycle_col: str = "cycle",
    prob_col: str = "failure_probability",
) -> Optional[Tuple[int, float]]:
    """Scan trajectory in data order to find the cycle and score where high_failure_risk first fires.

    Rule fires when failure_probability >= threshold for consecutive_n consecutive cycles.
    Returns (trigger_cycle, trigger_score) at the N-th consecutive cycle, or None if never fired.
    """
    if df.empty or prob_col not in df.columns or cycle_col not in df.columns:
        return None

    sorted_df = df.sort_values(cycle_col, ascending=True)
    streak = 0
    for _, row in sorted_df.iterrows():
        prob = float(row[prob_col])
        cycle = int(row[cycle_col])
        if prob >= threshold:
            streak += 1
            if streak == consecutive_n:
                return cycle, round(prob, 4)
        else:
            streak = 0

    return None


def find_severe_anomaly_trigger(
    df: pd.DataFrame,
    threshold: float = 0.80,
    cycle_col: str = "cycle",
    anom_col: str = "anomaly_score",
) -> Optional[Tuple[int, float]]:
    """Scan trajectory in data order to find the first cycle where anomaly_score >= threshold."""
    if df.empty or anom_col not in df.columns or cycle_col not in df.columns:
        return None

    sorted_df = df.sort_values(cycle_col, ascending=True)
    for _, row in sorted_df.iterrows():
        score = float(row[anom_col])
        cycle = int(row[cycle_col])
        if score >= threshold:
            return cycle, round(score, 4)

    return None


def evaluate_trajectory_alerts(
    df: pd.DataFrame,
    db: Optional[Session] = None,
    machine_id: Optional[Union[uuid.UUID, str]] = None,
    decision_threshold: float = 0.10,
    force_open_critical: bool = False,
    check_severe_anomaly: bool = False,
    persist: bool = True,
) -> Dict[str, Any]:
    """Unified alert rule evaluation across a machine's trajectory in data order.

    Parameters
    ----------
    df : pd.DataFrame
        Trajectory DataFrame containing cycle, failure_probability, and optionally anomaly_score,
        machine_health_indicator, data_quality_status.
    db : Session, optional
        Database session for querying active rules and persisting new alerts.
    machine_id : UUID or str, optional
        Target machine ID. Required if persist=True.
    decision_threshold : float
        Model decision threshold (default 0.10).
    force_open_critical : bool
        If True, ensures an open alert is created for the critical demo machine.
    persist : bool
        Whether to insert new Alert rows into db.

    Returns
    -------
    dict
        Evaluation summary with triggered rules, trigger_cycle, trigger_score, and generated alerts.
    """
    cycle_col = "cycle" if "cycle" in df.columns else "time_in_cycles"
    prob_col = "failure_probability"
    anom_col = "anomaly_score"
    hi_col = "machine_health_indicator" if "machine_health_indicator" in df.columns else "health_indicator"

    sorted_df = df.sort_values(cycle_col, ascending=True) if cycle_col in df.columns else df

    # Fetch active alert rules from DB if session provided, else use canonical defaults
    high_fail_thresh = 0.50
    fail_consecutive_n = 3
    fail_rule_id = "REC_HIGH_RISK_01"

    anom_thresh = 0.80
    anom_rule_id = "REC_SEVERE_ANOM_01"

    if db is not None:
        rule_high_fail = db.scalar(
            select(AlertRule).where(
                AlertRule.alert_type == "high_failure_risk",
                AlertRule.is_active.is_(True),
            )
        )
        if rule_high_fail:
            if rule_high_fail.failure_probability_threshold is not None:
                high_fail_thresh = float(rule_high_fail.failure_probability_threshold)
            if rule_high_fail.consecutive_cycles is not None:
                fail_consecutive_n = int(rule_high_fail.consecutive_cycles)
            fail_rule_id = rule_high_fail.rule_id

        rule_anom = db.scalar(
            select(AlertRule).where(
                AlertRule.alert_type == "severe_anomaly",
                AlertRule.is_active.is_(True),
            )
        )
        if rule_anom:
            anom_rule_id = rule_anom.rule_id

    # 1. Evaluate high failure risk rule in data order
    fail_trigger = find_high_failure_risk_trigger(
        sorted_df,
        threshold=high_fail_thresh,
        consecutive_n=fail_consecutive_n,
        cycle_col=cycle_col,
        prob_col=prob_col,
    )

    # 2. Evaluate severe anomaly rule in data order
    anom_trigger = find_severe_anomaly_trigger(
        sorted_df,
        threshold=anom_thresh,
        cycle_col=cycle_col,
        anom_col=anom_col,
    )

    created_alerts: List[Alert] = []
    latest_row = sorted_df.iloc[-1] if not sorted_df.empty else {}
    latest_fail = float(latest_row.get(prob_col, 0.0))
    latest_anom = float(latest_row.get(anom_col, 0.0))
    latest_hi = float(latest_row.get(hi_col, 50.0))
    dq_status = str(latest_row.get("data_quality_status", "DATA_OK"))

    m_uuid = uuid.UUID(str(machine_id)) if machine_id else None

    # Handle high failure risk alert
    if fail_trigger is not None or force_open_critical:
        trig_c, trig_s = fail_trigger if fail_trigger is not None else (int(latest_row.get(cycle_col, 1)), round(latest_fail, 4))
        rec = recommend_maintenance(
            failure_probability=trig_s,
            anomaly_flag=latest_anom >= 0.50,
            health_indicator=latest_hi,
            data_quality_status=dq_status,
            decision_threshold=decision_threshold,
        )
        rec_text = f"{rec['label']}: {rec['category']} - " + "; ".join(rec["reasons"]) + f". {rec['disclaimer']}"

        if db is not None and m_uuid is not None and persist:
            existing = db.scalar(
                select(Alert).where(
                    Alert.machine_id == m_uuid,
                    Alert.alert_type == "high_failure_risk",
                    Alert.status.in_(["open", "acknowledged"]),
                )
            )
            if not existing:
                alert = Alert(
                    id=uuid.uuid4(),
                    machine_id=m_uuid,
                    alert_type="high_failure_risk",
                    status="open",
                    severity="critical",
                    trigger_cycle=trig_c,
                    trigger_score=trig_s,
                    recommendation_text=rec_text,
                    recommendation_rule_id=fail_rule_id,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(alert)
                created_alerts.append(alert)
                logger.info(
                    "Created high_failure_risk alert for machine %s: trigger_cycle=%d, trigger_score=%.4f",
                    m_uuid, trig_c, trig_s
                )

    # Handle severe anomaly alert
    if check_severe_anomaly and anom_trigger is not None:
        trig_c, trig_s = anom_trigger
        rec = recommend_maintenance(
            failure_probability=latest_fail,
            anomaly_flag=True,
            health_indicator=latest_hi,
            data_quality_status=dq_status,
            decision_threshold=decision_threshold,
        )
        rec_text = f"{rec['label']}: {rec['category']} - " + "; ".join(rec["reasons"]) + f". {rec['disclaimer']}"

        if db is not None and m_uuid is not None and persist:
            existing = db.scalar(
                select(Alert).where(
                    Alert.machine_id == m_uuid,
                    Alert.alert_type == "severe_anomaly",
                    Alert.status.in_(["open", "acknowledged"]),
                )
            )
            if not existing:
                alert = Alert(
                    id=uuid.uuid4(),
                    machine_id=m_uuid,
                    alert_type="severe_anomaly",
                    status="open",
                    severity="warning",
                    trigger_cycle=trig_c,
                    trigger_score=trig_s,
                    recommendation_text=rec_text,
                    recommendation_rule_id=anom_rule_id,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(alert)
                created_alerts.append(alert)

    return {
        "high_failure_risk": {
            "triggered": fail_trigger is not None,
            "trigger_cycle": fail_trigger[0] if fail_trigger else None,
            "trigger_score": fail_trigger[1] if fail_trigger else None,
            "threshold": high_fail_thresh,
            "consecutive_n": fail_consecutive_n,
            "rule_id": fail_rule_id,
        },
        "severe_anomaly": {
            "triggered": anom_trigger is not None,
            "trigger_cycle": anom_trigger[0] if anom_trigger else None,
            "trigger_score": anom_trigger[1] if anom_trigger else None,
            "threshold": anom_thresh,
            "rule_id": anom_rule_id,
        },
        "created_alerts": created_alerts,
    }
