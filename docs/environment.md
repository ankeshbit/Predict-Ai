# Environment Matrix & Compatibility Specification

## 1. Runtime Versions

| Component | Target Version | Supported Range | Current Host / Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | Match bundle runtime | `3.10` – `3.12` | **Python 3.10.0 (Host)** | Container and CI match the bundle runtime. The model was trained on Kaggle, not Colab. The bundle metadata (`library_versions`, `python_version`) is authoritative for the runtime. If the bundle's Python version is not 3.10, change the Dockerfile and CI to match it rather than downgrading the bundle. |
| **Node.js** | `20.x` | `18.x` – `22.x` | `20.x` (Local) | Frontend build & test environment |
| **PostgreSQL** | `16.x` | `15.x` – `16.x` | Neon Serverless | Port 6543 pooled (runtime), 5432 direct (migrations) |

> **AUTHORITATIVE RUNTIME RULE**: The model was trained on Kaggle, not Colab. The bundle metadata (`library_versions`, `python_version`) is authoritative for the runtime. Do not assume Colab versions anywhere. If the bundle's Python version is not 3.10, change the Dockerfile and CI to match it rather than downgrading the bundle.

---

## 2. ML Constraints (`ml/constraints.txt`) & NumPy Compatibility Check

> **CRITICAL COMPATIBILITY NOTE: NumPy 2.x vs scikit-learn 1.4.2**
> NumPy 2.0+ introduces breaking C-API changes. Models trained with scikit-learn 1.4.2, XGBoost 2.0.3, and SHAP 0.45.0 **must not** use NumPy 2.x at training or inference time, as deserializing joblib/pickle estimators across NumPy 1.x and 2.x produces `ValueError: numpy.dtype size changed, may indicate binary incompatibility`.
> Therefore, `numpy==1.26.4` is explicitly pinned in `ml/constraints.txt`.

```
numpy==1.26.4
pandas==2.2.2
scipy==1.13.0
scikit-learn==1.4.2
xgboost==2.0.3
shap==0.45.0
joblib==1.4.0
pyyaml==6.0.1
pydantic==2.7.1
```

---

## 3. Human Kaggle (or Colab) Environment Log

*Run `ml/notebooks/00_environment_check.ipynb` in Kaggle (or Colab) and record the output below:*

```text
======================= [PASTE KAGGLE (OR COLAB) 00_ENV OUTPUT HERE] =======================
Python version:
Platform:
Packages:
  numpy:
  pandas:
  scipy:
  scikit-learn:
  xgboost:
  shap:
  joblib:
  pyyaml:
  pydantic:
=============================================================================================
```
