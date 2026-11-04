"""Comprehensive pytest verification suite for
`/home/titanagentik/sovereign-titan/src/engines/multimodal_vision_and_polymarket_sniper.py`
implementing Agent 28 (`multimodal-vision-polymarket-sniper`):
1. Sub-Second Multimodal GPU Vision (`Port 8002 Qwen3.8-27B`) + Nano (`Port 8006`) Social
   Screenshot Sniper (`evaluate_multimodal_vision_social_snipe`)
2. CEX-to-Polymarket Binary Strike Latency Arbitrageur (`evaluate_cex_to_polymarket_latency_arb`)
3. `MultimodalVisionAndPolymarketSniper` Facade Class (`RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER`)
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.engines.multimodal_vision_and_polymarket_sniper import (
    ACTION_BLOCK_PHISHING_SCREENSHOT_HONEYPOT,
    ACTION_FIRE_MULTIMODAL_VISION_JITO_SNIPE,
    ACTION_HOLD_POLYMARKET_NO_LATENCY_EDGE,
    ACTION_SKIP_LOW_CONFIDENCE_SOCIAL_IMAGE,
    ACTION_SWEEP_POLYMARKET_NO_CLOB,
    ACTION_SWEEP_POLYMARKET_YES_CLOB,
    CEX_IMPULSE_MAX_LATENCY_MS,
    FIREWALL_GATE_COUNT,
    GPU0_NANO_MAX_LATENCY_MS,
    GPU0_NANO_MODEL_NAME,
    GPU0_NANO_PORT,
    GPU1_VISION_MAX_LATENCY_MS,
    GPU1_VISION_MODEL_NAME,
    GPU1_VISION_PORT,
    HOURS_PER_YEAR,
    HUMAN_REACTION_ADVANTAGE_MAX_MULTIPLE,
    HUMAN_REACTION_ADVANTAGE_MIN_MULTIPLE,
    HUMAN_SCREENSHOT_REACTION_MAX_MS,
    HUMAN_SCREENSHOT_REACTION_MIN_MS,
    IPC_ACTION_RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER,
    MultimodalVisionAndPolymarketSniper,
    POLYMARKET_MAKER_QUOTE_LAG_MAX_MS,
    POLYMARKET_MAKER_QUOTE_LAG_MIN_MS,
    POLYMARKET_MIN_MAKER_STALENESS_MS,
    POLYMARKET_MIN_NET_EDGE_CENTS_PER_SHARE,
    SOLANA_BASE58_CA_MAX_LEN,
    SOLANA_BASE58_CA_MIN_LEN,
    SUPPORTED_CEX_SPOT_ASSETS,
    SUPPORTED_CEX_VENUES,
    TIER1_SOCIAL_ACCOUNTS,
    TITAN_MAX_DETECTION_TO_JITO_MS,
    VISION_SNIPE_MIN_CONFIDENCE,
    compute_black_scholes_digital_probability,
    evaluate_cex_to_polymarket_latency_arb,
    evaluate_multimodal_vision_social_snipe,
    extract_contracts_and_tickers_from_vision_text,
)


def test_multimodal_vision_constants_tier1_accounts_and_ocr_extraction() -> None:
    """Verifies GPU 1 Port 8002 Qwen3.8-27B Vision + GPU 0 Port 8006 Nano constants, Tier-1
    social accounts, and OCR regex extraction of Base58 Solana CAs (32-44 chars), EVM 0x CAs,
    and $TICKER symbols.
    """
    assert GPU1_VISION_PORT == 8002
    assert "Qwen3.8-27B" in GPU1_VISION_MODEL_NAME
    assert GPU1_VISION_MAX_LATENCY_MS == pytest.approx(250.0)

    assert GPU0_NANO_PORT == 8006
    assert "Nano" in GPU0_NANO_MODEL_NAME or "qwen2.5-3b" in GPU0_NANO_MODEL_NAME
    assert GPU0_NANO_MAX_LATENCY_MS == pytest.approx(15.0)
    assert TITAN_MAX_DETECTION_TO_JITO_MS == pytest.approx(300.0)

    assert HUMAN_SCREENSHOT_REACTION_MIN_MS == pytest.approx(8_000.0)
    assert HUMAN_SCREENSHOT_REACTION_MAX_MS == pytest.approx(25_000.0)
    assert HUMAN_REACTION_ADVANTAGE_MIN_MULTIPLE == pytest.approx(25.0)
    assert HUMAN_REACTION_ADVANTAGE_MAX_MULTIPLE == pytest.approx(80.0)

    expected_tier1 = {
        "ELON_MUSK",
        "OPENAI_OFFICIAL",
        "COINBASE_ASSETS",
        "BINANCE_ANNOUNCEMENTS",
        "TOLY_SOLANA",
        "VITALIK_BUTERIN",
        "TRUMP_TRUTH_X",
    }
    assert expected_tier1.issubset(set(TIER1_SOCIAL_ACCOUNTS))

    ocr_text = (
        "Screenshot from @elonmusk: $DOGEAI & $MARSx live! "
        "Solana CA: 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU "
        "Base EVM CA: 0x4200000000000000000000000000000000000006"
    )
    sol_cas, evm_cas, tickers = extract_contracts_and_tickers_from_vision_text(ocr_text)
    assert "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU" in sol_cas
    assert SOLANA_BASE58_CA_MIN_LEN <= len(sol_cas[0]) <= SOLANA_BASE58_CA_MAX_LEN
    assert "0x4200000000000000000000000000000000000006" in evm_cas
    assert "$DOGEAI" in tickers
    assert "$MARSX" in tickers


def test_multimodal_vision_social_snipe_fires_jito_bundle_with_25x_to_80x_human_advantage() -> None:
    """Verifies that a Tier-1 screenshot passing GPU 1 (<250ms), GPU 0 (<15ms), and all 6
    Contract Firewall gates emits `FIRE_MULTIMODAL_VISION_JITO_SNIPE` with confidence >= 0.85
    and `human_reaction_advantage_multiple` in the 25x-80x range.
    """
    res = evaluate_multimodal_vision_social_snipe(
        "ELON_MUSK",
        image_id="elon_cyber_screenshot",
        ocr_extracted_text=(
            "Official $OPTIMUS meme coin deployed! "
            "CA: DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        ),
        visual_meme_narrative="Optimus Robot Doge Viral Screenshot",
        vision_ocr_latency_ms=170.0,
        nano_classification_ms=8.5,
        jito_bundle_submission_ms=21.5,
        human_reaction_benchmark_ms=14_000.0,
        narrative_virality_score=0.96,
        spoof_phishing_probability=0.02,
        is_honeypot_ca=False,
        mint_authority_revoked=True,
        freeze_authority_revoked=True,
        lp_locked_or_canonical_curve=True,
        sell_tax_pct=0.0,
        top10_holder_concentration_pct=15.0,
        pool_liquidity_usd=90_000.0,
    )

    assert res.is_tier1_account is True
    assert res.gpu1_vision_port == 8002
    assert res.gpu0_nano_port == 8006
    assert res.vision_ocr_latency_ms < 250.0
    assert res.nano_classification_ms < 15.0
    assert res.total_detection_to_jito_ms == pytest.approx(200.0)
    assert res.total_detection_to_jito_ms < 300.0
    assert res.vision_latency_within_sla is True
    assert res.nano_latency_within_sla is True
    assert res.total_latency_within_sla is True

    # 14,000ms human / 200ms Titan = 70.0x advantage (within 25x-80x)
    assert res.human_reaction_advantage_multiple == pytest.approx(70.0)
    assert 25.0 <= res.human_reaction_advantage_multiple <= 80.0

    assert res.primary_contract_address == "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
    assert res.primary_chain == "SOLANA"
    assert res.primary_ticker == "$OPTIMUS"
    assert res.six_gate_firewall.gates_passed_count == FIREWALL_GATE_COUNT
    assert res.firewall_passed is True
    assert res.combined_snipe_confidence >= VISION_SNIPE_MIN_CONFIDENCE
    assert res.recommended_jito_snipe_sol > 0.0
    assert res.should_execute is True
    assert res.action == ACTION_FIRE_MULTIMODAL_VISION_JITO_SNIPE


def test_multimodal_vision_blocks_phishing_honeypot_and_skips_low_confidence() -> None:
    """Verifies that malicious honeypot/phishing screenshots trigger
    `BLOCK_PHISHING_SCREENSHOT_HONEYPOT` and low-virality/low-liquidity screenshots trigger
    `SKIP_LOW_CONFIDENCE_SOCIAL_IMAGE`.
    """
    honeypot_res = evaluate_multimodal_vision_social_snipe(
        "TRUMP_TRUTH_X",
        image_id="spoofed_honeypot_img",
        ocr_extracted_text="Buy $TRUMPFAKE at 8xHoneypotTrapAddress11111111111111111111111",
        spoof_phishing_probability=0.91,
        is_honeypot_ca=True,
        freeze_authority_revoked=False,
        sell_tax_pct=99.0,
    )
    assert honeypot_res.is_honeypot_or_phishing_ca is True
    assert honeypot_res.firewall_passed is False
    assert "GATE2_FREEZE_AUTHORITY_ACTIVE" in honeypot_res.six_gate_firewall.failed_gate_reasons
    assert "GATE4_EXCESSIVE_TRANSFER_OR_SELL_TAX" in honeypot_res.six_gate_firewall.failed_gate_reasons
    assert "GATE6_PHISHING_OR_HONEYPOT_DETECTED" in honeypot_res.six_gate_firewall.failed_gate_reasons
    assert honeypot_res.should_execute is False
    assert honeypot_res.recommended_jito_snipe_sol == pytest.approx(0.0)
    assert honeypot_res.action == ACTION_BLOCK_PHISHING_SCREENSHOT_HONEYPOT

    low_conf_res = evaluate_multimodal_vision_social_snipe(
        "UNKNOWN_USER_99",
        image_id="blurry_low_virality_img",
        ocr_extracted_text="Check out $LOWMEME 0x1111111111111111111111111111111111111111",
        narrative_virality_score=0.30,
        spoof_phishing_probability=0.05,
        is_honeypot_ca=False,
        pool_liquidity_usd=2_500.0,
    )
    assert low_conf_res.is_tier1_account is False
    assert low_conf_res.primary_chain == "EVM"
    assert low_conf_res.firewall_passed is False
    assert low_conf_res.combined_snipe_confidence < VISION_SNIPE_MIN_CONFIDENCE
    assert low_conf_res.should_execute is False
    assert low_conf_res.action == ACTION_SKIP_LOW_CONFIDENCE_SOCIAL_IMAGE


def test_black_scholes_digital_option_exact_formula_verification() -> None:
    """Verifies the exact Black-Scholes Digital Option / Log-Normal Terminal Probability formula:
        d_2 = [ln(S_t / K) + (mu - 0.5 * sigma^2) * tau] / (sigma * sqrt(tau))
        P_true(YES) = Phi(d_2) = 0.5 * [1 + erf(d_2 / sqrt(2))]
    against independent mathematical calculation.
    """
    s_t = 205.0
    k = 200.0
    sigma = 0.80
    tau = 0.5 / HOURS_PER_YEAR
    mu = 0.0

    expected_d2 = (math.log(s_t / k) + (mu - 0.5 * sigma ** 2) * tau) / (
        sigma * math.sqrt(tau)
    )
    expected_p_yes = 0.5 * (1.0 + math.erf(expected_d2 / math.sqrt(2.0)))
    expected_p_no = 1.0 - expected_p_yes

    d2, p_yes, p_no = compute_black_scholes_digital_probability(
        spot_price=s_t,
        strike_price=k,
        annualized_volatility=sigma,
        time_to_expiry_years=tau,
        drift_rate=mu,
    )

    assert d2 == pytest.approx(expected_d2, rel=1e-12)
    assert p_yes == pytest.approx(expected_p_yes, rel=1e-12)
    assert p_no == pytest.approx(expected_p_no, rel=1e-12)
    assert p_yes + p_no == pytest.approx(1.0, rel=1e-12)
    assert p_yes > 0.90  # Strong ITM probability with 30 minutes left

    with pytest.raises(ValueError):
        compute_black_scholes_digital_probability(0.0, 200.0, 0.8, tau)
    with pytest.raises(ValueError):
        compute_black_scholes_digital_probability(200.0, 0.0, 0.8, tau)
    with pytest.raises(ValueError):
        compute_black_scholes_digital_probability(200.0, 200.0, 0.0, tau)
    with pytest.raises(ValueError):
        compute_black_scholes_digital_probability(200.0, 200.0, 0.8, 0.0)


def test_cex_to_polymarket_latency_arb_sweeps_yes_and_no_clob_on_stale_maker_quotes() -> None:
    """Verifies CEX-to-Polymarket binary strike latency arbitrage across SOL, BTC, and ETH:
    - Triggers `SWEEP_POLYMARKET_YES_CLOB` on a bullish spot impulse when
      `net_edge_cents_per_share >= 8.0` and `maker_quote_staleness_ms >= 500.0`.
    - Triggers `SWEEP_POLYMARKET_NO_CLOB` on a bearish spot impulse when
      `net_edge_cents_per_share >= 8.0` and `maker_quote_staleness_ms >= 500.0`.
    - Holds when net edge < 8.0 cents/share or maker quote is not stale (< 500ms).
    """
    assert set(SUPPORTED_CEX_SPOT_ASSETS) == {"SOL", "BTC", "ETH"}
    assert set(SUPPORTED_CEX_VENUES) == {"BINANCE", "COINBASE", "BYBIT"}
    assert CEX_IMPULSE_MAX_LATENCY_MS == pytest.approx(100.0)
    assert POLYMARKET_MAKER_QUOTE_LAG_MIN_MS == pytest.approx(2_000.0)
    assert POLYMARKET_MAKER_QUOTE_LAG_MAX_MS == pytest.approx(8_000.0)
    assert POLYMARKET_MIN_MAKER_STALENESS_MS == pytest.approx(500.0)
    assert POLYMARKET_MIN_NET_EDGE_CENTS_PER_SHARE == pytest.approx(8.0)

    # 1. Bullish SOL impulse on Binance -> SWEEP_POLYMARKET_YES_CLOB
    yes_arb = evaluate_cex_to_polymarket_latency_arb(
        "SOL",
        cex_venue="BINANCE",
        contract_tenor="1H",
        pre_impulse_spot_price=198.50,
        spot_price=204.50,
        strike_price=200.00,
        annualized_volatility=0.80,
        time_to_expiry_hours=0.50,
        clob_yes_ask_price=0.55,
        clob_no_ask_price=0.47,
        maker_quote_staleness_ms=3_500.0,
        cex_impulse_latency_ms=35.0,
    )
    assert yes_arb.selected_side == "YES"
    assert yes_arb.p_true_yes > 0.90
    assert yes_arb.net_edge_cents_per_share >= 8.0
    assert yes_arb.expected_roi_pct > 50.0
    assert yes_arb.in_maker_quote_lag_window is True
    assert yes_arb.kelly_optimal_size_usd > 0.0
    assert yes_arb.recommended_shares_to_sweep > 0.0
    assert yes_arb.expected_net_profit_usd > 0.0
    assert yes_arb.should_execute is True
    assert yes_arb.action == ACTION_SWEEP_POLYMARKET_YES_CLOB

    # 2. Bearish ETH impulse on Bybit -> SWEEP_POLYMARKET_NO_CLOB
    no_arb = evaluate_cex_to_polymarket_latency_arb(
        "ETH",
        cex_venue="BYBIT",
        contract_tenor="4H",
        pre_impulse_spot_price=3_220.0,
        spot_price=3_120.0,
        strike_price=3_200.0,
        annualized_volatility=0.65,
        time_to_expiry_hours=0.75,
        clob_yes_ask_price=0.52,
        clob_no_ask_price=0.50,
        maker_quote_staleness_ms=4_200.0,
        cex_impulse_latency_ms=48.0,
    )
    assert no_arb.selected_side == "NO"
    assert no_arb.p_true_no > 0.90
    assert no_arb.net_edge_cents_per_share >= 8.0
    assert no_arb.expected_roi_pct > 50.0
    assert no_arb.kelly_optimal_size_usd > 0.0
    assert no_arb.should_execute is True
    assert no_arb.action == ACTION_SWEEP_POLYMARKET_NO_CLOB

    # 3. Efficiently priced / non-stale quote -> HOLD_POLYMARKET_NO_LATENCY_EDGE
    hold_arb = evaluate_cex_to_polymarket_latency_arb(
        "BTC",
        cex_venue="COINBASE",
        contract_tenor="1H",
        pre_impulse_spot_price=95_000.0,
        spot_price=95_050.0,
        strike_price=95_000.0,
        annualized_volatility=0.55,
        time_to_expiry_hours=2.0,
        clob_yes_ask_price=0.51,
        clob_no_ask_price=0.51,
        maker_quote_staleness_ms=250.0,  # Below 500ms staleness threshold
        cex_impulse_latency_ms=40.0,
    )
    assert hold_arb.net_edge_cents_per_share < 8.0
    assert hold_arb.should_execute is False
    assert hold_arb.action == ACTION_HOLD_POLYMARKET_NO_LATENCY_EDGE


def test_multimodal_vision_and_polymarket_sniper_facade_and_telemetry() -> None:
    """Verifies `MultimodalVisionAndPolymarketSniper` facade diagnostic and telemetry summary for
    `TitanIPCDaemon` (`RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER`).
    """
    engine = MultimodalVisionAndPolymarketSniper()
    diag = engine.run_full_vision_polymarket_diagnostic()

    assert diag["status"] == "OK"
    assert diag["ipc_action"] == IPC_ACTION_RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER
    assert diag["subsystem"] == "MULTIMODAL_VISION_AND_POLYMARKET_SNIPER_AGENT_28"
    assert diag["diagnostic_latency_ms"] >= 0.0

    assert (
        diag["vision_valid_jito_snipe"]["action"]
        == ACTION_FIRE_MULTIMODAL_VISION_JITO_SNIPE
    )
    assert (
        diag["vision_blocked_honeypot_screenshot"]["action"]
        == ACTION_BLOCK_PHISHING_SCREENSHOT_HONEYPOT
    )
    assert (
        diag["polymarket_yes_clob_sweep"]["action"]
        == ACTION_SWEEP_POLYMARKET_YES_CLOB
    )
    assert (
        diag["polymarket_no_clob_sweep"]["action"]
        == ACTION_SWEEP_POLYMARKET_NO_CLOB
    )

    telemetry = engine.get_telemetry_summary()
    assert telemetry["engine"] == "MultimodalVisionAndPolymarketSniper"
    assert telemetry["agent_id"] == "multimodal-vision-polymarket-sniper"
    assert telemetry["agent_number"] == 28
    assert telemetry["ipc_action"] == IPC_ACTION_RUN_MULTIMODAL_VISION_POLYMARKET_SNIPER
    assert telemetry["vision_evaluations"] == 2
    assert telemetry["vision_jito_snipes_fired"] == 1
    assert telemetry["vision_phishing_honeypots_blocked"] == 1
    assert telemetry["polymarket_evaluations"] == 2
    assert telemetry["polymarket_yes_sweeps_triggered"] == 1
    assert telemetry["polymarket_no_sweeps_triggered"] == 1
    assert telemetry["cumulative_expected_polymarket_profit_usd"] > 0.0
    assert telemetry["benchmarks"]["gpu1_vision_port"] == 8002
    assert telemetry["benchmarks"]["gpu0_nano_port"] == 8006
    assert telemetry["last_diagnostic_ts"] is not None
