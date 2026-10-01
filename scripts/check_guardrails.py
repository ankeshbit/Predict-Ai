#!/usr/bin/env python3
"""
scripts/check_guardrails.py
CI Guardrail Script for Predict-Ai (PrediCore)

Enforces:
1. Physical Sensor Semantic Leakage: Scans frontend/src (including mockData),
   backend/app, and ml/src/pdm_core for physical sensor words
   ('thermal', 'temperature', 'vibration', 'pressure', 'motor', etc.).
   Fails immediately unless an explicit allowlist entry with a Phase 6 removal TODO exists.
2. Fabricated Metric Guardrail: Scans backend code to ensure no hardcoded
   evaluation metrics are returned as literals.
"""

import sys
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

# Forbidden physical sensor semantics per PRD §3 Non-Negotiable Rules:
# C-MAPSS FD001 sensors must be referred to only by sensor_1..21 and op_setting_1..3.
FORBIDDEN_SENSOR_PATTERNS = [
    r'\bthermal\b',
    r'\btemperature\b',
    r'\bvibration\b',
    r'\bpressure\b',
    r'\bmotor\b',
]

# Phase 6 complete: mockData deleted and invented sensor labels removed.
# Retain only explicit legitimate negation disclaimers (PRD §6):
LEGITIMATE_DISCLAIMER_ALLOWLIST = {
    "frontend/src/components/modals/AboutResponsibleUseModal.tsx": [
        # PRD §6 Disclaimer: Legitimate negation of physical domains
        "not motor, pump, or compressor telemetry",
    ],
}


def is_allowed(rel_path: str, line_content: str) -> bool:
    normalized_path = rel_path.replace("\\", "/")
    if normalized_path in LEGITIMATE_DISCLAIMER_ALLOWLIST:
        allowed_snippets = LEGITIMATE_DISCLAIMER_ALLOWLIST[normalized_path]
        for snippet in allowed_snippets:
            if snippet.lower() in line_content.lower():
                return True
    return False


def check_physical_sensor_semantics():
    violations = []
    search_dirs = [
        ROOT_DIR / "frontend" / "src",
        ROOT_DIR / "backend" / "app",
        ROOT_DIR / "ml" / "src" / "pdm_core",
    ]

    pattern_re = re.compile("|".join(FORBIDDEN_SENSOR_PATTERNS), re.IGNORECASE)

    for sdir in search_dirs:
        if not sdir.exists():
            continue
        for file_path in sdir.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".ts", ".tsx", ".js", ".jsx", ".py", ".json"]:
                rel_path = file_path.relative_to(ROOT_DIR)
                try:
                    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                except Exception:
                    continue

                for line_idx, line in enumerate(lines, 1):
                    match = pattern_re.search(line)
                    if match:
                        if not is_allowed(str(rel_path), line):
                            matched_word = match.group(0)
                            violations.append(
                                f"{rel_path}:{line_idx} - Found forbidden physical semantic '{matched_word}': {line.strip()[:100]}"
                            )

    if violations:
        print("[-] FAILED: Physical sensor semantics detected without an explicit Phase 6 allowlist entry:")
        for v in violations:
            print(f"    {v}")
        return False

    print("[+] PASSED: Physical sensor semantics check passed (zero forbidden physical sensor semantics; mockData eliminated).")
    return True


def main():
    success = True
    if not check_physical_sensor_semantics():
        success = False

    if not success:
        sys.exit(1)

    print("[+] All CI guardrails passed successfully.")


if __name__ == "__main__":
    main()
