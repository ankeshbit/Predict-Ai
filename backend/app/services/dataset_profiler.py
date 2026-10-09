"""
Dataset Profiler Service
Computes genuine, non-fabricated descriptive statistics and structural metadata
directly from uploaded telemetry files prior to schema mapping or compatibility checks.
"""

import csv
import math
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


def detect_file_delimiter(sample_text: str) -> str:
    """Sniffs delimiter from a sample of text."""
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample_text, delimiters=",\t; ")
        delimiter = dialect.delimiter
        if delimiter == " ":
            return r"\s+"
        return delimiter
    except Exception:
        # Fallback heuristic
        lines = [line.strip() for line in sample_text.splitlines() if line.strip()][:5]
        if not lines:
            return ","
        # Count occurrences in sample lines
        commas = sum(line.count(",") for line in lines)
        tabs = sum(line.count("\t") for line in lines)
        semis = sum(line.count(";") for line in lines)
        if commas > 0 and commas >= tabs and commas >= semis:
            return ","
        if tabs > 0 and tabs >= semis:
            return "\t"
        if semis > 0:
            return ";"
        # If whitespace separated
        words_per_line = [len(line.split()) for line in lines]
        if words_per_line and all(w > 1 for w in words_per_line):
            return r"\s+"
        return ","


def detect_has_header(sample_text: str, delimiter: str) -> bool:
    """Detects if the first line is likely a header row."""
    lines = [line.strip() for line in sample_text.splitlines() if line.strip()][:5]
    if len(lines) < 2:
        return False
    try:
        sniffer = csv.Sniffer()
        return sniffer.has_header(sample_text)
    except Exception:
        pass

    # Heuristic: if first row tokens are mostly non-numeric and second row tokens are mostly numeric
    if delimiter == r"\s+":
        tokens_0 = lines[0].split()
        tokens_1 = lines[1].split()
    else:
        tokens_0 = [t.strip() for t in lines[0].split(delimiter)]
        tokens_1 = [t.strip() for t in lines[1].split(delimiter)]

    def is_num(val: str) -> bool:
        try:
            float(val)
            return True
        except ValueError:
            return False

    nums_0 = sum(1 for t in tokens_0 if is_num(t))
    nums_1 = sum(1 for t in tokens_1 if is_num(t))
    if len(tokens_0) > 0 and len(tokens_1) > 0:
        if (nums_0 / len(tokens_0) < 0.5) and (nums_1 / len(tokens_1) >= 0.5):
            return True
    return False


def profile_dataset_file(file_path: Path, original_filename: str) -> Dict[str, Any]:
    """
    Reads an uploaded file and computes an exhaustive dataset profile:
    - filename, row count, column count
    - detected delimiter and header
    - unit and cycle stats (if detectable)
    - missing value counts per column
    - min, max, mean for numeric columns
    - duplicate row count
    All values are computed directly from the file content without hardcoding.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Staged file not found: {file_path}")

    # Read up to 64KB for sniffing
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        sample = f.read(64 * 1024)

    delimiter = detect_file_delimiter(sample)
    has_header = detect_has_header(sample, delimiter)

    # Read dataframe
    sep_for_pandas = r"\s+" if delimiter == r"\s+" else delimiter
    try:
        if has_header:
            df = pd.read_csv(file_path, sep=sep_for_pandas, engine="python")
        else:
            df = pd.read_csv(file_path, sep=sep_for_pandas, header=None, engine="python")
            df.columns = [f"col_{i}" for i in range(df.shape[1])]
    except Exception:
        # Ultimate fallback
        df = pd.read_csv(file_path, sep=r"\s+", header=None, engine="python")
        df.columns = [f"col_{i}" for i in range(df.shape[1])]
        has_header = False
        delimiter = r"\s+"

    total_rows = int(len(df))
    total_columns = int(len(df.columns))
    column_names = [str(c) for c in df.columns]

    # Duplicate row count
    duplicate_rows = int(df.duplicated().sum())

    # Missing values per column
    missing_counts: Dict[str, int] = {}
    for col in column_names:
        missing_counts[col] = int(df[col].isna().sum())

    # Numeric summary statistics
    numeric_stats: Dict[str, Dict[str, float]] = {}
    for col in column_names:
        series_num = pd.to_numeric(df[col], errors="coerce")
        valid = series_num.dropna()
        if len(valid) > 0 and (len(valid) / max(1, len(df[col].dropna())) >= 0.8):
            min_val = float(valid.min())
            max_val = float(valid.max())
            mean_val = float(valid.mean())
            if not (math.isnan(min_val) or math.isinf(min_val)):
                numeric_stats[col] = {
                    "min": round(min_val, 4),
                    "max": round(max_val, 4),
                    "mean": round(mean_val, 4),
                    "valid_numeric_count": int(len(valid)),
                }

    # Unit and cycle detection heuristic
    detected_unit_col = None
    detected_cycle_col = None

    # Check for name matches first
    lower_map = {str(c).lower().strip(): str(c) for c in df.columns}
    for cand in ["unit_id", "unit", "engine_id", "unit_number", "id", "col_0"]:
        if cand in lower_map:
            detected_unit_col = lower_map[cand]
            break

    for cand in ["cycle", "cycles", "time_in_cycles", "time", "step", "col_1"]:
        if cand in lower_map:
            detected_cycle_col = lower_map[cand]
            break

    unit_stats: Optional[Dict[str, Any]] = None
    if detected_unit_col is not None and detected_unit_col in df.columns:
        unit_series = df[detected_unit_col].dropna()
        num_units = int(unit_series.nunique())
        if num_units > 0:
            unit_stats = {
                "detected_unit_column": detected_unit_col,
                "entity_count": num_units,
                "min_cycles_per_entity": None,
                "max_cycles_per_entity": None,
                "mean_cycles_per_entity": None,
            }
            if detected_cycle_col is not None and detected_cycle_col in df.columns:
                try:
                    cycle_counts = df.groupby(detected_unit_col)[detected_cycle_col].nunique()
                    unit_stats["detected_cycle_column"] = detected_cycle_col
                    unit_stats["min_cycles_per_entity"] = int(cycle_counts.min())
                    unit_stats["max_cycles_per_entity"] = int(cycle_counts.max())
                    unit_stats["mean_cycles_per_entity"] = round(float(cycle_counts.mean()), 1)
                except Exception:
                    pass

    delimiter_display = (
        "Whitespace (space / tab)"
        if delimiter == r"\s+"
        else "Comma (,)"
        if delimiter == ","
        else "Tab (\\t)"
        if delimiter == "\t"
        else f"Custom ({delimiter})"
    )

    return {
        "filename": original_filename,
        "total_rows": total_rows,
        "total_columns": total_columns,
        "detected_delimiter": delimiter_display,
        "raw_delimiter": delimiter,
        "has_header": has_header,
        "column_names": column_names,
        "duplicate_rows": duplicate_rows,
        "missing_counts": missing_counts,
        "numeric_stats": numeric_stats,
        "unit_stats": unit_stats,
    }
