"""
Unit tests for pdm_core.data (FD001 loader & per-cycle RUL derivation)
"""

import pandas as pd

from pdm_core.data.loader import compute_test_rul, compute_train_rul, load_fd001_raw


def test_load_fd001_raw(synthetic_engine_data):
    df = load_fd001_raw(synthetic_engine_data)
    assert "unit_id" in df.columns
    assert "cycle" in df.columns
    assert "op_setting_1" in df.columns
    assert "sensor_21" in df.columns
    assert df["unit_id"].dtype == int
    assert df["cycle"].dtype == int


def test_compute_train_rul():
    # Engine 1 has 10 cycles, Engine 2 has 20 cycles
    df = pd.DataFrame({
        "unit_id": [1] * 10 + [2] * 20,
        "cycle": list(range(1, 11)) + list(range(1, 21)),
    })
    res = compute_train_rul(df)
    assert "rul" in res.columns
    # For Engine 1, at cycle 1, RUL = 10 - 1 = 9; at cycle 10, RUL = 0
    e1 = res[res["unit_id"] == 1]
    assert e1[e1["cycle"] == 1]["rul"].iloc[0] == 9.0
    assert e1[e1["cycle"] == 10]["rul"].iloc[0] == 0.0

    # With cap
    capped = compute_train_rul(df, max_rul_cap=5)
    assert capped["rul"].max() == 5.0


def test_compute_test_rul():
    # Engine 1 stopped at cycle 15, ground truth remaining RUL is 25
    # Engine 2 stopped at cycle 30, ground truth remaining RUL is 10
    df = pd.DataFrame({
        "unit_id": [1] * 15 + [2] * 30,
        "cycle": list(range(1, 16)) + list(range(1, 31)),
    })
    rul_vector = [25, 10]
    res = compute_test_rul(df, rul_vector)
    assert "rul" in res.columns

    # Engine 1 at last cycle (15): RUL must be exactly 25
    e1_last = res[(res["unit_id"] == 1) & (res["cycle"] == 15)]["rul"].iloc[0]
    assert e1_last == 25.0

    # Engine 1 at cycle 1: RUL must be (15 - 1) + 25 = 39
    e1_first = res[(res["unit_id"] == 1) & (res["cycle"] == 1)]["rul"].iloc[0]
    assert e1_first == 39.0

    # Engine 2 at last cycle (30): RUL must be 10
    e2_last = res[(res["unit_id"] == 2) & (res["cycle"] == 30)]["rul"].iloc[0]
    assert e2_last == 10.0
