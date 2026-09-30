"""
Unit tests for pdm_core.splits (engine-grouped splits with zero overlap)
"""


from pdm_core.splits.grouped import engine_grouped_split, get_engine_split_ids


def test_get_engine_split_ids_two_way():
    units = list(range(1, 11))  # 10 units
    train_u, test_u = get_engine_split_ids(units, test_size=0.2, val_size=0.0, random_state=42)
    assert len(test_u) == 2
    assert len(train_u) == 8
    # Zero overlap
    assert set(train_u).isdisjoint(set(test_u))


def test_get_engine_split_ids_three_way():
    units = list(range(1, 21))  # 20 units
    train_u, val_u, test_u = get_engine_split_ids(units, test_size=0.2, val_size=0.2, random_state=42)
    assert len(test_u) == 4
    assert len(val_u) == 4
    assert len(train_u) == 12
    # Zero overlap across all pairs
    assert set(train_u).isdisjoint(set(val_u))
    assert set(train_u).isdisjoint(set(test_u))
    assert set(val_u).isdisjoint(set(test_u))


def test_engine_grouped_split_dataframe(synthetic_engine_data):
    # synthetic_engine_data has 4 engines: 1, 2, 3, 4
    train_df, test_df = engine_grouped_split(
        synthetic_engine_data, unit_col="unit_id", test_size=0.25, random_state=42
    )

    train_engines = set(train_df["unit_id"].unique())
    test_engines = set(test_df["unit_id"].unique())

    assert len(train_engines) == 3
    assert len(test_engines) == 1
    assert train_engines.isdisjoint(test_engines)
    assert len(train_df) + len(test_df) == len(synthetic_engine_data)
