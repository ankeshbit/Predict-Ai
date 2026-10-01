DEFAULT_RECOMMENDATION_CONFIG = {
    "urgent_probability": 0.80,
    "urgent_health_max": 25.0,
    "schedule_health_max": 50.0,
    "inspect_health_max": 75.0,
    "inspect_probability_fraction_of_threshold": 0.5,
}
CATEGORIES = ("MONITOR", "INSPECT", "SCHEDULE MAINTENANCE", "URGENT REVIEW")
LABEL = "AI recommendation - not a confirmed diagnosis"
DISCLAIMER = ("This is an AI-generated recommendation derived from model outputs by transparent rules. It is not a "
              "confirmed diagnosis or a maintenance instruction; a qualified person should make the final decision.")


def recommend_maintenance(failure_probability, anomaly_flag, health_indicator, data_quality_status,
                          decision_threshold, config=None):
    cfg = {**DEFAULT_RECOMMENDATION_CONFIG, **(config or {})}
    reasons = []
    if data_quality_status == "DATA_INVALID":
        return {"label": cfg.get("label", LABEL), "category": "DATA CHECK REQUIRED",
                "reasons": ["Input data failed validation; no prediction was made. This is not a failure claim."],
                "disclaimer": cfg.get("disclaimer", DISCLAIMER)}
    p, hi, thr = float(failure_probability), float(health_indicator), float(decision_threshold)
    urgent_p = max(cfg["urgent_probability"], thr)
    if p >= urgent_p or hi <= cfg["urgent_health_max"]:
        category = "URGENT REVIEW"
        reasons.append(f"Failure probability {p:.2f} >= {urgent_p:.2f}" if p >= urgent_p else f"Health indicator {hi:.1f} <= {cfg['urgent_health_max']}")
    elif p >= thr or hi <= cfg["schedule_health_max"]:
        category = "SCHEDULE MAINTENANCE"
        reasons.append(f"Failure probability {p:.2f} >= decision threshold {thr:.2f}" if p >= thr else f"Health indicator {hi:.1f} <= {cfg['schedule_health_max']}")
    elif anomaly_flag or p >= cfg["inspect_probability_fraction_of_threshold"] * thr or hi <= cfg["inspect_health_max"]:
        category = "INSPECT"
        if anomaly_flag:
            reasons.append("Anomaly detector flags unusual behaviour relative to healthy training data")
        if p >= cfg["inspect_probability_fraction_of_threshold"] * thr:
            reasons.append(f"Failure probability {p:.2f} is approaching the decision threshold {thr:.2f}")
        if hi <= cfg["inspect_health_max"]:
            reasons.append(f"Health indicator {hi:.1f} <= {cfg['inspect_health_max']}")
    else:
        category = "MONITOR"
        reasons.append("No rule triggered: low failure probability, no anomaly flag, health indicator high")
    if data_quality_status == "DATA_WARNING":
        reasons.append("Data-quality warning present: verify inputs before acting")
    return {"label": cfg.get("label", LABEL), "category": category, "reasons": reasons, "disclaimer": cfg.get("disclaimer", DISCLAIMER)}
