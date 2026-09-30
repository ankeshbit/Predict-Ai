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

    def detect_mapping(self, columns: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """
        Maps input raw column headers to the 26 C-MAPSS FD001 canonical channels.
        Normalizes names by lowercase and stripping whitespace/punctuation.
        """
        norm_map = {}
        for col in columns:
            cleaned = re.sub(r"[^a-z0-9]", "_", col.strip().lower()).strip("_")
            norm_map[cleaned] = col

        mapping: Dict[str, str] = {}
        unmapped: List[str] = []

        # 1. unit_id
        unit_candidates = ["unit_id", "unit", "unit_number", "engine_id", "engine", "id", "unitid"]
        found_unit = None
        for cand in unit_candidates:
            if cand in norm_map:
                found_unit = norm_map[cand]
                break
        if found_unit:
            mapping["unit_id"] = found_unit
        else:
            unmapped.append("unit_id")

        # 2. cycle
        cycle_candidates = ["cycle", "cycles", "time_in_cycles", "time", "step", "cycle_number"]
        found_cycle = None
        for cand in cycle_candidates:
            if cand in norm_map:
                found_cycle = norm_map[cand]
                break
        if found_cycle:
            mapping["cycle"] = found_cycle
        else:
            unmapped.append("cycle")

        # 3. op_settings 1..3
        for i in range(1, 4):
            c_name = f"op_setting_{i}"
            setting_cands = [
                f"op_setting_{i}",
                f"setting_{i}",
                f"setting{i}",
                f"operational_setting_{i}",
                f"op_setting{i}",
            ]
            found_set = None
            for cand in setting_cands:
                if cand in norm_map:
                    found_set = norm_map[cand]
                    break
            if found_set:
                mapping[c_name] = found_set
            else:
                unmapped.append(c_name)

        # 4. sensors 1..21
        for i in range(1, 22):
            s_name = f"sensor_{i}"
            sensor_cands = [
                f"sensor_{i}",
                f"sensor{i}",
                f"s_{i}",
                f"s{i}",
                f"sensor_reading_{i}",
            ]
            found_sensor = None
            for cand in sensor_cands:
                if cand in norm_map:
                    found_sensor = norm_map[cand]
                    break
            if found_sensor:
                mapping[s_name] = found_sensor
            else:
                unmapped.append(s_name)

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
