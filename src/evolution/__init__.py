"""Sovereign Titan OS — Self-Evolution & GEPA Arena Package (`src/evolution`)."""

from src.evolution.counterfactual_logger import (
    FALSE_NEGATIVE_MIN_LP_USD,
    FALSE_NEGATIVE_MIN_MULTIPLE,
    CounterfactualLogger,
    CounterfactualSkipRecord,
    StratifiedExecutionTrace,
    TraceCategory,
)
from src.evolution.gepa_arena import (
    AUTO_ROLLBACK_DRAWDOWN_PCT,
    IMMUTABLE_SAFETY_FILES,
    MAX_INSTRUCTION_TOKENS,
    PROMOTION_MIN_EV_RATIO,
    SHADOW_GATE_TRIGGER_COUNT,
    GEPAEvolutionReport,
    GEPAPolicyCandidate,
    GEPASelfImprovementArena,
    estimate_token_count,
    truncate_to_token_cap,
)

__all__ = [
    "AUTO_ROLLBACK_DRAWDOWN_PCT",
    "CounterfactualLogger",
    "CounterfactualSkipRecord",
    "FALSE_NEGATIVE_MIN_LP_USD",
    "FALSE_NEGATIVE_MIN_MULTIPLE",
    "GEPAEvolutionReport",
    "GEPAPolicyCandidate",
    "GEPASelfImprovementArena",
    "IMMUTABLE_SAFETY_FILES",
    "MAX_INSTRUCTION_TOKENS",
    "PROMOTION_MIN_EV_RATIO",
    "SHADOW_GATE_TRIGGER_COUNT",
    "StratifiedExecutionTrace",
    "TraceCategory",
    "estimate_token_count",
    "truncate_to_token_cap",
]
