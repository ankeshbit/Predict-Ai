#!/usr/bin/env python3
"""
CI Guardrail: Verify that backend/app/ml/*.py files are byte-identical to the
registered model bundle's code/*.py (and verify_artifacts.py).

Prevents training/serving skew and enforces that code executed in backend
matches the exact code exported by the training pipeline.
"""

import filecmp
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    app_ml = repo_root / "backend" / "app" / "ml"
    artifacts_dir = repo_root / "backend" / "model_artifacts"

    if not artifacts_dir.is_dir():
        print("No backend/model_artifacts/ directory found; skipping check.")
        return 0

    bundle_dirs = [
        d for d in artifacts_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".") and (d / "code").is_dir()
    ]

    if not bundle_dirs:
        print("No registered bundle with code/ directory found; skipping check.")
        return 0

    mismatches = []
    for bundle_dir in bundle_dirs:
        bundle_code = bundle_dir / "code"
        for bf in bundle_code.glob("*.py"):
            af = app_ml / bf.name
            if not af.is_file():
                mismatches.append(f"Missing file in backend/app/ml/: {bf.name}")
            elif not filecmp.cmp(bf, af, shallow=False):
                mismatches.append(f"File {bf.name} in backend/app/ml/ is not byte-identical to bundle {bundle_dir.name}/code/{bf.name}")

        bundle_verify = bundle_dir / "verify_artifacts.py"
        if bundle_verify.is_file():
            app_verify = app_ml / "verify_artifacts.py"
            if not app_verify.is_file() or not filecmp.cmp(bundle_verify, app_verify, shallow=False):
                mismatches.append("backend/app/ml/verify_artifacts.py is not byte-identical to bundle's verify_artifacts.py")

    if mismatches:
        print("=" * 72, file=sys.stderr)
        print("ERROR: backend/app/ml code is not byte-identical to the registered bundle!", file=sys.stderr)
        print("=" * 72, file=sys.stderr)
        for m in mismatches:
            print(f"  - {m}", file=sys.stderr)
        return 1

    print("[+] SUCCESS: backend/app/ml code is byte-identical to registered bundle code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
