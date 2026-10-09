"""
NASA C-MAPSS FD001 Turbofan Engine Adapter
Canonical column schema: unit_id, cycle, op_setting_1..3, sensor_1..21
"""

import re
from typing import Dict, List, Tuple

import pandas as pd

from app.adapters.base import BaseAdapter


class CmapssFd001Adapter(BaseAdapter):
    adapter_key = "cmapss_fd001"
    display_name = "NASA C-MAPSS FD001 Turbofan Engine"

    canonical_columns = (
        ["unit_id", "cycle"]
        + [f"op_setting_{i}" for i in range(1, 4)]
        + [f"sensor_{i}" for i in range(1, 22)]
    )

    def detect_mapping_with_confidence(
        self, columns: List[str]
    ) -> Tuple[Dict[str, str], List[str], Dict[str, float]]:
        """
        Maps input raw column headers to the 26 C-MAPSS FD001 canonical channels.
        Assigns confidence score (1.0 = exact match, 0.9 = synonym match, 0.85 = positional C-MAPSS layout).
        """
        mapping: Dict[str, str] = {}
        unmapped: List[str] = []
        confidences: Dict[str, float] = {}

        # Check for headerless 26-column standard C-MAPSS format (e.g. col_0..col_25 or 0..25)
        clean_cols = [str(c).strip() for c in columns]
        is_headerless_26 = len(clean_cols) == 26 and all(
            c.startswith("col_") or c.isdigit() for c in clean_cols
        )
        if is_headerless_26:
            for i, canon in enumerate(self.canonical_columns):
                src = clean_cols[i]
                mapping[canon] = src
                confidences[canon] = 0.85
            return mapping, [], confidences

        norm_map = {}
        for col in columns:
            cleaned = re.sub(r"[^a-z0-9]", "_", str(col).strip().lower()).strip("_")
            norm_map[cleaned] = str(col)

        # 1. unit_id
        unit_candidates = [("unit_id", 1.0), ("unit", 0.9), ("unit_number", 0.9), ("engine_id", 0.9), ("engine", 0.85), ("id", 0.8), ("unitid", 0.9)]
        found_unit = None
        unit_conf = 0.0
        for cand, conf in unit_candidates:
            if cand in norm_map:
                found_unit = norm_map[cand]
                unit_conf = conf
                break
        if found_unit:
            mapping["unit_id"] = found_unit
            confidences["unit_id"] = unit_conf
        else:
            unmapped.append("unit_id")
            confidences["unit_id"] = 0.0

        # 2. cycle
        cycle_candidates = [("cycle", 1.0), ("cycles", 0.95), ("time_in_cycles", 0.9), ("time", 0.8), ("step", 0.8), ("cycle_number", 0.9)]
        found_cycle = None
        cycle_conf = 0.0
        for cand, conf in cycle_candidates:
            if cand in norm_map:
                found_cycle = norm_map[cand]
                cycle_conf = conf
                break
        if found_cycle:
            mapping["cycle"] = found_cycle
            confidences["cycle"] = cycle_conf
        else:
            unmapped.append("cycle")
            confidences["cycle"] = 0.0

        # 3. op_settings 1..3
        for i in range(1, 4):
            c_name = f"op_setting_{i}"
            setting_cands = [
                (f"op_setting_{i}", 1.0),
                (f"op_setting{i}", 0.95),
                (f"operating_setting_{i}", 0.95),
                (f"operating_setting{i}", 0.95),
                (f"setting_{i}", 0.9),
                (f"setting{i}", 0.9),
                (f"operational_setting_{i}", 0.9),
                (f"op{i}", 0.85),
            ]
            found_set = None
            set_conf = 0.0
            for cand, conf in setting_cands:
                if cand in norm_map:
                    found_set = norm_map[cand]
                    set_conf = conf
                    break
            if found_set:
                mapping[c_name] = found_set
                confidences[c_name] = set_conf
            else:
                unmapped.append(c_name)
                confidences[c_name] = 0.0

        # 4. sensors 1..21
        for i in range(1, 22):
            s_name = f"sensor_{i}"
            sensor_cands = [
                (f"sensor_{i}", 1.0),
                (f"sensor{i}", 0.95),
                (f"s_{i}", 0.9),
                (f"s{i}", 0.9),
                (f"sensor_reading_{i}", 0.9),
            ]
            found_sensor = None
            s_conf = 0.0
            for cand, conf in sensor_cands:
                if cand in norm_map:
                    found_sensor = norm_map[cand]
                    s_conf = conf
                    break
            if found_sensor:
                mapping[s_name] = found_sensor
                confidences[s_name] = s_conf
            else:
                unmapped.append(s_name)
                confidences[s_name] = 0.0

        return mapping, unmapped, confidences

    def detect_mapping(self, columns: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """
        Maps input raw column headers to the 26 C-MAPSS FD001 canonical channels.
        Normalizes names by lowercase and stripping whitespace/punctuation.
        """
        mapping, unmapped, _ = self.detect_mapping_with_confidence(columns)
        return mapping, unmapped

    def transform(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Renames mapped columns to canonical channel names, strips unmapped columns,
        and enforces numeric data types.
        """
        # Invert mapping: source_col -> canonical_col
        rename_map = {src: canon for canon, src in mapping.items()}
        result_df = df.rename(columns=rename_map)

        # Retain only canonical columns that exist in the result
        cols_to_keep = [col for col in self.canonical_columns if col in result_df.columns]
        result_df = result_df[cols_to_keep].copy()

        # Enforce dtypes
        if "unit_id" in result_df.columns:
            result_df["unit_id"] = pd.to_numeric(result_df["unit_id"], errors="coerce").fillna(0).astype(int)
        if "cycle" in result_df.columns:
            result_df["cycle"] = pd.to_numeric(result_df["cycle"], errors="coerce").fillna(0).astype(int)

        for col in cols_to_keep:
            if col not in ["unit_id", "cycle"]:
                result_df[col] = pd.to_numeric(result_df[col], errors="coerce").astype(float)

        if "unit_id" in result_df.columns and "cycle" in result_df.columns:
            result_df = result_df.sort_values(by=["unit_id", "cycle"]).reset_index(drop=True)

        return result_df
