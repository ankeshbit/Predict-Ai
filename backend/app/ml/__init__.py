"""Vendored ML inference and verification modules from production Colab bundle."""
import sys
from pathlib import Path

# Ensure vendored modules are discoverable for unpickling and relative imports
_ml_dir = str(Path(__file__).resolve().parent)
if _ml_dir not in sys.path:
    sys.path.insert(0, _ml_dir)
