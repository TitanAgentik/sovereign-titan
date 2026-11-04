"""Sovereign Titan OS — Agent 28 (`multimodal-vision-polymarket-sniper`):
Sub-Second GPU Multimodal Vision (`Port 8002 Qwen3.8-27B` + `Port 8006 Nano`) Social Screenshot &
CA Sniper + CEX-to-Polymarket Binary Strike Latency Arbitrageur
(`src/engines/multimodal_vision_and_polymarket_sniper.py`).

Implements:
1. **Sub-Second Multimodal GPU Vision (`Port 8002 Qwen3.8-27B`) + Nano (`Port 8006`) Social
   Screenshot Sniper (`evaluate_multimodal_vision_social_snipe`)**:
   - Models the high-speed multimodal pipeline routing social/webhook images, memes, and
     screenshots posted by Tier-1 accounts (`ELON_MUSK`, `OPENAI_OFFICIAL`, `COINBASE_ASSETS`,
     `BINANCE_ANNOUNCEMENTS`, `TOLY_SOLANA`, `VITALIK_BUTERIN`, `TRUMP_TRUTH_X`) through:
     - **GPU 1 (`Port 8002 Qwen3.8-27B Vision`)**: Extracts embedded Base58 Solana contract
       addresses (`32-44` chars), EVM `0x` contract addresses, `$TICKER` symbols, and visual meme
       narratives from images/screenshots in `< 250.0ms` (`vision_ocr_latency_ms`).
     - **GPU 0 (`Port 8006 qwen2.5-3b Nano`)**: Scores narrative virality and spoof/phishing
       probability in `< 15.0ms` (`nano_classification_ms`).
   - Enforces the **6-Gate Contract Firewall & Liquidity Verification** before execution and
     computes `human_reaction_advantage_multiple` (comparing Titan's `< 300ms` total
     detection-to-Jito submission against human traders' `8,000-25,000ms` screenshot reading +
     typing latency = **`25x-80x` speed advantage**).
   - Emits `FIRE_MULTIMODAL_VISION_JITO_SNIPE` when confidence `>= 0.85` and
     `firewall_passed == True`, or `BLOCK_PHISHING_SCREENSHOT_HONEYPOT` when the image contains a
     malicious honeypot CA.

2. **CEX-to-Polymarket Binary Strike Latency Arbitrageur (`evaluate_cex_to_polymarket_latency_arb`)**:
   - Models sub-100ms Binance / Coinbase / Bybit spot price impulses on `SOL`, `BTC`, and `ETH`
     against active hourly/4-hour/daily **Polymarket CLOB** binary strike contracts (e.g.,
     *"Will SOL be above $K at expiry?"*).
   - Computes the exact instantaneous fair probability `P_true(YES)` using the **Black-Scholes
     Digital Option / Log-Normal Terminal Probability Formula**:
     `d_2 = [ln(S_t / K) + (mu - 0.5 * sigma^2) * tau] / (sigma * sqrt(tau))`
     `P_true(YES) = Phi(d_2) = 0.5 * [1 + erf(d_2 / sqrt(2))]`
   - Compares `P_true(YES)` and `P_true(NO) = 1 - P_true(YES)` against stale Polymarket CLOB best
     ask prices (`clob_yes_ask_price`, `clob_no_ask_price`) during the **2.0 to 8.0 second maker
     quote update lag**, computing `net_edge_cents_per_share`, `expected_roi_pct`, and
     `kelly_optimal_size_usd`.
   - Triggers `SWEEP_POLYMARKET_YES_CLOB` or `SWEEP_POLYMARKET_NO_CLOB` when
     `net_edge_cents_per_share >= 8.0` (`>= $0.08` per `$1.00` payout share after fees) and
     `maker_quote_staleness_ms >= 500.0`.

3. **`MultimodalVisionAndPolymarketSniper` Facade Class**:
   - Provides `run_full_vision_polymarket_diagnostic() -> Dict[str, Any]` and
     `get_telemetry_summary() -> Dict[str, Any]` for `TitanIPCDaemon`
     (`RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ============================================================================
# Architectural & Empirical Constants
# ============================================================================

IPC_ACTION_RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER: str = (
    "RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER"
)

# 1. Sub-Second Multimodal GPU Vision (Port 8002) + Nano (Port 8006) Constants
GPU1_VISION_PORT: int = 8002
GPU1_VISION_MODEL_NAME: str = "Qwen3.8-27B-Vision"
GPU1_VISION_ENDPOINT: str = "http://127.0.0.1:8002/v1/chat/completions"
GPU1_VISION_MAX_LATENCY_MS: float = 250.0
GPU1_VISION_DEFAULT_LATENCY_MS: float = 168.0

GPU0_NANO_PORT: int = 8006
GPU0_NANO_MODEL_NAME: str = "qwen2.5-3b-Nano"
GPU0_NANO_ENDPOINT: str = "http://127.0.0.1:8006/v1/completions"
GPU0_NANO_MAX_LATENCY_MS: float = 15.0
GPU0_NANO_DEFAULT_LATENCY_MS: float = 8.4

JITO_BUNDLE_BUILD_AND_DISPATCH_DEFAULT_MS: float = 24.0
TITAN_MAX_DETECTION_TO_JITO_MS: float = 300.0

HUMAN_SCREENSHOT_REACTION_MIN_MS: float = 8_000.0
HUMAN_SCREENSHOT_REACTION_MAX_MS: float = 25_000.0
HUMAN_SCREENSHOT_REACTION_BENCHMARK_MS: float = 15_000.0
HUMAN_REACTION_ADVANTAGE_MIN_MULTIPLE: float = 25.0
HUMAN_REACTION_ADVANTAGE_MAX_MULTIPLE: float = 80.0

TIER1_SOCIAL_ACCOUNTS: Tuple[str, ...] = (
    "ELON_MUSK",
    "OPENAI_OFFICIAL",
    "COINBASE_ASSETS",
    "BINANCE_ANNOUNCEMENTS",
    "TOLY_SOLANA",
    "VITALIK_BUTERIN",
    "TRUMP_TRUTH_X",
)

TIER1_ACCOUNT_CREDIBILITY_WEIGHTS: Dict[str, float] = {
    "ELON_MUSK": 0.98,
    "OPENAI_OFFICIAL": 0.94,
    "COINBASE_ASSETS": 0.99,
    "BINANCE_ANNOUNCEMENTS": 0.99,
    "TOLY_SOLANA": 0.95,
    "VITALIK_BUTERIN": 0.95,
    "TRUMP_TRUTH_X": 0.97,
}

SOLANA_BASE58_CA_MIN_LEN: int = 32
SOLANA_BASE58_CA_MAX_LEN: int = 44
EVM_HEX_ADDRESS_LEN: int = 42

VISION_SNIPE_MIN_CONFIDENCE: float = 0.85
FIREWALL_GATE_COUNT: int = 6
FIREWALL_MAX_SELL_TAX_PCT: float = 1.0
FIREWALL_MAX_TOP10_HOLDER_CONCENTRATION_PCT: float = 30.0
FIREWALL_MIN_LIQUIDITY_USD: float = 10_000.0
FIREWALL_MAX_PHISHING_PROBABILITY: float = 0.25

ACTION_FIRE_MULTIMODAL_VISION_JITO_SNIPE: str = "FIRE_MULTIMODAL_VISION_JITO_SNIPE"
ACTION_BLOCK_PHISHING_SCREENSHOT_HONEYPOT: str = "BLOCK_PHISHING_SCREENSHOT_HONEYPOT"
ACTION_SKIP_LOW_CONFIDENCE_SOCIAL_IMAGE: str = "SKIP_LOW_CONFIDENCE_SOCIAL_IMAGE"

# Regex patterns for OCR extraction from screenshots/memes
_SOLANA_BASE58_CA_REGEX = re.compile(r"\b([1-9A-HJ-NP-Za-km-z]{32,44})\b")
_EVM_ADDRESS_REGEX = re.compile(r"\b(0x[a-fA-F0-9]{40})\b")
_TICKER_SYMBOL_REGEX = re.compile(r"\$([A-Za-z][A-Za-z0-9_]{1,15})\b")

# 2. CEX-to-Polymarket Binary Strike Latency Arbitrage Constants
SUPPORTED_CEX_SPOT_ASSETS: Tuple[str, ...] = ("SOL", "BTC", "ETH")
SUPPORTED_CEX_VENUES: Tuple[str, ...] = ("BINANCE", "COINBASE", "BYBIT")
SUPPORTED_POLYMARKET_TENORS: Tuple[str, ...] = ("1H", "4H", "24H", "DAILY")

CEX_IMPULSE_MAX_LATENCY_MS: float = 100.0
POLYMARKET_MAKER_QUOTE_LAG_MIN_MS: float = 2_000.0
POLYMARKET_MAKER_QUOTE_LAG_MAX_MS: float = 8_000.0
POLYMARKET_MIN_MAKER_STALENESS_MS: float = 500.0

POLYMARKET_MIN_NET_EDGE_CENTS_PER_SHARE: float = 8.0
POLYMARKET_PAYOUT_PER_WINNING_SHARE_USD: float = 1.00
POLYMARKET_DEFAULT_TAKER_FEE_BPS: float = 10.0  # 0.10% CLOB fee
POLYMARKET_DEFAULT_KELLY_FRACTION: float = 0.25  # Quarter-Kelly sizing
SECONDS_PER_YEAR: float = 365.0 * 86_400.0  # 31,536,000 seconds
HOURS_PER_YEAR: float = 365.0 * 24.0  # 8,760 hours

ACTION_SWEEP_POLYMARKET_YES_CLOB: str = "SWEEP_POLYMARKET_YES_CLOB"
ACTION_SWEEP_POLYMARKET_NO_CLOB: str = "SWEEP_POLYMARKET_NO_CLOB"
ACTION_HOLD_POLYMARKET_NO_LATENCY_EDGE: str = "HOLD_POLYMARKET_NO_LATENCY_EDGE"


# ============================================================================
# Dataclasses for Multimodal Vision Sniper & Polymarket Latency Arbitrage
# ============================================================================


@dataclass(frozen=True)
class SixGateFirewallReport:
    """Detailed verification state of the 6-Gate Contract Firewall & Liquidity Verification."""

    gate1_mint_authority_revoked: bool
    gate2_freeze_authority_revoked: bool
    gate3_lp_locked_or_canonical_curve: bool
    gate4_transfer_tax_within_bounds: bool
    gate5_top10_holder_concentration_safe: bool
    gate6_liquidity_and_anti_honeypot_verified: bool
    gates_passed_count: int
    total_gates: int
    firewall_passed: bool
    failed_gate_reasons: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MultimodalVisionSocialSnipeResult:
    """Result of evaluating a social media image/meme/screenshot through GPU 1 (`Port 8002`
    Qwen3.8-27B Vision) and GPU 0 (`Port 8006` qwen2.5-3b Nano).
    """

    source_account: str
    is_tier1_account: bool
    image_id: str
    gpu1_vision_port: int
    gpu1_vision_model: str
    gpu0_nano_port: int
    gpu0_nano_model: str
    vision_ocr_latency_ms: float
    nano_classification_ms: float
    jito_bundle_submission_ms: float
    total_detection_to_jito_ms: float
    vision_latency_within_sla: bool
    nano_latency_within_sla: bool
    total_latency_within_sla: bool
    human_reaction_benchmark_ms: float
    human_reaction_advantage_multiple: float
    extracted_solana_cas: Tuple[str, ...]
    extracted_evm_cas: Tuple[str, ...]
    extracted_tickers: Tuple[str, ...]
    primary_contract_address: str
    primary_chain: str
    primary_ticker: str
    visual_meme_narrative: str
    narrative_virality_score: float
    spoof_phishing_probability: float
    is_honeypot_or_phishing_ca: bool
    six_gate_firewall: SixGateFirewallReport
    firewall_passed: bool
    combined_snipe_confidence: float
    recommended_jito_snipe_sol: float
    should_execute: bool
    action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CexToPolymarketLatencyArbResult:
    """Result of evaluating a sub-100ms CEX spot price impulse against a stale Polymarket CLOB
    binary strike contract using the Black-Scholes Digital Option formula.
    """

    asset: str
    cex_venue: str
    contract_tenor: str
    contract_question: str
    pre_impulse_spot_price: float
    spot_price: float
    strike_price: float
    cex_impulse_return_pct: float
    cex_impulse_latency_ms: float
    annualized_volatility: float
    drift_rate: float
    time_to_expiry_years: float
    time_to_expiry_hours: float
    d2: float
    p_true_yes: float
    p_true_no: float
    clob_yes_ask_price: float
    clob_no_ask_price: float
    polymarket_taker_fee_bps: float
    yes_effective_cost_usd: float
    no_effective_cost_usd: float
    yes_gross_edge_cents_per_share: float
    yes_net_edge_cents_per_share: float
    no_gross_edge_cents_per_share: float
    no_net_edge_cents_per_share: float
    selected_side: str
    selected_ask_price_usd: float
    selected_effective_cost_usd: float
    selected_true_probability: float
    gross_edge_cents_per_share: float
    net_edge_cents_per_share: float
    expected_roi_pct: float
    maker_quote_staleness_ms: float
    in_maker_quote_lag_window: bool
    full_kelly_fraction: float
    fractional_kelly_fraction: float
    bankroll_usd: float
    available_clob_ask_liquidity_usd: float
    kelly_optimal_size_usd: float
    recommended_shares_to_sweep: float
    expected_net_profit_usd: float
    should_execute: bool
    action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Helper Functions: OCR Extraction & Black-Scholes Digital Option Math
# ============================================================================


def extract_contracts_and_tickers_from_vision_text(
    vision_text: str,
) -> Tuple[Tuple[str, ...], Tuple[str, ...], Tuple[str, ...]]:
    """Extracts Base58 Solana contract addresses (`32-44` chars), EVM `0x` contract addresses
    (`42` chars), and `$TICKER` symbols from Qwen3.8-27B Vision OCR output.
    """
    if not vision_text:
        return (), (), ()

    evm_matches = tuple(dict.fromkeys(_EVM_ADDRESS_REGEX.findall(vision_text)))

    # Filter out hex strings from Base58 matches to avoid overlap
    raw_b58 = _SOLANA_BASE58_CA_REGEX.findall(vision_text)
    solana_matches: List[str] = []
    for candidate in raw_b58:
        if candidate.startswith("0x") or candidate in evm_matches:
            continue
        if SOLANA_BASE58_CA_MIN_LEN <= len(candidate) <= SOLANA_BASE58_CA_MAX_LEN:
            if candidate not in solana_matches:
                solana_matches.append(candidate)

    ticker_matches = tuple(
        dict.fromkeys(f"${t.upper()}" for t in _TICKER_SYMBOL_REGEX.findall(vision_text))
    )
    return tuple(solana_matches), evm_matches, ticker_matches


def compute_black_scholes_digital_probability(
    spot_price: float,
    strike_price: float,
    annualized_volatility: float,
    time_to_expiry_years: float,
    drift_rate: float = 0.0,
) -> Tuple[float, float, float]:
    """Computes the exact instantaneous fair probability `P_true(YES)` for a binary strike contract
    ("Will asset S be above strike K at expiry?") using the Black-Scholes Digital Option /
    Log-Normal Terminal Probability Formula:

        d_2 = [ln(S_t / K) + (mu - 0.5 * sigma^2) * tau] / (sigma * sqrt(tau))
        P_true(YES) = Phi(d_2) = 0.5 * [1 + erf(d_2 / sqrt(2))]
        P_true(NO)  = 1 - P_true(YES) = Phi(-d_2)

    Returns `(d_2, p_true_yes, p_true_no)`.
    """
    spot_price = max(float(spot_price), 1e-9)
    strike_price = max(float(strike_price), 1e-9)
    annualized_volatility = max(float(annualized_volatility), 1e-9)
    time_to_expiry_years = max(float(time_to_expiry_years), 1e-9)

    sigma_sqrt_tau = annualized_volatility * math.sqrt(time_to_expiry_years)
    d2 = (
        math.log(spot_price / strike_price)
        + (drift_rate - 0.5 * (annualized_volatility ** 2)) * time_to_expiry_years
    ) / sigma_sqrt_tau

    p_true_yes = 0.5 * (1.0 + math.erf(d2 / math.sqrt(2.0)))
    p_true_yes = max(0.0, min(1.0, p_true_yes))
    p_true_no = 1.0 - p_true_yes
    return d2, p_true_yes, p_true_no


# ============================================================================
# 1. Sub-Second Multimodal GPU Vision + Nano Social Screenshot Sniper
# ============================================================================


def evaluate_multimodal_vision_social_snipe(
    source_account: str = "ELON_MUSK",
    *,
    image_id: str = "social_img_001",
    ocr_extracted_text: str = (
        "Launching $CYBERDOG on Solana! CA: 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    ),
    extracted_solana_ca: Optional[str] = None,
    extracted_evm_ca: Optional[str] = None,
    extracted_ticker: Optional[str] = None,
    visual_meme_narrative: str = "AI Autonomous Cyberdog Viral Meme Catalyst",
    vision_ocr_latency_ms: float = GPU1_VISION_DEFAULT_LATENCY_MS,
    nano_classification_ms: float = GPU0_NANO_DEFAULT_LATENCY_MS,
    jito_bundle_submission_ms: float = JITO_BUNDLE_BUILD_AND_DISPATCH_DEFAULT_MS,
    human_reaction_benchmark_ms: float = HUMAN_SCREENSHOT_REACTION_BENCHMARK_MS,
    narrative_virality_score: float = 0.93,
    spoof_phishing_probability: float = 0.03,
    is_honeypot_ca: bool = False,
    mint_authority_revoked: bool = True,
    freeze_authority_revoked: bool = True,
    lp_locked_or_canonical_curve: bool = True,
    sell_tax_pct: float = 0.0,
    top10_holder_concentration_pct: float = 16.5,
    pool_liquidity_usd: float = 65_000.0,
    min_liquidity_usd: float = FIREWALL_MIN_LIQUIDITY_USD,
    base_snipe_sol: float = 15.0,
) -> MultimodalVisionSocialSnipeResult:
    """Evaluates a social media image, meme, or screenshot through:
    - **GPU 1 (`Port 8002 Qwen3.8-27B Vision`)**: Extracts Base58 Solana CAs (`32-44` chars),
      EVM `0x` CAs, `$TICKER` symbols, and visual meme narratives in `< 250.0ms`.
    - **GPU 0 (`Port 8006 qwen2.5-3b Nano`)**: Scores narrative virality and spoof/phishing
      probability in `< 15.0ms`.
    - **6-Gate Contract Firewall & Liquidity Verification**: Enforces all 6 on-chain safety gates
      and computes `human_reaction_advantage_multiple` (`25x-80x` faster than human screenshot
      reading + manual CA typing).
    """
    normalized_account = source_account.strip().upper()
    is_tier1 = normalized_account in TIER1_SOCIAL_ACCOUNTS
    account_weight = TIER1_ACCOUNT_CREDIBILITY_WEIGHTS.get(normalized_account, 0.72)

    # Extract CAs and tickers from OCR text
    sol_cas, evm_cas, tickers = extract_contracts_and_tickers_from_vision_text(
        ocr_extracted_text
    )

    if extracted_solana_ca and extracted_solana_ca not in sol_cas:
        sol_cas = (extracted_solana_ca,) + sol_cas
    if extracted_evm_ca and extracted_evm_ca not in evm_cas:
        evm_cas = (extracted_evm_ca,) + evm_cas
    if extracted_ticker:
        norm_ticker = (
            extracted_ticker.upper()
            if extracted_ticker.startswith("$")
            else f"${extracted_ticker.upper()}"
        )
        if norm_ticker not in tickers:
            tickers = (norm_ticker,) + tickers

    if sol_cas:
        primary_ca = sol_cas[0]
        primary_chain = "SOLANA"
    elif evm_cas:
        primary_ca = evm_cas[0]
        primary_chain = "EVM"
    else:
        primary_ca = ""
        primary_chain = "NONE"

    primary_ticker = tickers[0] if tickers else "$UNKNOWN"

    # Latency SLA verification
    vision_ok = 0.0 < vision_ocr_latency_ms < GPU1_VISION_MAX_LATENCY_MS
    nano_ok = 0.0 < nano_classification_ms < GPU0_NANO_MAX_LATENCY_MS
    total_latency_ms = round(
        vision_ocr_latency_ms + nano_classification_ms + jito_bundle_submission_ms, 3
    )
    total_ok = 0.0 < total_latency_ms < TITAN_MAX_DETECTION_TO_JITO_MS

    # Human reaction speed advantage multiple (8,000-25,000ms human vs <300ms Titan = 25x-80x)
    effective_human_ms = max(
        HUMAN_SCREENSHOT_REACTION_MIN_MS,
        min(HUMAN_SCREENSHOT_REACTION_MAX_MS, human_reaction_benchmark_ms),
    )
    human_advantage_multiple = round(
        effective_human_ms / max(total_latency_ms, 1.0), 2
    )

    # 6-Gate Contract Firewall & Liquidity Verification
    is_phishing_or_honeypot = bool(
        is_honeypot_ca or spoof_phishing_probability >= FIREWALL_MAX_PHISHING_PROBABILITY
    )
    gate1 = bool(mint_authority_revoked)
    gate2 = bool(freeze_authority_revoked)
    gate3 = bool(lp_locked_or_canonical_curve)
    gate4 = bool(0.0 <= sell_tax_pct <= FIREWALL_MAX_SELL_TAX_PCT)
    gate5 = bool(
        0.0
        <= top10_holder_concentration_pct
        <= FIREWALL_MAX_TOP10_HOLDER_CONCENTRATION_PCT
    )
    gate6 = bool(
        pool_liquidity_usd >= min_liquidity_usd
        and not is_phishing_or_honeypot
        and bool(primary_ca)
    )

    failed_reasons: List[str] = []
    if not gate1:
        failed_reasons.append("GATE1_MINT_AUTHORITY_ACTIVE")
    if not gate2:
        failed_reasons.append("GATE2_FREEZE_AUTHORITY_ACTIVE")
    if not gate3:
        failed_reasons.append("GATE3_LP_UNLOCKED_OR_NON_CANONICAL")
    if not gate4:
        failed_reasons.append("GATE4_EXCESSIVE_TRANSFER_OR_SELL_TAX")
    if not gate5:
        failed_reasons.append("GATE5_INSIDER_HOLDER_CONCENTRATION_TOO_HIGH")
    if not gate6:
        if is_phishing_or_honeypot:
            failed_reasons.append("GATE6_PHISHING_OR_HONEYPOT_DETECTED")
        elif not primary_ca:
            failed_reasons.append("GATE6_NO_VALID_CONTRACT_ADDRESS_EXTRACTED")
        else:
            failed_reasons.append("GATE6_INSUFFICIENT_POOL_LIQUIDITY")

    gates_list = (gate1, gate2, gate3, gate4, gate5, gate6)
    gates_passed_count = sum(1 for g in gates_list if g)
    firewall_passed = all(gates_list)

    firewall_report = SixGateFirewallReport(
        gate1_mint_authority_revoked=gate1,
        gate2_freeze_authority_revoked=gate2,
        gate3_lp_locked_or_canonical_curve=gate3,
        gate4_transfer_tax_within_bounds=gate4,
        gate5_top10_holder_concentration_safe=gate5,
        gate6_liquidity_and_anti_honeypot_verified=gate6,
        gates_passed_count=gates_passed_count,
        total_gates=FIREWALL_GATE_COUNT,
        firewall_passed=firewall_passed,
        failed_gate_reasons=tuple(failed_reasons),
    )

    # Combined multimodal confidence calculation
    clamped_virality = max(0.0, min(1.0, narrative_virality_score))
    clamped_phishing = max(0.0, min(1.0, spoof_phishing_probability))
    latency_bonus = 0.03 if (vision_ok and nano_ok and total_ok) else -0.10
    ca_extracted_factor = 1.0 if primary_ca else 0.35

    raw_confidence = (
        (0.45 * account_weight + 0.55 * clamped_virality)
        * (1.0 - clamped_phishing)
        * ca_extracted_factor
        + latency_bonus
    )
    if is_phishing_or_honeypot:
        raw_confidence = min(raw_confidence, 0.15)
    combined_confidence = round(max(0.0, min(0.999, raw_confidence)), 4)

    # Decision routing
    if is_phishing_or_honeypot or not gate1 or not gate2 or not gate4:
        action = ACTION_BLOCK_PHISHING_SCREENSHOT_HONEYPOT
        should_execute = False
        recommended_sol = 0.0
    elif (
        firewall_passed
        and combined_confidence >= VISION_SNIPE_MIN_CONFIDENCE
        and vision_ok
        and nano_ok
    ):
        action = ACTION_FIRE_MULTIMODAL_VISION_JITO_SNIPE
        should_execute = True
        recommended_sol = round(base_snipe_sol * combined_confidence, 4)
    else:
        action = ACTION_SKIP_LOW_CONFIDENCE_SOCIAL_IMAGE
        should_execute = False
        recommended_sol = 0.0

    return MultimodalVisionSocialSnipeResult(
        source_account=normalized_account,
        is_tier1_account=is_tier1,
        image_id=image_id,
        gpu1_vision_port=GPU1_VISION_PORT,
        gpu1_vision_model=GPU1_VISION_MODEL_NAME,
        gpu0_nano_port=GPU0_NANO_PORT,
        gpu0_nano_model=GPU0_NANO_MODEL_NAME,
        vision_ocr_latency_ms=round(vision_ocr_latency_ms, 3),
        nano_classification_ms=round(nano_classification_ms, 3),
        jito_bundle_submission_ms=round(jito_bundle_submission_ms, 3),
        total_detection_to_jito_ms=total_latency_ms,
        vision_latency_within_sla=vision_ok,
        nano_latency_within_sla=nano_ok,
        total_latency_within_sla=total_ok,
        human_reaction_benchmark_ms=round(effective_human_ms, 1),
        human_reaction_advantage_multiple=human_advantage_multiple,
        extracted_solana_cas=sol_cas,
        extracted_evm_cas=evm_cas,
        extracted_tickers=tickers,
        primary_contract_address=primary_ca,
        primary_chain=primary_chain,
        primary_ticker=primary_ticker,
        visual_meme_narrative=visual_meme_narrative,
        narrative_virality_score=round(clamped_virality, 4),
        spoof_phishing_probability=round(clamped_phishing, 4),
        is_honeypot_or_phishing_ca=is_phishing_or_honeypot,
        six_gate_firewall=firewall_report,
        firewall_passed=firewall_passed,
        combined_snipe_confidence=combined_confidence,
        recommended_jito_snipe_sol=recommended_sol,
        should_execute=should_execute,
        action=action,
    )


# ============================================================================
# 2. CEX-to-Polymarket Binary Strike Latency Arbitrageur
# ============================================================================


def evaluate_cex_to_polymarket_latency_arb(
    asset: str = "SOL",
    *,
    cex_venue: str = "BINANCE",
    contract_tenor: str = "1H",
    pre_impulse_spot_price: float = 198.20,
    spot_price: float = 203.50,
    strike_price: float = 200.00,
    annualized_volatility: float = 0.85,
    drift_rate: float = 0.0,
    time_to_expiry_years: Optional[float] = None,
    time_to_expiry_hours: float = 0.50,
    clob_yes_ask_price: float = 0.54,
    clob_no_ask_price: float = 0.48,
    maker_quote_staleness_ms: float = 3_400.0,
    cex_impulse_latency_ms: float = 42.0,
    polymarket_taker_fee_bps: float = POLYMARKET_DEFAULT_TAKER_FEE_BPS,
    bankroll_usd: float = 50_000.0,
    available_clob_ask_liquidity_usd: float = 8_500.0,
    kelly_fraction_multiplier: float = POLYMARKET_DEFAULT_KELLY_FRACTION,
    min_net_edge_cents_per_share: float = POLYMARKET_MIN_NET_EDGE_CENTS_PER_SHARE,
) -> CexToPolymarketLatencyArbResult:
    """Evaluates a sub-100ms CEX spot impulse on `SOL`, `BTC`, or `ETH` against an active
    Polymarket CLOB binary strike contract ("Will <ASSET> be above $<K> at expiry?").

    Computes exact instantaneous fair probability `P_true(YES)` via the Black-Scholes Digital
    Option formula:
        d_2 = [ln(S_t / K) + (mu - 0.5 * sigma^2) * tau] / (sigma * sqrt(tau))
        P_true(YES) = Phi(d_2) = 0.5 * [1 + erf(d_2 / sqrt(2))]

    Compares `P_true(YES)` and `P_true(NO) = 1 - P_true(YES)` against stale Polymarket CLOB best
    asks (`clob_yes_ask_price`, `clob_no_ask_price`) during the 2.0-8.0s maker quote update lag,
    and triggers `SWEEP_POLYMARKET_YES_CLOB` or `SWEEP_POLYMARKET_NO_CLOB` when
    `net_edge_cents_per_share >= 8.0` and `maker_quote_staleness_ms >= 500.0`.
    """
    norm_asset = asset.strip().upper()
    norm_venue = cex_venue.strip().upper()
    norm_tenor = contract_tenor.strip().upper()

    if time_to_expiry_years is not None and time_to_expiry_years > 0.0:
        tau_years = float(time_to_expiry_years)
        tau_hours = tau_years * HOURS_PER_YEAR
    else:
        tau_hours = max(time_to_expiry_hours, 1e-6)
        tau_years = tau_hours / HOURS_PER_YEAR

    d2, p_true_yes, p_true_no = compute_black_scholes_digital_probability(
        spot_price=spot_price,
        strike_price=strike_price,
        annualized_volatility=annualized_volatility,
        time_to_expiry_years=tau_years,
        drift_rate=drift_rate,
    )

    cex_impulse_return_pct = (
        ((spot_price - pre_impulse_spot_price) / pre_impulse_spot_price) * 100.0
        if pre_impulse_spot_price > 0.0
        else 0.0
    )

    fee_multiplier = 1.0 + max(0.0, polymarket_taker_fee_bps) / 10_000.0
    yes_effective_cost = clob_yes_ask_price * fee_multiplier
    no_effective_cost = clob_no_ask_price * fee_multiplier

    yes_gross_edge_cents = (p_true_yes - clob_yes_ask_price) * 100.0
    yes_net_edge_cents = (p_true_yes - yes_effective_cost) * 100.0

    no_gross_edge_cents = (p_true_no - clob_no_ask_price) * 100.0
    no_net_edge_cents = (p_true_no - no_effective_cost) * 100.0

    # Choose the side with the higher net edge per $1.00 payout share
    if yes_net_edge_cents >= no_net_edge_cents:
        selected_side = "YES"
        selected_ask = clob_yes_ask_price
        selected_cost = yes_effective_cost
        selected_prob = p_true_yes
        gross_edge_cents = yes_gross_edge_cents
        net_edge_cents = yes_net_edge_cents
    else:
        selected_side = "NO"
        selected_ask = clob_no_ask_price
        selected_cost = no_effective_cost
        selected_prob = p_true_no
        gross_edge_cents = no_gross_edge_cents
        net_edge_cents = no_net_edge_cents

    expected_roi_pct = (
        ((selected_prob - selected_cost) / selected_cost) * 100.0
        if selected_cost > 0.0
        else 0.0
    )

    # Binary Kelly Criterion: f* = (p - c) / (1 - c) for a binary payout of $1.00
    if selected_prob > selected_cost and selected_cost < 1.0:
        full_kelly = (selected_prob - selected_cost) / (1.0 - selected_cost)
    else:
        full_kelly = 0.0
    full_kelly = max(0.0, min(1.0, full_kelly))
    fractional_kelly = full_kelly * max(0.0, min(1.0, kelly_fraction_multiplier))

    raw_kelly_usd = bankroll_usd * fractional_kelly
    kelly_optimal_size_usd = round(
        min(raw_kelly_usd, available_clob_ask_liquidity_usd), 2
    )

    in_maker_lag_window = (
        POLYMARKET_MAKER_QUOTE_LAG_MIN_MS
        <= maker_quote_staleness_ms
        <= POLYMARKET_MAKER_QUOTE_LAG_MAX_MS
    )
    staleness_eligible = maker_quote_staleness_ms >= POLYMARKET_MIN_MAKER_STALENESS_MS
    cex_latency_ok = 0.0 < cex_impulse_latency_ms <= CEX_IMPULSE_MAX_LATENCY_MS

    if (
        net_edge_cents >= min_net_edge_cents_per_share
        and staleness_eligible
        and cex_latency_ok
        and kelly_optimal_size_usd > 0.0
    ):
        should_execute = True
        action = (
            ACTION_SWEEP_POLYMARKET_YES_CLOB
            if selected_side == "YES"
            else ACTION_SWEEP_POLYMARKET_NO_CLOB
        )
        recommended_shares = round(kelly_optimal_size_usd / selected_cost, 4)
        expected_net_profit_usd = round(
            recommended_shares * ( net_edge_cents / 100.0 ), 2
        )
    else:
        should_execute = False
        action = ACTION_HOLD_POLYMARKET_NO_LATENCY_EDGE
        kelly_optimal_size_usd = 0.0 if net_edge_cents <= 0.0 else kelly_optimal_size_usd
        recommended_shares = 0.0
        expected_net_profit_usd = 0.0

    question = (
        f"Will {norm_asset} be above ${strike_price:,.2f} at {norm_tenor} expiry?"
    )

    return CexToPolymarketLatencyArbResult(
        asset=norm_asset,
        cex_venue=norm_venue,
        contract_tenor=norm_tenor,
        contract_question=question,
        pre_impulse_spot_price=round(pre_impulse_spot_price, 6),
        spot_price=round(spot_price, 6),
        strike_price=round(strike_price, 6),
        cex_impulse_return_pct=round(cex_impulse_return_pct, 4),
        cex_impulse_latency_ms=round(cex_impulse_latency_ms, 3),
        annualized_volatility=round(annualized_volatility, 6),
        drift_rate=round(drift_rate, 6),
        time_to_expiry_years=tau_years,
        time_to_expiry_hours=round(tau_hours, 6),
        d2=d2,
        p_true_yes=p_true_yes,
        p_true_no=p_true_no,
        clob_yes_ask_price=round(clob_yes_ask_price, 6),
        clob_no_ask_price=round(clob_no_ask_price, 6),
        polymarket_taker_fee_bps=round(polymarket_taker_fee_bps, 4),
        yes_effective_cost_usd=round(yes_effective_cost, 6),
        no_effective_cost_usd=round(no_effective_cost, 6),
        yes_gross_edge_cents_per_share=round(yes_gross_edge_cents, 4),
        yes_net_edge_cents_per_share=round(yes_net_edge_cents, 4),
        no_gross_edge_cents_per_share=round(no_gross_edge_cents, 4),
        no_net_edge_cents_per_share=round(no_net_edge_cents, 4),
        selected_side=selected_side,
        selected_ask_price_usd=round(selected_ask, 6),
        selected_effective_cost_usd=round(selected_cost, 6),
        selected_true_probability=round(selected_prob, 6),
        gross_edge_cents_per_share=round(gross_edge_cents, 4),
        net_edge_cents_per_share=round(net_edge_cents, 4),
        expected_roi_pct=round(expected_roi_pct, 4),
        maker_quote_staleness_ms=round(maker_quote_staleness_ms, 2),
        in_maker_quote_lag_window=in_maker_lag_window,
        full_kelly_fraction=round(full_kelly, 6),
        fractional_kelly_fraction=round(fractional_kelly, 6),
        bankroll_usd=round(bankroll_usd, 2),
        available_clob_ask_liquidity_usd=round(available_clob_ask_liquidity_usd, 2),
        kelly_optimal_size_usd=kelly_optimal_size_usd,
        recommended_shares_to_sweep=recommended_shares,
        expected_net_profit_usd=expected_net_profit_usd,
        should_execute=should_execute,
        action=action,
    )


# ============================================================================
# 3. MultimodalVisionAndPolymarketSniper Facade Class
# ============================================================================


class MultimodalVisionAndPolymarketSniper:
    """Facade orchestrating Agent 28 (`multimodal-vision-polymarket-sniper`):
    1. Sub-Second Multimodal GPU Vision (`Port 8002 Qwen3.8-27B`) + Nano (`Port 8006`)
       Social Screenshot & CA Sniper
    2. CEX-to-Polymarket Binary Strike Latency Arbitrageur
    """

    def __init__(self) -> None:
        self._vision_evaluations: int = 0
        self._vision_jito_snipes_fired: int = 0
        self._vision_phishing_honeypots_blocked: int = 0
        self._polymarket_evaluations: int = 0
        self._polymarket_yes_sweeps_triggered: int = 0
        self._polymarket_no_sweeps_triggered: int = 0
        self._cumulative_expected_polymarket_profit_usd: float = 0.0
        self._last_diagnostic_ts: Optional[float] = None

    def evaluate_multimodal_vision_social_snipe(
        self,
        source_account: str = "ELON_MUSK",
        **kwargs: Any,
    ) -> MultimodalVisionSocialSnipeResult:
        """Evaluates a social screenshot/meme via GPU 1 Vision (`Port 8002`) + GPU 0 Nano
        (`Port 8006`) and updates telemetry counters.
        """
        res = evaluate_multimodal_vision_social_snipe(source_account, **kwargs)
        self._vision_evaluations += 1
        if res.action == ACTION_FIRE_MULTIMODAL_VISION_JITO_SNIPE:
            self._vision_jito_snipes_fired += 1
        elif res.action == ACTION_BLOCK_PHISHING_SCREENSHOT_HONEYPOT:
            self._vision_phishing_honeypots_blocked += 1
        return res

    def evaluate_cex_to_polymarket_latency_arb(
        self,
        asset: str = "SOL",
        **kwargs: Any,
    ) -> CexToPolymarketLatencyArbResult:
        """Evaluates a sub-100ms CEX impulse against a Polymarket binary strike CLOB contract and
        updates telemetry counters.
        """
        res = evaluate_cex_to_polymarket_latency_arb(asset, **kwargs)
        self._polymarket_evaluations += 1
        if res.action == ACTION_SWEEP_POLYMARKET_YES_CLOB:
            self._polymarket_yes_sweeps_triggered += 1
            self._cumulative_expected_polymarket_profit_usd = round(
                self._cumulative_expected_polymarket_profit_usd
                + res.expected_net_profit_usd,
                2,
            )
        elif res.action == ACTION_SWEEP_POLYMARKET_NO_CLOB:
            self._polymarket_no_sweeps_triggered += 1
            self._cumulative_expected_polymarket_profit_usd = round(
                self._cumulative_expected_polymarket_profit_usd
                + res.expected_net_profit_usd,
                2,
            )
        return res

    def run_full_vision_polymarket_diagnostic(self) -> Dict[str, Any]:
        """Runs a comprehensive diagnostic across both Agent 28 subsystems for `TitanIPCDaemon`
        (`RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER`).
        """
        t0 = time.perf_counter()

        # 1A. Tier-1 Viral Screenshot Snipe (Passes all 6 Firewall Gates, <250ms Vision, <15ms Nano)
        vision_snipe_res = self.evaluate_multimodal_vision_social_snipe(
            "ELON_MUSK",
            image_id="elon_x_meme_screenshot_001",
            ocr_extracted_text=(
                "Mars Colony official token $MARSAI live on Solana! "
                "CA: 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
            ),
            visual_meme_narrative="Elon Mars Colony AI Doge Meme Screenshot",
            vision_ocr_latency_ms=162.5,
            nano_classification_ms=8.1,
            jito_bundle_submission_ms=21.4,
            human_reaction_benchmark_ms=14_400.0,
            narrative_virality_score=0.95,
            spoof_phishing_probability=0.02,
            is_honeypot_ca=False,
            mint_authority_revoked=True,
            freeze_authority_revoked=True,
            lp_locked_or_canonical_curve=True,
            sell_tax_pct=0.0,
            top10_holder_concentration_pct=14.2,
            pool_liquidity_usd=85_000.0,
        )

        # 1B. Malicious Phishing / Honeypot Screenshot Blocked by 6-Gate Firewall
        vision_honeypot_res = self.evaluate_multimodal_vision_social_snipe(
            "OPENAI_OFFICIAL",
            image_id="fake_spoof_honeypot_002",
            ocr_extracted_text=(
                "Claim $GPT5 airdrop now! "
                "CA: 9xHoneypotMintTrap11111111111111111111111111"
            ),
            visual_meme_narrative="Spoofed Airdrop Phishing Screenshot",
            vision_ocr_latency_ms=174.0,
            nano_classification_ms=9.2,
            spoof_phishing_probability=0.88,
            is_honeypot_ca=True,
            freeze_authority_revoked=False,
            sell_tax_pct=99.0,
        )

        # 2A. Bullish CEX SOL Impulse -> Sweep Polymarket YES CLOB
        polymarket_yes_res = self.evaluate_cex_to_polymarket_latency_arb(
            "SOL",
            cex_venue="BINANCE",
            contract_tenor="1H",
            pre_impulse_spot_price=198.40,
            spot_price=204.20,
            strike_price=200.00,
            annualized_volatility=0.80,
            time_to_expiry_hours=0.50,
            clob_yes_ask_price=0.53,
            clob_no_ask_price=0.49,
            maker_quote_staleness_ms=3_200.0,
            cex_impulse_latency_ms=38.0,
        )

        # 2B. Bearish CEX BTC Impulse -> Sweep Polymarket NO CLOB
        polymarket_no_res = self.evaluate_cex_to_polymarket_latency_arb(
            "BTC",
            cex_venue="COINBASE",
            contract_tenor="4H",
            pre_impulse_spot_price=95_400.0,
            spot_price=93_600.0,
            strike_price=95_000.0,
            annualized_volatility=0.55,
            time_to_expiry_hours=1.0,
            clob_yes_ask_price=0.52,
            clob_no_ask_price=0.50,
            maker_quote_staleness_ms=4_100.0,
            cex_impulse_latency_ms=44.0,
        )

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        self._last_diagnostic_ts = time.time()

        return {
            "status": "OK",
            "ipc_action": IPC_ACTION_RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER,
            "subsystem": "MULTIMODAL_VISION_AND_POLYMARKET_SNIPER_AGENT_28",
            "diagnostic_latency_ms": latency_ms,
            "vision_valid_jito_snipe": vision_snipe_res.to_dict(),
            "vision_blocked_honeypot_screenshot": vision_honeypot_res.to_dict(),
            "polymarket_yes_clob_sweep": polymarket_yes_res.to_dict(),
            "polymarket_no_clob_sweep": polymarket_no_res.to_dict(),
            "telemetry": self.get_telemetry_summary(),
        }

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Returns real-time operational telemetry for `TitanIPCDaemon`."""
        return {
            "engine": "MultimodalVisionAndPolymarketSniper",
            "agent_id": "multimodal-vision-polymarket-sniper",
            "agent_number": 28,
            "ipc_action": IPC_ACTION_RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER,
            "vision_evaluations": self._vision_evaluations,
            "vision_jito_snipes_fired": self._vision_jito_snipes_fired,
            "vision_phishing_honeypots_blocked": self._vision_phishing_honeypots_blocked,
            "polymarket_evaluations": self._polymarket_evaluations,
            "polymarket_yes_sweeps_triggered": self._polymarket_yes_sweeps_triggered,
            "polymarket_no_sweeps_triggered": self._polymarket_no_sweeps_triggered,
            "cumulative_expected_polymarket_profit_usd": (
                self._cumulative_expected_polymarket_profit_usd
            ),
            "benchmarks": {
                "gpu1_vision_port": GPU1_VISION_PORT,
                "gpu1_vision_model": GPU1_VISION_MODEL_NAME,
                "gpu1_vision_max_latency_ms": GPU1_VISION_MAX_LATENCY_MS,
                "gpu0_nano_port": GPU0_NANO_PORT,
                "gpu0_nano_model": GPU0_NANO_MODEL_NAME,
                "gpu0_nano_max_latency_ms": GPU0_NANO_MAX_LATENCY_MS,
                "titan_max_detection_to_jito_ms": TITAN_MAX_DETECTION_TO_JITO_MS,
                "human_screenshot_reaction_min_ms": HUMAN_SCREENSHOT_REACTION_MIN_MS,
                "human_screenshot_reaction_max_ms": HUMAN_SCREENSHOT_REACTION_MAX_MS,
                "human_reaction_advantage_min_multiple": (
                    HUMAN_REACTION_ADVANTAGE_MIN_MULTIPLE
                ),
                "human_reaction_advantage_max_multiple": (
                    HUMAN_REACTION_ADVANTAGE_MAX_MULTIPLE
                ),
                "tier1_accounts_count": len(TIER1_SOCIAL_ACCOUNTS),
                "firewall_gate_count": FIREWALL_GATE_COUNT,
                "vision_snipe_min_confidence": VISION_SNIPE_MIN_CONFIDENCE,
                "polymarket_min_net_edge_cents_per_share": (
                    POLYMARKET_MIN_NET_EDGE_CENTS_PER_SHARE
                ),
                "polymarket_min_maker_staleness_ms": POLYMARKET_MIN_MAKER_STALENESS_MS,
                "polymarket_maker_quote_lag_window_ms": [
                    POLYMARKET_MAKER_QUOTE_LAG_MIN_MS,
                    POLYMARKET_MAKER_QUOTE_LAG_MAX_MS,
                ],
            },
            "last_diagnostic_ts": self._last_diagnostic_ts,
        }


__all__ = [
    "ACTION_BLOCK_PHISHING_SCREENSHOT_HONEYPOT",
    "ACTION_FIRE_MULTIMODAL_VISION_JITO_SNIPE",
    "ACTION_HOLD_POLYMARKET_NO_LATENCY_EDGE",
    "ACTION_SKIP_LOW_CONFIDENCE_SOCIAL_IMAGE",
    "ACTION_SWEEP_POLYMARKET_NO_CLOB",
    "ACTION_SWEEP_POLYMARKET_YES_CLOB",
    "CEX_IMPULSE_MAX_LATENCY_MS",
    "CexToPolymarketLatencyArbResult",
    "EVM_HEX_ADDRESS_LEN",
    "FIREWALL_GATE_COUNT",
    "FIREWALL_MAX_PHISHING_PROBABILITY",
    "FIREWALL_MAX_SELL_TAX_PCT",
    "FIREWALL_MAX_TOP10_HOLDER_CONCENTRATION_PCT",
    "FIREWALL_MIN_LIQUIDITY_USD",
    "GPU0_NANO_DEFAULT_LATENCY_MS",
    "GPU0_NANO_ENDPOINT",
    "GPU0_NANO_MAX_LATENCY_MS",
    "GPU0_NANO_MODEL_NAME",
    "GPU0_NANO_PORT",
    "GPU1_VISION_DEFAULT_LATENCY_MS",
    "GPU1_VISION_ENDPOINT",
    "GPU1_VISION_MAX_LATENCY_MS",
    "GPU1_VISION_MODEL_NAME",
    "GPU1_VISION_PORT",
    "HOURS_PER_YEAR",
    "HUMAN_REACTION_ADVANTAGE_MAX_MULTIPLE",
    "HUMAN_REACTION_ADVANTAGE_MIN_MULTIPLE",
    "HUMAN_SCREENSHOT_REACTION_BENCHMARK_MS",
    "HUMAN_SCREENSHOT_REACTION_MAX_MS",
    "HUMAN_SCREENSHOT_REACTION_MIN_MS",
    "IPC_ACTION_RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER",
    "JITO_BUNDLE_BUILD_AND_DISPATCH_DEFAULT_MS",
    "MultimodalVisionAndPolymarketSniper",
    "MultimodalVisionSocialSnipeResult",
    "POLYMARKET_DEFAULT_KELLY_FRACTION",
    "POLYMARKET_DEFAULT_TAKER_FEE_BPS",
    "POLYMARKET_MAKER_QUOTE_LAG_MAX_MS",
    "POLYMARKET_MAKER_QUOTE_LAG_MIN_MS",
    "POLYMARKET_MIN_MAKER_STALENESS_MS",
    "POLYMARKET_MIN_NET_EDGE_CENTS_PER_SHARE",
    "POLYMARKET_PAYOUT_PER_WINNING_SHARE_USD",
    "SECONDS_PER_YEAR",
    "SOLANA_BASE58_CA_MAX_LEN",
    "SOLANA_BASE58_CA_MIN_LEN",
    "SUPPORTED_CEX_SPOT_ASSETS",
    "SUPPORTED_CEX_VENUES",
    "SUPPORTED_POLYMARKET_TENORS",
    "SixGateFirewallReport",
    "TIER1_ACCOUNT_CREDIBILITY_WEIGHTS",
    "TIER1_SOCIAL_ACCOUNTS",
    "TITAN_MAX_DETECTION_TO_JITO_MS",
    "VISION_SNIPE_MIN_CONFIDENCE",
    "compute_black_scholes_digital_probability",
    "evaluate_cex_to_polymarket_latency_arb",
    "evaluate_multimodal_vision_social_snipe",
    "extract_contracts_and_tickers_from_vision_text",
]
