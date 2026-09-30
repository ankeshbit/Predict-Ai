"""
Unit tests for pdm_core.labels
"""

import pandas as pd
import pytest

from pdm_core.labels.binary import assign_binary_labels


def test_assign_binary_labels():
    df = pd.DataFrame({
        "unit_id": [1, 1, 1, 1],
        "cycle": [1, 2, 3, 4],
        "rul": [40.0, 30.0, 20.0, 5.0],
    })
    labeled = assign_binary_labels(df, horizon=30)
    assert "label" in labeled.columns
    # RUL 40 > 30 -> 0; RUL 30 <= 30 -> 1; RUL 20 <= 30 -> 1; RUL 5 <= 30 -> 1
    assert list(labeled["label"].values) == [0, 1, 1, 1]


def test_invalid_horizon():
    df = pd.DataFrame({"rul": [10.0, 5.0]})
    with pytest.raises(ValueError, match="positive"):
        assign_binary_labels(df, horizon=0)
    with pytest.raises(ValueError, match="positive"):
        assign_binary_labels(df, horizon=-5)
