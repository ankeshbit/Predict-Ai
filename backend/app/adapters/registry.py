"""
Adapter Registry
Manages discovery and instantiation of dataset schema adapters.
"""

from typing import Any, Dict, List
from app.adapters.base import BaseAdapter
from app.adapters.cmapss_fd001 import CmapssFd001Adapter

_ADAPTERS: Dict[str, BaseAdapter] = {
    CmapssFd001Adapter.adapter_key: CmapssFd001Adapter(),
}


def get_adapter(adapter_key: str) -> BaseAdapter:
    """Returns adapter instance by key or raises ValueError."""
    if adapter_key not in _ADAPTERS:
        raise ValueError(f"Unknown adapter key: '{adapter_key}'. Available: {list(_ADAPTERS.keys())}")
    return _ADAPTERS[adapter_key]


def list_adapters() -> List[Dict[str, Any]]:
    """Lists registered adapters with metadata."""
    return [
        {
            "adapter_key": adapter.adapter_key,
            "display_name": adapter.display_name,
            "canonical_columns": adapter.canonical_columns,
        }
        for adapter in _ADAPTERS.values()
    ]
