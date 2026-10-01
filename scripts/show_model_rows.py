from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import engine
from app.models.entities import ModelVersion, ModelEvaluation

with Session(engine) as db:
    mv = db.scalar(select(ModelVersion).where(ModelVersion.is_active.is_(True)))
    print("=== MODEL VERSION ROW ===")
    if mv:
        print(f"ID: {mv.id}")
        print(f"Bundle Version: {mv.bundle_version}")
        print(f"Task: {mv.task}")
        print(f"Model Type: {mv.model_type}")
        print(f"Adapter Key: {mv.adapter_key}")
        print(f"Feature Config Version: {mv.feature_config_version}")
        print(f"Preprocessing Version: {mv.preprocessing_version}")
        print(f"Input Features Count: {len(mv.input_features)}")
        print(f"Horizon: {mv.horizon} {mv.horizon_unit}")
        print(f"Decision Threshold: {mv.decision_threshold}")
        print(f"Is Active: {mv.is_active}")
        print(f"Model Card Complete: {mv.model_card_complete}")
        print(f"SHA256 Hash: {mv.sha256_hash}")
        print(f"Python Version: {mv.python_version}")
        print(f"Created At: {mv.created_at}")

    me = db.scalar(select(ModelEvaluation))
    print("\n=== MODEL EVALUATION ROW ===")
    if me:
        print(f"ID: {me.id}")
        print(f"Model Version ID: {me.model_version_id}")
        print(f"Task: {me.task}")
        print(f"Evaluated At: {me.evaluated_at}")
        print(f"Evaluation Sets in Curves: {list(me.curves.keys()) if isinstance(me.curves, dict) else None}")
        print("Metrics summary:")
        for k, v in me.metrics.items():
            if isinstance(v, dict):
                print(f"  [{k}] PR-AUC={v.get('pr_auc')}, Precision={v.get('precision')}, Recall={v.get('recall')}, F1={v.get('f1')}, Brier={v.get('brier_score')}, ROC-AUC={v.get('roc_auc')}")
            else:
                print(f"  [{k}]: {v}")
        print(f"Top 5 Features: {me.feature_importance[:5]}")
