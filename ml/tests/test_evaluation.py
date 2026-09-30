"""
Unit tests for pdm_core.evaluation
"""

import json

import numpy as np

from pdm_core.evaluation.metrics import (
    compute_evaluation,
    save_evaluation_json,
)
from pdm_core.schemas.bundle_schemas import EvaluationSchema


def test_compute_evaluation():
    np.random.seed(42)
    n = 200
    y_true = np.random.binomial(1, 0.3, size=n)
    # Probabilities correlate with true labels
    y_prob = np.clip(y_true * 0.7 + np.random.uniform(0.0, 0.3, size=n), 0.0, 1.0)

    feature_names = [f"sensor_{i}" for i in range(1, 10)]
    importances = list(np.random.uniform(0.01, 0.5, size=len(feature_names)))

    eval_result = compute_evaluation(
        y_true=y_true,
        y_prob=y_prob,
        model_name="XGBoost Failure Risk",
        model_version="1.0.0",
        task="failure_risk",
        threshold=0.50,
        feature_names=feature_names,
        importances=importances,
    )

    assert isinstance(eval_result, EvaluationSchema)
    assert 0.0 <= eval_result.metrics.pr_auc <= 1.0
    assert 0.0 <= eval_result.metrics.roc_auc <= 1.0
    assert 0.0 <= eval_result.metrics.brier_score <= 1.0
    assert 0.0 <= eval_result.metrics.expected_calibration_error <= 1.0

    # Curves must be downsampled to <= 50 points
    assert len(eval_result.curves.roc_curve.x) <= 50
    assert len(eval_result.curves.pr_curve.x) <= 50

    # Confusion matrix consistency
    cm = eval_result.confusion_matrix
    assert cm.tp + cm.fp + cm.tn + cm.fn == n

    # Feature importance ordering
    assert len(eval_result.feature_importance) == len(feature_names)
    importances_sorted = [item.importance for item in eval_result.feature_importance]
    assert importances_sorted == sorted(importances_sorted, reverse=True)


def test_save_and_reload_evaluation(tmp_path):
    y_true = [0, 1, 0, 1, 1, 0]
    y_prob = [0.1, 0.9, 0.2, 0.8, 0.7, 0.3]

    eval_obj = compute_evaluation(
        y_true=y_true,
        y_prob=y_prob,
        model_name="TestModel",
        model_version="0.1.0",
    )

    out_file = tmp_path / "evaluation.json"
    save_evaluation_json(eval_obj, out_file)

    assert out_file.is_file()
    with open(out_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    reloaded = EvaluationSchema(**data)
    assert reloaded.model_name == "TestModel"
    assert reloaded.metrics.precision == eval_obj.metrics.precision
