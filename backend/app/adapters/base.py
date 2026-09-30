"""
Base Adapter Interface for Telemetry Data Ingestion
"""

from abc import ABC, abstractmethod
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


class BaseAdapter(ABC):
    """
    Abstract base class for dataset adapters.
    Translates raw uploaded columns into canonical schema representation.
    """

    adapter_key: str
    display_name: str
    canonical_columns: List[str]

    @abstractmethod
    def detect_mapping(self, columns: List[str]) -> Tuple[Dict[str, str], List[str]]:
        """
        Attempts to map input raw column names to canonical channel names.
        Returns:
            mapping: Dict[canonical_column, source_column]
            unmapped_required: List of canonical columns that could not be mapped
        """
        pass

    @abstractmethod
    def transform(self, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Transforms raw DataFrame into canonical DataFrame.
        """
        pass

    @staticmethod
    def compute_mapping_hash(mapping: Dict[str, str]) -> str:
        """
        Computes deterministic SHA-256 hash of sorted canonical mapping dictionary.
        """
        sorted_pairs = sorted(mapping.items(), key=lambda x: x[0])
        canonical_str = json.dumps(sorted_pairs, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
