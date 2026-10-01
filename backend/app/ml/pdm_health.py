import numpy as np

DEFAULT_HEALTH_CONFIG = {
    "anomaly_weight": 0.30,
    "data_quality_penalty": {"DATA_OK": 0.0, "DATA_WARNING": 10.0},
}


def compute_health_indicator(failure_probability, anomaly_severity, data_quality_status="DATA_OK", config=None):
    """Machine Health Indicator in [0, 100] (deterministic; NOT a trained model, NOT a physical measurement).

    HI = clip(100 * (1 - P_fail) * (1 - w_a * severity) - penalty, 0, 100).
    Returns None for DATA_INVALID. Accepts scalars or numpy arrays.
    """
    cfg = {**DEFAULT_HEALTH_CONFIG, **(config or {})}
    if data_quality_status == "DATA_INVALID":
        return None
    w_a = float(cfg["anomaly_weight"])
    if not 0.0 <= w_a <= 1.0:
        raise ValueError("anomaly_weight must be in [0, 1]")
    p = np.clip(np.asarray(failure_probability, dtype=float), 0.0, 1.0)
    s = np.clip(np.asarray(anomaly_severity, dtype=float), 0.0, 1.0)
    penalty = float(cfg["data_quality_penalty"].get(data_quality_status, 0.0))
    hi = np.clip(100.0 * (1.0 - p) * (1.0 - w_a * s) - penalty, 0.0, 100.0)
    return float(np.round(hi, 2)) if hi.ndim == 0 else np.round(hi, 2)


def health_breakdown(failure_probability, anomaly_severity, data_quality_status="DATA_OK", config=None):
    """Additive decomposition of the HI (scalar inputs): 100 - failure_risk - anomaly - data_quality (+clip) = HI."""
    cfg = {**DEFAULT_HEALTH_CONFIG, **(config or {})}
    if data_quality_status == "DATA_INVALID":
        return None
    p = float(np.clip(failure_probability, 0.0, 1.0))
    s = float(np.clip(anomaly_severity, 0.0, 1.0))
    w_a = float(cfg["anomaly_weight"])
    penalty = float(cfg["data_quality_penalty"].get(data_quality_status, 0.0))
    risk, anom = 100.0 * p, 100.0 * (1.0 - p) * w_a * s
    raw = 100.0 - risk - anom - penalty
    hi = float(np.clip(raw, 0.0, 100.0))
    return {"start": 100.0, "failure_risk_points": round(risk, 2), "anomaly_points": round(anom, 2),
            "data_quality_points": round(penalty, 2), "trend_points": None, "trend_status": "not_enabled",
            "clipping_adjustment_points": round(hi - raw, 2), "health_indicator": round(hi, 2)}
