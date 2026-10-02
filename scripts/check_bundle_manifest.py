"""Guardrail script to verify the cryptographic SHA-256 manifest hashes of model artifacts.

Ensures that no files in registered model bundles have been altered, formatted, or corrupted.
Run in CI and pre-commit checks.
"""
import sys
from pathlib import Path

# Add backend to path to import verify_artifacts
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.ml.verify_artifacts import ArtifactVerificationError, verify_manifest  # noqa: E402

ARTIFACTS_DIR = BACKEND_DIR / "model_artifacts"


def main() -> None:
    if not ARTIFACTS_DIR.exists():
        print(f"[!] Artifacts directory {ARTIFACTS_DIR} not found.")
        sys.exit(1)

    bundle_dirs = [d for d in ARTIFACTS_DIR.iterdir() if d.is_dir() and (d / "metadata" / "artifact_manifest.json").exists()]
    if not bundle_dirs:
        print(f"[!] No valid model bundles found in {ARTIFACTS_DIR}.")
        sys.exit(1)

    print(f"[*] Found {len(bundle_dirs)} model bundle(s) to verify...")
    errors = []
    for b_dir in bundle_dirs:
        try:
            verify_manifest(b_dir)
            print(f"[+] Bundle manifest verified successfully: {b_dir.name}")
        except ArtifactVerificationError as exc:
            errors.append(f"Bundle {b_dir.name}: {exc}")

    if errors:
        print("\n[!] MANIFEST VERIFICATION FAILED:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    print("[+] All model bundle manifests passed cryptographic verification.")
    sys.exit(0)


if __name__ == "__main__":
    main()
