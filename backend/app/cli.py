"""
Command-Line Interface (CLI) for Predict-Ai administrative tasks
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Predict-Ai Administrative CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # register-model
    reg_parser = subparsers.add_parser("register-model", help="Register an exported model bundle")
    reg_parser.add_argument("bundle_path", help="Path to exported model bundle directory")

    # activate-model
    act_parser = subparsers.add_parser("activate-model", help="Activate a registered model for serving")
    act_parser.add_argument("model_id", help="Model version identifier to activate")

    # retire-model
    ret_parser = subparsers.add_parser("retire-model", help="Retire an active model")
    ret_parser.add_argument("model_id", help="Model version identifier to retire")

    # seed-demo
    subparsers.add_parser("seed-demo", help="Seed deterministic demo engines and predictions")

    # create-user
    user_parser = subparsers.add_parser("create-user", help="Create a user with role")
    user_parser.add_argument("--email", required=True)
    user_parser.add_argument("--password", required=True)
    user_parser.add_argument("--role", choices=["admin", "engineer"], required=True)
    user_parser.add_argument("--full-name", required=True)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    print(f"Executing CLI command: {args.command}")


if __name__ == "__main__":
    main()
