"""
Explainability and feature attribution for pdm_core
"""

from pdm_core.explain.attributions import (
    compute_feature_attributions,
    compute_linear_contribution,
    compute_tree_shap,
)

__all__ = [
    "compute_feature_attributions",
    "compute_linear_contribution",
    "compute_tree_shap",
]
