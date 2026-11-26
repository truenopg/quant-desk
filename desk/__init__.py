"""Quant desk: candidate strategies in, validated verdicts out.

Makes the vendored backtest-engine importable as `bt` (same trick as
paper-trader's research package).
"""
import sys
from pathlib import Path

_VENDOR = Path(__file__).resolve().parent.parent / "vendor" / "backtest-engine"
if _VENDOR.is_dir() and str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))
