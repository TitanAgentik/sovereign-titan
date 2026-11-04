"""
Comprehensive Automated Pytest Suite for On-Chain Graph Forensics & Runner Profiler
(Steps 1.1, 1.2, 1.3, 1.4, and Cluster Threshold Calibration CLI).
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

# Ensure both project root and packages/forensics-py are importable
_THIS_DIR = Path(__file__).resolve().parent
_FORENSICS_DIR = _THIS_DIR.parent
_PROJECT_ROOT = _FORENSICS_DIR.parent.parent
for _p in (str(_PROJECT_ROOT), str(_FORENSICS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from packages.calibration.cli import (
    main as calibration_cli_main,
    run_calibration_grid,
)
from packages.forensics_py.ping_trap_and_cluster_trigger import (
    ATOMIC_JITO_EXIT_BEFORE_PHASE1_COLLAPSE,
    CLUSTER_CONFLUENCE_SNIPE_SIGNAL,
    HOLD_POSITION_HEALTHY_FLOW,
    NO_CONFLUENCE_WAIT_SIGNAL,
    OrderFlowTick,
    RootFunderSeedEvent,
    ShadowWalletPurchaseEvent,
    build_zero_risk_recon_ping_trap,
    compute_1m_order_flow_imbalance,
    compute_vpin,
    evaluate_multi_wallet_cluster_trigger,
    evaluate_ofi_vpin_and_exit_tripwires,
)
from packages.forensics_py.runner_classifier import (
    ABORT_SNIPE_PARASITIC_CABAL,
    BayesianConfluenceResult,
    CabalHunterMcpClient,
    HistoricalLaunchRecord,
    PARASITIC_RUG_CABAL,
    SERIAL_RUNNER_SYNDICATE,
    SNIPE_WITH_CLUSTER_EXIT_TRIPWIRES,
    X402PaymentCapExceededError,
    classify_cluster_archetype,
    compute_bayesian_confluence_score,
    index_and_score_cluster_launches,
)
from packages.forensics_py.shadow_cluster_resolver import (
    CANONICAL_ZERO_DEV_CASE_STUDIES,
    EarlyBuyerRecord,
    FundingTransferEdge,
    HELIUS_BATCH_IDENTITY_MAX_ADDRS,
    HELIUS_LABELED_ENTITIES_COUNT,
    TokenLaunchTransaction,
    batch_resolve_helius_identities,
    build_forensic_digraph,
    detect_cex_deposit_sink_clusters,
    detect_early_block_sniper_bot,
    detect_slot0_bundle_bot,
    detect_wash_trading_wt1_wt2,
    resolve_persistent_cluster_id,
    resolve_zero_dev_shadow_cluster,
)


def test_step_1_1_helius_batch_identity_whitelister_and_batch_chunking() -> None:
    """Verifies Helius batch identity resolution (<=100 per batch, .sol/.bonk domains, CEX boundary tagging)."""
    binance_hot = "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9"
    coinbase_hot = "H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS"
    wintermute_mm = "WintermuteMM1111111111111111111111111111111"
    pumpfun_vault = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

    # Generate 135 addresses (including .sol / .bonk domains) to verify >100 multi-batch chunking
    synthetic_wallets = [f"ShadowUserWallet_{i:03d}" for i in range(125)]
    domains = ["funderblue.sol", "binance-treasury.sol", "cabalalpha.bonk"]
    all_inputs = [binance_hot, coinbase_hot, wintermute_mm, pumpfun_vault] + domains + synthetic_wallets

    resolved = batch_resolve_helius_identities(all_inputs)
    assert len(resolved) == len(all_inputs)
    assert resolved[binance_hot]["is_terminal_boundary"] is True
    assert resolved[binance_hot]["category"] == "CEX_HOT_WALLET"
    assert resolved[binance_hot]["labeled_database_size"] == HELIUS_LABELED_ENTITIES_COUNT
    assert resolved[coinbase_hot]["is_terminal_boundary"] is True
    assert resolved[wintermute_mm]["is_terminal_boundary"] is True
    assert resolved[wintermute_mm]["category"] == "INSTITUTIONAL_MM"
    assert resolved[pumpfun_vault]["is_terminal_boundary"] is True
    assert resolved[pumpfun_vault]["category"] == "PUBLIC_DEFI_VAULT"

    # Domain checks
    assert resolved["funderblue.sol"]["is_terminal_boundary"] is False
    assert resolved["binance-treasury.sol"]["is_terminal_boundary"] is True
    assert resolved["cabalalpha.bonk"]["is_terminal_boundary"] is False

    # Batch chunking check: first 100 are batch_index 0, remaining 32 are batch_index 1
    assert resolved[binance_hot]["batch_index"] == 0
    assert resolved[binance_hot]["batch_size"] == HELIUS_BATCH_IDENTITY_MAX_ADDRS
    assert resolved[synthetic_wallets[-1]]["batch_index"] == 1
    assert resolved[synthetic_wallets[-1]]["batch_size"] == len(all_inputs) - HELIUS_BATCH_IDENTITY_MAX_ADDRS


def test_step_1_1_zero_dev_shadow_cluster_resolver_baton_and_rl_models() -> None:
    """
    Verifies Zero-Percent Developer Illusion detection:
      - Models BATON (0% dev holding, 16.0% shadow cluster across 3-hop funding from funderblue)
      - Models $RL (0% dev holding, 95.65% total supply locked across fragmented shadow wallets)
      - Verifies Binance/Coinbase CEX hot wallets are pruned so retail exchange users are NOT conflated.
    """
    assert CANONICAL_ZERO_DEV_CASE_STUDIES["BATON"]["shadow_cluster_supply_pct"] == 16.0
    assert CANONICAL_ZERO_DEV_CASE_STUDIES["$RL"]["shadow_cluster_supply_pct"] == 95.65

    root_funder = "FunderBlueRootTreasury111111111111111111111"
    hop1_relay = "Hop1RelayWallet1111111111111111111111111111"
    hop2_relay = "Hop2RelayWallet1111111111111111111111111111"
    deployer_wc = "BatonZeroDevDeployer11111111111111111111111"
    binance_hot = "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9"

    # 3-hop backward path from deployer_wc -> hop2 -> hop1 -> root_funder
    # Plus forward dispersion from root_funder -> 4 shadow wallets controlling 4.0% each (16.0% total)
    # Plus 2 innocent retail buyers funded by Binance Hot Wallet (must be pruned!)
    shadow_buyers = [f"BatonShadowBuyer_{i}" for i in range(4)]
    retail_buyers = ["InnocentBinanceUser_1", "InnocentBinanceUser_2"]

    edges = [
        FundingTransferEdge(source=root_funder, target=hop1_relay, amount_sol=50.0, timestamp=100.0),
        FundingTransferEdge(source=hop1_relay, target=hop2_relay, amount_sol=25.0, timestamp=110.0),
        FundingTransferEdge(source=hop2_relay, target=deployer_wc, amount_sol=5.0, timestamp=120.0),
        # Binance also sent SOL to root_funder earlier, which must be pruned as terminal boundary
        FundingTransferEdge(source=binance_hot, target=root_funder, amount_sol=200.0, timestamp=50.0),
        # Innocent retail buyers withdrawing from Binance
        FundingTransferEdge(source=binance_hot, target=retail_buyers[0], amount_sol=10.0, timestamp=90.0),
        FundingTransferEdge(source=binance_hot, target=retail_buyers[1], amount_sol=12.0, timestamp=95.0),
    ]
    for idx, sb in enumerate(shadow_buyers):
        edges.append(
            FundingTransferEdge(
                source=hop1_relay,
                target=sb,
                amount_sol=4.5,
                timestamp=125.0 + idx,
            )
        )

    early_buyers = [
        EarlyBuyerRecord(wallet=sb, supply_pct=4.0, buy_sol=4.0, rank=idx + 1)
        for idx, sb in enumerate(shadow_buyers)
    ] + [
        EarlyBuyerRecord(wallet=retail_buyers[0], supply_pct=5.0, buy_sol=5.0, rank=5),
        EarlyBuyerRecord(wallet=retail_buyers[1], supply_pct=6.0, buy_sol=6.0, rank=6),
    ]

    baton_res = resolve_zero_dev_shadow_cluster(
        token_mint="BatonMint1111111111111111111111111111111111",
        deployer_wallet=deployer_wc,
        funding_edges=edges,
        early_buyers=early_buyers,
        deployer_supply_pct=0.0,
        max_hops=5,
    )

    assert baton_res.zero_dev_illusion_detected is True
    assert baton_res.deployer_supply_pct == 0.0
    assert baton_res.root_funder_wallet == root_funder
    assert baton_res.root_funder_alias == "funderblue"
    assert baton_res.hop_distance_to_deployer == 3
    assert baton_res.shadow_cluster_supply_pct == pytest.approx(16.0)
    assert set(baton_res.shadow_cluster_wallets) == set(shadow_buyers)
    # Innocent Binance users must NOT be conflated into the shadow cluster
    assert retail_buyers[0] not in baton_res.shadow_cluster_wallets
    assert retail_buyers[1] not in baton_res.shadow_cluster_wallets
    assert binance_hot in baton_res.terminal_boundary_nodes_pruned

    # Now test $RL model: 0% dev holding, 95.65% supply locked across 23 fragmented shadow wallets
    rl_deployer = "RLZeroDevDeployer11111111111111111111111111"
    rl_shadows = [f"RLFragmentedShadow_{i:02d}" for i in range(23)]
    rl_edges = [
        FundingTransferEdge(source=root_funder, target=rl_deployer, amount_sol=2.0, timestamp=200.0)
    ] + [
        FundingTransferEdge(source=root_funder, target=w, amount_sol=3.8, timestamp=201.0 + i)
        for i, w in enumerate(rl_shadows)
    ]
    rl_buyers = [
        EarlyBuyerRecord(wallet=w, supply_pct=round(95.65 / 23.0, 6), buy_sol=3.5, rank=i + 1)
        for i, w in enumerate(rl_shadows)
    ]

    rl_res = resolve_zero_dev_shadow_cluster(
        token_mint="RLMint1111111111111111111111111111111111111",
        deployer_wallet=rl_deployer,
        funding_edges=rl_edges,
        early_buyers=rl_buyers,
        deployer_supply_pct=0.0,
        max_hops=5,
    )
    assert rl_res.zero_dev_illusion_detected is True
    assert rl_res.shadow_cluster_supply_pct == pytest.approx(95.65, abs=0.01)
    assert rl_res.illusion_archetype == "RL_STYLE_TOTAL_SUPPLY_LOCK_95PCT"


def test_step_1_2_algorithms_1_2_wash_detectors_sink_and_louvain_clustering() -> None:
    """
    Verifies Step 1.2:
      - Directed DiGraph G = (V, E) with edges e_ij = (v_i, v_j, w, t)
      - Algorithm 1 (`detect_slot0_bundle_bot`) + bundle_supply_pct > 10.0 rug flag
      - Algorithm 2 (`detect_early_block_sniper_bot`, K = 5 blocks)
      - WT1 Smart-Contract Atomic Wash Trading & WT2 High-Frequency Bump Botting
      - CEX Deposit Address Sink Clustering + Louvain Community Detection + 15-30 wallet co-holding scan
    """
    mint = "Step12ForensicMint1111111111111111111111111"
    deployer_wc = "CreatorWalletWc1111111111111111111111111111"
    b_launch = 310_000_000

    launch_txs = [
        # Creator initial buy in Slot 0 (should NOT trigger bundle bot by itself)
        TokenLaunchTransaction(
            tx_signature="sig_creator_slot0",
            trader=deployer_wc,
            tx_type="buy",
            block=b_launch,
            amount_sol=1.5,
            supply_pct_acquired=2.0,
        ),
        # Non-creator Slot 0 bundle buys totaling 34.5% supply (> 10.0% rug indicator)
        TokenLaunchTransaction(
            tx_signature="sig_bundle_1",
            trader="BundleShadow_1",
            tx_type="buy",
            block=b_launch,
            amount_sol=12.0,
            supply_pct_acquired=18.5,
        ),
        TokenLaunchTransaction(
            tx_signature="sig_bundle_2",
            trader="BundleShadow_2",
            tx_type="buy",
            block=b_launch,
            amount_sol=10.0,
            supply_pct_acquired=16.0,
        ),
        # Early block sniper buys at b_launch + 2 and b_launch + 5 (within K=5)
        TokenLaunchTransaction(
            tx_signature="sig_sniper_b2",
            trader="SniperBot_A",
            tx_type="buy",
            block=b_launch + 2,
            amount_sol=5.0,
            supply_pct_acquired=6.5,
        ),
        TokenLaunchTransaction(
            tx_signature="sig_sniper_b5",
            trader="SniperBot_B",
            tx_type="buy",
            block=b_launch + 5,
            amount_sol=4.0,
            supply_pct_acquired=5.0,
        ),
        # Later organic buy at b_launch + 6 (outside K=5 window)
        TokenLaunchTransaction(
            tx_signature="sig_organic_b6",
            trader="RetailBuyer_Late",
            tx_type="buy",
            block=b_launch + 6,
            amount_sol=1.0,
            supply_pct_acquired=1.0,
        ),
        # WT1 Atomic wash trade: same signer executing buy + sell inside one atomic transaction
        TokenLaunchTransaction(
            tx_signature="sig_wt1_atomic_wash",
            trader="WashBotSigner_1",
            tx_type="buy",
            block=b_launch + 8,
            amount_sol=2.0,
            instructions=["pumpfun:buy", "pumpfun:sell"],
        ),
    ]
    # Add 10 micro bump-bot transactions (0.01 SOL each -> 10 txs / 0.10 SOL = 100 txs/SOL ratio)
    for i in range(10):
        launch_txs.append(
            TokenLaunchTransaction(
                tx_signature=f"sig_wt2_bump_{i}",
                trader="BumpBotMicroWallet",
                tx_type="buy",
                block=b_launch + 10 + i,
                amount_sol=0.01,
            )
        )

    # Algorithm 1 verification
    alg1 = detect_slot0_bundle_bot(
        token_mint=mint,
        deployer_wallet=deployer_wc,
        launch_block=b_launch,
        transactions=launch_txs,
    )
    assert alg1.indicator == 1
    assert alg1.is_bundle_bot is True
    assert alg1.bundled_wallets == ["BundleShadow_1", "BundleShadow_2"]
    assert alg1.bundle_supply_pct == pytest.approx(34.5)
    assert alg1.is_primary_single_block_rug_indicator is True

    # Verify Algorithm 1 returns 0 if only creator buys at b_launch
    alg1_creator_only = detect_slot0_bundle_bot(
        token_mint=mint,
        deployer_wallet=deployer_wc,
        launch_block=b_launch,
        transactions=[launch_txs[0]],
    )
    assert alg1_creator_only.indicator == 0
    assert alg1_creator_only.is_bundle_bot is False

    # Algorithm 2 verification (K = 5 blocks)
    alg2 = detect_early_block_sniper_bot(
        token_mint=mint,
        deployer_wallet=deployer_wc,
        launch_block=b_launch,
        transactions=launch_txs,
        k_blocks=5,
    )
    assert alg2.indicator == 1
    assert alg2.is_sniper_bot is True
    assert alg2.sniper_wallets == ["SniperBot_A", "SniperBot_B"]
    assert "RetailBuyer_Late" not in alg2.sniper_wallets
    assert alg2.sniper_supply_pct == pytest.approx(11.5)

    # WT1 & WT2 verification
    wash_res = detect_wash_trading_wt1_wt2(
        token_mint=mint,
        transactions=launch_txs,
    )
    assert wash_res.wt1_atomic_wash_detected is True
    assert "sig_wt1_atomic_wash" in wash_res.wt1_offending_txs
    assert "WashBotSigner_1" in wash_res.wt1_wash_signers
    assert wash_res.wt2_bump_bot_detected is True
    assert "BumpBotMicroWallet" in wash_res.wt2_bump_bot_wallets

    # CEX Deposit Sink Clustering + Louvain Community Detection + 20-wallet cross-token co-holding scan
    syndicate_wallets = [f"SyndicateRecurringWallet_{i:02d}" for i in range(20)]
    shared_cex_deposit_sink = "UserDedicatedBinanceDepositSubAccount_99"
    funding_edges = [
        FundingTransferEdge(
            source=deployer_wc,
            target=syndicate_wallets[i],
            amount_sol=3.0,
            timestamp=1_700_000_000.0 + i,
        )
        for i in range(5)
    ]
    post_sell_sweeps = [
        FundingTransferEdge(
            source=syndicate_wallets[i],
            target=shared_cex_deposit_sink,
            amount_sol=14.5,
            timestamp=1_700_000_600.0 + i,
        )
        for i in range(4)
    ]
    historical_holders = {
        "PrevLaunch_1": syndicate_wallets,
        "PrevLaunch_2": syndicate_wallets[:18],
        "PrevLaunch_3": syndicate_wallets[:16],
    }

    digraph = build_forensic_digraph(funding_edges=funding_edges, deployer_wallet=deployer_wc)
    assert digraph.number_of_edges() == 5
    for _u, _v, edge_data in digraph.edges(data=True):
        assert "w" in edge_data and "t" in edge_data

    sink_map = detect_cex_deposit_sink_clusters(post_sell_transfers=post_sell_sweeps)
    assert shared_cex_deposit_sink in sink_map
    assert len(sink_map[shared_cex_deposit_sink]) == 4

    cluster_res = resolve_persistent_cluster_id(
        token_mint=mint,
        funding_edges=funding_edges,
        post_sell_transfers=post_sell_sweeps,
        historical_token_holders=historical_holders,
        deployer_wallet=deployer_wc,
    )
    assert cluster_res.cluster_id.startswith("cluster_")
    assert cluster_res.coholding_wallet_count == 18
    assert cluster_res.is_recurring_syndicate_15_30 is True
    assert len(cluster_res.louvain_communities) >= 1


def test_step_1_3_serial_runner_classifier_and_cabal_hunter_x402_client() -> None:
    """
    Verifies Step 1.3:
      - Indexing 85 SOL (~$69k MCap) Pump.fun graduations
      - Classifying SERIAL_RUNNER_SYNDICATE vs PARASITIC_RUG_CABAL
      - CabalHunterMcpClient (`check_cabal_risk` & `scan_cabal_x402` with 0.01 USDC x402 headers & <100ms latency)
      - Decision override: ABORT_SNIPE_PARASITIC_CABAL vs SNIPE_WITH_CLUSTER_EXIT_TRIPWIRES
    """
    runner_launches = [
        HistoricalLaunchRecord(
            token_mint=f"RunnerGradMint_{i}",
            peak_bonding_curve_sol=92.0 if i < 3 else 45.0,  # 3 of 6 graduate (50% > 25%)
            hold_duration_minutes=28.5,
            realized_roi_multiple=3.2 if i < 4 else 0.8,  # 4 of 6 win (66.67% in [60, 85]), median ROI > 2.0x
            net_pnl_sol=18.0 if i < 4 else -2.0,
            single_block_bundle_dump_pct=0.0,
            trades_count=5,
        )
        for i in range(6)
    ]

    runner_profile = index_and_score_cluster_launches(
        cluster_id="cluster_serial_runner_01",
        launches=runner_launches,
        observation_days=7.0,
    )
    assert runner_profile.classification == SERIAL_RUNNER_SYNDICATE
    assert runner_profile.is_serial_runner_syndicate is True
    assert runner_profile.graduation_rate_pct == pytest.approx(50.0)
    assert runner_profile.avg_hold_duration_minutes > 10.0
    assert 60.0 <= runner_profile.win_rate_pct <= 85.0
    assert runner_profile.median_roi_multiple >= 2.0
    assert runner_profile.daily_trades_count >= 3.0
    assert runner_profile.risk_score < 60.0

    # Parasitic rug cabal profile: <=1% graduation, <2 min hold, 85% single-block bundle dump
    parasitic_profile = classify_cluster_archetype(
        cluster_id="cluster_parasitic_cabal_99",
        total_launches=40,
        graduation_rate_pct=0.5,
        avg_hold_duration_minutes=1.2,
        win_rate_pct=95.0,
        median_roi_multiple=1.15,
        daily_trades_count=12.0,
        risk_score=92.0,
    )
    assert parasitic_profile.classification == PARASITIC_RUG_CABAL
    assert parasitic_profile.is_parasitic_rug_cabal is True

    # Test CabalHunterMcpClient & x402 payment headers
    mcp_client = CabalHunterMcpClient(
        whitelisted_runner_clusters={"cluster_serial_runner_01": runner_profile}
    )

    parasitic_scan = mcp_client.check_cabal_risk(
        token_mint="ParasiticRugMint111111111111111111111111111",
        cluster_id="cluster_parasitic_cabal_99",
        cabal_score=84.0,
        is_controlled=True,
        evidence_txs=["tx_rug_bundle_1", "tx_rug_bundle_2"],
        funding_tx="tx_funder_parasitic",
    )
    assert parasitic_scan.latency_ms < 100.0
    parasitic_decision = mcp_client.evaluate_snipe_decision(parasitic_scan, parasitic_profile)
    assert parasitic_decision.action == ABORT_SNIPE_PARASITIC_CABAL
    assert parasitic_decision.should_snipe is False

    # Now scan a verified SERIAL_RUNNER_SYNDICATE token via x402 (0.01 USDC)
    runner_shadow_wallets = ["RunnerShadow_W1", "RunnerShadow_W2", "RunnerShadow_W3"]
    runner_scan = mcp_client.scan_cabal_x402(
        token_mint="SerialRunnerGemMint111111111111111111111111",
        payment_amount_usdc=0.01,
        cluster_id="cluster_serial_runner_01",
        cabal_score=76.0,
        is_controlled=True,
        evidence_txs=["tx_runner_accum_1", "tx_runner_accum_2"],
        funding_tx="tx_funderblue_seed",
        shadow_wallets=runner_shadow_wallets,
    )
    assert runner_scan.latency_ms < 100.0
    assert runner_scan.x402_payment_usdc == pytest.approx(0.01)
    assert runner_scan.x402_payment_headers["X-402-Payment-Amount"] == "0.010000"
    assert "solana-usdc:" in runner_scan.x402_payment_headers["X-Payment-402"]

    runner_decision = mcp_client.evaluate_snipe_decision(runner_scan)
    assert runner_decision.action == SNIPE_WITH_CLUSTER_EXIT_TRIPWIRES
    assert runner_decision.should_snipe is True
    assert runner_decision.override_avoidance_applied is True
    assert runner_decision.tripwire_armed is True
    assert runner_decision.exit_tripwire_wallets == runner_shadow_wallets
    assert "tx_runner_accum_1" in runner_decision.exit_tripwire_evidence_txs
    assert "tx_funderblue_seed" in runner_decision.exit_tripwire_evidence_txs

    # Guardrail verification: x402 payment > 0.01 USDC raises X402PaymentCapExceededError
    with pytest.raises(X402PaymentCapExceededError):
        mcp_client.scan_cabal_x402(
            token_mint="OverCapMint",
            payment_amount_usdc=0.05,
        )


def test_step_1_4_cluster_trigger_recon_ping_trap_and_ofi_vpin_gatekeeper() -> None:
    """
    Verifies Step 1.4:
      - Multi-wallet cluster confluence trigger (M >= 3 wallets with S >= 6.0 within <= 15.0s,
        plus whitelisted root funder seeding fresh deployer)
      - `build_zero_risk_recon_ping_trap` (< 0.000001 slippage, guaranteed_onchain_revert == True, capital_at_risk_sol == 0.0)
      - 1-minute OFI & VPIN calculation + shadow-cluster outbound transfer tripwires triggering atomic exit
    """
    mint = "ConfluenceRunnerMint11111111111111111111111"
    events = [
        ShadowWalletPurchaseEvent(
            wallet="RunnerShadow_W1",
            token_mint=mint,
            timestamp=100.0,
            wallet_score=7.4,
            cluster_id="cluster_serial_runner_01",
        ),
        ShadowWalletPurchaseEvent(
            wallet="RunnerShadow_W2",
            token_mint=mint,
            timestamp=106.5,
            wallet_score=6.8,
            cluster_id="cluster_serial_runner_01",
        ),
        ShadowWalletPurchaseEvent(
            wallet="RunnerShadow_W3",
            token_mint=mint,
            timestamp=113.2,
            wallet_score=8.1,
            cluster_id="cluster_serial_runner_01",
        ),
    ]
    trig = evaluate_multi_wallet_cluster_trigger(
        purchase_events=events,
        token_mint=mint,
        min_wallets=3,
        window_seconds=15.0,
        min_wallet_score=6.0,
    )
    assert trig.triggered is True
    assert trig.signal == CLUSTER_CONFLUENCE_SNIPE_SIGNAL
    assert trig.qualifying_wallet_count == 3
    assert trig.window_span_seconds == pytest.approx(13.2)

    # Also test root funder seeding a fresh deployer address
    seed_trig = evaluate_multi_wallet_cluster_trigger(
        purchase_events=[],
        root_seed_event=RootFunderSeedEvent(
            root_funder_wallet="FunderBlueRoot111",
            fresh_deployer_wallet="FreshDeployerWc222",
            amount_sol=5.0,
            timestamp=200.0,
            cluster_id="cluster_serial_runner_01",
            is_whitelisted_runner_root=True,
        ),
    )
    assert seed_trig.triggered is True
    assert seed_trig.signal == CLUSTER_CONFLUENCE_SNIPE_SIGNAL
    assert seed_trig.seeded_fresh_deployer == "FreshDeployerWc222"

    # Recon Ping Trap verification
    trap = build_zero_risk_recon_ping_trap(
        target_wallet="RunnerShadow_W1",
        token_mint=mint,
        max_slippage=0.0000005,
    )
    assert trap.guaranteed_onchain_revert is True
    assert trap["guaranteed_onchain_revert"] is True
    assert trap.capital_at_risk_sol == 0.0
    assert trap["capital_at_risk_sol"] == 0.0
    assert trap.max_slippage < 0.000001
    assert trap.rpc_execution_alert_armed is True

    with pytest.raises(ValueError):
        build_zero_risk_recon_ping_trap(
            target_wallet="RunnerShadow_W1",
            token_mint=mint,
            max_slippage=0.000001,  # Must be strictly < 0.000001
        )

    # Healthy order flow -> HOLD_POSITION_HEALTHY_FLOW
    healthy_ticks = [
        OrderFlowTick(timestamp=100.0 + i, side="buy", volume_sol=8.0, signer=f"Retail_{i}")
        for i in range(6)
    ] + [
        OrderFlowTick(timestamp=108.0, side="sell", volume_sol=4.0, signer="Retail_X")
    ]
    healthy_gate = evaluate_ofi_vpin_and_exit_tripwires(
        token_mint=mint,
        ticks=healthy_ticks,
        watched_shadow_wallets=["RunnerShadow_W1", "RunnerShadow_W2"],
    )
    assert healthy_gate.trigger_atomic_exit is False
    assert healthy_gate.action == HOLD_POSITION_HEALTHY_FLOW
    assert healthy_gate.ofi_1m_normalized > 0.0

    # Toxic order flow + shadow cluster outbound SPL transfer tripwire -> ATOMIC_JITO_EXIT_BEFORE_PHASE1_COLLAPSE
    toxic_ticks = [
        OrderFlowTick(timestamp=200.0, side="buy", volume_sol=2.0, signer="Retail_Late"),
        OrderFlowTick(timestamp=205.0, side="sell", volume_sol=25.0, signer="WhaleSeller_1"),
        OrderFlowTick(timestamp=210.0, side="sell", volume_sol=30.0, signer="WhaleSeller_2"),
        OrderFlowTick(
            timestamp=212.0,
            side="sell",
            volume_sol=15.0,
            signer="RunnerShadow_W1",
            tx_type="spl_transfer",
            recipient="FreshUnindexedDumpStagingWallet",
            tx_signature="sig_shadow_outbound_spl_stage",
        ),
    ]
    ofi_raw, ofi_norm = compute_1m_order_flow_imbalance(toxic_ticks)
    vpin_val = compute_vpin(toxic_ticks, bucket_volume_sol=10.0)
    assert ofi_raw < 0.0
    assert ofi_norm < -0.35
    assert vpin_val > 0.70

    exit_gate = evaluate_ofi_vpin_and_exit_tripwires(
        token_mint=mint,
        ticks=toxic_ticks,
        watched_shadow_wallets=["RunnerShadow_W1", "RunnerShadow_W2"],
    )
    assert exit_gate.trigger_atomic_exit is True
    assert exit_gate.action == ATOMIC_JITO_EXIT_BEFORE_PHASE1_COLLAPSE
    assert exit_gate.toxic_order_flow_detected is True
    assert exit_gate.shadow_cluster_outbound_transfer_detected is True
    assert "RunnerShadow_W1" in exit_gate.tripped_shadow_wallets
    assert exit_gate.external_market_phase1_collapse_avoided_pct == pytest.approx(80.0)


def test_step_5_calibration_cli_grid_search(capsys: pytest.CaptureFixture[str]) -> None:
    """
    Verifies `python -m packages.calibration.cli calibrate --min-wallets 3,4,5 --window 5,15,30`
    evaluates all 9 grid points and selects optimal parameters (M=3, window=15s, score>=6.0).
    """
    suite = calibration_cli_main(
        ["calibrate", "--min-wallets", "3,4,5", "--window", "5,15,30"]
    )
    captured = capsys.readouterr().out

    assert len(suite.grid_results) == 9
    assert suite.optimal_min_wallets == 3
    assert suite.optimal_window_seconds == 15
    assert suite.optimal_min_wallet_score == pytest.approx(6.0)
    assert suite.sqlite_rows_persisted == 9
    assert "M=3, window=15s, score>=6.0" in suite.optimal_label
    assert "M=3, window=15s, score>=6.0" in captured


def test_bayesian_confluence_and_forensics_hardening_invariants() -> None:
    """
    Verifies:
      1. `compute_bayesian_confluence_score` produces calibrated log-odds Bayesian posterior + quarter-Kelly size.
      2. `scan_cabal_x402` populates `x402_payment_headers` even after a prior `check_cabal_risk` cache warm.
      3. `resolve_zero_dev_shadow_cluster` ignores <0.1 SOL dust predecessors when resolving the root funder.
      4. `resolve_persistent_cluster_id` caps co-holder graph density via hub-and-ring for >30 wallets.
      5. `evaluate_multi_wallet_cluster_trigger` does not conflate distinct token mints when `token_mint=""`.
    """
    # 1. Bayesian confluence score
    confluence: BayesianConfluenceResult = compute_bayesian_confluence_score(
        token_mint="RunnerConfluenceMint111111111111111111111111",
        cluster_id="cluster_serial_runner_01",
        graduation_rate_pct=62.5,
        is_serial_runner_syndicate=True,
        qualifying_wallet_count=4,
        window_span_seconds=8.5,
        avg_wallet_score=7.6,
        shadow_cluster_supply_pct=15.0,
        ofi_1m_normalized=0.45,
        vpin_score=0.22,
    )
    assert confluence.posterior_win_probability > 0.65
    assert confluence.should_execute_snipe is True
    assert confluence.fractional_kelly_scalar > 0.0
    assert confluence.confidence_tier in ("HIGH_CONVICTION_SLOT0_SNIPE", "MODERATE_CONFLUENCE_SNIPE")

    parasitic_confluence = compute_bayesian_confluence_score(
        token_mint="ParasiticMint1111111111111111111111111111111",
        cluster_id="cluster_parasitic_cabal_99",
        graduation_rate_pct=0.5,
        is_serial_runner_syndicate=False,
        qualifying_wallet_count=1,
        avg_wallet_score=3.0,
        shadow_cluster_supply_pct=85.0,
        wt1_atomic_wash_detected=True,
        ofi_1m_normalized=-0.55,
        vpin_score=0.82,
    )
    assert parasitic_confluence.posterior_win_probability < 0.25
    assert parasitic_confluence.should_execute_snipe is False
    assert parasitic_confluence.fractional_kelly_scalar == 0.0
    assert parasitic_confluence.confidence_tier == "REJECT_INSUFFICIENT_BAYESIAN_EDGE"

    # 2. x402 payment header preservation after prior check_cabal_risk cache hit
    client = CabalHunterMcpClient()
    mint_cached = "CachedMintX402Test1111111111111111111111111"
    pre_scan = client.check_cabal_risk(token_mint=mint_cached, cluster_id="cluster_x", cabal_score=40.0)
    assert pre_scan.x402_payment_headers == {}
    x402_scan = client.scan_cabal_x402(token_mint=mint_cached, payment_amount_usdc=0.01)
    assert x402_scan.cached_hit is True
    assert x402_scan.x402_payment_headers.get("X-402-Payment-Amount") == "0.010000"

    # 3. Dust predecessor immunity in resolve_zero_dev_shadow_cluster
    dust_edges = [
        FundingTransferEdge("DustAttacker111", "RealRootFunder999", 0.001, 50.0, "tx_dust"),
        FundingTransferEdge("RealRootFunder999", "FreshDeployer001", 2.5, 90.0, "tx_seed_dep"),
        FundingTransferEdge("RealRootFunder999", "ShadowBuyer_A", 5.0, 91.0, "tx_seed_a"),
        FundingTransferEdge("RealRootFunder999", "ShadowBuyer_B", 5.0, 92.0, "tx_seed_b"),
        FundingTransferEdge("RealRootFunder999", "ShadowBuyer_C", 5.0, 93.0, "tx_seed_c"),
    ]
    buyers = [
        EarlyBuyerRecord("ShadowBuyer_A", 2.0, 4.5, 100, 100.0, "tx_buy_a"),
        EarlyBuyerRecord("ShadowBuyer_B", 2.0, 4.2, 100, 101.0, "tx_buy_b"),
        EarlyBuyerRecord("ShadowBuyer_C", 2.0, 4.1, 101, 102.0, "tx_buy_c"),
    ]
    res = resolve_zero_dev_shadow_cluster(
        token_mint="DustImmunityMint111111111111111111111111111",
        deployer_wallet="FreshDeployer001",
        deployer_supply_pct=0.0,
        early_buyers=buyers,
        funding_edges=dust_edges,
    )
    assert res.root_funder_wallet == "RealRootFunder999"

    # 4. >30 co-holding wallets hub-and-ring edge cap in resolve_persistent_cluster_id
    cohort_wallets = [f"CohortWallet_{i:03d}" for i in range(40)]
    large_coholders = {
        "LargeCohortMint_1": cohort_wallets,
        "LargeCohortMint_2": cohort_wallets,
    }
    cluster_res = resolve_persistent_cluster_id(
        token_mint="LargeCohortMint_3",
        funding_edges=[],
        post_sell_transfers=[],
        historical_token_holders=large_coholders,
    )
    assert cluster_res.cluster_id.startswith("cluster_")
    assert cluster_res.coholding_wallet_count == 40
    assert len(cluster_res.louvain_communities) >= 1

    # 5. Multi-mint separation when token_mint="" in evaluate_multi_wallet_cluster_trigger
    cross_mint_events = [
        ShadowWalletPurchaseEvent("W1", "Mint_Alpha", 100.0, 7.5, "cluster_1"),
        ShadowWalletPurchaseEvent("W2", "Mint_Beta", 102.0, 7.5, "cluster_1"),
        ShadowWalletPurchaseEvent("W3", "Mint_Gamma", 104.0, 7.5, "cluster_1"),
    ]
    cross_res = evaluate_multi_wallet_cluster_trigger(
        purchase_events=cross_mint_events,
        token_mint="",
        min_wallets=3,
        window_seconds=15.0,
        min_wallet_score=6.0,
    )
    assert cross_res.triggered is False
    assert cross_res.signal == NO_CONFLUENCE_WAIT_SIGNAL
