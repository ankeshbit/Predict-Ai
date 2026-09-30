# Google Colab Execution Runbook

This guide instructs the human operator on how to run the offline training and evaluation pipeline in Google Colab to produce a production model bundle for Predict-Ai.

---

## Prerequisites
1. A Google account with access to [Google Colab](https://colab.research.google.com/).
2. A Google Drive folder structured as:
   ```
   My Drive/predict-ai/
   ├── data/
   │   ├── train_FD001.txt
   │   ├── test_FD001.txt
   │   └── RUL_FD001.txt
   ```
3. The `ml/` folder from this repository uploaded or cloned to Colab.

---

## Step-by-Step Procedure

### 1. Environment Verification
1. Open `ml/notebooks/00_environment_check.ipynb` in Colab.
2. Select runtime: **Python 3 (CPU or T4 GPU)**.
3. Run all cells to verify Python version (3.10+) and inspect installed packages.

### 2. Exploratory Data Analysis (Optional Verification)
1. Open `ml/notebooks/01_eda_fd001.ipynb`.
2. Mount Google Drive:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```
3. Run the notebook to inspect sensor variance, constant channel identification, and operating envelope distributions.

### 3. Model Training, Calibration, & Bundle Export
1. Open `ml/notebooks/02_train_evaluate_export.ipynb`.
2. Follow the cell progression:
   - **Cell 1**: Mount Google Drive.
   - **Cell 2**: Install `pdm_core` package with pinned `constraints.txt`.
   - **Cell 3**: Load raw C-MAPSS FD001 data and derive run-to-failure RUL.
   - **Cell 4**: Candidate Horizon ($H$) comparison table (evaluating $H \in [20, 25, 30, 35, 40]$).
   - **Cell 5**: Train and calibrate Isolation Forest anomaly detector on early-life healthy windows.
   - **Cell 6**: Train, cross-validate (GroupKFold), calibrate (Platt scaling), and evaluate failure classification models (Logistic Baseline, Random Forest, XGBoost).
   - **Cell 7**: Compute all official evaluation metrics (PR-AUC, ROC-AUC, Brier score, downsampled curves, confusion matrix, and SHAP importances).
   - **Cell 8**: Generate `bundle_v1.0.0.zip` with complete SHA-256 manifest and model cards.
   - **Cell 9**: Download `bundle_v1.0.0.zip` or save to `My Drive/predict-ai/artifacts/`.

### 4. Transferring the Bundle to the Backend
1. Extract or copy the exported `bundle_v1.0.0` folder into the backend model artifacts directory:
   ```bash
   cp -r bundle_v1.0.0/ backend/model_artifacts/bundle_v1.0.0/
   ```
2. Verify that `backend/model_artifacts/bundle_v1.0.0/failure_risk/manifest.json` exists.
3. Register the bundle via CLI:
   ```bash
   python -m app.cli register-model backend/model_artifacts/bundle_v1.0.0
   ```
