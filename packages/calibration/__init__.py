"""
Calibration & Offline Backtesting Package (`packages/calibration`).
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "CalibrationGridPointResult",
    "CalibrationSuiteResult",
    "main",
    "persist_calibration_results_sqlite",
    "run_calibration_grid",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import cli

        return getattr(cli, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
