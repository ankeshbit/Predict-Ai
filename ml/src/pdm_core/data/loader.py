"""
FD001 dataset loading and per-cycle Remaining Useful Life (RUL) derivation.
"""

from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import pandas as pd

UNIT_COL = "unit_id"
CYCLE_COL = "cycle"
OP_SETTING_COLS = ["op_setting_1", "op_setting_2", "op_setting_3"]
SENSOR_COLS = [f"sensor_{i}" for i in range(1, 22)]
CANONICAL_COLUMNS = [UNIT_COL, CYCLE_COL] + OP_SETTING_COLS + SENSOR_COLS


def load_fd001_raw(
    source: Union[str, Path, pd.DataFrame],
    is_csv: Optional[bool] = None,
) -> pd.DataFrame:
    """
    Loads raw C-MAPSS FD001 engine telemetry.
    Supports either whitespace-delimited raw NASA text files or standard CSVs with/without headers.
    """
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"FD001 data file not found at: {path}")

        # Auto-detect CSV vs whitespace if not specified
        if is_csv is None:
            is_csv = path.suffix.lower() == ".csv"

        if is_csv:
            # Check if headers exist
            sample = pd.read_csv(path, nrows=2)
            has_headers = set(sample.columns).intersection(set(CANONICAL_COLUMNS))
            if has_headers:
                df = pd.read_csv(path)
            else:
                df = pd.read_csv(path, header=None, names=CANONICAL_COLUMNS[:sample.shape[1]])
        else:
            # NASA raw space-delimited text files
            df = pd.read_csv(path, sep=r"\s+", header=None)

    # Trim extra empty columns if parsed from whitespace lines with trailing spaces
    if df.shape[1] > len(CANONICAL_COLUMNS):
        df = df.iloc[:, :len(CANONICAL_COLUMNS)]

    if df.shape[1] < len(CANONICAL_COLUMNS):
        # Assign available subset of canonical columns
        df.columns = CANONICAL_COLUMNS[:df.shape[1]]
    else:
        df.columns = CANONICAL_COLUMNS

    df[UNIT_COL] = df[UNIT_COL].astype(int)
    df[CYCLE_COL] = df[CYCLE_COL].astype(int)

    for col in OP_SETTING_COLS + SENSOR_COLS:
        if col in df.columns:
            df[col] = df[col].astype(float)

    return df.sort_values([UNIT_COL, CYCLE_COL]).reset_index(drop=True)


def compute_train_rul(
    df: pd.DataFrame,
    max_rul_cap: Optional[int] = None,
    rul_col: str = "rul",
) -> pd.DataFrame:
    """
    Computes per-cycle RUL for training engines (run-to-failure).
    RUL at cycle t = max_cycle_for_unit - t.
    Optionally clips RUL to max_rul_cap (e.g. 125 cycles piecewise linear degradation).
    """
    if UNIT_COL not in df.columns or CYCLE_COL not in df.columns:
        raise ValueError(f"Input dataframe must contain '{UNIT_COL}' and '{CYCLE_COL}'")

    res = df.copy()
    max_cycles = res.groupby(UNIT_COL)[CYCLE_COL].transform("max")
    res[rul_col] = (max_cycles - res[CYCLE_COL]).astype(float)

    if max_rul_cap is not None:
        if max_rul_cap <= 0:
            raise ValueError("max_rul_cap must be positive")
        res[rul_col] = res[rul_col].clip(upper=float(max_rul_cap))

    return res


def compute_test_rul(
    test_df: pd.DataFrame,
    rul_vector: Union[str, Path, List[int], np.ndarray, pd.Series],
    max_rul_cap: Optional[int] = None,
    rul_col: str = "rul",
) -> pd.DataFrame:
    """
    Computes per-cycle RUL for test engines (stopped prior to failure).
    Given the ground truth remaining cycles at the last observed cycle R_i,
    RUL at cycle t = (max_cycle_for_unit - t) + R_i.
    """
    if UNIT_COL not in test_df.columns or CYCLE_COL not in test_df.columns:
        raise ValueError(f"Input dataframe must contain '{UNIT_COL}' and '{CYCLE_COL}'")

    if isinstance(rul_vector, (str, Path)):
        rul_path = Path(rul_vector)
        if not rul_path.exists():
            raise FileNotFoundError(f"RUL ground-truth vector file not found at: {rul_path}")
        rul_values = np.loadtxt(rul_path)
    elif isinstance(rul_vector, pd.Series):
        rul_values = rul_vector.values
    else:
        rul_values = np.asarray(rul_vector)

    units = sorted(test_df[UNIT_COL].unique())
    if len(rul_values) < len(units):
        raise ValueError(
            f"RUL vector length ({len(rul_values)}) is smaller than unique test units ({len(units)})"
        )

    # Unit IDs are typically 1-indexed
    unit_to_final_rul = {u: float(rul_values[idx]) for idx, u in enumerate(units)}

    res = test_df.copy()
    last_cycles = res.groupby(UNIT_COL)[CYCLE_COL].transform("max")
    final_ruls = res[UNIT_COL].map(unit_to_final_rul)

    res[rul_col] = (last_cycles - res[CYCLE_COL]) + final_ruls

    if max_rul_cap is not None:
        if max_rul_cap <= 0:
            raise ValueError("max_rul_cap must be positive")
        res[rul_col] = res[rul_col].clip(upper=float(max_rul_cap))

    return res
