"""
Past-only, causal feature engineering pipeline driven by feature_config.yaml.
Guaranteed zero future data leakage:
For any engine unit and cycle t, feature values depend exclusively on cycles <= t.
"""

from pathlib import Path
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd
import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "default_config.yaml"


def load_feature_config(config_source: Union[str, Path, Dict[str, Any], None] = None) -> Dict[str, Any]:
    """Loads feature configuration dictionary from path, yaml string, or returns default."""
    if config_source is None:
        with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    if isinstance(config_source, dict):
        return config_source.copy()

    path = Path(config_source)
    if path.is_file():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # Attempt parsing as raw YAML string
    return yaml.safe_load(str(config_source))


def extract_features(
    df: pd.DataFrame,
    config: Union[str, Path, Dict[str, Any], None] = None,
) -> pd.DataFrame:
    """
    Public feature extraction function used by both training and serving.

    Transforms raw telemetry into a feature-engineered DataFrame.
    Operates strictly past-only:
    - Sorts by unit_id and cycle.
    - Groups by unit_id.
    - Rolling calculations only use trailing past windows (min_periods=1, right-aligned).
    - Lags are strictly positive shifts (t - lag).
    - Never inspects future cycles (no forward shift, no centered window).
    """
    cfg = load_feature_config(config)
    unit_col = cfg.get("unit_col", "unit_id")
    cycle_col = cfg.get("cycle_col", "cycle")

    if unit_col not in df.columns or cycle_col not in df.columns:
        raise ValueError(f"Input dataframe missing required keys: {unit_col}, {cycle_col}")

    # Preserve original index for alignment, work on a sorted view
    sorted_df = df.sort_values([unit_col, cycle_col]).copy()

    drop_channels = set(cfg.get("drop_channels", []))
    rolling_windows = cfg.get("rolling_windows", [5, 15, 30])
    rolling_ops = cfg.get("rolling_ops", ["mean", "std"])
    lag_steps = cfg.get("lag_steps", [1, 5])
    compute_rolling_diff = cfg.get("compute_rolling_diff", True)
    include_raw = cfg.get("include_raw_channels", True)

    # Determine numeric channels to transform (op_settings and sensors)
    all_numeric = [
        c for c in sorted_df.columns
        if c not in [unit_col, cycle_col, "rul", "label"] and pd.api.types.is_numeric_dtype(sorted_df[c])
    ]
    active_channels = [c for c in all_numeric if c not in drop_channels]

    # Pre-allocate dictionary of engineered feature columns
    features_dict: Dict[str, np.ndarray] = {
        unit_col: sorted_df[unit_col].values,
        cycle_col: sorted_df[cycle_col].values,
    }

    if include_raw:
        for ch in active_channels:
            features_dict[ch] = sorted_df[ch].values

    # Groupby object for causal rolling operations
    grouped = sorted_df.groupby(unit_col)

    # 1. Rolling statistics (mean, std)
    for w in rolling_windows:
        rolling_obj = grouped[active_channels].rolling(window=w, min_periods=1)

        if "mean" in rolling_ops:
            mean_df = rolling_obj.mean().reset_index(level=0, drop=True)
            for ch in active_channels:
                feat_name = f"{ch}_roll_mean_{w}"
                features_dict[feat_name] = mean_df[ch].values

                if compute_rolling_diff:
                    # Current value minus rolling mean
                    features_dict[f"{ch}_diff_roll_mean_{w}"] = sorted_df[ch].values - mean_df[ch].values

        if "std" in rolling_ops:
            std_df = rolling_obj.std().reset_index(level=0, drop=True)
            for ch in active_channels:
                feat_name = f"{ch}_roll_std_{w}"
                # Replace initial single-point NaNs in std with 0.0
                features_dict[feat_name] = std_df[ch].fillna(0.0).values

    # 2. Causal lag differences: val(t) - val(t - lag)
    for lag in lag_steps:
        lag_df = grouped[active_channels].shift(lag)
        for ch in active_channels:
            diff_feat = f"{ch}_lag_diff_{lag}"
            # Where lag goes beyond engine start, difference is filled with 0.0
            diff_vals = sorted_df[ch].values - lag_df[ch].values
            features_dict[diff_feat] = np.nan_to_num(diff_vals, nan=0.0)

    # Reconstruct DataFrame matching sorted order
    feature_df = pd.DataFrame(features_dict, index=sorted_df.index)

    # Carry forward target columns if present in original data (for training sets)
    for target_col in ["rul", "label"]:
        if target_col in sorted_df.columns:
            feature_df[target_col] = sorted_df[target_col].values

    # Re-align back to original input row index order
    return feature_df.loc[df.index]


def get_feature_names(config: Union[str, Path, Dict[str, Any], None] = None) -> List[str]:
    """
    Returns ordered list of engineered feature column names (excluding unit_id, cycle, rul, label).
    """
    cfg = load_feature_config(config)
    unit_col = cfg.get("unit_col", "unit_id")
    cycle_col = cfg.get("cycle_col", "cycle")

    # Generate synthetic single-engine dummy frame to inspect output columns
    dummy_rows = []
    for c in range(1, 35):
        row = {unit_col: 1, cycle_col: c}
        for s in range(1, 22):
            row[f"sensor_{s}"] = 100.0
        for o in range(1, 4):
            row[f"op_setting_{o}"] = 0.0
        dummy_rows.append(row)
    dummy_df = pd.DataFrame(dummy_rows)

    extracted = extract_features(dummy_df, cfg)
    non_feature_cols = {unit_col, cycle_col, "rul", "label"}
    return [col for col in extracted.columns if col not in non_feature_cols]
