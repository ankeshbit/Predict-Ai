
"""Interface example only - NOT the production application."""
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import verify_artifacts  # VENDORED stdlib-only copy (do not import it from the artifact folder)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ARTIFACT_DIR = Path("artifacts")
state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) refuse to start on tampered files or library-version mismatch
    verify_artifacts.verify_all(ARTIFACT_DIR)
    # 2) only now is it safe to import artifact code (alternatively: vendor pdm_*.py into the backend)
    sys.path.insert(0, str(ARTIFACT_DIR / "code"))
    from pdm_inference import ModelBundle
    state["bundle"] = ModelBundle.load(ARTIFACT_DIR)
    yield
    state.clear()


app = FastAPI(title="Predictive Maintenance inference (example)", lifespan=lifespan)


class PredictRequest(BaseModel):
    machine_id: Optional[Union[int, str]] = None
    history: List[Dict[str, Any]]      # chronological rows: cycle, operating settings, sensors


@app.get("/model/info")
def model_info():
    m = state["bundle"].metadata
    return {k: m[k] for k in ("model_version", "dataset", "failure_horizon", "failure_horizon_status", "calibration_method", "threshold", "training_timestamp")}


@app.post("/predict")
def predict(req: PredictRequest):
    from pdm_inference import predict_machine_state
    if not req.history:
        raise HTTPException(status_code=422, detail="history must not be empty")
    return predict_machine_state(pd.DataFrame(req.history), state["bundle"], machine_id=req.machine_id)


@app.post("/trajectory")
def trajectory(req: PredictRequest):
    from pdm_inference import DataInvalidError, score_trajectory
    try:
        return score_trajectory(pd.DataFrame(req.history), state["bundle"]).to_dict(orient="records")
    except DataInvalidError as e:
        raise HTTPException(status_code=422, detail=e.quality["issues"])
