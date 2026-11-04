"""
Python import bridge for `packages/forensics-py/` allowing standard dotted imports
via `packages.forensics_py.*`.
"""

from pathlib import Path

_HYPHEN_DIR = str(Path(__file__).resolve().parent.parent / "forensics-py")
if _HYPHEN_DIR not in __path__:
    __path__.append(_HYPHEN_DIR)

from .ping_trap_and_cluster_trigger import *  # noqa: F401,F403,E402
from .runner_classifier import *  # noqa: F401,F403,E402
from .shadow_cluster_resolver import *  # noqa: F401,F403,E402
