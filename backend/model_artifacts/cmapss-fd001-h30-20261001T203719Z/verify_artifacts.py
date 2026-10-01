"""Standalone, stdlib-only artifact verifier. VENDOR this file into the backend (do not import it from the artifact folder).

Run verify_all(artifact_dir) BEFORE adding artifact_dir/code to sys.path or unpickling anything.
"""
import hashlib
import json
import platform
from importlib import metadata as importlib_metadata
from pathlib import Path


class ArtifactVerificationError(RuntimeError):
    pass


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest(artifact_dir, allow_unlisted=False):
    root = Path(artifact_dir)
    mpath = root / "metadata" / "artifact_manifest.json"
    if not mpath.is_file():
        raise ArtifactVerificationError("artifact_manifest.json not found")
    files = json.loads(mpath.read_text())["files"]
    problems = []
    for rel, info in files.items():
        p = root / rel
        if not p.is_file():
            problems.append(f"missing: {rel}")
        elif p.stat().st_size != info["bytes"] or _sha256(p) != info["sha256"]:
            problems.append(f"hash mismatch: {rel}")
    if not allow_unlisted:
        for p in root.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                rel = p.relative_to(root).as_posix()
                if rel not in files and rel != "metadata/artifact_manifest.json":
                    problems.append(f"unlisted file: {rel}")
    if problems:
        raise ArtifactVerificationError("; ".join(problems[:10]))
    return True


def check_library_versions(metadata, strict=True):
    """Compare installed versions with metadata['library_versions'] (python: major.minor only)."""
    problems = []
    for name, want in metadata.get("library_versions", {}).items():
        if want is None or name == "shap":      # shap is training/explanation-plot only
            continue
        if name == "python":
            have, want = ".".join(platform.python_version().split(".")[:2]), ".".join(want.split(".")[:2])
        else:
            try:
                have = importlib_metadata.version(name)
            except importlib_metadata.PackageNotFoundError:
                problems.append(f"{name}: required {want}, not installed")
                continue
        if have != want:
            problems.append(f"{name}: artifacts built with {want}, installed {have}")
    if problems and strict:
        raise ArtifactVerificationError("library version mismatch: " + "; ".join(problems))
    return problems


def verify_all(artifact_dir, strict_versions=True):
    verify_manifest(artifact_dir)
    metadata = json.loads((Path(artifact_dir) / "metadata" / "model_metadata.json").read_text())
    check_library_versions(metadata, strict=strict_versions)
    return metadata
