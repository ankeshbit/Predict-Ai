import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from pdm_quality import check_data_quality
from pdm_health import compute_health_indicator, health_breakdown
from pdm_recommendation import recommend_maintenance
from pdm_explain import explain_row

# Data-quality status -> user-facing reliability wording
RELIABILITY = {"DATA_OK": "reliable", "DATA_WARNING": "reliability_reduced", "DATA_INVALID": "not_scored"}


class DataInvalidError(ValueError):
    """Raised by score_trajectory when the input fails validation (the result holds the quality report)."""

    def __init__(self, quality):
        super().__init__("; ".join(i["message"] for i in quality["issues"]) or "invalid input")
        self.quality = quality


class ModelBundle:
    """Everything needed for inference. Load with ModelBundle.load(artifact_dir).

    SECURITY: pickled classes come from artifact_dir/code. Verify artifact_manifest.json
    (verify_artifacts.verify_all) BEFORE putting that folder on sys.path / calling load().
    """

    def __init__(self, feature_engineer, imputer, calibrated_model, anomaly_scorer, metadata):
        self.feature_engineer = feature_engineer
        self.imputer = imputer
        self.calibrated_model = calibrated_model
        self.anomaly_scorer = anomaly_scorer
        self.metadata = metadata
        self.feature_names = list(metadata["features"])
        self.reference_values = pd.Series(imputer.statistics_, index=self.feature_names)

    @classmethod
    def load(cls, artifact_dir):
        d = Path(artifact_dir)
        code_dir = str(d / "code")
        if code_dir not in sys.path:
            sys.path.insert(0, code_dir)
        metadata = json.loads((d / "metadata" / "model_metadata.json").read_text())
        return cls(joblib.load(d / "preprocessing" / "feature_engineer.joblib"),
                   joblib.load(d / "preprocessing" / "imputer.joblib"),
                   joblib.load(d / "model" / "calibrated_failure_model.joblib"),
                   joblib.load(d / "model" / "anomaly_detector.joblib"),
                   metadata)


def _py(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    return v


def _prepare_history(history, bundle, lookback=True):
    req = list(bundle.metadata["quality"]["required_columns"])
    cols = req + (["unit_id"] if "unit_id" in history.columns and "unit_id" not in req else [])
    df = history[cols].copy()
    for c in req:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df[req] = df[req].replace([np.inf, -np.inf], np.nan)
    df = df.sort_values("cycle", kind="mergesort")
    if lookback:
        df = df.tail(bundle.feature_engineer.max_lookback)
    return df.reset_index(drop=True)


def _impute(bundle, feats):
    return pd.DataFrame(bundle.imputer.transform(feats), columns=bundle.feature_names, index=feats.index)


def predict_machine_state(history, bundle, machine_id=None, top_k=5, include_explanation=True):
    """Score the LATEST cycle of one machine's chronological history. Returns a JSON-serialisable dict."""
    meta = bundle.metadata
    threshold = float(meta["threshold"]["value"])
    horizon = int(meta["failure_horizon"])
    rec_cfg = meta["recommendation_rules"]["config"]
    dq = check_data_quality(history, meta["quality"])
    if machine_id is None and isinstance(history, pd.DataFrame) and "unit_id" in history.columns and len(history):
        machine_id = _py(history["unit_id"].iloc[0])
    base = {"machine_id": _py(machine_id), "cycle": dq.get("latest_cycle"), "failure_horizon": horizon,
            "data_quality_status": dq["status"], "reliability": RELIABILITY[dq["status"]],
            "data_quality_issues": dq["issues"], "model_version": meta["model_version"], "decision_threshold": threshold}

    if dq["status"] == "DATA_INVALID":
        rec = recommend_maintenance(0.0, False, 0.0, "DATA_INVALID", threshold, rec_cfg)
        return {**base, "failure_probability": None, "anomaly_score": None, "anomaly_raw_score": None, "anomaly_flag": None,
                "machine_health_indicator": None, "health_breakdown": None, "prediction_status": "NOT_EVALUATED",
                "top_contributing_features": [], "maintenance_recommendation": rec}

    frame = _prepare_history(history, bundle, lookback=True)
    X = _impute(bundle, bundle.feature_engineer.transform(frame).iloc[[-1]])

    p = float(bundle.calibrated_model.predict_proba(X)[0, 1])
    a = bundle.anomaly_scorer.score(X)
    severity = float(a["anomaly_severity"][0])
    flag = bool(a["anomaly_flag"][0])
    hi_cfg = meta["health_indicator"]["config"]
    hi = compute_health_indicator(p, severity, dq["status"], hi_cfg)
    breakdown = health_breakdown(p, severity, dq["status"], hi_cfg)
    rec = recommend_maintenance(p, flag, hi, dq["status"], threshold, rec_cfg)

    top, method = [], None
    if include_explanation:
        try:
            exp = explain_row(bundle.calibrated_model.base_model, X, bundle.feature_names, bundle.reference_values, top_k)
            top, method = exp["top_features"], exp["method"]
        except Exception as exc:  # explanations must never break a prediction
            method = f"unavailable: {exc}"

    return {**base,
            "failure_probability": round(p, 6),
            "anomaly_score": round(float(a["anomaly_score"][0]), 6),
            "anomaly_raw_score": round(float(a["raw"][0]), 6),
            "anomaly_flag": flag,
            "machine_health_indicator": hi,
            "health_breakdown": breakdown,
            "prediction_status": "ALERT" if p >= threshold else "NO_ALERT",
            "top_contributing_features": top,
            "explanation_method": method,
            "maintenance_recommendation": rec}


def score_trajectory(history, bundle, include_recommendation=True):
    """Vectorised per-cycle scoring of a whole chronological history (same maths as predict_machine_state).

    Data quality is evaluated once for the submitted history and applied to every row. Raises DataInvalidError
    for invalid input. Use this (not one predict_machine_state call per cycle) for trajectories / seeding.
    """
    meta = bundle.metadata
    threshold = float(meta["threshold"]["value"])
    dq = check_data_quality(history, meta["quality"])
    if dq["status"] == "DATA_INVALID":
        raise DataInvalidError(dq)
    frame = _prepare_history(history, bundle, lookback=False)
    X = _impute(bundle, bundle.feature_engineer.transform(frame))
    p = bundle.calibrated_model.predict_proba(X)[:, 1]
    a = bundle.anomaly_scorer.score(X)
    hi = compute_health_indicator(p, a["anomaly_severity"], dq["status"], meta["health_indicator"]["config"])
    out = pd.DataFrame({"cycle": frame["cycle"].astype(int).to_numpy(),
                        "failure_probability": p, "anomaly_raw_score": a["raw"], "anomaly_score": a["anomaly_score"],
                        "anomaly_flag": a["anomaly_flag"], "anomaly_severity": a["anomaly_severity"],
                        "machine_health_indicator": hi,
                        "prediction_status": np.where(p >= threshold, "ALERT", "NO_ALERT")})
    if "unit_id" in frame.columns:
        out.insert(0, "machine_id", frame["unit_id"].to_numpy())
    if include_recommendation:
        out["recommendation_category"] = [
            recommend_maintenance(pp, ff, hh, dq["status"], threshold, meta["recommendation_rules"]["config"])["category"]
            for pp, ff, hh in zip(out["failure_probability"], out["anomaly_flag"], out["machine_health_indicator"])]
    out["data_quality_status"] = dq["status"]
    out["reliability"] = RELIABILITY[dq["status"]]
    out.attrs["data_quality"] = dq
    return out
