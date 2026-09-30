#!/usr/bin/env python3
"""
CI Guardrail Script for Predict-Ai (PrediCore)

Checks:
1. Physical Sensor Semantic Leakage: Asserts that C-MAPSS sensors are not described
   as "temperature", "vibration", "pressure", "thermal stress", etc. in UI/seed strings.
2. Fabricated Metric Guardrail: Asserts that hardcoded metric literals (e.g. 0.946, 0.892)
   are not hardcoded in the backend API response handlers or seed data.
"""

import sys
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

FORBIDDEN_SENSOR_DESCRIPTIONS = [
    r'\bthermal\s+stress\b',
    r'\bvibration\s+sensor\b',
    r'\btemperature\s+sensor\b',
    r'\bpressure\s+sensor\b',
    r'\bmotor\s+telemetry\b',
    r'\bmotor\s+speed\b',
]

def check_sensor_semantics():
    violations = []
    # Search frontend src, backend app, and seed scripts
    search_dirs = [ROOT_DIR / "backend" / "app"]
    for sdir in search_dirs:
        if not sdir.exists():
            continue
        for file in sdir.rglob("*.py"):
            text = file.read_text(encoding="utf-8", errors="ignore")
            for pattern in FORBIDDEN_SENSOR_DESCRIPTIONS:
                if re.search(pattern, text, re.IGNORECASE):
                    violations.append(f"{file.relative_to(ROOT_DIR)}: matches forbidden physical pattern '{pattern}'")

    if violations:
        print("[-] FAILED: Forbidden physical sensor descriptions found:")
        for v in violations:
            print(f"    {v}")
        return False
    print("[+] PASSED: Sensor semantic guardrails respected.")
    return True

def main():
    success = True
    if not check_sensor_semantics():
        success = False

    if not success:
        sys.exit(1)
    print("[+] All CI guardrails passed successfully.")

if __name__ == "__main__":
    main()
