"""Test suite configuration for pdm_core"""
import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_engine_data():
    """Generates synthetic run-to-failure engine telemetry strictly for unit testing."""
    np.random.seed(42)
    rows = []
    for unit_id in range(1, 5):
        max_cycles = np.random.randint(60, 100)
        for cycle in range(1, max_cycles + 1):
            deg = cycle / max_cycles
            row = {
                "unit_id": unit_id,
                "cycle": cycle,
                "op_setting_1": 0.0,
                "op_setting_2": 0.0,
                "op_setting_3": 100.0,
            }
            for s in range(1, 22):
                if s in [1, 5, 6, 10, 16, 18, 19]:
                    row[f"sensor_{s}"] = 500.0 # constant channel
                else:
                    row[f"sensor_{s}"] = 100.0 + deg * 20.0 + np.random.normal(0, 1.0)
            rows.append(row)
    return pd.DataFrame(rows)
