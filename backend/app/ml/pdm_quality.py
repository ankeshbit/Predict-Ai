import numpy as np
import pandas as pd

STATUS_OK, STATUS_WARNING, STATUS_INVALID = "DATA_OK", "DATA_WARNING", "DATA_INVALID"


def _issue(code, severity, message):
    return {"code": code, "severity": severity, "message": message}


def check_data_quality(history, meta):
    """Validate a single machine's history. `meta` = metadata['quality'] saved by the training notebook."""
    cfg = meta["quality_config"]
    required = list(meta["required_columns"])
    schema = set(meta["schema_columns"])
    ranges = meta["feature_ranges"]
    issues = []
    info = {"n_history_rows": 0, "latest_cycle": None, "extreme_fraction": None, "missing_fraction_latest": None}

    def result():
        sev = {i["severity"] for i in issues}
        status = STATUS_INVALID if "INVALID" in sev else STATUS_WARNING if "WARNING" in sev else STATUS_OK
        return {"status": status, "issues": issues, **info}

    if not isinstance(history, pd.DataFrame) or history.empty:
        issues.append(_issue("EMPTY_INPUT", "INVALID", "History is empty or not a DataFrame."))
        return result()
    info["n_history_rows"] = int(len(history))

    missing_cols = [c for c in required if c not in history.columns]
    if missing_cols:
        issues.append(_issue("MISSING_COLUMNS", "INVALID", f"Required columns missing: {missing_cols}"))
        return result()
    unexpected = [c for c in history.columns if c not in schema]
    if unexpected:
        issues.append(_issue("UNEXPECTED_COLUMNS", "WARNING", f"Unexpected columns ignored: {unexpected}"))

    df = history[required + (["unit_id"] if "unit_id" in history.columns and "unit_id" not in required else [])].copy()
    for c in required:
        if not pd.api.types.is_numeric_dtype(df[c]):
            coerced = pd.to_numeric(df[c], errors="coerce")
            if (coerced.isna() & df[c].notna()).any():
                issues.append(_issue("NON_NUMERIC", "INVALID", f"Non-numeric values in column '{c}'."))
            df[c] = coerced
    df[required] = df[required].replace([np.inf, -np.inf], np.nan)
    if any(i["severity"] == "INVALID" for i in issues):
        return result()

    if "unit_id" in df.columns and df["unit_id"].nunique(dropna=False) > 1:
        issues.append(_issue("MULTIPLE_UNITS", "INVALID", "History must contain exactly one machine."))
        return result()

    cyc = df["cycle"]
    if cyc.isna().any():
        issues.append(_issue("CYCLE_MISSING", "INVALID", "Missing cycle values."))
    elif (cyc <= 0).any() or (cyc % 1 != 0).any():
        issues.append(_issue("CYCLE_INVALID", "INVALID", "Cycles must be positive integers."))
    elif cyc.duplicated().any():
        issues.append(_issue("DUPLICATE_CYCLES", "INVALID", "Duplicate cycle numbers."))
    else:
        if not cyc.is_monotonic_increasing:
            issues.append(_issue("UNSORTED_CYCLES", "WARNING", "Cycles not sorted; they will be sorted before scoring."))
        if (np.diff(np.sort(cyc.to_numpy())) > 1).any():
            issues.append(_issue("CYCLE_GAPS", "WARNING", "Gaps between cycles; rolling features may be less reliable."))
    if any(i["severity"] == "INVALID" for i in issues):
        return result()

    df = df.sort_values("cycle", kind="mergesort")
    n = len(df)
    info["latest_cycle"] = int(df["cycle"].iloc[-1])
    if n < cfg["min_history_invalid"]:
        issues.append(_issue("INSUFFICIENT_HISTORY", "INVALID", f"Only {n} row(s); at least {cfg['min_history_invalid']} required."))
        return result()
    if n < meta["min_history_warn"]:
        issues.append(_issue("SHORT_HISTORY", "WARNING", f"{n} rows < {meta['min_history_warn']}: rolling/trend features are based on partial windows."))

    feature_cols = [c for c in required if c != "cycle"]
    latest = df.iloc[-1]
    miss_latest = float(latest[feature_cols].isna().mean())
    info["missing_fraction_latest"] = miss_latest
    if miss_latest > cfg["max_missing_fraction_latest"]:
        issues.append(_issue("MISSING_VALUES_LATEST", "INVALID", f"{miss_latest:.0%} of latest-row values missing."))
        return result()
    if miss_latest > 0:
        issues.append(_issue("MISSING_VALUES_LATEST", "WARNING", f"{miss_latest:.0%} of latest-row values missing (imputed with training medians)."))
    elif df[feature_cols].isna().any().any():
        issues.append(_issue("MISSING_VALUES_HISTORY", "WARNING", "Missing values in earlier history rows."))

    m = float(cfg["range_margin_fraction"])
    checked, extreme = 0, []
    for c in feature_cols:
        v = latest[c]
        if pd.isna(v):
            continue
        checked += 1
        lo, hi = ranges[c]["min"], ranges[c]["max"]
        span = hi - lo
        if v < lo - m * span or v > hi + m * span:
            extreme.append(c)
    info["extreme_fraction"] = (len(extreme) / checked) if checked else 0.0
    if extreme:
        sev = "INVALID" if info["extreme_fraction"] >= cfg["extreme_invalid_fraction"] else "WARNING"
        issues.append(_issue("EXTREME_VALUES" if sev == "WARNING" else "OUT_OF_DISTRIBUTION", sev,
                             f"{len(extreme)} of {checked} latest values outside widened training range (e.g. {extreme[:5]})."))
    return result()
