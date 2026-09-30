"""
Unit tests for Dataset Adapters and Canonical Schema Translation
"""

import pandas as pd
from app.adapters.cmapss_fd001 import CmapssFd001Adapter
from app.adapters.registry import get_adapter, list_adapters


def test_adapter_registry():
    adapters = list_adapters()
    assert len(adapters) >= 1
    assert any(a["adapter_key"] == "cmapss_fd001" for a in adapters)

    adapter = get_adapter("cmapss_fd001")
    assert isinstance(adapter, CmapssFd001Adapter)


def test_cmapss_adapter_exact_mapping():
    adapter = CmapssFd001Adapter()
    exact_cols = adapter.canonical_columns
    mapping, unmapped = adapter.detect_mapping(exact_cols)

    assert len(unmapped) == 0
    assert len(mapping) == 26
    for c in exact_cols:
        assert mapping[c] == c


def test_cmapss_adapter_fuzzy_variation_mapping():
    adapter = CmapssFd001Adapter()
    fuzzy_cols = (
        ["unit", "cycles", "setting_1", "setting_2", "setting_3"]
        + [f"s_{i}" for i in range(1, 22)]
    )
    mapping, unmapped = adapter.detect_mapping(fuzzy_cols)

    assert len(unmapped) == 0
    assert mapping["unit_id"] == "unit"
    assert mapping["cycle"] == "cycles"
    assert mapping["op_setting_1"] == "setting_1"
    assert mapping["sensor_21"] == "s_21"


def test_cmapss_adapter_missing_columns():
    adapter = CmapssFd001Adapter()
    # Missing sensor_20, sensor_21
    cols = ["unit_id", "cycle", "op_setting_1", "op_setting_2", "op_setting_3"] + [
        f"sensor_{i}" for i in range(1, 20)
    ]
    mapping, unmapped = adapter.detect_mapping(cols)

    assert "sensor_20" in unmapped
    assert "sensor_21" in unmapped
    assert len(unmapped) == 2


def test_compute_mapping_hash_deterministic():
    adapter = CmapssFd001Adapter()
    mapping_a = {"sensor_2": "s2", "sensor_1": "s1", "unit_id": "unit"}
    mapping_b = {"unit_id": "unit", "sensor_1": "s1", "sensor_2": "s2"}

    hash_a = adapter.compute_mapping_hash(mapping_a)
    hash_b = adapter.compute_mapping_hash(mapping_b)

    assert hash_a == hash_b
    assert len(hash_a) == 64


def test_transform_types_and_ordering():
    adapter = CmapssFd001Adapter()
    data = {
        "engine": ["2", "1", "1"],
        "time": ["10", "5", "1"],
        "setting1": ["0.1", "0.2", "0.3"],
        "setting2": ["0.01", "0.02", "0.03"],
        "setting3": ["100.0", "100.0", "100.0"],
    }
    for i in range(1, 22):
        data[f"s{i}"] = [float(i), float(i * 2), float(i * 3)]

    raw_df = pd.DataFrame(data)
    mapping, _ = adapter.detect_mapping(list(raw_df.columns))
    df = adapter.transform(raw_df, mapping)

    assert df["unit_id"].dtype == "int32" or df["unit_id"].dtype == "int64"
    assert df["cycle"].dtype == "int32" or df["cycle"].dtype == "int64"
    assert df["sensor_1"].dtype == "float64"

    # Sorted by unit_id ascending, cycle ascending
    assert list(df["unit_id"]) == [1, 1, 2]
    assert list(df["cycle"]) == [1, 5, 10]
