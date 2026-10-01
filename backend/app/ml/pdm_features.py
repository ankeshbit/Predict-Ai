import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


def _slope(y):
    """Least-squares slope of y against 0..n-1 (NaN if <2 points or any NaN)."""
    n = len(y)
    if n < 2 or np.isnan(y).any():
        return np.nan
    t = np.arange(n, dtype=float)
    t -= t.mean()
    return float(np.dot(t, y) / np.dot(t, t))


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Causal per-unit time-series feature builder (stateless: fit learns nothing).

    Input columns : cycle, setting_cols, sensor_cols and optionally unit_id.
    Every output row depends only on the same unit's current and PAST rows.
    """

    def __init__(self, sensor_cols, setting_cols, windows=(5, 10), slope_window=10,
                 pct_change_eps=1e-6, pct_change_clip=1.0):
        self.sensor_cols = sensor_cols
        self.setting_cols = setting_cols
        self.windows = windows
        self.slope_window = slope_window
        self.pct_change_eps = pct_change_eps
        self.pct_change_clip = pct_change_clip

    @property
    def max_lookback(self):
        """Number of most-recent rows needed to reproduce the features of the latest row exactly."""
        return int(max(max(self.windows), self.slope_window) + 1)

    def get_feature_names(self):
        names = ["cycle"] + list(self.setting_cols)
        for s in self.sensor_cols:
            names.append(s)
            names += [f"{s}__roll_mean_{w}" for w in self.windows]
            names += [f"{s}__roll_std_{w}" for w in self.windows]
            names += [f"{s}__diff1", f"{s}__pct_change1", f"{s}__slope_{self.slope_window}"]
        return names

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        settings, sensors = list(self.setting_cols), list(self.sensor_cols)
        missing = [c for c in ["cycle"] + settings + sensors if c not in X.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        if not X.index.is_unique:
            raise ValueError("X.index must be unique")
        df = X[["cycle"] + settings + sensors].astype(float).copy()
        df["_unit"] = X["unit_id"].to_numpy() if "unit_id" in X.columns else 0
        df["_order"] = np.arange(len(df))
        df = df.sort_values(["_unit", "cycle", "_order"], kind="mergesort")
        grouped = df.groupby("_unit", sort=False)
        parts = {"cycle": df["cycle"]}
        for c in settings:
            parts[c] = df[c]
        for s in sensors:
            parts[s] = df[s]
            g = grouped[s]
            for w in self.windows:
                parts[f"{s}__roll_mean_{w}"] = g.transform(lambda v, w=w: v.rolling(w, min_periods=1).mean())
                parts[f"{s}__roll_std_{w}"] = g.transform(lambda v, w=w: v.rolling(w, min_periods=1).std(ddof=0))
            diff = g.diff()
            prev = g.shift(1)
            safe = prev.abs() > self.pct_change_eps
            pct = (diff / prev.where(safe)).clip(-self.pct_change_clip, self.pct_change_clip)
            parts[f"{s}__diff1"] = diff.fillna(0.0)
            parts[f"{s}__pct_change1"] = pct.fillna(0.0)
            sw = self.slope_window
            parts[f"{s}__slope_{sw}"] = g.transform(
                lambda v, sw=sw: v.rolling(sw, min_periods=2).apply(_slope, raw=True)).fillna(0.0)
        out = pd.DataFrame(parts, index=df.index)[self.get_feature_names()]
        return out.reindex(X.index)
