"""
Command-Line Interface (CLI) for Predict-Ai Backend Administration
Commands:
  python -m app.cli create-user --email <email> --password <pwd> --role <admin|engineer>
  python -m app.cli migrate-check
  python -m app.cli seed-defaults
"""

import argparse
import os
import sys

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import engine
from app.core.security import get_password_hash
from app.models.entities import HealthIndicatorConfig, Setting, User


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
    """Seeds default health indicator config and admin/engineer accounts.
    Admin and engineer passwords MUST come from INITIAL_ADMIN_PASSWORD and INITIAL_ENGINEER_PASSWORD
    environment variables. Fails immediately if either is missing.
    """
    with Session(engine) as db:
        cfg = db.scalar(select(HealthIndicatorConfig).where(HealthIndicatorConfig.is_active.is_(True)))
        if not cfg:
            cfg = HealthIndicatorConfig(
                version="v1.0",
                anomaly_weight=0.30,
                data_quality_penalty={"DATA_OK": 0.0, "DATA_WARNING": 10.0},
                trend_enabled=False,
                is_active=True,
            )
            db.add(cfg)
            print("[+] Seeded HealthIndicatorConfig v1.0")

        # Seed health bands in settings table if not present
        bands_setting = db.scalar(select(Setting).where(Setting.key == "health_bands"))
        if not bands_setting:
            bands_setting = Setting(
                key="health_bands",
                value={
                    "bands": [
                        {"key": "Excellent", "label": "Excellent (86–100)", "min_score": 86, "max_score": 100},
                        {"key": "Healthy", "label": "Healthy (71–85)", "min_score": 71, "max_score": 85},
                        {"key": "Warning", "label": "Warning (51–70)", "min_score": 51, "max_score": 70},
                        {"key": "Poor", "label": "Poor (31–50)", "min_score": 31, "max_score": 50},
                        {"key": "Critical", "label": "Critical (0–30)", "min_score": 0, "max_score": 30},
                    ]
                },
                description="Machine Health Indicator bands (PRD §5 / FR-10)",
            )
            db.add(bands_setting)
            print("[+] Seeded Setting: health_bands")

        # Check admin
        admin_email = settings.INITIAL_ADMIN_EMAIL.lower()
        admin = db.scalar(select(User).where(User.email == admin_email))
        if not admin:
            if not settings.INITIAL_ADMIN_PASSWORD:
                print("[-] Fatal error: INITIAL_ADMIN_PASSWORD environment variable is missing.", file=sys.stderr)
                print("[-] Admin account cannot be seeded without an explicit password from the environment.", file=sys.stderr)
                sys.exit(1)
            admin = User(
                email=admin_email,
                password_hash=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            print(f"[+] Seeded admin: {admin_email}")

        # Check engineer
        eng_email = settings.INITIAL_ENGINEER_EMAIL.lower()
        eng = db.scalar(select(User).where(User.email == eng_email))
        if not eng:
            if not settings.INITIAL_ENGINEER_PASSWORD:
                print("[-] Fatal error: INITIAL_ENGINEER_PASSWORD environment variable is missing.", file=sys.stderr)
                print("[-] Engineer account cannot be seeded without an explicit password from the environment.", file=sys.stderr)
                sys.exit(1)
            eng = User(
                email=eng_email,
                password_hash=get_password_hash(settings.INITIAL_ENGINEER_PASSWORD),
                role="engineer",
                is_active=True,
            )
            db.add(eng)
            print(f"[+] Seeded engineer: {eng_email}")

        db.commit()
    print("[+] Default seed completed.")


def reset_admin_password_cmd(password: str | None = None):
    """Resets the admin account password in the database.
    Password is read from ADMIN_NEW_PASSWORD env var or --password argument. Never echoed.
    """
    pwd = password or os.environ.get("ADMIN_NEW_PASSWORD")
    if not pwd:
        print("[-] Fatal error: ADMIN_NEW_PASSWORD environment variable or --password argument required.", file=sys.stderr)
        sys.exit(1)
    if len(pwd) < 12:
        print("[-] Fatal error: Admin password must be at least 12 characters long.", file=sys.stderr)
        sys.exit(1)

    with Session(engine) as db:
        admin = db.scalar(select(User).where(User.role == "admin"))
        if not admin:
            # If no admin exists, create one using INITIAL_ADMIN_EMAIL
            admin = User(
                email=settings.INITIAL_ADMIN_EMAIL.lower(),
                password_hash=get_password_hash(pwd),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"[+] Success: Created admin account {admin.email} with new password.")
            return

        admin.password_hash = get_password_hash(pwd)
        admin.is_active = True
        db.commit()
        print(f"[+] Success: Admin password for {admin.email} has been reset.")


def register_model_cmd(bundle_path: str, activate: bool):
    """Registers a model bundle into model_versions and model_evaluations."""
    from app.services.importer import register_model_bundle
    print(f"[*] Registering model bundle from: {bundle_path}")
    try:
        mv = register_model_bundle(bundle_path, activate=activate)
        print(f"[+] Successfully registered model: {mv.bundle_version} (ID: {mv.id}, Active: {mv.is_active})")
    except Exception as e:
        print(f"[-] Registration failed: {e}")
        sys.exit(1)


def seed_demo_cmd(bundle_path: str):
    """Seeds demo machines (Healthy, Warning, Critical) from demo bundle data."""
    from app.services.importer import seed_demo_engines
    print(f"[*] Seeding demo fleet from: {bundle_path}")
    try:
        res = seed_demo_engines(bundle_path)
        print("[+] Demo fleet seeded successfully:")
        for category, info in res.items():
            print(f"    - {category.upper()}: {info['machine_code']} (Cutoff: {info['cutoff_cycle']}, Readings: {info['readings_count']}, Health: {info['health_indicator']})")
    except Exception as e:
        print(f"[-] Demo seeding failed: {e}")
        sys.exit(1)


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

    # register-model
    reg_parser = subparsers.add_parser("register-model", help="Register a validated model bundle")
    reg_parser.add_argument("--bundle-path", required=True, help="Path to model bundle directory")
    reg_parser.add_argument("--activate", action="store_true", default=True, help="Set model as active")

    # seed-demo
    demo_parser = subparsers.add_parser("seed-demo", help="Seed demo fleet from bundle")
    demo_parser.add_argument("--bundle-path", required=True, help="Path to model bundle directory containing demo/ folder")

    # reset-admin-password
    reset_parser = subparsers.add_parser("reset-admin-password", help="Reset admin account password securely from env var or arg")
    reset_parser.add_argument("--password", required=False, default=None, help="New admin password (optional; otherwise read from ADMIN_NEW_PASSWORD env var)")

    args = parser.parse_args()

    if args.command == "create-user":
        create_user(args.email, args.password, args.role)
    elif args.command == "migrate-check":
        migrate_check()
    elif args.command == "seed-defaults":
        seed_defaults()
    elif args.command == "reset-admin-password":
        reset_admin_password_cmd(args.password)
    elif args.command == "register-model":
        register_model_cmd(args.bundle_path, args.activate)
    elif args.command == "seed-demo":
        seed_demo_cmd(args.bundle_path)


if __name__ == "__main__":
    main()

