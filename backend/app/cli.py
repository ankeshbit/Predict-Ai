"""
Command-Line Interface (CLI) for Predict-Ai Backend Administration
Commands:
  python -m app.cli create-user --email <email> --password <pwd> --role <admin|engineer>
  python -m app.cli migrate-check
  python -m app.cli seed-defaults
"""

import argparse
import sys

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.core.db import engine
from app.core.security import get_password_hash
from app.models.entities import HealthIndicatorConfig, User


def create_user(email: str, password: str, role: str):
    """Creates a new user account with Argon2id hashed password."""
    if role not in ["admin", "engineer"]:
        print(f"[-] Invalid role: '{role}'. Must be 'admin' or 'engineer'.")
        sys.exit(1)

    with Session(engine) as db:
        existing = db.scalar(select(User).where(User.email == email.lower()))
        if existing:
            print(f"[-] User with email '{email}' already exists.")
            sys.exit(1)

        user = User(
            email=email.lower(),
            password_hash=get_password_hash(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"[+] User created successfully: {user.email} (Role: {user.role}, ID: {user.id})")


def migrate_check():
    """Validates database connection and checks table schemas."""
    print("[*] Connecting to database...")
    try:
        with Session(engine) as db:
            db.execute(text("SELECT 1"))
        print("[+] Database connection successful.")
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        sys.exit(1)

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"[*] Found {len(tables)} tables in database:")
    for t in sorted(tables):
        print(f"    - {t}")

    expected = [
        "users", "datasets", "dataset_compatibility_checks", "machines",
        "sensor_readings", "model_versions", "model_evaluations",
        "health_indicator_configs", "predictions", "anomalies", "alerts",
        "maintenance_records", "alert_rules", "settings", "jobs", "audit_log",
    ]
    missing = [t for t in expected if t not in tables]
    if missing:
        print(f"[!] Warning: Missing expected tables: {missing}")
    else:
        print("[+] All 16 PRD core tables are present.")


def seed_defaults():
    """Seeds default health indicator config and test admin/engineer accounts."""
    with Session(engine) as db:
        cfg = db.scalar(select(HealthIndicatorConfig).where(HealthIndicatorConfig.is_active.is_(True)))
        if not cfg:
            cfg = HealthIndicatorConfig(
                version="v1.0",
                weight_risk=50.0,
                weight_anomaly=30.0,
                weight_trend=20.0,
                trend_window=20,
                is_active=True,
            )
            db.add(cfg)
            print("[+] Seeded HealthIndicatorConfig v1.0")

        # Check default admin
        admin = db.scalar(select(User).where(User.email == "admin@predicore.internal"))
        if not admin:
            admin = User(
                email="admin@predicore.internal",
                password_hash=get_password_hash("AdminSecurePass123!"),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            print("[+] Seeded default admin: admin@predicore.internal")

        # Check default engineer
        eng = db.scalar(select(User).where(User.email == "engineer@predicore.internal"))
        if not eng:
            eng = User(
                email="engineer@predicore.internal",
                password_hash=get_password_hash("EngineerSecurePass123!"),
                role="engineer",
                is_active=True,
            )
            db.add(eng)
            print("[+] Seeded default engineer: engineer@predicore.internal")

        db.commit()
    print("[+] Default seed completed.")


def main():
    parser = argparse.ArgumentParser(description="Predict-Ai Administrative CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create-user
    create_parser = subparsers.add_parser("create-user", help="Create a user account")
    create_parser.add_argument("--email", required=True, help="User email address")
    create_parser.add_argument("--password", required=True, help="User password")
    create_parser.add_argument("--role", default="engineer", choices=["admin", "engineer"], help="User role")

    # migrate-check
    subparsers.add_parser("migrate-check", help="Check database connectivity and tables")

    # seed-defaults
    subparsers.add_parser("seed-defaults", help="Seed default health config and test accounts")

    args = parser.parse_args()

    if args.command == "create-user":
        create_user(args.email, args.password, args.role)
    elif args.command == "migrate-check":
        migrate_check()
    elif args.command == "seed-defaults":
        seed_defaults()


if __name__ == "__main__":
    main()
