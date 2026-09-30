"""
Evaluation metrics and curve computation for pdm_core.
Generates evaluation.json matching EvaluationSchema with PR-AUC, ROC-AUC, Brier score,
ECE, calibration bins, downsampled curves (<=50 points), and feature importances.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.metrics import (
    auc,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from pdm_core.schemas.bundle_schemas import (
    CalibrationCurveSchema,
    ConfusionMatrixSchema,
    CurvePointSchema,
    CurvesSchema,
    EvaluationMetricsSchema,
    EvaluationSchema,
    FeatureImportanceItem,
)


def compute_ece(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> Tuple[float, List[float], List[float], List[int]]:
    """
    Computes Expected Calibration Error (ECE) and binning statistics.
    """
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_indices = np.digitize(y_prob, bin_edges) - 1
    # Clip edge cases (e.g. prob == 1.0)
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    ece = 0.0
    total_samples = len(y_true)
    prob_pred_list: List[float] = []
    prob_true_list: List[float] = []
    bin_counts: List[int] = []

    for b in range(n_bins):
        mask = bin_indices == b
        count = int(np.sum(mask))
        bin_counts.append(count)
        if count > 0:
            bin_acc = float(np.mean(y_true[mask]))
            bin_conf = float(np.mean(y_prob[mask]))
            ece += (count / total_samples) * abs(bin_acc - bin_conf)
            prob_true_list.append(round(bin_acc, 5))
            prob_pred_list.append(round(bin_conf, 5))
        else:
            midpoint = float(0.5 * (bin_edges[b] + bin_edges[b + 1]))
            prob_true_list.append(0.0)
            prob_pred_list.append(round(midpoint, 5))

    return float(round(ece, 5)), prob_pred_list, prob_true_list, bin_counts


def downsample_curve(
    x_raw: np.ndarray,
    y_raw: np.ndarray,
    thresholds_raw: Optional[np.ndarray] = None,
    max_points: int = 50,
) -> CurvePointSchema:
    """
    Downsamples monotonic/staircase curve coordinates to at most max_points,
    guaranteeing start and end points are preserved.
    """
    n = len(x_raw)
    if n <= max_points:
        indices = np.arange(n)
    else:
        # Uniformly spaced integer sample indices
        indices = np.unique(np.linspace(0, n - 1, max_points, dtype=int))

    def sanitize_float(v: Any, fallback: float = 1.0) -> float:
        try:
            fv = float(v)
            if np.isnan(fv) or np.isinf(fv):
                return fallback
            return float(round(fv, 5))
        except (ValueError, TypeError):
            return fallback

    x_sampled = [sanitize_float(v, 0.0) for v in x_raw[indices]]
    y_sampled = [sanitize_float(v, 0.0) for v in y_raw[indices]]

    thresh_sampled = None
    if thresholds_raw is not None and len(thresholds_raw) == n:
        thresh_sampled = [sanitize_float(v, 1.0) for v in thresholds_raw[indices]]

    return CurvePointSchema(x=x_sampled, y=y_sampled, thresholds=thresh_sampled)


def compute_evaluation(
    y_true: Union[List[int], np.ndarray, pd.Series],
    y_prob: Union[List[float], np.ndarray, pd.Series],
    model_name: str,
    model_version: str,
    task: str = "failure_risk",
    threshold: float = 0.50,
    feature_names: Optional[Sequence[str]] = None,
    importances: Optional[Sequence[float]] = None,
    methodology: str = "Engine-grouped cross-validation on C-MAPSS FD001",
    limitations: Optional[List[str]] = None,
) -> EvaluationSchema:
    """
    Computes all standard PRD FR-16 / FR-17 evaluation metrics and returns validated EvaluationSchema.
    """
    yt = np.asarray(y_true, dtype=int)
    yp = np.asarray(y_prob, dtype=float)

    if len(yt) != len(yp):
        raise ValueError(f"Length mismatch: y_true ({len(yt)}) vs y_prob ({len(yp)})")

    # Binary predictions at specified threshold
    y_pred = (yp >= threshold).astype(int)

    # 1. Confusion Matrix
    cm = confusion_matrix(yt, y_pred, labels=[0, 1])
    tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

    # 2. Scalar Metrics
    prec = float(precision_score(yt, y_pred, zero_division=0))
    rec = float(recall_score(yt, y_pred, zero_division=0))
    f1 = float(f1_score(yt, y_pred, zero_division=0))
    brier = float(brier_score_loss(yt, yp))

    # ROC-AUC & Curves
    try:
        roc_val = float(roc_auc_score(yt, yp))
    except ValueError:
        roc_val = 0.5

    fpr, tpr, roc_thresh = roc_curve(yt, yp)
    roc_point_schema = downsample_curve(fpr, tpr, roc_thresh, max_points=50)

    # PR-AUC & Curves
    prec_curve, rec_curve, pr_thresh = precision_recall_curve(yt, yp)
    pr_auc_val = float(auc(rec_curve, prec_curve))
    # Pad thresholds by 1 for pr curve matching length
    pr_thresh_padded = np.append(pr_thresh, 1.0)
    pr_point_schema = downsample_curve(rec_curve, prec_curve, pr_thresh_padded, max_points=50)

    # 3. Calibration & ECE
    ece_val, prob_pred_list, prob_true_list, bin_counts = compute_ece(yt, yp, n_bins=10)

    # 4. Feature Importance
    feat_importance_items: List[FeatureImportanceItem] = []
    if feature_names is not None and importances is not None:
        if len(feature_names) == len(importances):
            sorted_idx = np.argsort(importances)[::-1]
            for idx in sorted_idx:
                feat_importance_items.append(
                    FeatureImportanceItem(
                        feature=str(feature_names[idx]),
                        importance=float(round(importances[idx], 5)),
                    )
                )

    default_limitations = [
        "Evaluated on NASA C-MAPSS FD001 simulated turbofan data under sea-level conditions.",
        "Not calibrated for high-altitude transients or multi-operating condition flight profiles.",
        "Predictions indicate statistical failure probability within horizon H, not a confirmed physical failure.",
    ]

    metrics = EvaluationMetricsSchema(
        pr_auc=round(pr_auc_val, 4),
        roc_auc=round(roc_val, 4),
        precision=round(prec, 4),
        recall=round(rec, 4),
        f1_score=round(f1, 4),
        brier_score=round(brier, 4),
        expected_calibration_error=round(ece_val, 4),
    )

    return EvaluationSchema(
        task=task,
        model_name=model_name,
        model_version=model_version,
        evaluation_date=datetime.now(timezone.utc).isoformat(),
        metrics=metrics,
        confusion_matrix=ConfusionMatrixSchema(
            threshold=threshold,
            tp=tp,
            fp=fp,
            tn=tn,
            fn=fn,
        ),
        calibration_curve=CalibrationCurveSchema(
            prob_pred=prob_pred_list,
            prob_true=prob_true_list,
            bin_counts=bin_counts,
        ),
        curves=CurvesSchema(
            roc_curve=roc_point_schema,
            pr_curve=pr_point_schema,
        ),
        feature_importance=feat_importance_items,
        methodology=methodology,
        limitations=limitations or default_limitations,
    )


def save_evaluation_json(evaluation: EvaluationSchema, output_path: Union[str, Path]) -> Path:
    """Saves EvaluationSchema as formatted JSON."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(evaluation.model_dump_json(indent=2))
    return out
