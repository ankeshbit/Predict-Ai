"""
Cryptographic hashing utilities for pdm_core model bundles.
"""

import hashlib
from pathlib import Path
from typing import Dict, Union


def compute_file_sha256(filepath: Union[str, Path]) -> str:
    """Computes SHA-256 hexadecimal digest for a given file."""
    p = Path(filepath)
    if not p.is_file():
        raise FileNotFoundError(f"File not found for hash calculation: {p}")

    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_dir_hashes(directory: Union[str, Path], exclude_manifest: bool = True) -> Dict[str, str]:
    """
    Computes SHA-256 hashes for all files in a directory (relative path -> hash).
    Optionally excludes manifest.json so the manifest can store the other file hashes.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Directory not found: {dir_path}")

    hashes = {}
    for p in sorted(dir_path.rglob("*")):
        if p.is_file():
            rel_name = p.relative_to(dir_path).as_posix()
            if exclude_manifest and rel_name == "manifest.json":
                continue
            hashes[rel_name] = compute_file_sha256(p)
    return hashes
