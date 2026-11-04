import React, { useEffect, useRef, useState } from "react";
import { useModuleToggles } from "../hooks/useModuleToggles";
import { usePrivacyMode } from "../hooks/usePrivacyMode";
import {
  closeAppWindow,
  minimizeAppWindow,
  sendTitanIpcCommand,
  toggleMaximizeAppWindow,
} from "../services/titanIpcClient";
import { MacroRegime, TitanTelemetryFrame, VaultMode } from "../types/telemetry";

interface FuturisticMenuBarProps {
  frame: TitanTelemetryFrame;
  activeWorkspace: number;
  onSelectWorkspace: (ws: number) => void;
  onChangeMacroRegime: (regime: MacroRegime) => void;
  onChangeVaultMode: (mode: VaultMode) => void;
  onTogglePauseAll: () => void;
  onPanicFlattenAll: () => void;
  uiScale: number;
  onChangeUiScale: (scale: number) => void;
}

type MenuId =
  | "WORKSPACES"
  | "GOLDEN5"
  | "PROFIT8"
  | "SHIELDS"
  | "MEV_FLASH"
  | "SWARM"
  | "SYSTEM_VPN"
  | null;

export const FuturisticMenuBar: React.FC<FuturisticMenuBarProps> = ({
  frame,
  activeWorkspace,
  onSelectWorkspace,
  onChangeMacroRegime,
  onChangeVaultMode,
  onTogglePauseAll,
  onPanicFlattenAll,
  uiScale,
  onChangeUiScale,
}) => {
  const { isOn, toggleButton } = useModuleToggles(frame);
  const [privacyMode, togglePrivacyMode] = usePrivacyMode();
  const [openMenu, setOpenMenu] = useState<MenuId>(null);
  const [lastMenuAction, setLastMenuAction] = useState<string>(
    "All 7 Command Menus Ready · Sub-1ms RAMDisk IPC Active"
  );
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenu(null);
      }
    };
    window.addEventListener("mousedown", handleClickOutside);
    return () => window.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const g5 = frame.golden5_governor;
  const aiAutoEnabled: boolean = g5?.ai_autonomous_control_enabled ?? true;
  const totalCapitalSol = Number(
    frame.total_equity_sol ??
      Number(g5?.total_contributed_principal_sol ?? 0.0) +
        Number(g5?.accumulated_house_profit_sol ?? 0.0)
  );
  const driftMode = frame.zero_loss_shields?.drift_hedge?.mode ?? "OFF";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const vpnMode =
    frame.colocated_vpn_mesh?.routing_mode ??
    (frame.colocated_vpn_mesh as any)?.active_mode ??
    "LEADER_FOLLOW_AUTO";
  const isParallelVpnMode =
    vpnMode === "PARALLEL_6RELAY_FANOUT" ||
    vpnMode === "MULTI_REGION_6WAY_FANOUT" ||
    vpnMode === "PARALLEL_5_REGION_FANOUT";

  const renderTogglePill = (enabled: boolean) => (
    <span className="inline-flex items-center gap-1.5 shrink-0">
      <span
        className={`px-1.5 py-0.5 rounded text-[9.5px] font-mono font-bold border ${
          enabled
            ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]/60"
            : "bg-[#ef6069]/20 text-[#ef6069] border-[#ef6069]/60"
        }`}
      >
        {enabled ? "🟢 ON" : "🔴 OFF"}
      </span>
      <span className={`titan-switch-track ${enabled ? "is-on" : "is-off"}`}>
        <span className="titan-switch-thumb" />
      </span>
    </span>
  );

  const handleToggleItem = async (
    key: string,
    label: string,
    ipcAction?: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ipcParams?: Record<string, any>
  ) => {
    const res = await toggleButton(key, label, ipcAction, ipcParams);
    setLastMenuAction(res.message);
  };

  const menuBtnCls = (id: MenuId) =>
    `px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold border flex items-center gap-1.5 whitespace-nowrap transition ${
      openMenu === id
        ? "bg-[#35e0b0]/18 text-[#35e0b0] border-[#35e0b0]"
        : "bg-[#0a111d] text-[#d6e3f3] border-[#182638] hover:border-[#35e0b0]/50 hover:text-white"
    }`;

  return (
    <div
      ref={menuRef}
      style={{ zIndex: 9999 }}
      className="w-full h-[38px] min-h-[38px] bg-[#040810]/95 border-b border-[#182638] sticky top-0 z-[9999] backdrop-blur-xl select-none"
    >
      <div className="max-w-[1920px] h-full mx-auto px-4 flex items-center justify-between gap-3">
        {/* Left: Brand Mark + 7 Clean Dropdown Menus */}
        <div className="flex items-center gap-1.5">
          <div className="flex items-center gap-2 pr-2.5 mr-1 border-r border-[#182638]">
            <span
              className={frame.paused_all ? "titan-led-off" : "titan-led-on"}
            />
            <span className="font-mono font-extrabold text-[11.5px] tracking-wider text-white">
              TITAN <span className="text-[#35e0b0]">OS</span>
            </span>
          </div>

          {/* MENU 1: 1 · Workspaces */}
          <div className="relative">
            <button
              type="button"
              onClick={() =>
                setOpenMenu((m) => (m === "WORKSPACES" ? null : "WORKSPACES"))
              }
              className={menuBtnCls("WORKSPACES")}
            >
              <span>1 · Workspaces</span>
              <span className="text-[9px] text-[#35e0b0]">▼</span>
            </button>
            {openMenu === "WORKSPACES" && (
              <div
                style={{ zIndex: 10000 }}
                className="absolute left-0 mt-1.5 w-[355px] rounded-xl bg-[#07101c] border border-[#35e0b0]/60 shadow-[0_20px_50px_rgba(0,0,0,0.95)] p-2 z-[10000] space-y-1"
              >
                <div className="px-2 py-1 text-[9.5px] font-mono uppercase tracking-wider text-[#35e0b0] font-bold border-b border-[#182638]">
                  7 Institutional Command Workspaces (Alt+1..Alt+7)
                </div>
                {[
                  {
                    id: 1,
                    title: "1 · Trading Cockpit",
                    sub: "Superchart · 12 Shields · Live Positions & Sniper Dock",
                  },
                  {
                    id: 2,
                    title: "2 · Alpha & Profit Engines",
                    sub: "Agents 25–32 · Phases 9–13 · 3-Hop Shadow Graph",
                  },
                  {
                    id: 3,
                    title: "3 · MEV & Flash Loans",
                    sub: "Engine A/B/C · Kamino 0.001% Flash · JIT DLMM",
                  },
                  {
                    id: 4,
                    title: "4 · 32-Agent AI Swarm",
                    sub: "96 Subagents · 4-Lane vLLM (:8005/:8006/:8002/:8007)",
                  },
                  {
                    id: 5,
                    title: "5 · Vault & 25 Shards",
                    sub: "80% Reserve Lockbox · 25 Stealth Shards · Solana Pay QR",
                  },
                  {
                    id: 6,
                    title: "6 · Tax & Settings",
                    sub: "FIFO/LIFO Form 8949 · Parquet Ledger · Core 0 Watchdog",
                  },
                  {
                    id: 7,
                    title: "7 · VPN Relay Mesh",
                    sub: "FRA/NYC/AMS/TYO/SLC Colocated Jito WireGuard Mesh",
                  },
                ].map((ws) => {
                  const isActive = activeWorkspace === ws.id;
                  return (
                    <button
                      key={ws.id}
                      type="button"
                      onClick={() => {
                        onSelectWorkspace(ws.id);
                        setLastMenuAction(`Switched to ${ws.title}`);
                        setOpenMenu(null);
                      }}
                      className={`w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 border ${
                        isActive
                          ? "bg-[#35e0b0]/18 border-[#35e0b0] text-white"
                          : "bg-[#0d1828]/80 border-[#182638] text-[#c4d4e6] hover:border-[#35e0b0]/50"
                      }`}
                    >
                      <div className="min-w-0">
                        <div className="text-[10.5px] font-bold truncate">
                          {ws.title}
                        </div>
                        <div className="text-[9px] font-mono text-[#8b9fb7] truncate">
                          {ws.sub}
                        </div>
                      </div>
                      {renderTogglePill(isActive)}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* MENU 2: 2 · Capital Autopilot */}
          <div className="relative">
            <button
              type="button"
              onClick={() =>
                setOpenMenu((m) => (m === "GOLDEN5" ? null : "GOLDEN5"))
              }
              className={menuBtnCls("GOLDEN5")}
            >
              <span>2 · Capital Autopilot</span>
              <span className="text-[9px] text-[#35e0b0]">▼</span>
            </button>
            {openMenu === "GOLDEN5" && (
              <div
                style={{ zIndex: 10000 }}
                className="absolute left-0 mt-1.5 w-[410px] rounded-xl bg-[#07101c] border border-[#35e0b0]/60 shadow-[0_20px_50px_rgba(0,0,0,0.95)] p-2 z-[10000] space-y-1"
              >
                <div className="px-2 py-1 text-[9.5px] font-mono uppercase tracking-wider text-[#35e0b0] font-bold border-b border-[#182638] flex items-center justify-between">
                  <span>Autonomous Capital-Adaptive Engine</span>
                  <span>{totalCapitalSol.toFixed(2)} SOL</span>
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    const res = await sendTitanIpcCommand(
                      "TOGGLE_AI_AUTONOMOUS_CONTROL",
                      {}
                    );
                    setLastMenuAction(
                      res.message || "Toggled AI Autonomous Capital Engine"
                    );
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828] border border-[#182638] hover:border-[#35e0b0]"
                >
                  <div>
                    <div className="text-[10.5px] font-bold text-white">
                      🤖 AI Autonomous Capital Engine (Dual-Control)
                    </div>
                    <div className="text-[9px] font-mono text-[#8b9fb7]">
                      Auto-sizes every strategy from live capital + manual override
                    </div>
                  </div>
                  {renderTogglePill(aiAutoEnabled)}
                </button>

                {[
                  {
                    key: "GOLDEN5_STEP1_STACK",
                    label: "⚡ Atomic Flash, Sanctum LST & Funding Stack",
                    sub: "Auto-scaled 0.001% Kamino flash + Sanctum + Crank + Funding",
                    ipc: "RUN_GOLDEN5_STEP1_FLASH_STACK",
                    params: {},
                  },
                  {
                    key: "GOLDEN5_STEP2_STACK",
                    label: "🎯 65%–84.5% Curve Squeeze & Slot-0 Graduation Sniper",
                    sub: "Auto-sized per-shard allocation + 4 Pre-Entry Shields",
                    ipc: "RUN_GOLDEN5_STEP2_LATE_CURVE_STACK",
                    params: {},
                  },
                  {
                    key: "GOLDEN5_STEP3_STACK",
                    label: "🚀 Asymmetric Bridge, :8002 GPU Vision & CTO Hunters",
                    sub: "Auto-sized from realized profits · Bridge + Vision + CTO",
                    ipc: "RUN_GOLDEN5_STEP3_HOMERUN_STACK",
                    params: {},
                  },
                  {
                    key: "ACTIVATE_5K_DAILY_VELOCITY_PRESET",
                    label: "💰 Uncapped Capital-Adaptive Velocity Scaling",
                    sub: "Auto-scales Kamino Flash, 25 Shards, DLMM & Concurrent Waves",
                    ipc: "ACTIVATE_5K_DAILY_VELOCITY_PRESET",
                    params: {},
                  },
                  {
                    key: "AI_AUTONOMOUS_OPTIMIZER",
                    label: "⚡ AI Auto-Scale All Dashboard Settings By Capital",
                    sub: "Applies optimal Jito tip, Drift hedge & shard sizing",
                    ipc: "APPLY_AI_AUTONOMOUS_OPTIMAL_SETTINGS",
                    params: {},
                  },
                  {
                    key: "BIWEEKLY_CAPITAL_INJECTION",
                    label: "🎲 Inject Random Capital Now (80% Lockbox / 20% Shards)",
                    sub: "80% Protected Reserve Lockbox (0% Risk) + 20% Active Shards",
                    ipc: "RECORD_CAPITAL_INJECTION",
                    params: { random_amount: true },
                  },
                ].map((item) => {
                  const enabled = isOn(item.key, true);
                  return (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() => {
                        void handleToggleItem(
                          item.key,
                          item.label,
                          item.ipc,
                          item.params
                        );
                      }}
                      className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                    >
                      <div className="min-w-0">
                        <div className="text-[10.5px] font-bold text-white truncate">
                          {item.label}
                        </div>
                        <div className="text-[9px] font-mono text-[#8b9fb7] truncate">
                          {item.sub}
                        </div>
                      </div>
                      {renderTogglePill(enabled)}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* MENU 3: 3 · 8 Profit Engines */}
          <div className="relative">
            <button
              type="button"
              onClick={() =>
                setOpenMenu((m) => (m === "PROFIT8" ? null : "PROFIT8"))
              }
              className={menuBtnCls("PROFIT8")}
            >
              <span>3 · 8 Profit Engines</span>
              <span className="text-[9px] text-[#35e0b0]">▼</span>
            </button>
            {openMenu === "PROFIT8" && (
              <div
                style={{ zIndex: 10000 }}
                className="absolute left-0 mt-1.5 w-[415px] rounded-xl bg-[#07101c] border border-[#35e0b0]/60 shadow-[0_20px_50px_rgba(0,0,0,0.95)] p-2 z-[10000] space-y-1"
              >
                <div className="px-2 py-1 text-[9.5px] font-mono uppercase tracking-wider text-[#35e0b0] font-bold border-b border-[#182638]">
                  Phase 13 · All 8 High-Yield Profit Expansion Engines (25–32)
                </div>
                {[
                  {
                    key: "ALL_8_PROFIT_ENGINES",
                    label: "⚡ MASTER SWITCH: All 8 Profit Expansion Engines",
                    sub: "Toggles & executes all 8 engines (Agents 25–32) simultaneously",
                    ipc: "RUN_ALL_8_PROFIT_ENGINES",
                  },
                  {
                    key: "RUN_SANCTUM_LST_FLASH_ARB",
                    label: "1. Agent 25: Sanctum LST Depeg & Epoch Flash Arb",
                    sub: "jitoSOL/mSOL/bSOL/INF vs Sanctum Stake NAV · 0.001% Kamino",
                    ipc: "RUN_SANCTUM_LST_FLASH_ARB",
                  },
                  {
                    key: "RUN_JITO_5TX_SUPERBUNDLE_COMBINER",
                    label: "2. Agent 26: 5-Tx Jito Super-Bundle Combiner",
                    sub: "Packs Tx[0..4] + jitodontfront · +25%–40% Auction Win Boost",
                    ipc: "RUN_JITO_5TX_SUPERBUNDLE_COMBINER",
                  },
                  {
                    key: "RUN_METEORA_DLMM_FEE_SURGE_HARVESTER",
                    label: "3. Agent 27: Meteora DLMM 2.5%–10% Fee Harvester",
                    sub: "3-Bin Active LP + Continuous PumpSwap Delta Hedge",
                    ipc: "RUN_METEORA_DLMM_FEE_SURGE_HARVESTER",
                  },
                  {
                    key: "RUN_DELTA_NEUTRAL_FUNDING_HARVESTER",
                    label: "4. Agent 28: 100% Delta-Neutral Funding Harvester",
                    sub: "+1x jitoSOL + -1x Short Perp (Drift/Jup/Hyperliquid)",
                    ipc: "RUN_DELTA_NEUTRAL_FUNDING_HARVESTER",
                  },
                  {
                    key: "RUN_PROTOCOL_BUYBACK_TAX_CRANK_SNIPER",
                    label: "5. Agent 29: Protocol Buyback & Tax Crank Sniper",
                    sub: "Atomic 3-Step Kamino Flash Sandwich on >=98% Vaults",
                    ipc: "RUN_PROTOCOL_BUYBACK_TAX_CRANK_SNIPER",
                  },
                  {
                    key: "RUN_CROSSCHAIN_WHALE_BRIDGE_LOOKAHEAD",
                    label: "6. Agent 30: Cross-Chain Whale Bridge Lookahead",
                    sub: "3–12s Mayan Swift / deBridge DLN / Relay Pre-Position",
                    ipc: "RUN_CROSSCHAIN_WHALE_BRIDGE_LOOKAHEAD",
                  },
                  {
                    key: "RUN_MULTIMODAL_GPU_VISION_CA_SNIPER",
                    label: "7. Agent 31: GPU :8002 Multimodal Vision Sniper",
                    sub: "<250ms Qwen3.8-27B Screenshot CA OCR (25x–80x Speed)",
                    ipc: "RUN_MULTIMODAL_GPU_VISION_CA_SNIPER",
                  },
                  {
                    key: "RUN_CEX_POLYMARKET_STRIKE_LATENCY_ARB",
                    label: "8. Agent 32: CEX-to-Polymarket Strike Latency Arb",
                    sub: "Black-Scholes Digital Φ(d2) Stale CLOB Ask Sweeper",
                    ipc: "RUN_CEX_POLYMARKET_STRIKE_LATENCY_ARB",
                  },
                ].map((eng) => {
                  const enabled = isOn(eng.key, true);
                  return (
                    <button
                      key={eng.key}
                      type="button"
                      onClick={() =>
                        void handleToggleItem(eng.key, eng.label, eng.ipc)
                      }
                      className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                    >
                      <div className="min-w-0">
                        <div className="text-[10.5px] font-bold text-white truncate">
                          {eng.label}
                        </div>
                        <div className="text-[9px] font-mono text-[#8b9fb7] truncate">
                          {eng.sub}
                        </div>
                      </div>
                      {renderTogglePill(enabled)}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* MENU 4: 4 · Zero-Loss Shields */}
          <div className="relative">
            <button
              type="button"
              onClick={() =>
                setOpenMenu((m) => (m === "SHIELDS" ? null : "SHIELDS"))
              }
              className={menuBtnCls("SHIELDS")}
            >
              <span>4 · Zero-Loss Shields</span>
              <span className="text-[9px] text-[#35e0b0]">▼</span>
            </button>
            {openMenu === "SHIELDS" && (
              <div
                style={{ zIndex: 10000 }}
                className="absolute left-0 mt-1.5 w-[410px] rounded-xl bg-[#07101c] border border-[#35e0b0]/60 shadow-[0_20px_50px_rgba(0,0,0,0.95)] p-2 z-[10000] space-y-1"
              >
                <div className="px-2 py-1 text-[9.5px] font-mono uppercase tracking-wider text-[#35e0b0] font-bold border-b border-[#182638]">
                  Zero-Loss Fortress Shields & On-Chain Forensics
                </div>
                {[
                  {
                    key: "GOLDEN5_SHIELD_6GATE_FIREWALL",
                    label: "Shield 1 (Agent 18): 6-Gate Contract Firewall",
                    sub: "48h Wallet Audit + Arkham 12-Cluster Rug Republic Block",
                    ipc: "RUN_6GATE_CABAL_HUNTER_FORENSICS",
                  },
                  {
                    key: "GOLDEN5_SHIELD_TARJAN_SCC",
                    label: "Shield 2: Tarjan SCC Sybil & Wash Filter",
                    sub: "Requires >=65% Organic Non-Circular Volume",
                    ipc: "RUN_DECEPTIVE_COUNTER_EXPLOIT_SUITE",
                  },
                  {
                    key: "GOLDEN5_SHIELD_SALMONELLA_TOKEN2022",
                    label: "Shield 3 (Agent 24): Salmonella & FoT Guard",
                    sub: "Multi-Origin Sim + Token-2022 PermanentDelegate Block",
                    ipc: "RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD",
                  },
                  {
                    key: "GOLDEN5_SHIELD_SVM_ROUNDTRIP",
                    label: "Shield 4: <0.4ms Local SVM Roundtrip Guard",
                    sub: "Simulates Atomic Buy+Sell Before Any Entry",
                    ipc: "RUN_ROUNDTRIP_PREFLIGHT",
                  },
                  {
                    key: "RUN_PRE_MINT_PEEL_CHAIN_LISTENER",
                    label: "Agent 17: Shred Pre-Mint 8-Burner Peel Listener",
                    sub: "6x CabalSpy WS + 65%–78% Curve Squeeze Math",
                    ipc: "RUN_PRE_MINT_PEEL_CHAIN_LISTENER",
                  },
                  {
                    key: "RUN_JITO_KNAPSACK_DONTFRONT_JUDGE",
                    label: "Agent 19/20: Jito Knapsack & jitodontfront Judge",
                    sub: "2-Stage Tip/CU Solver + Index-0 Contiguity Validator",
                    ipc: "RUN_JITO_KNAPSACK_DONTFRONT_JUDGE",
                  },
                  {
                    key: "RUN_MELT_MEMETRANS_AUDIT",
                    label: "MELT 122-Feature & MemeTrans Bundle Audit",
                    sub: "De-clusters Creator/Sniper Wash Bundles",
                    ipc: "RUN_MELT_MEMETRANS_AUDIT",
                  },
                  {
                    key: "RUN_RUG_PULL_HORIZON_CHECK",
                    label: "Short-Horizon 240s Rug Guard & LP Cliff Monitor",
                    sub: "Front-Runs Dev Removals via ShredStream",
                    ipc: "RUN_RUG_PULL_HORIZON_CHECK",
                  },
                ].map((sh) => {
                  const enabled = isOn(sh.key, true);
                  return (
                    <button
                      key={sh.key}
                      type="button"
                      onClick={() =>
                        void handleToggleItem(sh.key, sh.label, sh.ipc)
                      }
                      className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                    >
                      <div className="min-w-0">
                        <div className="text-[10.5px] font-bold text-white truncate">
                          {sh.label}
                        </div>
                        <div className="text-[9px] font-mono text-[#8b9fb7] truncate">
                          {sh.sub}
                        </div>
                      </div>
                      {renderTogglePill(enabled)}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* MENU 5: 5 · MEV & Flash */}
          <div className="relative">
            <button
              type="button"
              onClick={() =>
                setOpenMenu((m) => (m === "MEV_FLASH" ? null : "MEV_FLASH"))
              }
              className={menuBtnCls("MEV_FLASH")}
            >
              <span>5 · MEV &amp; Flash</span>
              <span className="text-[9px] text-[#35e0b0]">▼</span>
            </button>
            {openMenu === "MEV_FLASH" && (
              <div
                style={{ zIndex: 10000 }}
                className="absolute left-0 mt-1.5 w-[410px] rounded-xl bg-[#07101c] border border-[#35e0b0]/60 shadow-[0_20px_50px_rgba(0,0,0,0.95)] p-2 z-[10000] space-y-1"
              >
                <div className="px-2 py-1 text-[9.5px] font-mono uppercase tracking-wider text-[#35e0b0] font-bold border-b border-[#182638]">
                  MEV Triad (Engine A/B/C) &amp; Zero-Collateral Flash Suite
                </div>
                {[
                  {
                    key: "ENGINE_A_BACKRUNNER_TOGGLE",
                    label: "Engine A: Kamino 0.001% Flash Backrunner",
                    sub: "2,000-Pool Zero-Copy Mirror · Closed-Form Optimal Borrow",
                    ipc: "SIMULATE_FLASH_LOAN",
                  },
                  {
                    key: "ENGINE_B_SANDWICH_TOGGLE",
                    label: "Engine B: Atomic 3-Tx Jito Bundle Sandwich",
                    sub: "14% Uncontested Tip Floor (86% Profit Retained)",
                    ipc: "EXECUTE_ATOMIC_SANDWICH",
                  },
                  {
                    key: "ENGINE_C_JIT_DLMM_TOGGLE",
                    label: "Engine C: Single-Tick 4,000x JIT Liquidity",
                    sub: "Flash-Amplified Active Tick LP + Cross-Pool Delta Hedge",
                    ipc: "DEPLOY_JIT_DLMM",
                  },
                  {
                    key: "RUN_SLOT0_845_MIGRATION_SUITE",
                    label: "Agent 14: 80% Pre-Warm & 84.5 SOL Slot-0 Sniper",
                    sub: "<5ms PumpSwap Migration Snipe + Kamino Atomic Liquidator",
                    ipc: "RUN_SLOT0_845_MIGRATION_SUITE",
                  },
                  {
                    key: "RUN_DECEPTIVE_CTO_SUITE",
                    label: "Agent 13: Deceptive CTO Counter-Exploiter",
                    sub: "Genuine CTO Ride vs Cabal V-Shape Trap Dump-Into-Cabal",
                    ipc: "RUN_DECEPTIVE_CTO_SUITE",
                  },
                  {
                    key: "RUN_ZERO_COLLATERAL_FLASH_PRIMITIVES",
                    label: "Agent 21: Zero-Collateral 7-Venue Flash Primitives",
                    sub: "#![no_std] Byte [64..72] + Durable Nonce Dual-Route",
                    ipc: "RUN_ZERO_COLLATERAL_FLASH_PRIMITIVES",
                  },
                  {
                    key: "RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE",
                    label: "Agent 22: Forced Graduation & CLMM Spoof Guard",
                    sub: "92%->100% Flash Sweep + $1.4B Phantom CLMM Blocker",
                    ipc: "RUN_COVERT_MIGRATION_JIT_SPOOF_SUITE",
                  },
                  {
                    key: "RUN_NEXTGEN_MAYHEM_V4HOOK_MULTIPLY_SUITE",
                    label: "Agent 23: Mayhem Mode AI Backrun & Base V4 Hook",
                    sub: "90+ Quote Pairs + Hour-24 Burn + 5x Multiply Squeeze",
                    ipc: "RUN_NEXTGEN_MAYHEM_V4HOOK_MULTIPLY_SUITE",
                  },
                ].map((item) => {
                  const enabled = isOn(item.key, true);
                  return (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() =>
                        void handleToggleItem(item.key, item.label, item.ipc)
                      }
                      className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                    >
                      <div className="min-w-0">
                        <div className="text-[10.5px] font-bold text-white truncate">
                          {item.label}
                        </div>
                        <div className="text-[9px] font-mono text-[#8b9fb7] truncate">
                          {item.sub}
                        </div>
                      </div>
                      {renderTogglePill(enabled)}
                    </button>
                  );
                })}

                <div className="px-2 pt-1.5 pb-1 text-[9.5px] font-mono uppercase tracking-wider text-[#fde68a] font-bold border-t border-[#182638]">
                  $100K / $1M / $10M / $50M Mega-Flash Syndicate &amp; Ecosystem
                </div>
                {[
                  {
                    tier_usd: 100000,
                    tier_label: "$100K",
                    label:
                      "⚡ $100K Flash Syndicate Tier (~510 SOL · 0.0 bps MarginFi)",
                    sub: "Single-Tx MarginFi V2 0.00% Flash Loan · 0.00 SOL Principal Risk",
                  },
                  {
                    tier_usd: 1000000,
                    tier_label: "$1M",
                    label:
                      "🏦 $1M Flash Syndicate Tier (~5,100 SOL · MarginFi + Kamino)",
                    sub: "Dual-Protocol Stacked CPI (0.03 bps Blended Fee)",
                  },
                  {
                    tier_usd: 10000000,
                    tier_label: "$10M",
                    label:
                      "🏛️ $10M Flash Syndicate Tier (~51,000 SOL · 4-Protocol Stack)",
                    sub: "MarginFi + Kamino + Sanctum/JLP + Save (0.06 bps Blended Fee)",
                  },
                  {
                    tier_usd: 50000000,
                    tier_label: "$50M",
                    label:
                      "👑 $50M Mega-Flash Syndicate (~255,000 SOL · Full 5-Tx Super-Bundle)",
                    sub: "All 7 Solana Flash Pools + Jito 5-Tx Super-Bundle (0.14 bps Fee)",
                  },
                ].map((tier) => {
                  const activeTierUsd =
                    frame.mega_flash_syndicate?.active_tier_usd ?? 10000000;
                  const isActiveTier = activeTierUsd === tier.tier_usd;
                  return (
                    <button
                      key={tier.tier_label}
                      type="button"
                      onClick={async () => {
                        const res = await sendTitanIpcCommand(
                          "SET_MEGA_FLASH_SYNDICATE_TIER",
                          {
                            tier_usd: tier.tier_usd,
                            tier_label: tier.tier_label,
                          }
                        );
                        setLastMenuAction(
                          String(
                            res.message ||
                              `Mega-Flash Syndicate Tier -> ${tier.tier_label}`
                          )
                        );
                      }}
                      className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#f59e0b]"
                    >
                      <div className="min-w-0">
                        <div className="text-[10.5px] font-bold text-[#fde68a] truncate">
                          {tier.label}
                        </div>
                        <div className="text-[9px] font-mono text-[#8b9fb7] truncate">
                          {tier.sub}
                        </div>
                      </div>
                      {renderTogglePill(isActiveTier)}
                    </button>
                  );
                })}

                <button
                  type="button"
                  onClick={async () => {
                    const res = await sendTitanIpcCommand(
                      "RUN_WHOLE_SOLANA_ECOSYSTEM_SWEEP",
                      {}
                    );
                    setLastMenuAction(
                      String(
                        res.message ||
                          "Executed Whole-Solana Ecosystem Mega-Flash Sweep"
                      )
                    );
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0a1d17] border border-[#10b981]/60 hover:border-[#34d399]"
                >
                  <div className="min-w-0">
                    <div className="text-[10.5px] font-bold text-[#34d399] truncate">
                      🌐 Execute Whole-Solana Ecosystem Mega-Flash Sweep
                    </div>
                    <div className="text-[9px] font-mono text-[#8b9fb7] truncate">
                      CLMM/DLMM Water-Fill + INF 50-LST + JLP Basis + Liquidations
                    </div>
                  </div>
                  <span className="titan-pill positive">FIRE</span>
                </button>
              </div>
            )}
          </div>

          {/* MENU 6: 6 · 32-Agent Swarm */}
          <div className="relative">
            <button
              type="button"
              onClick={() =>
                setOpenMenu((m) => (m === "SWARM" ? null : "SWARM"))
              }
              className={menuBtnCls("SWARM")}
            >
              <span>6 · 32-Agent Swarm</span>
              <span className="text-[9px] text-[#35e0b0]">▼</span>
            </button>
            {openMenu === "SWARM" && (
              <div
                style={{ zIndex: 10000 }}
                className="absolute right-0 mt-1.5 w-[395px] rounded-xl bg-[#07101c] border border-[#35e0b0]/60 shadow-[0_20px_50px_rgba(0,0,0,0.95)] p-2 z-[10000] space-y-1"
              >
                <div className="px-2 py-1 text-[9.5px] font-mono uppercase tracking-wider text-[#35e0b0] font-bold border-b border-[#182638]">
                  32 Primary Agents / 96 Subagents &amp; 4-Lane vLLM Swarm
                </div>
                <button
                  type="button"
                  onClick={() =>
                    void handleToggleItem(
                      "RUN_SWARM_HEALTH_CHECK",
                      "32-Agent / 96-Subagent Swarm Health",
                      "RUN_SWARM_HEALTH_CHECK"
                    )
                  }
                  className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                >
                  <div>
                    <div className="text-[10.5px] font-bold text-white">
                      🤖 32 Primary Agents / 96 Subagents (96 CPU Threads)
                    </div>
                    <div className="text-[9px] font-mono text-[#8b9fb7]">
                      Ports :8005, :8006, :8002, :8007 · GEPA Prompt Arena
                    </div>
                  </div>
                  {renderTogglePill(isOn("RUN_SWARM_HEALTH_CHECK", true))}
                </button>

                <button
                  type="button"
                  onClick={() => {
                    onSelectWorkspace(4);
                    setOpenMenu(null);
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                >
                  <span className="text-[10.5px] font-bold text-white">
                    🧠 Open 32-Agent Swarm &amp; GEPA Arena (Alt+4)
                  </span>
                  <span className="titan-pill positive">OPEN</span>
                </button>
              </div>
            )}
          </div>

          {/* MENU 7: 7 · System & VPN */}
          <div className="relative">
            <button
              type="button"
              onClick={() =>
                setOpenMenu((m) => (m === "SYSTEM_VPN" ? null : "SYSTEM_VPN"))
              }
              className={menuBtnCls("SYSTEM_VPN")}
            >
              <span>7 · System &amp; VPN</span>
              <span className="text-[9px] text-[#35e0b0]">▼</span>
            </button>
            {openMenu === "SYSTEM_VPN" && (
              <div
                style={{ zIndex: 10000 }}
                className="absolute right-0 mt-1.5 w-[390px] rounded-xl bg-[#07101c] border border-[#35e0b0]/60 shadow-[0_20px_50px_rgba(0,0,0,0.95)] p-2 z-[10000] space-y-1"
              >
                <div className="px-2 py-1 text-[9.5px] font-mono uppercase tracking-wider text-[#35e0b0] font-bold border-b border-[#182638]">
                  Capital Mode, Macro Regime, 5-Region VPN &amp; System Controls
                </div>
                {(["PAPER", "CANARY", "LIVE"] as VaultMode[]).map((m) => {
                  const active = frame.graduation.mode === m;
                  return (
                    <button
                      key={m}
                      type="button"
                      onClick={() => {
                        onChangeVaultMode(m);
                        setLastMenuAction(`Capital Mode set to ${m}`);
                      }}
                      className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                    >
                      <span className="text-[10.5px] font-bold text-white">
                        Capital Mode: {m} (
                        {m === "PAPER"
                          ? "0 Shards"
                          : m === "CANARY"
                          ? "4 Shards · 15%"
                          : "25 Shards · 100%"}
                        )
                      </span>
                      {renderTogglePill(active)}
                    </button>
                  );
                })}

                {(
                  ["GREEN", "AMBER", "RED_MACRO_FLUSH"] as MacroRegime[]
                ).map((reg) => {
                  const active = String(
                    frame.macro_directive.regime
                  ).startsWith(reg.split("_")[0]);
                  return (
                    <button
                      key={reg}
                      type="button"
                      onClick={() => {
                        onChangeMacroRegime(reg);
                        setLastMenuAction(`Macro Regime set to ${reg}`);
                      }}
                      className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                    >
                      <span className="text-[10.5px] font-bold text-white">
                        Macro Regime: {reg}
                      </span>
                      {renderTogglePill(active)}
                    </button>
                  );
                })}

                <button
                  type="button"
                  onClick={async () => {
                    const nextHedge =
                      driftMode === "FULL_100PCT" ? "OFF" : "FULL_100PCT";
                    await sendTitanIpcCommand("SET_DRIFT_HEDGE_MODE", {
                      mode: nextHedge,
                    });
                    setLastMenuAction(`Drift SOL-PERP Hedge -> ${nextHedge}`);
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                >
                  <span className="text-[10.5px] font-bold text-white">
                    Drift 100% Delta-Neutral SOL-PERP Hedge
                  </span>
                  {renderTogglePill(driftMode !== "OFF")}
                </button>

                <button
                  type="button"
                  onClick={async () => {
                    const nextVpn =
                      vpnMode === "LEADER_FOLLOW_AUTO"
                        ? "PARALLEL_6RELAY_FANOUT"
                        : "LEADER_FOLLOW_AUTO";
                    await sendTitanIpcCommand("SWITCH_COLOCATED_VPN_MODE", {
                      routing_mode: nextVpn,
                    });
                    setLastMenuAction(`VPN Routing Mode -> ${nextVpn}`);
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                >
                  <span className="text-[10.5px] font-bold text-white">
                    🌐 VPN Auto-Leader Follow ({vpnMode})
                  </span>
                  {renderTogglePill(vpnMode === "LEADER_FOLLOW_AUTO")}
                </button>

                <button
                  type="button"
                  onClick={async () => {
                    const nextVpn = isParallelVpnMode
                      ? "LEADER_FOLLOW_AUTO"
                      : "PARALLEL_6RELAY_FANOUT";
                    await sendTitanIpcCommand("SWITCH_COLOCATED_VPN_MODE", {
                      routing_mode: nextVpn,
                    });
                    setLastMenuAction(`VPN Routing Mode -> ${nextVpn}`);
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                >
                  <span className="text-[10.5px] font-bold text-white">
                    ⚡ Parallel 6-Relay Fan-Out (5 Jito + SWQoS)
                  </span>
                  {renderTogglePill(isParallelVpnMode)}
                </button>

                <button
                  type="button"
                  onClick={async () => {
                    await sendTitanIpcCommand("PROBE_COLOCATED_VPN_MESH", {});
                    setLastMenuAction("Probed 5 Jito Regions + NICs");
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                >
                  <span className="text-[10.5px] font-bold text-white">
                    📡 Live 5-Region Jito TCP &amp; NIC Probe
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[9.5px] font-mono font-bold border bg-[#f2b33d]/20 text-[#f2b33d] border-[#f2b33d]/60">
                    [PROBE]
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    togglePrivacyMode();
                    setLastMenuAction(
                      `Privacy Mode ${!privacyMode ? "🟢 ON" : "🔴 OFF"}`
                    );
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left flex items-center justify-between gap-2 bg-[#0d1828]/90 border border-[#182638] hover:border-[#35e0b0]"
                >
                  <span className="text-[10.5px] font-bold text-white">
                    🔒 Privacy Mode (Mask SOL &amp; USD Balances)
                  </span>
                  {renderTogglePill(privacyMode)}
                </button>

                <div className="flex items-center justify-between px-2.5 py-1.5 bg-[#0d1828]/90 rounded-lg border border-[#182638]">
                  <span className="text-[10.5px] font-bold text-white">
                    🔍 UI Zoom Scale ({Math.round(uiScale * 100)}%)
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      onClick={() =>
                        onChangeUiScale(
                          Math.max(0.85, Number((uiScale - 0.05).toFixed(2)))
                        )
                      }
                      className="px-2 py-0.5 rounded bg-[#162436] text-white text-[10px] font-mono"
                    >
                      -
                    </button>
                    <button
                      type="button"
                      onClick={() => onChangeUiScale(1.0)}
                      className="px-2 py-0.5 rounded bg-[#162436] text-[#35e0b0] text-[10px] font-mono"
                    >
                      100%
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        onChangeUiScale(
                          Math.min(1.1, Number((uiScale + 0.05).toFixed(2)))
                        )
                      }
                      className="px-2 py-0.5 rounded bg-[#162436] text-white text-[10px] font-mono"
                    >
                      +
                    </button>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    onPanicFlattenAll();
                    setOpenMenu(null);
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-center font-mono font-bold text-[10.5px] bg-[#ef6069] text-[#070b11] hover:opacity-95"
                >
                  🚨 [F12] EMERGENCY PANIC FLATTEN ALL POSITIONS
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Center: Concise Status Indicator */}
        <div className="hidden xl:flex items-center gap-2 px-3 py-0.5 rounded-md bg-[#09101b] border border-[#182638] text-[10.5px] font-mono text-[#8b9fb7] truncate max-w-[440px]">
          <span className="text-[#35e0b0] font-bold shrink-0">IPC 120Hz</span>
          <span className="text-[#283e5c]">·</span>
          <span className="truncate">{lastMenuAction}</span>
        </div>

        {/* Right: Native Window Controls (─, □, ✕) */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={async () => {
              await minimizeAppWindow();
              setLastMenuAction("Window Minimized");
            }}
            title="Minimize Window"
            className="w-7 h-6 rounded flex items-center justify-center text-[11px] font-mono font-bold bg-[#0a111d] hover:bg-[#162436] text-[#8b9fb7] hover:text-white border border-[#182638] transition"
          >
            ─
          </button>
          <button
            type="button"
            onClick={async () => {
              const isMax = await toggleMaximizeAppWindow();
              setLastMenuAction(
                isMax ? "Window Maximized" : "Window Restored"
              );
            }}
            title="Maximize / Restore Window"
            className="w-7 h-6 rounded flex items-center justify-center text-[11px] font-mono font-bold bg-[#0a111d] hover:bg-[#162436] text-[#8b9fb7] hover:text-[#35e0b0] border border-[#182638] transition"
          >
            □
          </button>
          <button
            type="button"
            onClick={() => {
              void closeAppWindow();
            }}
            title="Close Command Center (Backend Daemons Continue Running)"
            className="w-7 h-6 rounded flex items-center justify-center text-[11px] font-mono font-bold bg-[#1a0b10] hover:bg-[#ef6069] text-[#ff858d] hover:text-[#060a12] border border-[#ef6069]/50 transition"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
};
