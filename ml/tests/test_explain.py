"""
Unit tests for pdm_core.explain
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from pdm_core.explain.attributions import (
    compute_feature_attributions,
    compute_linear_contribution,
    compute_tree_shap,
)


def test_linear_contribution():
    X = np.array([[1.0, 2.0], [2.0, 1.0], [0.5, 3.0]])
    y = np.array([0, 1, 0])
    model = LogisticRegression().fit(X, y)
    feature_names = ["sensor_2", "sensor_3"]

    results = compute_linear_contribution(model, X[0], feature_names)
    assert len(results) == 2
    assert "feature" in results[0]
    assert "attribution" in results[0]
    # Highest absolute magnitude first
    assert abs(results[0]["attribution"]) >= abs(results[1]["attribution"])


def test_tree_shap():
    X = np.random.normal(0, 1, size=(50, 4))
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    model = RandomForestClassifier(n_estimators=10, random_state=42).fit(X, y)
    feature_names = ["sensor_2", "sensor_3", "sensor_4", "sensor_7"]

    results = compute_tree_shap(model, X[:2], feature_names)
    assert len(results) == 4
    assert abs(results[0]["attribution"]) >= abs(results[-1]["attribution"])


def test_unified_dispatcher():
    X = np.array([[1.0, 2.0], [2.0, 1.0]])
    y = np.array([0, 1])
    lin_model = LogisticRegression().fit(X, y)
    res_lin = compute_feature_attributions(lin_model, X[0], ["sensor_2", "sensor_3"])
    assert len(res_lin) == 2
