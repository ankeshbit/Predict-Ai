"""
CLI interface for pdm_core.bundle:
python -m pdm_core.bundle validate <path>
"""

import argparse
import sys
from pathlib import Path

from pdm_core.bundle.validator import validate_model_bundle


def main():
    parser = argparse.ArgumentParser(
        description="pdm_core model bundle verification CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate bundle integrity and contract")
    validate_parser.add_argument("path", help="Path to bundle directory or task sub-bundle")

    args = parser.parse_args()

    if args.command == "validate":
        target = Path(args.path)
        print(f"[*] Validating model bundle at: {target.resolve()}")
        result = validate_model_bundle(target)

        if result.warnings:
            for w in result.warnings:
                print(f"[!] Warning: {w}")

        if not result.valid:
            print("[-] VALIDATION FAILED with errors:")
            for err in result.errors:
                print(f"    - {err}")
            sys.exit(1)
        else:
            print("[+] BUNDLE VALIDATION PASSED:")
            if result.manifest:
                print(f"    - Task: {result.manifest.task}")
                print(f"    - Bundle Version: {result.manifest.bundle_version}")
                print(f"    - Model Type: {result.manifest.model_type}")
                print(f"    - SHA-256 Verified Files: {len(result.manifest.file_sha256)}")
            if result.evaluation:
                print(f"    - PR-AUC: {result.evaluation.metrics.pr_auc}")
                print(f"    - ROC-AUC: {result.evaluation.metrics.roc_auc}")
                print(f"    - Brier Score: {result.evaluation.metrics.brier_score}")
            sys.exit(0)


if __name__ == "__main__":
    main()
