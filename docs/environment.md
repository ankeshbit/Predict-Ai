# Environment & Dependency Compatibility Specifications

## 1. Runtime Versions

| Component | Target Version | Supported Range | Notes |
| :--- | :--- | :--- | :--- |
| **Python** | `3.10.x` | `3.10` – `3.11` | Matches Google Colab standard runtime and Render/Railway base |
| **Node.js** | `20.x` | `18.x` – `22.x` | Used for frontend build and Vite server |
| **PostgreSQL** | `16.x` | `15.x` – `16.x` | Neon Serverless PostgreSQL |

---

## 2. ML Constraints (`ml/constraints.txt`)

To prevent pickle deserialization errors across Colab and the backend, the following exact package versions are enforced:

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

## 3. Human Colab Environment Log

*When executing `00_environment_check.ipynb` in Colab, paste the printed runtime details below:*

```
[PASTE COLAB ENVIRONMENT CHECK OUTPUT HERE]
Python Version: 
scikit-learn Version: 
xgboost Version: 
```
