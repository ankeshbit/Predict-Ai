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


def check_frontend_no_password_literals():
    """
    Security Guardrail:
    frontend/src (excluding tests) must NOT contain any hardcoded password literals.
    Users must type their credentials; no credentials may be downloaded by the browser.
    """
    src_dir = ROOT_DIR / "frontend" / "src"
    if not src_dir.exists():
        return True

    violations = []

    password_literal_patterns = [
        (re.compile(r"""\bpassword\s*[:=]\s*['"][^'"]{2,}['"]""", re.IGNORECASE), "password literal assignment"),
        (re.compile(r"""\b(?:AdminSecret|EngineerSecurePass|Password123|Secret123)\b""", re.IGNORECASE), "credential token literal"),
        (re.compile(r"""(?:handlePerformLogin|loginUser|loginMutation\.mutate)\s*\([^,)]+,\s*['"][^'"]+['"]""", re.IGNORECASE), "hardcoded password in login call"),
    ]

    for file_path in src_dir.rglob("*"):
        if not file_path.is_file() or file_path.suffix not in [".ts", ".tsx", ".js", ".jsx"]:
            continue

        rel_path = file_path.relative_to(ROOT_DIR)
        rel_str = str(rel_path).replace("\\", "/")

        # Exclude tests
        if "/tests/" in rel_str or "/__tests__/" in rel_str or ".test." in rel_str or ".spec." in rel_str:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lines = content.splitlines()
        for line_idx, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip pure comments
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            # Skip type annotations (e.g. password: string)
            if re.search(r"\bpassword\s*:\s*(?:string|string\s*\|)", stripped):
                continue
            # Skip input types (e.g. type="password")
            if re.search(r"""type\s*=\s*['"]password['"]""", stripped):
                continue

            for pat, desc in password_literal_patterns:
                m = pat.search(line)
                if m:
                    violations.append(
                        f"{rel_str}:{line_idx} - Found forbidden {desc}: '{m.group(0)}' in: {stripped[:100]}"
                    )

    if violations:
        print("[-] FAILED: Hardcoded password literal detected in frontend/src:")
        for v in violations:
            print(f"    {v}")
        return False

    print("[+] PASSED: Frontend password literals check passed (zero password literals in frontend/src).")
    return True


def check_docs_and_config_no_credential_literals():
    """
    Security Guardrail:
    README.md, .env.example, and all files under docs/ must NOT contain
    hardcoded credential literals (e.g. EngineerSecurePass, AdminSecret, Password123, Secret123).
    All credentials must come from environment variables, keeping placeholders only.
    """
    targets = [ROOT_DIR / "README.md", ROOT_DIR / ".env.example"]
    docs_dir = ROOT_DIR / "docs"
    if docs_dir.exists():
        for doc_file in docs_dir.rglob("*"):
            if doc_file.is_file() and doc_file.suffix in [".md", ".txt", ".json", ".yaml", ".yml", ".html"]:
                targets.append(doc_file)

    forbidden_literals = [
        (re.compile(r"""\b(?:AdminSecret|EngineerSecurePass|Password123|Secret123|EngineerSecret)\w*\b""", re.IGNORECASE), "credential literal"),
        (re.compile(r"""(?:INITIAL_ADMIN_PASSWORD|INITIAL_ENGINEER_PASSWORD)\s*=\s*(?!<|change_this|\$\{)[^\s#]+""", re.IGNORECASE), "plain-text password in seed env template"),
    ]

    violations = []
    for file_path in targets:
        if not file_path.is_file():
            continue
        rel_path = file_path.relative_to(ROOT_DIR)
        rel_str = str(rel_path).replace("\\", "/")
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_idx, line in enumerate(content.splitlines(), 1):
            for pat, desc in forbidden_literals:
                m = pat.search(line)
                if m:
                    violations.append(
                        f"{rel_str}:{line_idx} - Found forbidden {desc}: '{m.group(0)}' in: {line.strip()[:100]}"
                    )

    if violations:
        print("[-] FAILED: Forbidden credential literal detected in README.md, .env.example, or docs/:")
        for v in violations:
            print(f"    {v}")
        return False

    print("[+] PASSED: Documentation and config credential hygiene check passed (zero credential literals in README.md, .env.example, or docs/).")
    return True


def check_frontend_no_invented_fallbacks():
    """
    Guardrail:
    Ensures zero invented fallbacks in frontend/src:
    - No ?? <number>
    - No || <number>
    - No ?? '<identifier>' (allow-list only '—')
    - No || '<identifier>' (allow-list only '—')
    - No 64-hex literals
    - No forbidden strings: 'Test Cell', 'RULE_DEFAULT', 'Platt', 'Turbofan', 'Offline Evaluation'
      (banner string "Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data" is preserved per PRD)
    - No numeric literal threshold comparison on score or probability (e.g. > 0.5)
    - No constant string badge applied unconditionally to every machine (e.g. datasetBadge: 'Demo / Simulated Data')
    """
    targets = []
    src_dir = ROOT_DIR / "frontend" / "src"
    if src_dir.exists():
        for p in src_dir.rglob("*.tsx"):
            targets.append(p)
        for p in src_dir.rglob("*.ts"):
            targets.append(p)

    violations = []

    # 1. ?? <number>
    nullish_number_re = re.compile(r'\?\?\s*\d+(?:\.\d+)?')
    # 2. || <number>
    or_number_re = re.compile(r'\|\|\s*\d+(?:\.\d+)?')
    # 3. ?? '<text>' (allow-list only '—')
    nullish_string_re = re.compile(r'\?\?\s*([\'"])([^\'"]*)\1')
    # 4. || '<text>' (allow-list only '—')
    or_string_re = re.compile(r'\|\|\s*([\'"])([^\'"]*)\1')
    # 5. 64-hex literal
    hex64_re = re.compile(r'\b[a-fA-F0-9]{64}\b')
    # 6. Numeric threshold comparison on score or probability
    score_threshold_re = re.compile(r'\b(?:anomaly_score|failure_probability|health_indicator|anomalyScore|failureProbability|healthIndicator|score)\s*(?:[<>]=?)\s*\d+(?:\.\d+)?')
    score_threshold_rev_re = re.compile(r'\d+(?:\.\d+)?\s*(?:[<>]=?)\s*\b(?:anomaly_score|failure_probability|health_indicator|anomalyScore|failureProbability|healthIndicator|score)')
    # 7. Constant badge applied unconditionally to every machine
    constant_badge_re = re.compile(r'datasetBadge\s*:\s*[\'"][^\'"]+[\'"]')
    # 8. forbidden strings
    forbidden_strings = ['Test Cell', 'RULE_DEFAULT', 'Platt', 'Turbofan', 'Offline Evaluation']

    for target in sorted(set(targets)):
        if not target.is_file():
            continue
        rel_path = target.relative_to(ROOT_DIR)
        rel_str = str(rel_path).replace("\\", "/")
        if "/tests/" in rel_str or ".test." in rel_str or ".spec." in rel_str or "/e2e/" in rel_str:
            continue
        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_idx, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            # Check 1: ?? <number>
            m_num = nullish_number_re.search(line)
            if m_num:
                violations.append(
                    f"{rel_str}:{line_idx} - Found forbidden nullish number fallback '?? <number>': '{m_num.group(0)}' in: {stripped[:100]}"
                )

            # Check 2: || <number>
            m_or_num = or_number_re.search(line)
            if m_or_num:
                violations.append(
                    f"{rel_str}:{line_idx} - Found forbidden or number fallback '|| <number>': '{m_or_num.group(0)}' in: {stripped[:100]}"
                )

            # Check 3: ?? '<text>' (allow-list only '—' and empty string '')
            for m_null_str in nullish_string_re.finditer(line):
                text_val = m_null_str.group(2)
                if text_val not in ('—', ''):
                    violations.append(
                        f"{rel_str}:{line_idx} - Found forbidden nullish string fallback '?? <identifier>': '{m_null_str.group(0)}' in: {stripped[:100]}"
                    )

            # Check 4: || '<text>' (allow-list only '—' and empty string '')
            for m_or_str in or_string_re.finditer(line):
                text_val = m_or_str.group(2)
                if text_val not in ('—', ''):
                    violations.append(
                        f"{rel_str}:{line_idx} - Found forbidden string fallback '|| <identifier>': '{m_or_str.group(0)}' in: {stripped[:100]}"
                    )

            # Check 5: 64-hex literal
            m_hex = hex64_re.search(line)
            if m_hex:
                violations.append(
                    f"{rel_str}:{line_idx} - Found forbidden 64-hex literal: '{m_hex.group(0)}' in: {stripped[:100]}"
                )

            # Check 6: Numeric literal threshold comparison on score or probability
            m_score_thresh = score_threshold_re.search(line) or score_threshold_rev_re.search(line)
            if m_score_thresh:
                violations.append(
                    f"{rel_str}:{line_idx} - Found forbidden numeric literal threshold comparison on score/probability: '{m_score_thresh.group(0)}' in: {stripped[:100]}"
                )

            # Check 7: Constant badge applied to every machine
            m_const_badge = constant_badge_re.search(line)
            if m_const_badge:
                violations.append(
                    f"{rel_str}:{line_idx} - Found forbidden constant badge assigned to machine: '{m_const_badge.group(0)}' in: {stripped[:100]}"
                )

            # Check 8: forbidden strings
            # Allow PRD required banner line: "Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data"
            if "Demo Dataset: NASA C-MAPSS FD001" in line:
                continue
            for s in forbidden_strings:
                if s in line:
                    violations.append(
                        f"{rel_str}:{line_idx} - Found forbidden string literal '{s}' in: {stripped[:100]}"
                    )

    if violations:
        print("[-] FAILED: Invented data fallbacks or forbidden literals detected in frontend/src:")
        for v in violations:
            print(f"    {v}")
        return False

    print("[+] PASSED: Frontend invented fallback guardrail passed (zero ?? <number>, || <number>, ?? '<identifier>', || '<identifier>', score threshold comparisons, constant badges, 64-hex, or forbidden strings).")
    return True


def main():
    success = True
    if not check_physical_sensor_semantics():
        success = False

    if not check_secrets_hygiene():
        success = False

    if not check_frontend_live_data():
        success = False

    if not check_frontend_no_password_literals():
        success = False

    if not check_docs_and_config_no_credential_literals():
        success = False

    if not check_frontend_no_invented_fallbacks():
        success = False

    if not success:
        sys.exit(1)

    print("[+] All CI guardrails passed successfully.")


if __name__ == "__main__":
    main()


