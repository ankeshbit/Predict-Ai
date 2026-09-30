"""
Feature attribution and explainability helpers for pdm_core.
Supports TreeSHAP for tree-based models (XGBoost, Random Forest)
and linear weight contributions for linear models.
"""

from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd


def compute_tree_shap(
    model: Any,
    X_sample: Union[np.ndarray, pd.DataFrame],
    feature_names: List[str],
) -> List[Dict[str, Any]]:
    """
    Computes TreeSHAP attributions for tree models.
    Returns feature contributions sorted by absolute importance descending.
    """
    import shap

    X_mat = X_sample.values if isinstance(X_sample, pd.DataFrame) else np.asarray(X_sample)
    if X_mat.ndim == 1:
        X_mat = X_mat.reshape(1, -1)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_mat)

    # In binary classification, some models return 2D array (samples, features)
    # or list of arrays [class_0, class_1]. We target positive class (failure risk).
    if isinstance(shap_values, list):
        vals = shap_values[1] if len(shap_values) > 1 else shap_values[0]
    elif hasattr(shap_values, "values"):  # Explanation object
        vals = shap_values.values
    else:
        vals = shap_values

    # In multiclass / binary 3D output (samples, features, classes), select positive class
    if hasattr(vals, "ndim") and vals.ndim == 3:
        vals = vals[:, :, 1] if vals.shape[2] > 1 else vals[:, :, 0]

    # Mean attribution across sample rows
    if hasattr(vals, "ndim") and vals.ndim > 1:
        mean_attr = np.mean(vals, axis=0)
    else:
        mean_attr = vals

    sample_values = np.mean(X_mat, axis=0) if X_mat.ndim > 1 else X_mat

    results: List[Dict[str, Any]] = []
    for idx, name in enumerate(feature_names):
        attr_val = float(np.ravel(mean_attr)[idx])
        samp_val = float(np.ravel(sample_values)[idx])
        results.append({
            "feature": name,
            "attribution": float(round(attr_val, 5)),
            "value": float(round(samp_val, 5)),
        })

    # Sort descending by absolute attribution magnitude
    results.sort(key=lambda item: abs(item["attribution"]), reverse=True)
    return results


def compute_linear_contribution(
    model: Any,
    X_sample: Union[np.ndarray, pd.DataFrame],
    feature_names: List[str],
) -> List[Dict[str, Any]]:
    """
    Computes linear contributions for linear models (e.g. LogisticRegression).
    Contribution = coef_j * x_j.
    """
    X_mat = X_sample.values if isinstance(X_sample, pd.DataFrame) else np.asarray(X_sample)
    if X_mat.ndim == 1:
        X_mat = X_mat.reshape(1, -1)

    if not hasattr(model, "coef_"):
        raise ValueError("Model does not have 'coef_' attribute for linear contributions")

    coefs = model.coef_
    if coefs.ndim > 1:
        coefs = coefs[0]

    sample_values = np.mean(X_mat, axis=0)
    contributions = coefs * sample_values

    results: List[Dict[str, Any]] = []
    for idx, name in enumerate(feature_names):
        results.append({
            "feature": name,
            "attribution": float(round(contributions[idx], 5)),
            "value": float(round(sample_values[idx], 5)),
        })

    results.sort(key=lambda item: abs(item["attribution"]), reverse=True)
    return results


def compute_feature_attributions(
    model: Any,
    X_sample: Union[np.ndarray, pd.DataFrame],
    feature_names: List[str],
    explainer_kind: str = "auto",
) -> List[Dict[str, Any]]:
    """
    Unified public dispatcher for feature attributions.
    """
    if explainer_kind == "linear" or hasattr(model, "coef_"):
        return compute_linear_contribution(model, X_sample, feature_names)
    elif explainer_kind == "tree_shap" or hasattr(model, "feature_importances_"):
        try:
            return compute_tree_shap(model, X_sample, feature_names)
        except Exception:
            # Fallback to feature_importances_ weighting if TreeSHAP fails on custom tree wrapper
            X_mat = X_sample.values if isinstance(X_sample, pd.DataFrame) else np.asarray(X_sample)
            if X_mat.ndim == 1:
                X_mat = X_mat.reshape(1, -1)
            sample_values = np.mean(X_mat, axis=0)
            imp = getattr(model, "feature_importances_", np.ones(len(feature_names)))
            results = [
                {
                    "feature": name,
                    "attribution": float(round(imp[idx] * (sample_values[idx] != 0), 5)),
                    "value": float(round(sample_values[idx], 5)),
                }
                for idx, name in enumerate(feature_names)
            ]
            results.sort(key=lambda item: abs(item["attribution"]), reverse=True)
            return results
    else:
        raise ValueError(f"Unsupported explainer kind or model type: {explainer_kind}")
