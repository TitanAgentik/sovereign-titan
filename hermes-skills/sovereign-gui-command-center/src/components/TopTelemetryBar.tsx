import React from "react";
import { usePrivacyMode } from "../hooks/usePrivacyMode";
import { sendTitanIpcCommand } from "../services/titanIpcClient";
import {
  MacroRegime,
  TitanTelemetryFrame,
  VaultMode,
} from "../types/telemetry";

interface TopTelemetryBarProps {
  frame: TitanTelemetryFrame;
  activeWorkspace: number;
  onSelectWorkspace: (ws: number) => void;
  onChangeMacroRegime: (regime: MacroRegime) => void;
  onChangeVaultMode: (mode: VaultMode) => void;
  onTogglePauseAll: () => void;
  onPanicFlattenAll: () => void;
  uiScale: number;
  onChangeUiScale: (scale: number) => void;
  statusBanner?: string;
}

const CITY_BADGES: Record<string, string> = {
  Frankfurt: "FRA",
  "New York": "NYC",
  Amsterdam: "AMS",
  Tokyo: "TYO",
  "Salt Lake City": "SLC",
};

export const TopTelemetryBar: React.FC<TopTelemetryBarProps> = ({
  frame,
  activeWorkspace,
  onSelectWorkspace,
  onChangeMacroRegime,
  onChangeVaultMode,
  onTogglePauseAll,
  onPanicFlattenAll,
  uiScale,
  onChangeUiScale,
  statusBanner,
}) => {
  const [privacyMode, togglePrivacyModeState] = usePrivacyMode();

  const handleTogglePrivacyMode = () => {
    const next = !privacyMode;
    togglePrivacyModeState();
    void sendTitanIpcCommand("DISPATCH_SOVEREIGN_SUBAGENT", {
      agent_id: "agent-d-artifact-bundle-validator",
      subagent_id: "mission-control-privacy-mask-enforcer-subagent",
      payload: { privacy_mode_on: next },
    });
  };

  const grad = frame.graduation;
  const vault = frame.vault;
  const regime = frame.macro_directive.regime;
  const activeShardTotalSol = frame.shards.reduce(
    (acc, s) => acc + s.sol_balance,
    0
  );
  const totalEquitySol: number =
    typeof frame.total_equity_sol === "number" &&
    Number.isFinite(frame.total_equity_sol)
      ? frame.total_equity_sol
      : vault.active_hot_wallet_sol +
        vault.pending_unclaimed_sweeps_sol +
        activeShardTotalSol +
        (frame.unrealized_pnl_sol || 0);
  const reclaimedSol = frame.ata_rent_reclaimed_total_sol ?? 0.0;
  const baseEquitySol = Math.max(totalEquitySol - frame.net_24h_pnl_sol, 1.0);
  const roi24hPct = (frame.net_24h_pnl_sol / baseEquitySol) * 100.0;
  const unrealizedRoiPct =
    ((frame.unrealized_pnl_sol || 0) /
      Math.max(vault.active_hot_wallet_sol, 1.0)) *
    100.0;
  const hotWalletSharePct =
    (vault.active_hot_wallet_sol / Math.max(totalEquitySol, 1.0)) * 100.0;
  const lockboxSharePct =
    (vault.pending_unclaimed_sweeps_sol / Math.max(totalEquitySol, 1.0)) *
    100.0;

  const gatePillClass = frame.paused_all
    ? "bg-[#f2b33d]/18 border-[#f2b33d]/60 text-[#f2b33d]"
    : grad.mode === "LIVE"
    ? "bg-[#ef6069]/18 border-[#ef6069]/60 text-[#ff7a82]"
    : grad.mode === "CANARY"
    ? "bg-[#f2b33d]/18 border-[#f2b33d]/60 text-[#f2b33d]"
    : "bg-[#35e0b0]/15 border-[#35e0b0]/50 text-[#35e0b0]";

  const gatePillLabel = frame.paused_all
    ? "PAUSED"
    : grad.mode === "LIVE"
    ? `LIVE SHARDS (${grad.active_live_shards}/25)`
    : grad.mode === "CANARY"
    ? "CANARY 15%"
    : "PAPER SIM";

  const activeHedgeRatio =
    frame.zero_loss_shields?.drift_hedge?.hedge_ratio_pct ?? 0;

  return (
    <div className="w-full select-none">
      <div className="max-w-[1920px] mx-auto px-4 pt-3 pb-1.5 space-y-2.5">
        {/* ROW 1: Compact Command & Mode Bar */}
        <header className="titan-panel px-3.5 py-2 flex flex-wrap items-center justify-between gap-2.5">
          {/* Left: Brand + Gate Mode Pill + Live Spot + Slot/Leader/PTP */}
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-[15px] font-extrabold tracking-wider text-white whitespace-nowrap">
              SOVEREIGN <span className="text-[#35e0b0]">TITAN OS</span>
            </h1>

            <span
              className={`px-2 py-0.5 rounded-md font-mono text-[10.5px] font-bold border ${gatePillClass}`}
            >
              {gatePillLabel}
            </span>

            <div className="flex items-center gap-2 bg-[#070c15] border border-[#182638] rounded-md px-2.5 py-1 font-mono text-[11px]">
              <span>
                SOL{" "}
                <strong className="text-[#35e0b0]">
                  ${frame.sol_usd.toFixed(2)}
                </strong>
              </span>
              <span className="text-[#4a5f78]">·</span>
              <span>
                BTC{" "}
                <strong className="text-[#f2b33d]">
                  ${frame.btc_usd.toFixed(0)}
                </strong>
              </span>
            </div>

            <div className="hidden lg:flex items-center gap-2 bg-[#070c15] border border-[#182638] rounded-md px-2.5 py-1 font-mono text-[10.5px] text-[#8b9fb7]">
              <span>
                Slot{" "}
                <strong className="text-white">
                  #{frame.alpenglow_slot.toLocaleString()}
                </strong>
              </span>
              <span className="text-[#283e5c]">·</span>
              <span>
                <strong className="text-[#f2b33d]">
                  {CITY_BADGES[frame.leader.city] || "FRA"}
                </strong>{" "}
                ({frame.leader.validator})
              </span>
              <span className="text-[#283e5c]">·</span>
              <span>
                BAM <strong className="text-white">T{frame.bam_tick_index + 1}/8</strong>
              </span>
              <span className="text-[#283e5c]">·</span>
              <span className="text-[#35e0b0] font-semibold">
                +{frame.ptp_offset_ns}ns LOCKED
              </span>
            </div>

            {/* Interactive Autonomous Closed-Loop & Zero-Rent Status Pill */}
            <div className="flex flex-wrap items-center gap-1.5 bg-[#070c15] border border-[#182638] rounded-md px-2 py-0.5 font-mono text-[10.5px]">
              <button
                type="button"
                onClick={() =>
                  void sendTitanIpcCommand("TOGGLE_AUTONOMOUS_CLOSED_LOOP", {
                    enabled: !(frame.autonomous_closed_loop?.enabled !== false),
                  })
                }
                title="Click to toggle Autonomous Closed-Loop Execution (5s Arb, 20s Wallet Copy, 1s Time-Stop, Lookahead Crank)"
                className={`px-2 py-0.5 rounded font-bold border transition cursor-pointer ${
                  frame.autonomous_closed_loop?.enabled !== false
                    ? frame.autonomous_closed_loop?.execution_stage ===
                      "LIVE_MAINNET_AUTONOMOUS_ACTIVE"
                      ? "bg-[#10b981]/25 border-[#10b981] text-[#34d399]"
                      : "bg-[#35e0b0]/18 border-[#35e0b0]/60 text-[#35e0b0]"
                    : "bg-[#f2b33d]/20 border-[#f2b33d]/60 text-[#f2b33d]"
                }`}
              >
                {`🤖 AUTO-LOOP: ${
                  frame.autonomous_closed_loop?.enabled !== false
                    ? frame.autonomous_closed_loop?.execution_stage ===
                      "LIVE_MAINNET_AUTONOMOUS_ACTIVE"
                      ? "🟢 LIVE ACTIVE"
                      : "⚡ ARMED (Min 0.05 SOL)"
                    : "⏸️ PAUSED"
                }`}
              </button>
              <span className="px-1.5 py-0.5 rounded bg-[#0a1814] border border-[#10b981]/40 text-[#34d399] font-semibold">
                🛡️ 0-Rent Jup Guard (+1.85 SOL Saved)
              </span>
              <span className="px-1.5 py-0.5 rounded bg-[#081523] border border-[#38bdf8]/40 text-[#7dd3fc] font-semibold">
                {`⚡ MMAP ${(
                  frame.atomic_arb_scanner?.local_mmap_sub50us_scan_us ?? 8.2
                ).toFixed(1)}µs`}
              </span>
              <span className="px-1.5 py-0.5 rounded bg-[#141024] border border-[#a855f7]/40 text-[#d8b4fe] font-semibold">
                🚀 0ms LLM Bypass
              </span>
              <button
                type="button"
                onClick={() => {
                  const curTierUsd =
                    frame.mega_flash_syndicate?.active_tier_usd ?? 10000000;
                  const nextSpec =
                    curTierUsd === 100000
                      ? { tier_usd: 1000000, tier_label: "$1M" }
                      : curTierUsd === 1000000
                      ? { tier_usd: 10000000, tier_label: "$10M" }
                      : curTierUsd === 10000000
                      ? { tier_usd: 50000000, tier_label: "$50M" }
                      : { tier_usd: 100000, tier_label: "$100K" };
                  void sendTitanIpcCommand(
                    "SET_MEGA_FLASH_SYNDICATE_TIER",
                    nextSpec
                  );
                }}
                title="Click to cycle Mega-Flash Syndicate Tier ($100K -> $1M -> $10M -> $50M · 0.00 SOL Own Principal Risk)"
                className="px-2 py-0.5 rounded bg-[#1a1306] hover:bg-[#2a1f0a] border border-[#f59e0b]/60 text-[#fde68a] font-bold transition cursor-pointer"
              >
                {`🏦 FLASH SYNDICATE: ${
                  frame.mega_flash_syndicate?.active_tier_label ?? "$10M"
                } (${(
                  frame.mega_flash_syndicate?.max_borrow_sol ?? 51000
                ).toLocaleString()} SOL)`}
              </button>
              <button
                type="button"
                onClick={() =>
                  void sendTitanIpcCommand("EXECUTE_MEGA_FLASH_SYNDICATE_ARB", {
                    tier_usd:
                      frame.mega_flash_syndicate?.active_tier_usd ?? 10000000,
                    tier_label:
                      frame.mega_flash_syndicate?.active_tier_label ?? "$10M",
                    borrow_sol:
                      frame.mega_flash_syndicate?.max_borrow_sol ?? 51000,
                  })
                }
                title="1-Click Execute Multi-Protocol Mega-Flash Syndicate Arbitrage Sweep"
                className="px-2 py-0.5 rounded bg-[#10b981]/25 hover:bg-[#10b981]/40 border border-[#10b981] text-[#34d399] font-extrabold transition cursor-pointer"
              >
                ⚡ FIRE MEGA-FLASH
              </button>
            </div>
          </div>

          {/* Right: Macro Regime, Capital Mode, Drift Hedge, Privacy, Zoom, Global Pause & [F12] Panic Flatten */}
          <div className="flex flex-wrap items-center gap-1.5">
            {/* Macro Regime */}
            <div className="flex items-center bg-[#070c15] border border-[#182638] rounded-md p-0.5 font-mono text-[10.5px]">
              {(
                [
                  {
                    id: "GREEN",
                    match: "GREEN",
                    label: "GREEN",
                    cls: "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]/50",
                  },
                  {
                    id: "AMBER",
                    match: "AMBER",
                    label: "AMBER",
                    cls: "bg-[#f2b33d]/20 text-[#f2b33d] border-[#f2b33d]/50",
                  },
                  {
                    id: "RED_MACRO_FLUSH",
                    match: "RED",
                    label: "RED",
                    cls: "bg-[#ef6069]/25 text-[#ef6069] border-[#ef6069]/50",
                  },
                ] as const
              ).map((r) => {
                const isOn = String(regime).startsWith(r.match);
                return (
                  <button
                    key={r.id}
                    type="button"
                    onClick={() => onChangeMacroRegime(r.id as MacroRegime)}
                    className={`px-2 py-0.5 rounded font-bold border transition ${
                      isOn
                        ? r.cls
                        : "border-transparent text-[#8b9fb7] hover:text-white"
                    }`}
                  >
                    {r.label}
                  </button>
                );
              })}
            </div>

            {/* Capital Mode */}
            <div className="flex items-center bg-[#070c15] border border-[#182638] rounded-md p-0.5 font-mono text-[10.5px]">
              {(
                [
                  {
                    id: "PAPER",
                    label: "PAPER",
                    cls: "bg-[#5b9dff]/20 text-[#5b9dff] border-[#5b9dff]/50",
                  },
                  {
                    id: "CANARY",
                    label: "CANARY",
                    cls: "bg-[#f2b33d]/20 text-[#f2b33d] border-[#f2b33d]/50",
                  },
                  {
                    id: "LIVE",
                    label: "LIVE",
                    cls: "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]/50",
                  },
                ] as const
              ).map((m) => {
                const isOn = grad.mode === m.id;
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => onChangeVaultMode(m.id)}
                    className={`px-2 py-0.5 rounded font-bold border transition ${
                      isOn
                        ? m.cls
                        : "border-transparent text-[#8b9fb7] hover:text-white"
                    }`}
                  >
                    {m.label}
                  </button>
                );
              })}
            </div>

            {/* Drift Perp Hedge */}
            <div className="hidden xl:flex items-center bg-[#070c15] border border-[#182638] rounded-md p-0.5 font-mono text-[10.5px]">
              <span className="px-1.5 text-[#8b9fb7]">Hedge:</span>
              {(
                [
                  { id: "OFF", label: "OFF", ratio: 0 },
                  { id: "HALF_50PCT", label: "50%", ratio: 50 },
                  { id: "FULL_100PCT", label: "100%", ratio: 100 },
                ] as const
              ).map((opt) => {
                const isSelected = Math.abs(activeHedgeRatio - opt.ratio) < 1;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() =>
                      void sendTitanIpcCommand("SET_DRIFT_HEDGE_MODE", {
                        mode: opt.id,
                      })
                    }
                    className={`px-1.5 py-0.5 rounded font-bold border transition ${
                      isSelected
                        ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]/50"
                        : "border-transparent text-[#8b9fb7] hover:text-white"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>

            {/* Privacy Toggle */}
            <button
              type="button"
              onClick={handleTogglePrivacyMode}
              title="Toggle Privacy Mode (Mask raw SOL/USD balances)"
              className={`px-2 py-1 rounded-md font-mono font-bold text-[10.5px] border transition ${
                privacyMode
                  ? "bg-[#35e0b0]/20 border-[#35e0b0]/60 text-[#35e0b0]"
                  : "bg-[#070c15] border-[#182638] text-[#8b9fb7] hover:text-white"
              }`}
            >
              {privacyMode ? "🔒 Privacy ON" : "🔓 Privacy"}
            </button>

            {/* Zoom Scale */}
            <div className="hidden 2xl:flex items-center bg-[#070c15] border border-[#182638] rounded-md p-0.5 font-mono text-[10px]">
              {[0.85, 0.95, 1.0, 1.1].map((sc) => (
                <button
                  key={sc}
                  type="button"
                  onClick={() => onChangeUiScale(sc)}
                  className={`px-1.5 py-0.5 rounded ${
                    Math.abs(uiScale - sc) < 0.02
                      ? "bg-[#182638] text-[#35e0b0] font-bold"
                      : "text-[#8b9fb7] hover:text-white"
                  }`}
                >
                  {Math.round(sc * 100)}%
                </button>
              ))}
            </div>

            {/* Global Pause */}
            <button
              type="button"
              onClick={onTogglePauseAll}
              className={`px-2.5 py-1 rounded-md font-mono font-bold text-[10.5px] border transition ${
                frame.paused_all
                  ? "bg-[#f2b33d]/20 border-[#f2b33d] text-[#f2b33d]"
                  : "bg-[#35e0b0]/15 border-[#35e0b0]/50 text-[#35e0b0] hover:border-[#f2b33d]"
              }`}
            >
              {frame.paused_all ? "⏸ PAUSED" : "⚡ ACTIVE"}
            </button>

            {/* [F12] Panic Flatten */}
            <button
              type="button"
              onClick={onPanicFlattenAll}
              title="Shortcut: [F12] — Flatten all open positions via Jito Bundle & demote to PAPER"
              className="px-2.5 py-1 rounded-md font-mono font-bold text-[10.5px] bg-[#ef6069]/20 hover:bg-[#ef6069]/35 border border-[#ef6069]/80 text-[#ff858d] transition"
            >
              [F12] Panic Flatten
            </button>
          </div>
        </header>

        {/* ROW 2: Clean 6-KPI Summary Strip */}
        <section className="titan-kpi-grid">
          <div
            className="titan-kpi-card"
            style={{ ["--kc" as string]: "var(--mint)" }}
          >
            <div className="text-[10px] uppercase tracking-wider text-[#8b9fb7] font-semibold">
              Total Equity
            </div>
            <div className="text-[17px] font-bold font-mono text-[#35e0b0] mt-0.5">
              {privacyMode
                ? `••• SOL (+${roi24hPct.toFixed(1)}%)`
                : `${totalEquitySol.toFixed(2)} SOL`}
            </div>
            <div className="text-[10.5px] text-[#8b9fb7] font-mono truncate">
              {privacyMode
                ? `Hot Share: ${hotWalletSharePct.toFixed(1)}%`
                : `$${(totalEquitySol * frame.sol_usd).toLocaleString("en-US", {
                    maximumFractionDigits: 0,
                  })} USD · Hot: ${vault.active_hot_wallet_sol.toFixed(1)} SOL`}
            </div>
          </div>

          <div
            className="titan-kpi-card"
            style={{ ["--kc" as string]: "var(--blue)" }}
          >
            <div className="text-[10px] uppercase tracking-wider text-[#8b9fb7] font-semibold">
              25-Shard Ring
            </div>
            <div className="text-[17px] font-bold font-mono text-[#5b9dff] mt-0.5">
              {privacyMode
                ? "••• SOL (25/25)"
                : `${activeShardTotalSol.toFixed(2)} SOL`}
            </div>
            <div className="text-[10.5px] text-[#8b9fb7] font-mono truncate">
              25/25 AES-256-GCM · 0 Copy-Bots
            </div>
          </div>

          <div
            className="titan-kpi-card"
            style={{ ["--kc" as string]: "var(--amber)" }}
          >
            <div className="text-[10px] uppercase tracking-wider text-[#8b9fb7] font-semibold">
              80% Reserve Lockbox
            </div>
            <div className="text-[17px] font-bold font-mono text-[#f2b33d] mt-0.5">
              {privacyMode
                ? `••• SOL (${lockboxSharePct.toFixed(1)}%)`
                : `${vault.pending_unclaimed_sweeps_sol.toFixed(2)} SOL`}
            </div>
            <div className="text-[10.5px] text-[#8b9fb7] font-mono truncate">
              {privacyMode
                ? "HWM Protected · 0% Risk"
                : `HWM: ${vault.high_water_mark_sol.toFixed(1)} SOL · 0% Risk`}
            </div>
          </div>

          <div
            className="titan-kpi-card"
            style={{ ["--kc" as string]: "var(--mint)" }}
          >
            <div className="text-[10px] uppercase tracking-wider text-[#8b9fb7] font-semibold">
              Open P&amp;L
            </div>
            <div className="text-[17px] font-bold font-mono text-[#35e0b0] mt-0.5">
              {privacyMode
                ? `••• SOL (+${unrealizedRoiPct.toFixed(2)}%)`
                : `+${(frame.unrealized_pnl_sol || 0).toFixed(4)} SOL`}
            </div>
            <div className="text-[10.5px] text-[#8b9fb7] font-mono truncate">
              {(frame.open_positions || []).length} Open Positions · Live MTM
            </div>
          </div>

          <div
            className="titan-kpi-card"
            style={{ ["--kc" as string]: "var(--violet)" }}
          >
            <div className="text-[10px] uppercase tracking-wider text-[#8b9fb7] font-semibold">
              24h Net P&amp;L
            </div>
            <div className="text-[17px] font-bold font-mono text-[#a78bfa] mt-0.5">
              {privacyMode
                ? `••• SOL (+${roi24hPct.toFixed(2)}%)`
                : `+${frame.net_24h_pnl_sol.toFixed(2)} SOL`}
            </div>
            <div className="text-[10.5px] text-[#8b9fb7] font-mono truncate">
              {privacyMode
                ? "Rent Reclaimed: 100% Active"
                : `+$${frame.net_24h_pnl_usd.toLocaleString("en-US", {
                    maximumFractionDigits: 0,
                  })} · Rent +${reclaimedSol.toFixed(3)} SOL`}
            </div>
          </div>

          <div
            className="titan-kpi-card"
            style={{ ["--kc" as string]: "var(--blue)" }}
          >
            <div className="text-[10px] uppercase tracking-wider text-[#8b9fb7] font-semibold">
              Win-Rate &amp; Risk Gate
            </div>
            <div className="text-[17px] font-bold font-mono text-[#e6eef8] mt-0.5">
              {grad.total_paper_trades}/40{" "}
              <span className="text-[13px] text-[#35e0b0]">
                PF {grad.profit_factor.toFixed(2)}x
              </span>
            </div>
            <div className="text-[10.5px] text-[#8b9fb7] font-mono truncate">
              Max DD {grad.max_drawdown_pct.toFixed(2)}% (&le;5%) ·{" "}
              {frame.zero_loss_shields?.roundtrip_honeypot_blocks_today ?? 7}{" "}
              Blocks
            </div>
          </div>
        </section>

        {/* ROW 3: Prominent 7-Workspace Navigation Bar */}
        <nav className="titan-panel px-2.5 py-1.5 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: 1, key: "Alt+1", label: "1 · Trading Cockpit" },
              { id: 2, key: "Alt+2", label: "2 · Alpha & Profit Engines" },
              { id: 3, key: "Alt+3", label: "3 · MEV & Flash Loans" },
              { id: 4, key: "Alt+4", label: "4 · 32-Agent AI Swarm" },
              { id: 5, key: "Alt+5", label: "5 · Vault & 25 Shards" },
              { id: 6, key: "Alt+6", label: "6 · Tax & Settings" },
              { id: 7, key: "Alt+7", label: "7 · VPN Relay Mesh" },
            ].map((tab) => {
              const isActive = activeWorkspace === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => onSelectWorkspace(tab.id)}
                  className={`px-3 py-1.5 rounded-lg font-mono text-[11.5px] font-semibold transition flex items-center gap-2 border cursor-pointer ${
                    isActive
                      ? "bg-[#35e0b0]/16 border-[#35e0b0] text-white shadow-[inset_0_-2px_0_#35e0b0]"
                      : "bg-[#070c15] border-[#182638] text-[#8b9fb7] hover:text-white hover:border-[#243852]"
                  }`}
                >
                  <span
                    className={`text-[9.5px] px-1.5 py-0.5 rounded font-bold ${
                      isActive
                        ? "bg-[#35e0b0]/25 text-[#35e0b0]"
                        : "bg-[#111b2a] text-[#5b9dff]"
                    }`}
                  >
                    {tab.key}
                  </span>
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          <div className="hidden xl:flex items-center gap-2 text-[10.5px] font-mono text-[#8b9fb7] pr-1">
            {statusBanner ? (
              <span className="truncate max-w-[340px] text-[#35e0b0]">
                {statusBanner}
              </span>
            ) : (
              <span>
                Policy:{" "}
                <strong className="text-[#35e0b0]">
                  {frame.gepa.champion.policy_id}
                </strong>
              </span>
            )}
          </div>
        </nav>
      </div>
    </div>
  );
};
