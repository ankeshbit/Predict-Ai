# Kaggle (or Colab) Execution Runbook

This guide instructs the human operator on how to run the offline training and evaluation pipeline in Kaggle (or Colab) to produce a production model bundle for Predict-Ai.

> **AUTHORITATIVE RUNTIME RULE**: The model was trained on Kaggle, not Colab. The bundle metadata (`library_versions`, `python_version`) is authoritative for the runtime. Do not assume Colab versions anywhere. If the bundle's Python version is not 3.10, update the Dockerfile and CI to match the bundle rather than downgrading or modifying the bundle.

---

## Prerequisites
1. A Kaggle account (or a Google account with access to [Google Colab](https://colab.research.google.com/)).
2. Dataset storage (Kaggle Dataset or Google Drive folder) structured as:
   ```
   predict-ai/
   ├── data/
   │   ├── train_FD001.txt
   │   ├── test_FD001.txt
   │   └── RUL_FD001.txt
   ```
3. The `ml/` folder from this repository uploaded or cloned to Kaggle (or Colab).

---

## Step-by-Step Procedure

### 1. Environment Verification
1. Open `ml/notebooks/00_environment_check.ipynb` in Kaggle (or Colab).
2. Select runtime: **Python 3 (CPU or GPU)**.
3. Run all cells to verify the environment's Python version and inspect installed packages.

### 2. Exploratory Data Analysis (Optional Verification)
1. Open `ml/notebooks/01_eda_fd001.ipynb` in Kaggle (or Colab).
2. Load or mount data:
   - For Kaggle: Load from `/kaggle/input/...`
   - For Colab: Mount Google Drive:
     ```python
     from google.colab import drive
     drive.mount('/content/drive')
     ```
3. Run the notebook to inspect sensor variance, constant channel identification, and operating envelope distributions.

### 3. Model Training, Calibration, & Bundle Export
1. Open `ml/notebooks/02_train_evaluate_export.ipynb` (or `ml/notebooks/AI_Predictive_Maintenance_CMAPSS_FD001.ipynb`) in Kaggle (or Colab).
2. Follow the cell progression:
   - **Cell 1**: Attach dataset path / storage.
   - **Cell 2**: Install `pdm_core` package with pinned `constraints.txt`.
   - **Cell 3**: Load raw C-MAPSS FD001 data and derive run-to-failure RUL.
   - **Cell 4**: Candidate Horizon ($H$) comparison table (evaluating $H \in [20, 25, 30, 35, 40]$).
   - **Cell 5**: Train and calibrate Isolation Forest anomaly detector on early-life healthy windows.
   - **Cell 6**: Train, cross-validate (GroupKFold), calibrate (Platt scaling), and evaluate failure classification models (Logistic Baseline, Random Forest, XGBoost).
   - **Cell 7**: Compute all official evaluation metrics (PR-AUC, ROC-AUC, Brier score, downsampled curves, confusion matrix, and SHAP importances).
   - **Cell 8**: Generate production model bundle (`bundle_v1.0.0.zip` or artifact directory) with complete SHA-256 manifest and model cards.
   - **Cell 9**: Download bundle artifact from the Kaggle (or Colab) output directory.

### 4. Transferring the Bundle to the Backend
1. Extract `artifacts_bundle.zip` into `backend/model_artifacts/<model_version>/` (e.g. `backend/model_artifacts/cmapss-fd001-h30-20261001T.../`).
2. Copy the bundle's own `requirements-inference.txt` directly to `backend/requirements-inference.txt` (never guess package versions):
   ```bash
   cp backend/model_artifacts/<model_version>/requirements-inference.txt backend/requirements-inference.txt
   ```
3. If the bundle's `python_version` in `metadata/model_card.json` or `library_versions` is not 3.10, update `backend/Dockerfile` and `.github/workflows/ci.yml` to match the bundle's Python version.
4. Register the model bundle and seed the demo fleet inside the backend Docker container (which matches the bundle's Python runtime) or a virtualenv with identical pins:
   ```bash
   # Register model (verifies manifest hashes; zero unpickling; no version check at import time)
   docker compose run --rm backend python -m app.cli register-model --bundle-path model_artifacts/<model_version>

   # Seed demo fleet (re-runs score_trajectory in backend, asserts parity with demo_reference_scores.csv, uses distinct engines)
   docker compose run --rm backend python -m app.cli seed-demo --bundle-path model_artifacts/<model_version>
   ```
5. Start the application. At startup, FastAPI lifespan runs `verify_all()` with strict Python (major.minor) and library version checking, refusing to start if any runtime dependency differs from `metadata.library_versions`.
