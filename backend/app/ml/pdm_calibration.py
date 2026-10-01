import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

_EPS = 1e-6


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), _EPS, 1 - _EPS)
    return np.log(p / (1 - p))


class ProbabilityCalibrator:
    """Maps raw model probabilities to calibrated probabilities. method: none | sigmoid | isotonic."""

    def __init__(self, method="sigmoid"):
        self.method = method

    def fit(self, raw_proba, y):
        raw = np.asarray(raw_proba, dtype=float).ravel()
        y = np.asarray(y).astype(int).ravel()
        if self.method == "sigmoid":
            self._model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000).fit(_logit(raw).reshape(-1, 1), y)
        elif self.method == "isotonic":
            self._model = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(raw, y)
        elif self.method == "none":
            self._model = None
        else:
            raise ValueError(f"Unknown calibration method: {self.method}")
        return self

    def transform(self, raw_proba):
        raw = np.asarray(raw_proba, dtype=float).ravel()
        if self.method == "none":
            out = raw
        elif self.method == "sigmoid":
            out = self._model.predict_proba(_logit(raw).reshape(-1, 1))[:, 1]
        else:
            out = self._model.predict(raw)
        return np.clip(out, 0.0, 1.0)


class CalibratedFailureModel:
    """Base classifier + fitted calibrator. predict_proba(X)[:, 1] = calibrated P(failure within H)."""

    def __init__(self, base_model, calibrator, feature_names):
        self.base_model = base_model
        self.calibrator = calibrator
        self.feature_names = list(feature_names)

    def predict_raw_proba(self, X):
        return self.base_model.predict_proba(X)[:, 1]

    def predict_proba(self, X):
        p = self.calibrator.transform(self.predict_raw_proba(X))
        return np.column_stack([1 - p, p])
