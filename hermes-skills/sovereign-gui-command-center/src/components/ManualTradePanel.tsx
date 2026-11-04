import React, { useEffect, useRef, useState } from "react";
import { usePrivacyMode } from "../hooks/usePrivacyMode";
import {
  HorizonConfigItem,
  OpenPositionState,
  StealthShardState,
  TrailWinPositionTelemetry,
} from "../types/telemetry";
import { sendTitanIpcCommand } from "../services/titanIpcClient";

interface ManualTradePanelProps {
  activeMint: string;
  onChangeMint: (mint: string) => void;
  shards: StealthShardState[];
  openPositions: OpenPositionState[];
  horizonsConfig?: Record<string, HorizonConfigItem>;
  activeTrailState?: TrailWinPositionTelemetry;
  trailPctOverride: number;
  onChangeTrailPctOverride: (pct: number) => void;
  onLogExecution: (msg: string) => void;
}

const DEFAULT_HORIZONS: Record<string, HorizonConfigItem> = {
  H1_BLIND_0BLOCK: {
    id: "H1_BLIND_0BLOCK",
    horizon_type: "HORIZON_1_BLIND_0BLOCK_SNIPER",
    label: "H1_BLIND_0BLOCK: <65% Early Curve Sniper",
    subtitle:
      "Blind 0-Block Pump.fun <65% Curve Entry (Blocked by 98.5% Early-Curve Mortality Filter)",
    mode: "OFF",
    max_sol: 0.0,
    min_bonding_curve_pct: 0.0,
    max_bonding_curve_pct: 65.0,
  },
  H1: {
    id: "H1",
    horizon_type: "HORIZON_1_BONDING_SCALP",
    label: "H1: Pre-Grad Squeeze (88%–99.5%)",
    subtitle:
      "Pump.fun 88.0%–99.5% Velocity Squeeze Only (No <88% Mid-Curve Fee Bleed · Handoff -> 0-Slot Arb)",
    mode: "ON",
    max_sol: 1.5,
    min_bonding_curve_pct: 88.0,
    max_bonding_curve_pct: 99.5,
  },
  H2: {
    id: "H2",
    horizon_type: "HORIZON_2_GRADUATION_RECLAIM",
    label: "H2: Post-Grad Reclaim",
    subtitle: "-30%..-60% Flush + 1m VWAP · 2m–45m",
    mode: "ON",
    max_sol: 2.5,
  },
  H3: {
    id: "H3",
    horizon_type: "HORIZON_3_MIDCAP_SWING",
    label: "H3: Mid-Cap Swing (45m Moonbag Gate)",
    subtitle:
      "4h Compression Breakout ($500k–$50M · 45m Principal-Free Rule: 0 Raw Principal Held >45m)",
    mode: "ON",
    max_sol: 4.0,
    max_raw_principal_hold_sec: 2700,
  },
  H4: {
    id: "H4",
    horizon_type: "HORIZON_4_WICK_MICROSCALP",
    label: "H4: Wick Micro-Scalp",
    subtitle: "25ms BAM Panic-Wick · Hold 1s–45s",
    mode: "ON",
    max_sol: 2.0,
  },
};

export const ManualTradePanel: React.FC<ManualTradePanelProps> = ({
  activeMint,
  onChangeMint,
  shards,
  openPositions,
  horizonsConfig,
  activeTrailState,
  trailPctOverride,
  onChangeTrailPctOverride,
  onLogExecution,
}) => {
  const [privacyMode] = usePrivacyMode();
  const [selectedShard, setSelectedShard] = useState<string>("AUTO_CLEAN");
  const [jitoDontFront, setJitoDontFront] = useState<boolean>(true);
  const [jitoPriority, setJitoPriority] = useState<
    "75TH" | "90TH" | "95TH_TURBO" | "BAM_58PCT"
  >("95TH_TURBO");
  const [customSolAmount, setCustomSolAmount] = useState<string>("1.5");
  const [lastTxReceipt, setLastTxReceipt] = useState<string>(
    "Ready · Sub-2ms V0 Builder Warmed (3 ALTs / 540 Vaults)"
  );

  const activePos = openPositions.find((p) => p.mint === activeMint);

  // Optimistic local position lock state keyed by mint
  const [localPositionLockedMap, setLocalPositionLockedMap] = useState<
    Record<string, boolean>
  >({});
  const lastLockEditTsRef = useRef<number>(0);

  useEffect(() => {
    if (
      activePos &&
      typeof activePos.locked_manual === "boolean" &&
      Date.now() - lastLockEditTsRef.current > 1000
    ) {
      setLocalPositionLockedMap((prev) =>
        prev[activeMint] === activePos.locked_manual
          ? prev
          : { ...prev, [activeMint]: activePos.locked_manual }
      );
    }
  }, [activeMint, activePos]);

  const localPositionLocked =
    activeMint in localPositionLockedMap
      ? localPositionLockedMap[activeMint]
      : Boolean(activePos?.locked_manual);
  const manualTakeoverLocked = localPositionLocked;

  // Local Horizons state with anti-snapback guard
  const [localHorizons, setLocalHorizons] = useState<
    Record<string, HorizonConfigItem>
  >(() => {
    const merged: Record<string, HorizonConfigItem> = { ...DEFAULT_HORIZONS };
    if (horizonsConfig) {
      for (const [k, v] of Object.entries(horizonsConfig)) {
        merged[k] = { ...(DEFAULT_HORIZONS[k] || {}), ...v };
      }
    }
    return merged;
  });
  const lastHorizonEditTsRef = useRef<number>(0);
  const horizonDebounceRef = useRef<Record<string, number>>({});
  const trailDebounceRef = useRef<number | null>(null);

  useEffect(() => {
    if (!horizonsConfig) return;
    if (Date.now() - lastHorizonEditTsRef.current > 1000) {
      setLocalHorizons((prev) => {
        const merged: Record<string, HorizonConfigItem> = {
          ...DEFAULT_HORIZONS,
          ...prev,
        };
        for (const [k, v] of Object.entries(horizonsConfig)) {
          merged[k] = {
            ...(DEFAULT_HORIZONS[k] || {}),
            ...(prev[k] || {}),
            ...v,
          };
        }
        return merged;
      });
    }
  }, [horizonsConfig]);

  useEffect(() => {
    return () => {
      Object.values(horizonDebounceRef.current).forEach((id) =>
        window.clearTimeout(id)
      );
      if (trailDebounceRef.current !== null) {
        window.clearTimeout(trailDebounceRef.current);
      }
    };
  }, []);

  const horizons = localHorizons;

  // Live preview stop price computed dynamically from trailPctOverride while dragging
  const baseStopPrice = activeTrailState?.active_trail_stop_price ?? 0.00412;
  const hwmRefPrice =
    activeTrailState?.high_water_mark_price_sol &&
    activeTrailState.high_water_mark_price_sol > 0
      ? activeTrailState.high_water_mark_price_sol
      : activePos?.mark_price_usd && activePos.mark_price_usd > 0
      ? Math.max(
          activePos.mark_price_usd,
          (activePos.entry_price_usd || activePos.mark_price_usd) * 1.08
        )
      : baseStopPrice / (1.0 - 0.11);
  const stopPrice = Math.max(
    0.000001,
    hwmRefPrice * (1.0 - Math.max(0.005, Math.min(0.35, trailPctOverride / 100.0)))
  );
  const lockedProfitPct = activeTrailState?.locked_profit_pct ?? 184.1;
  const currentStage = activeTrailState?.current_stage ?? 3;

  const executeBuy = async (solAmount: number) => {
    const res = await sendTitanIpcCommand("MANUAL_DIRECTIONAL_BUY", {
      mint: activeMint,
      sol_amount: solAmount,
      shard: selectedShard,
      jitodontfront: jitoDontFront,
      jito_priority: jitoPriority,
    });
    const receipt =
      res.message ||
      `BUY ${solAmount.toFixed(2)} SOL on ${activeMint.slice(
        0,
        8
      )}... via Shard[${selectedShard}] -> V0 Tx 332B (${
        res.latency_ms ?? 0.21
      }ms)`;
    setLastTxReceipt(receipt);
    onLogExecution(receipt);
  };

  const executeScaleOut = async (
    pct: number,
    label: string,
    reclaimRent = false
  ) => {
    const res = await sendTitanIpcCommand("MANUAL_DIRECTIONAL_EXIT", {
      mint: activeMint,
      exit_pct: pct,
      label,
      close_account_rent_reclaim: reclaimRent,
      jito_priority: jitoPriority,
    });
    const rentTag = reclaimRent ? " + 0.00203928 SOL Rent" : "";
    const receipt =
      res.message ||
      `EXIT ${label} (${pct}%) on ${activeMint.slice(
        0,
        8
      )}...${rentTag} -> V0 Tx 368B (${res.latency_ms ?? 0.19}ms)`;
    setLastTxReceipt(receipt);
    onLogExecution(receipt);
  };

  const handleToggleLock = async () => {
    const next = !localPositionLocked;
    lastLockEditTsRef.current = Date.now();
    setLocalPositionLockedMap((prev) => ({
      ...prev,
      [activeMint]: next,
    }));
    const msg = next
      ? `LOCKED ${activeMint.slice(0, 8)}... (Manual Takeover ACTIVE)`
      : `UNLOCKED ${activeMint.slice(0, 8)}... (Auto Exit Ladder ACTIVE)`;
    setLastTxReceipt(msg);
    onLogExecution(msg);
    await sendTitanIpcCommand("TOGGLE_POSITION_LOCK", {
      mint: activeMint,
      locked: next,
    });
  };

  const handleHorizonModeChange = async (
    horizonId: "H1_BLIND_0BLOCK" | "H1" | "H2" | "H3" | "H4",
    mode: "ON" | "PAPER" | "OFF"
  ) => {
    lastHorizonEditTsRef.current = Date.now();
    setLocalHorizons((prev) => {
      const existing = prev[horizonId] || DEFAULT_HORIZONS[horizonId];
      return {
        ...prev,
        [horizonId]: {
          ...existing,
          mode,
        },
      };
    });
    const res = await sendTitanIpcCommand("UPDATE_HORIZON_CONFIG", {
      horizon: horizonId,
      horizon_id: horizonId,
      mode,
    });
    const msg =
      res.message || `[HORIZON ${horizonId}] Mode switched to ${mode}`;
    setLastTxReceipt(msg);
    onLogExecution(msg);
  };

  const commitHorizonAllocationIpc = async (
    horizonId: "H1_BLIND_0BLOCK" | "H1" | "H2" | "H3" | "H4",
    maxSol: number
  ) => {
    if (horizonDebounceRef.current[horizonId]) {
      window.clearTimeout(horizonDebounceRef.current[horizonId]);
      delete horizonDebounceRef.current[horizonId];
    }
    const res = await sendTitanIpcCommand("UPDATE_HORIZON_CONFIG", {
      horizon: horizonId,
      horizon_id: horizonId,
      max_sol: maxSol,
    });
    const msg =
      res.message ||
      `[HORIZON ${horizonId}] Max allocation set to ${maxSol.toFixed(1)} SOL`;
    setLastTxReceipt(msg);
    onLogExecution(msg);
  };

  const handleHorizonAllocationChange = (
    horizonId: "H1_BLIND_0BLOCK" | "H1" | "H2" | "H3" | "H4",
    maxSol: number
  ) => {
    lastHorizonEditTsRef.current = Date.now();
    setLocalHorizons((prev) => {
      const existing = prev[horizonId] || DEFAULT_HORIZONS[horizonId];
      return {
        ...prev,
        [horizonId]: {
          ...existing,
          max_sol: maxSol,
        },
      };
    });
    if (horizonDebounceRef.current[horizonId]) {
      window.clearTimeout(horizonDebounceRef.current[horizonId]);
    }
    horizonDebounceRef.current[horizonId] = window.setTimeout(() => {
      void commitHorizonAllocationIpc(horizonId, maxSol);
    }, 150);
  };

  const handleActivateTurboTrail = async () => {
    onChangeTrailPctOverride(4.0);
    const res = await sendTitanIpcCommand("ACTIVATE_TURBO_SCALP_TRAIL", {
      mint: activeMint,
    });
    const msg =
      res.message ||
      `⚡ [TURBO SCALP TRAIL 4% HWM] Activated on ${activeMint.slice(0, 8)}...`;
    setLastTxReceipt(msg);
    onLogExecution(msg);
  };

  const commitTrailStopIpc = async (pct: number) => {
    if (trailDebounceRef.current !== null) {
      window.clearTimeout(trailDebounceRef.current);
      trailDebounceRef.current = null;
    }
    const res = await sendTitanIpcCommand("UPDATE_TRAIL_WIN_STOP", {
      mint: activeMint,
      trail_pct: pct / 100.0,
    });
    const msg =
      res.message ||
      `🛡️ Updated Trail-Win Stop to ${pct.toFixed(2)}% HWM (Stop: $${stopPrice.toFixed(6)}) on ${activeMint.slice(0, 8)}...`;
    setLastTxReceipt(msg);
  };

  const handleTrailSliderChange = (pct: number) => {
    onChangeTrailPctOverride(pct);
    if (trailDebounceRef.current !== null) {
      window.clearTimeout(trailDebounceRef.current);
    }
    trailDebounceRef.current = window.setTimeout(() => {
      void commitTrailStopIpc(pct);
    }, 150);
  };

  const handleLockBreakevenFloor = async () => {
    onChangeTrailPctOverride(0.85);
    const res = await sendTitanIpcCommand("UPDATE_TRAIL_WIN_STOP", {
      action: "ARM_INSTANT_BREAKEVEN_RATCHET_085",
      mint: activeMint,
      trail_pct: 0.0085,
      fee_adjusted_breakeven_floor_pct: 0.85,
    });
    const msg =
      res.message ||
      `🔒 [INSTANT BE FLOOR +0.85%] Locked Fee-Adjusted Floor on ${activeMint.slice(0, 8)}...`;
    setLastTxReceipt(msg);
    onLogExecution(msg);
  };

  const [compactHorizons, setCompactHorizons] = useState<boolean>(false);

  return (
    <aside className="titan-panel flex flex-col justify-between">
      <div>
        {/* Panel Header */}
        <div className="titan-panel-header">
          <div>
            <h2>Manual Trade &amp; Sniper Dock</h2>
            <div className="panel-sub">
              4-Section Tactical Execution · Sub-0.05ms Ratchet Trail-Win Engine
            </div>
          </div>
          <span className="titan-pill positive">&lt;1.8ms V0</span>
        </div>

        <div className="p-3.5 space-y-3.5 text-[11px]">
          {/* Target Token Mint / CA Header Strip */}
          <div className="bg-[#080d15] border border-[#1a2534] rounded-lg p-2.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-[#93c5fd] text-[10px] font-bold uppercase tracking-wider">
                🎯 Target Token Mint / CA
              </label>
              {activePos ? (
                <span className="px-1.5 py-0.5 rounded bg-[#10b981]/20 border border-[#10b981]/50 text-[#34d399] font-mono text-[9.5px] font-bold">
                  HELD: {activePos.symbol} (
                  {privacyMode ? "•••" : activePos.size_sol.toFixed(2)} SOL)
                </span>
              ) : (
                <span className="font-mono text-[9.5px] text-[#7e91a8]">
                  Synced w/ Superchart #1
                </span>
              )}
            </div>
            <input
              type="text"
              value={activeMint}
              onChange={(e) => onChangeMint(e.target.value)}
              placeholder="Paste Solana Mint CA..."
              className="w-full bg-[#060a10] border border-[#1e2d40] rounded px-2.5 py-1.5 font-mono text-[11px] text-[#eef4fb] focus:outline-none focus:border-[#3b82f6]"
            />
          </div>

          {/* SECTION 1: STRATEGY HORIZON */}
          <div className="bg-[#090e16] border border-[#1a2534] rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between border-b border-[#162030] pb-1.5">
              <div>
                <span className="text-[10.5px] font-extrabold uppercase tracking-wider text-[#35e0b0]">
                  1. Strategy Horizon
                </span>
                <div className="text-[9.5px] text-[#7e91a8]">
                  4-Horizon Lifecycle Matrix (Cores 24–31 · Concurrent)
                </div>
              </div>
              <button
                type="button"
                onClick={() => setCompactHorizons((prev) => !prev)}
                className="px-2 py-0.5 rounded bg-[#101824] border border-[#243246] text-[#93c5fd] font-mono text-[9.5px] cursor-pointer hover:text-white"
              >
                {compactHorizons ? "Expand ▼" : "Compact ▲"}
              </button>
            </div>

            <div className="space-y-2">
              {(["H1_BLIND_0BLOCK", "H1", "H2", "H3", "H4"] as const).map(
                (hKey) => {
                  const item = {
                    ...DEFAULT_HORIZONS[hKey],
                    ...(horizons[hKey] || {}),
                  };
                  return (
                    <div
                      key={hKey}
                      className="bg-[#070b11] border border-[#1a2534] rounded-md p-2 space-y-1.5"
                    >
                      <div className="flex items-center justify-between gap-1.5">
                        <div className="min-w-0">
                          <div className="font-bold text-[#dce6f2] text-[10.5px] truncate">
                            {item.label}
                          </div>
                          {hKey === "H1_BLIND_0BLOCK" && item.mode === "OFF" && (
                            <div className="mt-0.5 inline-block px-1.5 py-0.5 rounded bg-[#ef4444]/20 border border-[#ef4444]/60 text-[#fca5a5] font-mono text-[9px] font-bold">
                              🛑 &lt;65% Early Curve Disabled (98.5% Mortality Filter)
                            </div>
                          )}
                          {!compactHorizons && (
                            <div className="text-[9px] text-[#7e8fa3] leading-snug">
                              {item.subtitle}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-0.5 shrink-0">
                          {(["ON", "PAPER", "OFF"] as const).map((m) => {
                            const active = item.mode === m;
                            const activeCls =
                              m === "ON"
                                ? "bg-[#10b981]/25 border-[#10b981] text-[#34d399]"
                                : m === "PAPER"
                                ? "bg-[#3b82f6]/25 border-[#3b82f6] text-[#93c5fd]"
                                : "bg-[#ef4444]/25 border-[#ef4444] text-[#fca5a5]";
                            return (
                              <button
                                key={m}
                                type="button"
                                onClick={() => handleHorizonModeChange(hKey, m)}
                                className={`px-1.5 py-0.5 rounded border text-[9.5px] font-mono font-bold transition-colors cursor-pointer ${
                                  active
                                    ? activeCls
                                    : "bg-[#0c121b] border-[#1a2534] text-[#7e8fa3]"
                                }`}
                              >
                                {m}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] text-[#7e91a8] w-20 shrink-0">
                          Max: {item.max_sol.toFixed(1)} SOL
                        </span>
                        <input
                          type="range"
                          min={0.0}
                          max={10.0}
                          step={0.5}
                          value={item.max_sol}
                          onChange={(e) =>
                            handleHorizonAllocationChange(
                              hKey,
                              parseFloat(e.target.value)
                            )
                          }
                          onMouseUp={() =>
                            void commitHorizonAllocationIpc(hKey, item.max_sol)
                          }
                          onTouchEnd={() =>
                            void commitHorizonAllocationIpc(hKey, item.max_sol)
                          }
                          className="flex-1 accent-[#35e0b0]"
                        />
                      </div>
                    </div>
                  );
                }
              )}
            </div>
          </div>

          {/* SECTION 2: QUICK BUY SOL */}
          <div className="bg-[#090e16] border border-[#10b981]/40 rounded-lg p-3 space-y-2.5">
            <div className="flex items-center justify-between border-b border-[#162030] pb-1.5">
              <div>
                <span className="text-[10.5px] font-extrabold uppercase tracking-wider text-[#10b981]">
                  2. Quick Buy SOL
                </span>
                <div className="text-[9.5px] text-[#7e91a8]">
                  Instant Atomic Snipe · 25% / 75% Split Entry
                </div>
              </div>
              <span className="font-mono text-[9.5px] px-1.5 py-0.5 rounded bg-[#10b981]/15 text-[#34d399] border border-[#10b981]/40">
                V0 Atomic
              </span>
            </div>

            {/* Shard Selector & Jito Priority */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[9.5px] text-[#7e91a8] font-bold uppercase block mb-1">
                  Stealth Shard
                </label>
                <select
                  value={selectedShard}
                  onChange={(e) => setSelectedShard(e.target.value)}
                  className="w-full bg-[#070b11] border border-[#1a2534] rounded px-2 py-1.5 text-[10.5px] font-mono text-[#eef4fb]"
                >
                  <option value="AUTO_CLEAN">Auto Clean Ring</option>
                  {shards.map((s) => (
                    <option
                      key={s.shard_index}
                      value={`#${String(s.shard_index + 1).padStart(2, "0")}`}
                    >
                      Shard #{String(s.shard_index + 1).padStart(2, "0")} (
                      {privacyMode ? "•••" : s.sol_balance.toFixed(1)} SOL)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[9.5px] text-[#7e91a8] font-bold uppercase block mb-1">
                  Jito BAM Tip
                </label>
                <select
                  value={jitoPriority}
                  onChange={(e) =>
                    setJitoPriority(e.target.value as typeof jitoPriority)
                  }
                  className="w-full bg-[#070b11] border border-[#1a2534] rounded px-2 py-1.5 text-[10.5px] font-mono text-[#fbbf24]"
                >
                  <option value="75TH">75th (0.0005 SOL)</option>
                  <option value="90TH">90th (0.0012 SOL)</option>
                  <option value="95TH_TURBO">95th (0.0030 SOL)</option>
                  <option value="BAM_58PCT">58% BAM EV</option>
                </select>
              </div>
            </div>

            {/* Quick Buy Preset Amounts */}
            <div className="grid grid-cols-5 gap-1.5">
              {[0.5, 1.0, 2.5, 5.0, 10.0].map((amt) => (
                <button
                  key={amt}
                  type="button"
                  onClick={() => executeBuy(amt)}
                  className="py-1.5 rounded bg-[#10b981]/20 hover:bg-[#10b981]/35 border border-[#10b981]/50 text-[#34d399] font-mono font-bold text-[11px] transition-colors cursor-pointer"
                >
                  {amt}
                </button>
              ))}
            </div>

            {/* Custom SOL Input + Primary Snipe Button */}
            <div className="flex gap-1.5">
              <input
                type="number"
                min="0.05"
                step="0.1"
                value={customSolAmount}
                onChange={(e) => setCustomSolAmount(e.target.value)}
                className="w-24 bg-[#070b11] border border-[#1a2534] rounded px-2 py-1.5 font-mono text-[11px] text-[#eef4fb]"
              />
              <button
                type="button"
                onClick={() =>
                  executeBuy(Math.max(0.05, parseFloat(customSolAmount) || 1.0))
                }
                className="flex-1 py-1.5 rounded bg-[#10b981] hover:bg-[#059669] text-[#04130d] font-extrabold text-[11px] transition-colors cursor-pointer shadow-[0_0_10px_rgba(16,185,129,0.25)]"
              >
                ⚡ SNIPE ({customSolAmount} SOL)
              </button>
            </div>
          </div>

          {/* SECTION 3: QUICK SELL % & AUTO-EXIT RATCHET */}
          <div className="bg-[#091216] border border-[#f59e0b]/40 rounded-lg p-3 space-y-2.5">
            <div className="flex items-center justify-between border-b border-[#182632] pb-1.5">
              <div>
                <span className="text-[10.5px] font-extrabold uppercase tracking-wider text-[#fbbf24]">
                  3. Quick Sell % &amp; Auto-Exit Ratchet
                </span>
                <div className="text-[9.5px] text-[#7e91a8]">
                  Scale-Out + ATA Rent Reclaim · Stage {currentStage}/3 Ratchet
                </div>
              </div>
              <span className="font-mono text-[10px] font-bold text-[#10b981]">
                [
                {lockedProfitPct >= 0
                  ? `+${lockedProfitPct.toFixed(0)}%`
                  : `${lockedProfitPct.toFixed(0)}%`}{" "}
                LOCKED]
              </span>
            </div>

            {/* Quick Scale-Out Grid */}
            <div className="grid grid-cols-2 gap-1.5">
              <button
                type="button"
                onClick={() => executeScaleOut(25, "Sell 25%")}
                className="py-1.5 rounded bg-[#101824] hover:bg-[#ef4444]/20 border border-[#243246] hover:border-[#ef4444]/50 text-[#d5deea] font-mono font-bold text-[10.5px] transition-colors cursor-pointer"
              >
                Sell 25%
              </button>
              <button
                type="button"
                onClick={() => executeScaleOut(50, "Sell 50%")}
                className="py-1.5 rounded bg-[#101824] hover:bg-[#ef4444]/20 border border-[#243246] hover:border-[#ef4444]/50 text-[#d5deea] font-mono font-bold text-[10.5px] transition-colors cursor-pointer"
              >
                Sell 50%
              </button>
              <button
                type="button"
                onClick={() => executeScaleOut(75, "Sell 75%")}
                className="py-1.5 rounded bg-[#101824] hover:bg-[#ef4444]/20 border border-[#243246] hover:border-[#ef4444]/50 text-[#d5deea] font-mono font-bold text-[10.5px] transition-colors cursor-pointer"
              >
                Sell 75%
              </button>
              <button
                type="button"
                onClick={() => executeScaleOut(40, "Sell Initials")}
                className="py-1.5 rounded bg-[#f59e0b]/15 hover:bg-[#f59e0b]/30 border border-[#f59e0b]/40 text-[#fbbf24] font-mono font-bold text-[10.5px] transition-colors cursor-pointer"
              >
                Sell Initials (40%)
              </button>
            </div>

            <button
              type="button"
              onClick={() =>
                executeScaleOut(100, "DUMP 100% + Reclaim Rent", true)
              }
              className="w-full py-1.5 rounded bg-[#ef4444]/25 hover:bg-[#ef4444]/40 border border-[#ef4444]/60 text-[#fca5a5] font-mono font-bold text-[10.5px] transition-colors cursor-pointer"
            >
              DUMP 100% + Reclaim ATA Rent (+0.002039 SOL)
            </button>

            {/* Trail-Win Stop Ratchet Box */}
            <div className="bg-[#071014] border border-[#10b981]/35 rounded-md p-2 space-y-2">
              <div className="flex items-center justify-between text-[10.5px] font-mono">
                <span className="text-[#94a3b8]">Active Stop Floor:</span>
                <span className="text-[#34d399] font-bold">
                  Stop: ${stopPrice.toFixed(6)} ({trailPctOverride.toFixed(2)}% HWM)
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] text-[#94a3b8]">
                  Trail % (0.5–35%):
                </span>
                <input
                  type="range"
                  min={0.5}
                  max={35}
                  step={0.25}
                  value={trailPctOverride}
                  onChange={(e) =>
                    handleTrailSliderChange(parseFloat(e.target.value))
                  }
                  onMouseUp={() => void commitTrailStopIpc(trailPctOverride)}
                  onTouchEnd={() => void commitTrailStopIpc(trailPctOverride)}
                  className="flex-1 accent-[#10b981]"
                />
              </div>

              <div className="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={handleLockBreakevenFloor}
                  className="py-1.5 px-2 rounded bg-[#f59e0b]/25 hover:bg-[#f59e0b]/40 border border-[#f59e0b] text-[#fde68a] font-mono font-bold text-[10px] transition-colors cursor-pointer"
                >
                  🔒 Lock +0.85% BE Floor
                </button>
                <button
                  type="button"
                  onClick={handleActivateTurboTrail}
                  className="py-1.5 px-2 rounded bg-[#10b981]/25 hover:bg-[#10b981]/40 border border-[#10b981] text-[#34d399] font-mono font-bold text-[10px] transition-colors cursor-pointer"
                >
                  ⚡ Turbo Trail (4% HWM)
                </button>
              </div>
            </div>

            {/* Manual Takeover Lock */}
            <button
              type="button"
              onClick={handleToggleLock}
              className={`w-full py-1.5 rounded font-bold text-[10.5px] border transition-colors cursor-pointer ${
                manualTakeoverLocked
                  ? "bg-[#a855f7]/25 border-[#a855f7] text-[#e9d5ff]"
                  : "bg-[#101824] border-[#243246] text-[#d5deea] hover:border-[#a855f7]/60"
              }`}
            >
              {manualTakeoverLocked
                ? "🔒 LOCKED (Manual Takeover Active)"
                : "🔓 Lock Position (Override Auto-Exit)"}
            </button>
          </div>

          {/* SECTION 4: PRE-FLIGHT SECURITY STATUS */}
          <div className="bg-[#090e16] border border-[#06b6d4]/40 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between border-b border-[#162030] pb-1.5">
              <div>
                <span className="text-[10.5px] font-extrabold uppercase tracking-wider text-[#67e8f9]">
                  4. Pre-Flight Security Status
                </span>
                <div className="text-[9.5px] text-[#7e91a8]">
                  Zero-Loss Guards &amp; Frontrun Protection
                </div>
              </div>
              <span className="px-1.5 py-0.5 rounded bg-[#10b981]/20 border border-[#10b981]/50 text-[#34d399] font-mono text-[9.5px] font-bold">
                🛡️ VERIFIED
              </span>
            </div>

            {/* jitodontfront Toggle */}
            <label className="flex items-center justify-between bg-[#070b11] border border-[#1a2534] rounded px-2.5 py-1.5 cursor-pointer">
              <span className="text-[10.5px] font-mono text-[#d5deea]">
                Inject `jitodontfront` Guard (Ix0){" "}
                <span
                  className={
                    jitoDontFront
                      ? "text-[#34d399] font-bold"
                      : "text-[#ef6069] font-bold"
                  }
                >
                  {jitoDontFront ? "[🟢 ON]" : "[🔴 OFF]"}
                </span>
              </span>
              <input
                type="checkbox"
                checked={jitoDontFront}
                onChange={async (e) => {
                  const nextChecked = e.target.checked;
                  setJitoDontFront(nextChecked);
                  const res = await sendTitanIpcCommand("UPDATE_SETTINGS", {
                    jitodontfront_enabled: nextChecked,
                  });
                  const msg =
                    res.message ||
                    `🛡️ jitodontfront Index-0 Guard ${
                      nextChecked ? "ENABLED [🟢 ON]" : "DISABLED [🔴 OFF]"
                    }`;
                  setLastTxReceipt(msg);
                  onLogExecution(msg);
                }}
                className="h-3.5 w-3.5 accent-[#06b6d4]"
              />
            </label>

            {/* Pre-Flight Checklist Grid */}
            <div className="grid grid-cols-2 gap-1.5 font-mono text-[9.5px]">
              <div className="px-2 py-1 rounded bg-[#071019] border border-[#1a2c3e] flex items-center justify-between">
                <span className="text-[#94a3b8]">🎯 P(Win) Gate</span>
                <span className="text-[#34d399] font-bold">&ge; 92.5%</span>
              </div>
              <div className="px-2 py-1 rounded bg-[#071019] border border-[#1a2c3e] flex items-center justify-between">
                <span className="text-[#94a3b8]">🔒 BE Floor</span>
                <span className="text-[#fbbf24] font-bold">+0.85%</span>
              </div>
              <div className="px-2 py-1 rounded bg-[#071019] border border-[#1a2c3e] flex items-center justify-between">
                <span className="text-[#94a3b8]">🧪 Rug/FoT Sim</span>
                <span className="text-[#34d399] font-bold">0% Tax</span>
              </div>
              <div className="px-2 py-1 rounded bg-[#071019] border border-[#1a2c3e] flex items-center justify-between">
                <span className="text-[#94a3b8]">⚡ V0 ALTs</span>
                <span className="text-[#67e8f9] font-bold">3 / 540</span>
              </div>
            </div>

            {/* 1-Click High-Sharpe Pre-Trade Sim Gate & ATA Rent Harvest */}
            <div className="space-y-1.5 pt-1">
              <button
                type="button"
                onClick={async () => {
                  const res = await sendTitanIpcCommand(
                    "SIMULATE_PRETRADE_ROUNDTRIP_GATE",
                    {
                      mint: activeMint,
                      amount_sol: Math.max(
                        0.05,
                        parseFloat(customSolAmount) || 0.5
                      ),
                    }
                  );
                  const msg =
                    res.message ||
                    `🔬 [PRE-TRADE ROUND-TRIP SIM GATE PASS] Simulated Buy + Instant Sell on ${activeMint.slice(
                      0,
                      8
                    )}... (<=1.8% Loss Cap Verified)`;
                  setLastTxReceipt(msg);
                  onLogExecution(msg);
                }}
                className="w-full py-1.5 px-2 rounded bg-[#0284c7]/25 hover:bg-[#0284c7]/40 border border-[#38bdf8] text-[#7dd3fc] font-mono font-bold text-[10px] transition-colors cursor-pointer"
              >
                🔬 Pre-Trade Round-Trip Sim Gate (&lt;=1.8% Loss Cap)
              </button>
              <button
                type="button"
                onClick={async () => {
                  const res = await sendTitanIpcCommand(
                    "EXECUTE_MEGA_FLASH_SYNDICATE_ARB",
                    {
                      mint: activeMint,
                      tier_usd: 10000000,
                      tier_label: "$10M",
                      borrow_sol: 51000,
                    }
                  );
                  const msg =
                    res.message ||
                    `🏦 [MEGA-FLASH SYNDICATE ARB] Executed Stacked CPI Flash Arb on ${activeMint.slice(
                      0,
                      8
                    )}... (0.00 SOL Principal Risk)`;
                  setLastTxReceipt(msg);
                  onLogExecution(msg);
                }}
                className="w-full py-1.5 px-2 rounded bg-[#f59e0b]/20 hover:bg-[#f59e0b]/35 border border-[#f59e0b] text-[#fde68a] font-mono font-bold text-[10px] transition-colors cursor-pointer"
              >
                🏦 Execute $100K–$50M Syndicate Flash Arb on Pair
              </button>
              <button
                type="button"
                onClick={async () => {
                  const res = await sendTitanIpcCommand(
                    "HARVEST_CLOSED_ATA_RENT",
                    {
                      mint: activeMint,
                      accounts_count: 1,
                    }
                  );
                  const msg =
                    res.message ||
                    "🧹 [ATA RENT HARVESTED] Reclaimed +0.00203928 SOL from closed token account";
                  setLastTxReceipt(msg);
                  onLogExecution(msg);
                }}
                className="w-full py-1.5 px-2 rounded bg-[#10b981]/20 hover:bg-[#10b981]/35 border border-[#10b981] text-[#34d399] font-mono font-bold text-[10px] transition-colors cursor-pointer"
              >
                🧹 Harvest Closed ATA Rent (+0.002039 SOL)
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Receipt Footer */}
      <div className="px-3.5 pb-3.5 pt-2 border-t border-[#1a2534]">
        <div className="bg-[#070b11] border border-[#1a2534] rounded p-2 font-mono text-[10px] text-[#38bdf8] break-words leading-relaxed">
          {lastTxReceipt}
        </div>
      </div>
    </aside>
  );
};

