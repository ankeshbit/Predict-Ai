"""
Unit tests for pdm_core.features
Verifies strict causality and absence of future data leakage.
"""

import numpy as np
import pandas as pd

from pdm_core.features.pipeline import extract_features, get_feature_names


def test_extract_features_runs(synthetic_engine_data):
    features_df = extract_features(synthetic_engine_data)
    assert "unit_id" in features_df.columns
    assert "cycle" in features_df.columns
    feature_names = get_feature_names()
    for fn in feature_names:
        assert fn in features_df.columns


def test_strict_causality_no_future_leakage():
    """
    Core invariant test:
    Features computed at cycle t must depend ONLY on data at cycles <= t.
    Modifying or appending future rows (t+1 ... N) MUST NOT alter the feature
    values at cycle t.
    """
    np.random.seed(42)
    # Generate an engine with 60 cycles
    cycles = 60
    rows = []
    for c in range(1, cycles + 1):
        row = {"unit_id": 1, "cycle": c}
        for s in range(1, 22):
            row[f"sensor_{s}"] = float(100.0 + c * 0.5 + np.random.normal(0, 0.2))
        for o in range(1, 4):
            row[f"op_setting_{o}"] = float(0.0)
        rows.append(row)
    full_df = pd.DataFrame(rows)

    # 1. Extract features on the first 30 cycles alone
    sub_df = full_df[full_df["cycle"] <= 30].copy()
    sub_features = extract_features(sub_df)

    # 2. Extract features on the full 60 cycles
    full_features = extract_features(full_df)

    # 3. Features at cycle <= 30 in both runs must be BIT-FOR-BIT IDENTICAL
    feature_cols = [c for c in sub_features.columns if c not in ["unit_id", "cycle"]]
    for col in feature_cols:
        sub_vals = sub_features[col].values
        full_vals_up_to_30 = full_features[full_features["cycle"] <= 30][col].values
        np.testing.assert_allclose(
            sub_vals,
            full_vals_up_to_30,
            rtol=1e-7,
            atol=1e-7,
            err_msg=f"Future data leakage detected in feature '{col}': values at cycle <= 30 changed when future data was present!",
        )

    # 4. Modify future data (cycles 31..60) with extreme values / noise and re-test
    perturbed_df = full_df.copy()
    for s in range(1, 22):
        perturbed_df.loc[perturbed_df["cycle"] > 30, f"sensor_{s}"] = 999999.0

    perturbed_features = extract_features(perturbed_df)
    for col in feature_cols:
        sub_vals = sub_features[col].values
        perturbed_vals_up_to_30 = perturbed_features[perturbed_features["cycle"] <= 30][col].values
        np.testing.assert_allclose(
            sub_vals,
            perturbed_vals_up_to_30,
            rtol=1e-7,
            atol=1e-7,
            err_msg=f"Future perturbation leaked backward into historical cycle in feature '{col}'!",
        )
