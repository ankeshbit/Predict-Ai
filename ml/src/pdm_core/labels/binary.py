"""
Binary failure risk labeling for predictive maintenance.
Rule: label = 1 if RUL <= H, where H is the prediction horizon in operating cycles.
"""

import pandas as pd


def assign_binary_labels(
    df: pd.DataFrame,
    horizon: int,
    rul_col: str = "rul",
    label_col: str = "label",
) -> pd.DataFrame:
    """
    Labels records with binary failure risk over a finite horizon H.
    label = 1 if RUL <= horizon, else 0.
    """
    if horizon <= 0:
        raise ValueError(f"Prediction horizon H must be positive, got {horizon}")
    if rul_col not in df.columns:
        raise ValueError(f"RUL column '{rul_col}' not found in dataframe")

    res = df.copy()
    res[label_col] = (res[rul_col] <= horizon).astype(int)
    return res
