#!/usr/bin/env python3
"""
Black-box CLI utility (`scripts/sybil_check.py`) to verify Top-10 non-pool holder
concentration (<= 15% safe threshold) and detect bundled Jito sybil wallet clusters.
"""

from __future__ import annotations

from pathlib import Path
import runpy

if __name__ == "__main__":
    target = (
        Path(__file__).resolve().parents[1]
        / ".agents"
        / "skills"
        / "web-strategy-harvester"
        / "scripts"
        / "sybil_check.py"
    )
    runpy.run_path(str(target), run_name="__main__")
