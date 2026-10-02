#!/usr/bin/env python3
"""
scripts/prepare_cmapss.py
Utility script to process raw whitespace-delimited NASA C-MAPSS FD001 text files
into canonical CSV format with standardized column headers.
"""

import sys
from pathlib import Path

import pandas as pd

COLUMN_NAMES = [
    "unit_id", "cycle",
    "op_setting_1", "op_setting_2", "op_setting_3"
] + [f"sensor_{i}" for i in range(1, 22)]

def convert_raw_to_csv(raw_path: Path, output_csv_path: Path) -> None:
    if not raw_path.exists():
        print(f"Error: {raw_path} not found.")
        sys.exit(1)

    print(f"Loading raw C-MAPSS data from {raw_path}...")
    df = pd.read_csv(raw_path, sep=r"\s+", header=None, names=COLUMN_NAMES)
    print(f"Loaded {len(df)} rows across {df['unit_id'].nunique()} units.")

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv_path, index=False)
    print(f"Saved canonical CSV to {output_csv_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python prepare_cmapss.py <raw_txt_file> <output_csv_file>")
        sys.exit(1)
    convert_raw_to_csv(Path(sys.argv[1]), Path(sys.argv[2]))
