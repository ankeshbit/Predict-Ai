#!/usr/bin/env python3
"""
scripts/make_sample_csvs.py
Generates sample CSV datasets for testing the FR-6 Dataset Compatibility Gate:
1. compatible_sample.csv: Valid C-MAPSS FD001 engine run with canonical columns and valid ranges.
2. perturbed_sample.csv: C-MAPSS run with controlled drift/scaling.
3. incompatible_ai4i_sample.csv: Incompatible schema missing required sensor channels.
"""

import numpy as np
import pandas as pd
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "database" / "sample_data"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

def generate_compatible_sample(filename: str = "compatible_fd001_synthetic_test_fixture.csv"):
    np.random.seed(42)
    rows = []
    # 2 engines, 45 cycles each
    for unit in [1, 2]:
        for cycle in range(1, 46):
            deg = cycle / 45.0
            row = {
                "unit_id": unit,
                "cycle": cycle,
                "op_setting_1": -0.0007,
                "op_setting_2": -0.0004,
                "op_setting_3": 100.0,
            }
            for s in range(1, 22):
                if s in [1, 5, 6, 10, 16, 18, 19]:
                    row[f"sensor_{s}"] = 518.67
                else:
                    row[f"sensor_{s}"] = round(642.0 + deg * 15.0 + np.random.normal(0, 0.5), 4)
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(SAMPLE_DIR / filename, index=False)
    print(f"Generated {SAMPLE_DIR / filename} ({len(df)} rows)")

def generate_perturbed_sample(filename: str = "perturbed_fd001_synthetic_test_fixture.csv"):
    np.random.seed(101)
    rows = []
    for unit in [10]:
        for cycle in range(1, 40):
            deg = cycle / 40.0
            row = {
                "unit_id": unit,
                "cycle": cycle,
                "op_setting_1": 0.0012,
                "op_setting_2": 0.0001,
                "op_setting_3": 100.0,
            }
            for s in range(1, 22):
                if s in [1, 5, 6, 10, 16, 18, 19]:
                    row[f"sensor_{s}"] = 518.67
                else:
                    # Perturbed scaling (+25% baseline shift)
                    row[f"sensor_{s}"] = round((642.0 + deg * 25.0) * 1.25 + np.random.normal(0, 1.2), 4)
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(SAMPLE_DIR / filename, index=False)
    print(f"Generated {SAMPLE_DIR / filename} ({len(df)} rows)")

def generate_incompatible_sample(filename: str = "incompatible_ai4i_synthetic_test_fixture.csv"):
    # AI4I 2020 schema
    df = pd.DataFrame({
        "UDI": [1, 2, 3, 4, 5],
        "Product ID": ["M14860", "L47181", "L47182", "L47183", "L47184"],
        "Type": ["M", "L", "L", "L", "L"],
        "Air temperature [K]": [298.1, 298.2, 298.1, 298.2, 298.2],
        "Process temperature [K]": [308.6, 308.7, 308.5, 308.6, 308.7],
        "Rotational speed [rpm]": [1551, 1408, 1498, 1433, 1408],
        "Torque [Nm]": [42.8, 46.3, 49.4, 39.5, 40.0],
        "Tool wear [min]": [0, 3, 5, 7, 9],
        "Machine failure": [0, 0, 0, 0, 0]
    })
    df.to_csv(SAMPLE_DIR / filename, index=False)
    print(f"Generated {SAMPLE_DIR / filename} ({len(df)} rows)")

if __name__ == "__main__":
    # Clean up obsolete non-suffixed files if present
    for old_file in ["compatible_fd001_sample.csv", "perturbed_fd001_sample.csv", "incompatible_ai4i_sample.csv"]:
        old_path = SAMPLE_DIR / old_file
        if old_path.exists():
            old_path.unlink()
            print(f"Removed legacy file {old_path}")

    generate_compatible_sample()
    generate_perturbed_sample()
    generate_incompatible_sample()
