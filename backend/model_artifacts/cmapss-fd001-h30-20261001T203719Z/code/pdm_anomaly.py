import numpy as np
from sklearn.ensemble import IsolationForest


def _matrix(X, feature_names):
    return np.asarray(X[list(feature_names)], dtype=float)


class AnomalyScorer:
    """Isolation Forest trained on healthy observations, with transparent user-facing scores."""

    def __init__(self, feature_names, contamination=0.02, n_estimators=300, random_state=42):
        self.feature_names = list(feature_names)
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state

    def fit(self, X_healthy):
        self.iforest_ = IsolationForest(n_estimators=self.n_estimators, contamination="auto",
                                        random_state=self.random_state, n_jobs=-1)
        self.iforest_.fit(_matrix(X_healthy, self.feature_names))
        raw = self.raw_score(X_healthy)
        self.reference_scores_ = np.sort(raw)
        self.flag_percentile_ = 1.0 - self.contamination
        self.flag_threshold_ = float(np.quantile(raw, self.flag_percentile_))
        self.calibration_source_ = "training healthy rows (in-sample)"
        return self

    def recalibrate(self, X_reference):
        """Re-derive the percentile reference and alarm threshold from healthy rows the forest has NOT seen."""
        raw = self.raw_score(X_reference)
        self.reference_scores_ = np.sort(raw)
        self.flag_threshold_ = float(np.quantile(raw, self.flag_percentile_))
        self.calibration_source_ = "held-out healthy rows"
        return self

    def raw_score(self, X):
        """Higher = more anomalous (= -sklearn score_samples)."""
        return -self.iforest_.score_samples(_matrix(X, self.feature_names))

    def score(self, X):
        raw = self.raw_score(X)
        pct = np.searchsorted(self.reference_scores_, raw, side="right") / len(self.reference_scores_)
        q = self.flag_percentile_
        return {"raw": raw,
                "anomaly_score": pct,
                "anomaly_flag": raw > self.flag_threshold_,
                "anomaly_severity": np.clip((pct - q) / (1.0 - q), 0.0, 1.0)}


class ZScoreBaseline:
    """Simple statistical baseline: RMS of per-feature z-scores w.r.t. healthy data."""

    def __init__(self, feature_names, contamination=0.02):
        self.feature_names = list(feature_names)
        self.contamination = contamination

    def fit(self, X_healthy):
        M = _matrix(X_healthy, self.feature_names)
        self.mean_ = M.mean(axis=0)
        sd = M.std(axis=0)
        self.std_ = np.where(sd > 0, sd, 1.0)
        self.flag_threshold_ = float(np.quantile(self.raw_score(X_healthy), 1.0 - self.contamination))
        return self

    def recalibrate(self, X_reference):
        self.flag_threshold_ = float(np.quantile(self.raw_score(X_reference), 1.0 - self.contamination))
        return self

    def raw_score(self, X):
        z = (_matrix(X, self.feature_names) - self.mean_) / self.std_
        return np.sqrt((z ** 2).mean(axis=1))

    def score(self, X):
        raw = self.raw_score(X)
        return {"raw": raw, "anomaly_flag": raw > self.flag_threshold_}
