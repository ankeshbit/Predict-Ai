#!/usr/bin/env python3
"""
CI / Pre-flight check: Verify that backend/requirements-inference.txt matches
the registered bundle's requirements-inference.txt.

If any model bundle exists in backend/model_artifacts/, this script ensures
there is zero discrepancy between the bundle's inference pins and the backend's
inference requirements.
"""

import sys
from pathlib import Path


def parse_pins(path: Path) -> dict[str, str]:
    """Parses a requirements.txt file into a package -> version mapping."""
    pins = {}
    if not path.is_file():
        return pins
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "==" in line:
            pkg, ver = line.split("==", 1)
            pins[pkg.strip().lower()] = ver.strip()
        else:
            pins[line.strip().lower()] = "*"
    return pins


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    backend_req_path = repo_root / "backend" / "requirements-inference.txt"

    if not backend_req_path.is_file():
        print(f"ERROR: {backend_req_path} not found!", file=sys.stderr)
        return 1

    backend_pins = parse_pins(backend_req_path)
    artifacts_dir = repo_root / "backend" / "model_artifacts"

    if not artifacts_dir.is_dir():
        print("backend/model_artifacts/ directory not found. Skipping bundle pin check.")
        return 0

    bundle_dirs = [
        d for d in artifacts_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]

    if not bundle_dirs:
        print("No registered model bundle found in backend/model_artifacts/; bundle pin check skipped.")
        return 0

    mismatches = []
    for bundle_dir in bundle_dirs:
        # Check root or metadata/ for requirements-inference.txt
        bundle_req = bundle_dir / "requirements-inference.txt"
        if not bundle_req.is_file():
            bundle_req = bundle_dir / "metadata" / "requirements-inference.txt"

        if not bundle_req.is_file():
            # If directory has manifest.json or model_card.json but no reqs, report warning
            if (bundle_dir / "manifest.json").is_file():
                mismatches.append(
                    f"Bundle at {bundle_dir} is missing requirements-inference.txt!"
                )
            continue

        bundle_pins = parse_pins(bundle_req)

        # Compare pins
        diffs = []
        all_pkgs = sorted(set(backend_pins.keys()) | set(bundle_pins.keys()))
        for pkg in all_pkgs:
            b_ver = backend_pins.get(pkg)
            bundle_ver = bundle_pins.get(pkg)
            if b_ver != bundle_ver:
                diffs.append(
                    f"  - {pkg}: backend={b_ver or 'MISSING'} vs bundle={bundle_ver or 'MISSING'}"
                )

        if diffs:
            diff_text = "\n".join(diffs)
            mismatches.append(
                f"Bundle: {bundle_dir.name}\n"
                f"Bundle file: {bundle_req}\n"
                f"Discrepancies:\n{diff_text}"
            )

    if mismatches:
        print("=" * 72, file=sys.stderr)
        print("ERROR: backend/requirements-inference.txt does not match the registered bundle!", file=sys.stderr)
        print("=" * 72, file=sys.stderr)
        for m in mismatches:
            print(m, file=sys.stderr)
            print("-" * 72, file=sys.stderr)
        print(
            "\nACTION REQUIRED:\n"
            "Do not hardcode or guess library pins. Copy the exact pins from the\n"
            "registered model bundle's requirements-inference.txt to backend/requirements-inference.txt.\n",
            file=sys.stderr,
        )
        return 1

    print("SUCCESS: backend/requirements-inference.txt matches registered model bundle pins.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
