"""
Engine-grouped train/val/test splits.
Enforces zero engine overlap across split partitions.
"""

from typing import List, Set, Tuple, Union

import numpy as np
import pandas as pd


def get_engine_split_ids(
    unit_ids: Union[List[int], np.ndarray, pd.Series],
    test_size: float = 0.2,
    val_size: float = 0.0,
    random_state: int = 42,
) -> Tuple[List[int], ...]:
    """
    Partitions unique engine unit IDs into disjoint sets with zero overlap.
    """
    unique_units = np.unique(unit_ids)
    n_units = len(unique_units)
    if n_units < 2:
        raise ValueError(f"Need at least 2 unique engines to perform split, found {n_units}")

    rng = np.random.default_rng(random_state)
    shuffled = rng.permutation(unique_units)

    n_test = max(1, int(round(n_units * test_size)))
    n_val = int(round(n_units * val_size)) if val_size > 0.0 else 0

    if n_test + n_val >= n_units:
        raise ValueError(
            f"Test size ({n_test}) + Val size ({n_val}) exceeds or equals total engines ({n_units})"
        )

    test_units = sorted(shuffled[:n_test].tolist())
    if n_val > 0:
        val_units = sorted(shuffled[n_test : n_test + n_val].tolist())
        train_units = sorted(shuffled[n_test + n_val :].tolist())
        # Verify strict disjointness
        assert len(set(train_units) & set(val_units)) == 0
        assert len(set(train_units) & set(test_units)) == 0
        assert len(set(val_units) & set(test_units)) == 0
        return train_units, val_units, test_units
    else:
        train_units = sorted(shuffled[n_test:].tolist())
        assert len(set(train_units) & set(test_units)) == 0
        return train_units, test_units


def engine_grouped_split(
    df: pd.DataFrame,
    unit_col: str = "unit_id",
    test_size: float = 0.2,
    val_size: float = 0.0,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, ...]:
    """
    Splits telemetry DataFrame into train/test (or train/val/test) sets by engine ID.
    Guarantees that no engine appears in more than one partition.
    """
    if unit_col not in df.columns:
        raise ValueError(f"Unit column '{unit_col}' not found in dataframe")

    unique_units = df[unit_col].unique()

    if val_size > 0.0:
        train_u, val_u, test_u = get_engine_split_ids(
            unique_units, test_size=test_size, val_size=val_size, random_state=random_state
        )
        train_df = df[df[unit_col].isin(train_u)].copy()
        val_df = df[df[unit_col].isin(val_u)].copy()
        test_df = df[df[unit_col].isin(test_u)].copy()

        # Enforce zero overlap
        train_set: Set[int] = set(train_df[unit_col].unique())
        val_set: Set[int] = set(val_df[unit_col].unique())
        test_set: Set[int] = set(test_df[unit_col].unique())
        if train_set.intersection(val_set) or train_set.intersection(test_set) or val_set.intersection(test_set):
            raise AssertionError("Engine leakage detected across split partitions!")

        return train_df, val_df, test_df
    else:
        train_u, test_u = get_engine_split_ids(
            unique_units, test_size=test_size, val_size=0.0, random_state=random_state
        )
        train_df = df[df[unit_col].isin(train_u)].copy()
        test_df = df[df[unit_col].isin(test_u)].copy()

        train_set = set(train_df[unit_col].unique())
        test_set = set(test_df[unit_col].unique())
        if train_set.intersection(test_set):
            raise AssertionError("Engine leakage detected across train and test partitions!")

        return train_df, test_df
