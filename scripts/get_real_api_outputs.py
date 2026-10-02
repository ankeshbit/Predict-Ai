import json

from app.core.auth import create_access_token
from app.core.db import SessionLocal
from app.main import app
from app.models.entities import User
from fastapi.testclient import TestClient

client = TestClient(app)

# Ensure engineer user exists for auth
with SessionLocal() as db:
    user = db.query(User).filter(User.role == "engineer").first()
    if not user:
        user = db.query(User).first()
    token = create_access_token({"sub": str(user.id), "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

print("=== 1. GET /api/v1/models/active ===")
res_models = client.get("/api/v1/models/active", headers=headers)
print(f"Status: {res_models.status_code}")
print(json.dumps(res_models.json(), indent=2))

print("\n=== 2. GET /api/v1/models/active/evaluation ===")
res_eval = client.get("/api/v1/models/active/evaluation", headers=headers)
print(f"Status: {res_eval.status_code}")
eval_json = res_eval.json()
# Truncate curves for clean display
if "curves" in eval_json:
    for k in list(eval_json["curves"].keys()):
        eval_json["curves"][k] = f"<{len(eval_json['curves'][k])} points>"
print(json.dumps(eval_json, indent=2))

print("\n=== 3. GET /api/v1/predictions?limit=2 ===")
res_preds = client.get("/api/v1/predictions?limit=2", headers=headers)
print(f"Status: {res_preds.status_code}")
print(json.dumps(res_preds.json(), indent=2))

print("\n=== 4. GET /api/v1/alerts ===")
res_alerts = client.get("/api/v1/alerts", headers=headers)
print(f"Status: {res_alerts.status_code}")
print(json.dumps(res_alerts.json(), indent=2))
