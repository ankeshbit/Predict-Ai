from app.core.db import engine
from app.models.entities import ModelEvaluation, ModelVersion, Prediction
from sqlalchemy import select
from sqlalchemy.orm import Session

with Session(engine) as db:
    model_versions = db.scalars(select(ModelVersion).order_by(ModelVersion.created_at.asc())).all()
    print("=== MODEL VERSIONS IN DATABASE ===")
    for mv in model_versions:
        print(f"\n[ModelVersion ID: {mv.id}]")
        print(f"  Bundle Version: {mv.bundle_version}")
        print(f"  Task: {mv.task}")
        print(f"  Model Type: {mv.model_type}")
        print(f"  Adapter Key: {mv.adapter_key}")
        print(f"  Horizon: {mv.horizon} {mv.horizon_unit}")
        print(f"  Decision Threshold: {mv.decision_threshold}")
        print(f"  Is Active: {mv.is_active}")
        print(f"  Model Card Complete: {mv.model_card_complete}")
        print(f"  Python Version: {mv.python_version}")
        print(f"  Created At: {mv.created_at}")

        eval_row = db.scalar(select(ModelEvaluation).where(ModelEvaluation.model_version_id == mv.id))
        if eval_row:
            print(f"  [ModelEvaluation ID: {eval_row.id}]")
            print(f"    Task: {eval_row.task}")
            print(f"    Evaluated At: {eval_row.evaluated_at}")
            print(f"    Evaluation Sets: {list(eval_row.curves.keys()) if isinstance(eval_row.curves, dict) else None}")
            if eval_row.task == "failure_risk":
                for set_name, set_metrics in eval_row.metrics.items():
                    if isinstance(set_metrics, dict):
                        brier = set_metrics.get("brier_score") or set_metrics.get("brier")
                        ece = set_metrics.get("expected_calibration_error") or set_metrics.get("ece")
                        print(f"      Set '{set_name}': PR-AUC={set_metrics.get('pr_auc')}, Brier={brier}, ECE={ece}, Precision={set_metrics.get('precision')}, Recall={set_metrics.get('recall')}")
            else:
                print(f"    Anomaly Metrics: {eval_row.metrics}")

    # Check predictions lineage
    preds = db.scalars(select(Prediction).order_by(Prediction.predicted_at.desc()).limit(3)).all()
    print(f"\n=== LATEST PREDICTIONS (Count sample: {len(preds)}) ===")
    for p in preds:
        print(f"Prediction {p.id}: machine={p.machine_id}, cycle={p.cycle}, fail_prob={p.failure_probability}, health={p.health_indicator}, failure_model_id={p.failure_model_version_id}, anomaly_model_id={p.anomaly_model_version_id}, penalty_anomaly={p.penalty_anomaly}")

