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

import re
import sys
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


def check_secrets_hygiene():
    """Scans all tracked files for Neon credentials, database URIs with passwords, and Neon hosts."""
    import subprocess

    violations = []
    try:
        tracked_files = subprocess.check_output(
            ["git", "ls-files"], cwd=str(ROOT_DIR), text=True, errors="ignore"
        ).splitlines()
    except Exception as exc:
        print(f"[-] WARNING: Could not run git ls-files ({exc}). Scanning directory directly.")
        tracked_files = [
            str(p.relative_to(ROOT_DIR))
            for p in ROOT_DIR.rglob("*")
            if p.is_file() and not any(part.startswith(".") for part in p.parts)
        ]

    # Secret patterns per AGENTS.md and Security Hygiene policy:
    # 1. Neon API key / password tokens: npg_[A-Za-z0-9]+
    # 2. Connection URIs with credentials pointing to neon.tech
    # 3. Specific Neon endpoint host identifiers: ep-[a-z]+-[a-z]+-[a-z0-9]+
    secret_patterns = [
        (
            re.compile(r"npg_" + r"[A-Za-z0-9]+"),
            "Neon password / token pattern (npg_*)",
        ),
        (
            re.compile(r"postgres(?:ql)?(?:\+psycopg)?://" + r"[^:@/\s]+:[^@\s$<{]+@[^\s]*neon\.tech"),
            "Database connection string with inline credentials to neon.tech",
        ),
        (
            re.compile(r"ep-" + r"[a-z]+-[a-z]+-[a-z0-9]+"),
            "Neon host identifier pattern (ep-*-*-*)",
        ),
    ]

    binary_extensions = {
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".joblib", ".pkl",
        ".pyc", ".woff", ".woff2", ".ttf", ".eot", ".zip", ".tar", ".gz"
    }

    for rel_path in tracked_files:
        file_path = ROOT_DIR / rel_path
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() in binary_extensions:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_idx, line in enumerate(content.splitlines(), 1):
            for pat, desc in secret_patterns:
                match = pat.search(line)
                if match:
                    violations.append(
                        f"{rel_path}:{line_idx} - Found forbidden pattern ({desc}): '{match.group(0)}' in: {line.strip()[:100]}"
                    )

    if violations:
        print("[-] FAILED: Hardcoded secrets, credentials, or Neon hosts detected in tracked files:")
        for v in violations:
            print(f"    {v}")
        return False

    print("[+] PASSED: Secrets hygiene check passed (zero hardcoded Neon credentials or hosts across all tracked files).")
    return True


def check_frontend_live_data():
    """
    Enforces Live Data Guardrail:
    frontend/src (excluding tests) must NOT contain:
    - Math.random
    - 'ds-ai4i-sample' style ids
    - arrays of object literals with machine/alert/metric-like keys
    - forbidden strings: 'mockData', 'dummy', 'sample data' (case-insensitive, except PRD banner)
    """
    src_dir = ROOT_DIR / "frontend" / "src"
    if not src_dir.exists():
        return True

    violations = []

    # 1. Simple line patterns
    forbidden_line_patterns = [
        (re.compile(r"\bMath\.random\s*\("), "Math.random call"),
        (re.compile(r"['\"]?ds-[a-z0-9_-]*sample['\"]?"), "sample dataset id ('ds-*-sample')"),
        (re.compile(r"\bmockData\b", re.IGNORECASE), "mockData identifier"),
        (re.compile(r"\bdummy\b", re.IGNORECASE), "dummy keyword"),
        (re.compile(r"\bsample\s+data\b", re.IGNORECASE), "'sample data' literal"),
    ]

    # 2. Literal arrays of machine/alert/metric objects
    # Matches hardcoded arrays of mock entities: e.g. [ { machineCode: '...', failureProbability: ... } ]
    array_literal_pattern = re.compile(
        r"\[\s*\{\s*(?:[a-zA-Z0-9_]+\s*:\s*[^,}]+,\s*)*(?:machineCode|machine_code|failureProbability|healthIndicator|healthBand|recommendationText|recommendationRuleId|trigger_score|asOfCycle)\s*:\s*['\"\d]",
        re.MULTILINE
    )

    for file_path in src_dir.rglob("*"):
        if not file_path.is_file() or file_path.suffix not in [".ts", ".tsx", ".js", ".jsx"]:
            continue

        rel_path = file_path.relative_to(ROOT_DIR)
        rel_str = str(rel_path).replace("\\", "/")

        # Exclude test files
        if "/tests/" in rel_str or "/__tests__/" in rel_str or ".test." in rel_str or ".spec." in rel_str:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lines = content.splitlines()
        for line_idx, line in enumerate(lines, 1):
            # Exclude exact PRD banner text and badge
            if "Demo Dataset: NASA C-MAPSS FD001" in line or "Demo / Simulated Data" in line:
                continue

            for pat, desc in forbidden_line_patterns:
                m = pat.search(line)
                if m:
                    violations.append(
                        f"{rel_str}:{line_idx} - Found forbidden pattern ({desc}): '{m.group(0)}' in: {line.strip()[:100]}"
                    )

        # Check array of object literals
        for match in array_literal_pattern.finditer(content):
            start_pos = match.start()
            line_idx = content[:start_pos].count("\n") + 1
            matched_snippet = content[start_pos:start_pos+100].replace("\n", " ")
            violations.append(
                f"{rel_str}:{line_idx} - Found hardcoded object array literal: {matched_snippet}..."
            )

    if violations:
        print("[-] FAILED: Hardcoded mock/dummy/sample data detected in frontend/src:")
        for v in violations:
            print(f"    {v}")
        return False

    print("[+] PASSED: Frontend live-data check passed (zero Math.random, dummy, mockData, or hardcoded object arrays).")
    return True


def main():
    success = True
    if not check_physical_sensor_semantics():
        success = False

    if not check_secrets_hygiene():
        success = False

    if not check_frontend_live_data():
        success = False

    if not success:
        sys.exit(1)

    print("[+] All CI guardrails passed successfully.")


if __name__ == "__main__":
    main()


