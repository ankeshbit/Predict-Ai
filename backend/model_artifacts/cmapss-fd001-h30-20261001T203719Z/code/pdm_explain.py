import numpy as np
import pandas as pd


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def model_kind(model):
    if type(model).__name__ == "XGBClassifier":
        return "xgboost"
    steps = getattr(model, "steps", None)
    if steps and type(steps[-1][1]).__name__ == "LogisticRegression":
        return "logistic_regression"
    return "generic"


def raw_contributions(model, x_row, feature_names, reference_values):
    """Per-feature contributions (log-odds scale, uncalibrated model) for a single-row DataFrame."""
    kind = model_kind(model)
    x = x_row[list(feature_names)]
    if kind == "xgboost":
        import xgboost as xgb
        contrib = model.get_booster().predict(xgb.DMatrix(x), pred_contribs=True)[0][:-1]
        return np.asarray(contrib, dtype=float), "TreeSHAP (xgboost pred_contribs)"
    if kind == "logistic_regression":
        scaler, clf = model.steps[0][1], model.steps[-1][1]
        return clf.coef_[0] * scaler.transform(x)[0], "logistic coefficient x standardised value"
    base = _logit(model.predict_proba(x)[0, 1])
    occl = pd.concat([x] * len(feature_names), ignore_index=True)
    for i, f in enumerate(feature_names):
        occl.iloc[i, occl.columns.get_loc(f)] = reference_values[f]
    return base - _logit(model.predict_proba(occl)[:, 1]), "occlusion vs training-median reference"


def explain_row(model, x_row, feature_names, reference_values, top_k=5):
    contrib, method = raw_contributions(model, x_row, feature_names, reference_values)
    order = np.argsort(-np.abs(contrib))[:top_k]
    top = [{"feature": feature_names[i],
            "value": float(x_row[feature_names[i]].iloc[0]),
            "contribution": float(contrib[i]),
            "direction": "increases_failure_risk" if contrib[i] > 0 else "decreases_failure_risk"}
           for i in order]
    return {"method": method, "space": "log-odds of uncalibrated model", "top_features": top}
