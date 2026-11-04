import React, { useEffect, useState } from "react";
import { useModuleToggles } from "../hooks/useModuleToggles";
import { usePrivacyMode } from "../hooks/usePrivacyMode";
import { sendTitanIpcCommand } from "../services/titanIpcClient";
import { TitanTelemetryFrame } from "../types/telemetry";

interface FuturisticHoloDeckProps {
  frame: TitanTelemetryFrame;
  activeWorkspace: number;
  onSelectWorkspace: (ws: number) => void;
}

interface PowerMatrixItem {
  key: string;
  label: string;
  sub: string;
  category: "GOLDEN_5" | "PROFIT_8" | "SHIELDS" | "ENGINES";
  ipcAction?: string;
  ipcParams?: Record<string, unknown>;
}

const POWER_MATRIX_ITEMS: PowerMatrixItem[] = [
  {
    key: "GOLDEN5_STEP1_STACK",
    label: "Atomic Flash & Sanctum Stack",
    sub: "Auto-Scaled · 0% Principal Risk",
    category: "GOLDEN_5",
    ipcAction: "RUN_GOLDEN5_STEP1_FLASH_STACK",
  },
  {
    key: "GOLDEN5_STEP2_STACK",
    label: "65%–84.5% Curve Squeeze & Slot-0",
    sub: "Auto-Sized Per-Shard Allocation",
    category: "GOLDEN_5",
    ipcAction: "RUN_GOLDEN5_STEP2_LATE_CURVE_STACK",
  },
  {
    key: "GOLDEN5_STEP3_STACK",
    label: "3x–10x Bridge, Vision & CTO",
    sub: "Auto-Sized From Realized Profit",
    category: "GOLDEN_5",
    ipcAction: "RUN_GOLDEN5_STEP3_HOMERUN_STACK",
  },
  {
    key: "AI_AUTONOMOUS_OPTIMIZER",
    label: "AI Autonomous Capital Engine",
    sub: "100% Capital-Adaptive Autopilot",
    category: "GOLDEN_5",
    ipcAction: "APPLY_AI_AUTONOMOUS_OPTIMAL_SETTINGS",
  },
  {
    key: "RUN_SANCTUM_LST_FLASH_ARB",
    label: "Agent 25: Sanctum LST Flash Arb",
    sub: "0.001% Kamino · jitoSOL/mSOL/INF",
    category: "PROFIT_8",
    ipcAction: "RUN_SANCTUM_LST_FLASH_ARB",
  },
  {
    key: "RUN_JITO_5TX_SUPERBUNDLE_COMBINER",
    label: "Agent 26: 5-Tx Super-Bundle",
    sub: "+25%–40% Jito Win-Rate Boost",
    category: "PROFIT_8",
    ipcAction: "RUN_JITO_5TX_SUPERBUNDLE_COMBINER",
  },
  {
    key: "RUN_METEORA_DLMM_FEE_SURGE_HARVESTER",
    label: "Agent 27: Meteora DLMM Fee Surge",
    sub: "2.5%–10% Dynamic Fee Harvest",
    category: "PROFIT_8",
    ipcAction: "RUN_METEORA_DLMM_FEE_SURGE_HARVESTER",
  },
  {
    key: "RUN_DELTA_NEUTRAL_FUNDING_HARVESTER",
    label: "Agent 28: Delta-Neutral Funding",
    sub: "jitoSOL + 1x Short SOL-PERP",
    category: "PROFIT_8",
    ipcAction: "RUN_DELTA_NEUTRAL_FUNDING_HARVESTER",
  },
  {
    key: "RUN_PROTOCOL_BUYBACK_TAX_CRANK_SNIPER",
    label: "Agent 29: Buyback & Tax Crank",
    sub: "3-Step Kamino Crank Sandwich",
    category: "PROFIT_8",
    ipcAction: "RUN_PROTOCOL_BUYBACK_TAX_CRANK_SNIPER",
  },
  {
    key: "RUN_CROSSCHAIN_WHALE_BRIDGE_LOOKAHEAD",
    label: "Agent 30: Cross-Chain Bridge",
    sub: "3–12s Mayan/deBridge Lookahead",
    category: "PROFIT_8",
    ipcAction: "RUN_CROSSCHAIN_WHALE_BRIDGE_LOOKAHEAD",
  },
  {
    key: "RUN_MULTIMODAL_GPU_VISION_CA_SNIPER",
    label: "Agent 31: GPU :8002 Vision Sniper",
    sub: "<250ms Tier-1 Screenshot OCR",
    category: "PROFIT_8",
    ipcAction: "RUN_MULTIMODAL_GPU_VISION_CA_SNIPER",
  },
  {
    key: "RUN_CEX_POLYMARKET_STRIKE_LATENCY_ARB",
    label: "Agent 32: Polymarket Strike Arb",
    sub: "Black-Scholes Digital CLOB Sweep",
    category: "PROFIT_8",
    ipcAction: "RUN_CEX_POLYMARKET_STRIKE_LATENCY_ARB",
  },
  {
    key: "GOLDEN5_SHIELD_6GATE_FIREWALL",
    label: "Shield 1: 6-Gate Contract Firewall",
    sub: "Agent 18 · Rug Republic Filter",
    category: "SHIELDS",
    ipcAction: "RUN_6GATE_CABAL_HUNTER_FORENSICS",
  },
  {
    key: "GOLDEN5_SHIELD_TARJAN_SCC",
    label: "Shield 2: Tarjan SCC Sybil Guard",
    sub: "Organic Volume >= 65% Gate",
    category: "SHIELDS",
    ipcAction: "RUN_DECEPTIVE_COUNTER_EXPLOIT_SUITE",
  },
  {
    key: "GOLDEN5_SHIELD_SALMONELLA_TOKEN2022",
    label: "Shield 3: Salmonella & FoT Guard",
    sub: "Agent 24 · Token-2022 Trap Block",
    category: "SHIELDS",
    ipcAction: "RUN_SALMONELLA_FOT_ADVERSARIAL_SHIELD",
  },
  {
    key: "GOLDEN5_SHIELD_SVM_ROUNDTRIP",
    label: "Shield 4: <0.4ms SVM Roundtrip",
    sub: "Pre-Flight Buy+Sell Verification",
    category: "SHIELDS",
    ipcAction: "RUN_ROUNDTRIP_PREFLIGHT",
  },
  {
    key: "ENGINE_A_BACKRUNNER_TOGGLE",
    label: "Engine A: Kamino Flash Backrunner",
    sub: "2,000-Pool Zero-Copy Mirror",
    category: "ENGINES",
    ipcAction: "SIMULATE_FLASH_LOAN",
  },
  {
    key: "ENGINE_B_SANDWICH_TOGGLE",
    label: "Engine B: Atomic 3-Tx Sandwich",
    sub: "14% Uncontested Jito Tip Floor",
    category: "ENGINES",
    ipcAction: "EXECUTE_ATOMIC_SANDWICH",
  },
  {
    key: "ENGINE_C_JIT_DLMM_TOGGLE",
    label: "Engine C: JIT DLMM Liquidity",
    sub: "Single-Tick 4,000x Efficiency",
    category: "ENGINES",
    ipcAction: "DEPLOY_JIT_DLMM",
  },
  {
    key: "RUN_SLOT0_845_MIGRATION_SUITE",
    label: "Agent 14: 84.5 SOL Slot-0 Sniper",
    sub: "80% Pre-Warm · <5ms PumpSwap",
    category: "ENGINES",
    ipcAction: "RUN_SLOT0_845_MIGRATION_SUITE",
  },
];

export const FuturisticHoloDeck: React.FC<FuturisticHoloDeckProps> = ({
  frame,
  activeWorkspace,
  onSelectWorkspace,
}) => {
  const { isOn, toggleButton, setBatchModuleToggles } = useModuleToggles(frame);
  const [privacyMode] = usePrivacyMode();
  const [expanded, setExpanded] = useState<boolean>(false);
  const [showMatrix, setShowMatrix] = useState<boolean>(false);
  const [matrixFilter, setMatrixFilter] = useState<
    "ALL" | "GOLDEN_5" | "PROFIT_8" | "SHIELDS" | "ENGINES"
  >("ALL");
  const [wavePhase, setWavePhase] = useState<number>(0);
  const [lastActionMsg, setLastActionMsg] = useState<string>(
    "All 20 Strategy & Shield Modules Synchronized · Click any switch to toggle ON/OFF"
  );

  // Smooth 20fps waveform animation for the live oscilloscope
  useEffect(() => {
    const id = window.setInterval(() => {
      setWavePhase((p) => (p + 1) % 360);
    }, 60);
    return () => window.clearInterval(id);
  }, []);

  const g5 = frame.golden5_governor;
  const aiAutoEnabled: boolean = g5?.ai_autonomous_control_enabled ?? true;
  const houseProfitSol: number =
    g5?.accumulated_house_profit_sol ??
    frame.zero_loss_shields?.daily_realized_net_sol ??
    0.0;
  const totalCapitalSol = Number(
    frame.total_equity_sol ??
      Number(g5?.total_contributed_principal_sol ?? 0.0) + houseProfitSol
  );

  const activeCount = POWER_MATRIX_ITEMS.filter((item) =>
    isOn(item.key, true)
  ).length;

  const handleToggleAllMatrix = async (turnOn: boolean) => {
    const allKeys = POWER_MATRIX_ITEMS.map((item) => item.key);
    await setBatchModuleToggles(allKeys, turnOn, "Master Power Matrix");
    setLastActionMsg(
      turnOn
        ? `🟢 [MASTER POWER ON] All ${POWER_MATRIX_ITEMS.length} Modules & Profit Engines Armed (🟢 ON)`
        : `🔴 [MASTER POWER OFF] All ${POWER_MATRIX_ITEMS.length} Modules Paused (🔴 OFF)`
    );
  };

  const filteredMatrix =
    matrixFilter === "ALL"
      ? POWER_MATRIX_ITEMS
      : POWER_MATRIX_ITEMS.filter((i) => i.category === matrixFilter);

  // Build animated sine wave path for the live oscilloscope
  const wavePoints: string[] = [];
  for (let x = 0; x <= 240; x += 6) {
    const rad = ((x * 2.2 + wavePhase * 8) * Math.PI) / 180;
    const rad2 = ((x * 4.1 - wavePhase * 12) * Math.PI) / 180;
    const amp = frame.paused_all ? 2 : 11;
    const y = 24 + Math.sin(rad) * amp + Math.cos(rad2) * (amp * 0.45);
    wavePoints.push(`${x},${y.toFixed(1)}`);
  }

  return (
    <div className="w-full max-w-[1920px] mx-auto px-4 pt-1.5">
      <div className="titan-panel border-[#182638] bg-[#08101c]/95">
        {/* Compact 1-Line Quick-Power Switchboard Bar */}
        <div
          className={`px-3.5 py-1.5 flex flex-wrap items-center justify-between gap-2 ${
            expanded || showMatrix ? "border-b border-[#182638]" : ""
          }`}
        >
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono font-bold text-[#e6eef8]">
              <span className="titan-led-on" />
              <span>🎛️ QUICK POWER SWITCHBOARD:</span>
              <span className="text-[#35e0b0]">
                {activeCount}/{POWER_MATRIX_ITEMS.length} MODULES ON
              </span>
            </span>
            <span className="text-[10.5px] font-mono text-[#8b9fb7] hidden lg:inline truncate max-w-[520px]">
              · {lastActionMsg}
            </span>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              type="button"
              onClick={() => handleToggleAllMatrix(true)}
              className="px-2.5 py-1 rounded-md text-[10px] font-mono font-bold bg-[#35e0b0]/16 hover:bg-[#35e0b0]/28 text-[#35e0b0] border border-[#35e0b0]/50 flex items-center gap-1.5"
              title="Turn ALL 20 Strategy & Shield Modules ON"
            >
              <span className="titan-led-on" />
              ALL ON
            </button>
            <button
              type="button"
              onClick={() => handleToggleAllMatrix(false)}
              className="px-2.5 py-1 rounded-md text-[10px] font-mono font-bold bg-[#ef6069]/15 hover:bg-[#ef6069]/25 text-[#ef6069] border border-[#ef6069]/45 flex items-center gap-1.5"
              title="Turn ALL Modules OFF"
            >
              <span className="titan-led-off" />
              ALL OFF
            </button>
            <button
              type="button"
              onClick={() => setShowMatrix((s) => !s)}
              className={`px-2.5 py-1 rounded-md text-[10px] font-mono font-bold border flex items-center gap-1.5 ${
                showMatrix
                  ? "bg-[#5b9dff]/22 text-[#5b9dff] border-[#5b9dff]"
                  : "bg-[#0d1726] text-[#9fb3c8] border-[#182638] hover:text-white"
              }`}
            >
              🎛️ Power Matrix {showMatrix ? "[OPEN]" : ""}
            </button>
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              className={`px-2.5 py-1 rounded-md text-[10px] font-mono font-bold border ${
                expanded
                  ? "bg-[#35e0b0]/18 text-[#35e0b0] border-[#35e0b0]/60"
                  : "bg-[#0d1726] hover:bg-[#152338] text-[#8b9fb7] hover:text-white border-[#182638]"
              }`}
            >
              {expanded ? "▲ Collapse HUD" : "▼ Expand HUD"}
            </button>
          </div>
        </div>

        {/* Interactive Futuristic 3-Column Visual Deck */}
        {expanded && (
          <div className="p-3 grid grid-cols-1 lg:grid-cols-12 gap-3 items-stretch">
            {/* 1. Interactive 3-Ring Orbital Radar (3 cols) */}
            <div className="lg:col-span-3 bg-[#070d17]/90 border border-[#1a293d] rounded-xl p-2.5 flex items-center gap-3 relative overflow-hidden">
              <div className="relative w-[96px] h-[96px] shrink-0 flex items-center justify-center">
                <svg
                  viewBox="0 0 100 100"
                  className="w-full h-full overflow-visible"
                >
                  {/* Concentric radar rings */}
                  <circle
                    cx="50"
                    cy="50"
                    r="44"
                    fill="none"
                    stroke="rgba(53, 224, 176, 0.22)"
                    strokeWidth="1"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="30"
                    fill="none"
                    stroke="rgba(91, 157, 255, 0.22)"
                    strokeWidth="1"
                    strokeDasharray="3 3"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="16"
                    fill="none"
                    stroke="rgba(167, 139, 250, 0.28)"
                    strokeWidth="1"
                  />
                  {/* Crosshairs */}
                  <line
                    x1="6"
                    y1="50"
                    x2="94"
                    y2="50"
                    stroke="rgba(53, 224, 176, 0.14)"
                    strokeWidth="0.8"
                  />
                  <line
                    x1="50"
                    y1="6"
                    x2="50"
                    y2="94"
                    stroke="rgba(53, 224, 176, 0.14)"
                    strokeWidth="0.8"
                  />
                  {/* Rotating Radar Sweep Wedge */}
                  <g className="titan-radar-spin">
                    <path
                      d="M50,50 L50,6 A44,44 0 0,1 88,28 Z"
                      fill="rgba(53, 224, 176, 0.18)"
                    />
                    <line
                      x1="50"
                      y1="50"
                      x2="50"
                      y2="6"
                      stroke="#35e0b0"
                      strokeWidth="1.5"
                    />
                  </g>
                  {/* 5 Interactive Jito Regional Nodes */}
                  {[
                    { cx: 50, cy: 12, label: "FRA", color: "#35e0b0" },
                    { cx: 84, cy: 38, label: "NYC", color: "#5b9dff" },
                    { cx: 72, cy: 82, label: "AMS", color: "#35e0b0" },
                    { cx: 26, cy: 80, label: "TYO", color: "#a78bfa" },
                    { cx: 15, cy: 36, label: "SLC", color: "#f2b33d" },
                  ].map((node) => (
                    <g
                      key={node.label}
                      className="cursor-pointer"
                      onClick={() => {
                        onSelectWorkspace(7);
                        setLastActionMsg(
                          `🌐 [ORBITAL RADAR] Focused ${node.label} Jito Colocated Node · Switching to VPN Relay Mesh`
                        );
                      }}
                    >
                      <circle
                        cx={node.cx}
                        cy={node.cy}
                        r="4"
                        fill={node.color}
                      />
                      <circle
                        cx={node.cx}
                        cy={node.cy}
                        r="7"
                        fill="none"
                        stroke={node.color}
                        strokeWidth="0.8"
                        opacity="0.65"
                      />
                    </g>
                  ))}
                  {/* Center Core */}
                  <circle cx="50" cy="50" r="5" fill="#35e0b0" />
                </svg>
              </div>

              <div className="flex-1 min-w-0">
                <div className="text-[10px] font-mono uppercase tracking-wider text-[#35e0b0] font-bold">
                  5-REGION JITO ORBITAL RADAR
                </div>
                <div className="text-[11px] font-bold text-white truncate mt-0.5">
                  Leader: {frame.leader.flag} {frame.leader.city} ({frame.leader.validator})
                </div>
                <div className="text-[10px] font-mono text-[#869ab2] mt-0.5">
                  Slot #{frame.alpenglow_slot.toLocaleString()} · 96 Threads
                </div>
                {/* Mini Live Waveform Oscilloscope */}
                <div className="mt-1.5 bg-[#050911] border border-[#172638] rounded p-1">
                  <svg viewBox="0 0 240 48" className="w-full h-6">
                    <polyline
                      fill="none"
                      stroke="#35e0b0"
                      strokeWidth="1.8"
                      points={wavePoints.join(" ")}
                    />
                  </svg>
                </div>
              </div>
            </div>

            {/* 2. Interactive Animated Autonomous Capital-Adaptive Pipeline (6 cols) */}
            <div className="lg:col-span-6 bg-[#070d17]/90 border border-[#1a293d] rounded-xl p-2.5 flex flex-col justify-between">
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span className="text-[10px] font-mono uppercase tracking-wider text-[#5b9dff] font-bold">
                  ⚡ AUTONOMOUS CAPITAL-ADAPTIVE EXECUTION PIPELINE (100% AUTO-SIZED BY LIVE CAPITAL)
                </span>
                <span className="text-[10px] font-mono text-[#35e0b0] font-bold">
                  Live Capital:{" "}
                  {privacyMode ? "••• SOL" : `${totalCapitalSol.toFixed(2)} SOL`} · Auto-Scaled
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 items-center relative">
                {[
                  {
                    stageId: "FLASH_SANCTUM_STACK",
                    toggleKey: "GOLDEN5_STEP1_STACK",
                    ipcAction: "RUN_GOLDEN5_STEP1_FLASH_STACK",
                    title: "FLASH & SANCTUM STACK",
                    sub: "Auto-Scaled · 0% Principal Risk",
                    metric: "Kamino 0.001% + Sanctum + Funding",
                    accent: "#35e0b0",
                  },
                  {
                    stageId: "CURVE_SQUEEZE_SLOT0",
                    toggleKey: "GOLDEN5_STEP2_STACK",
                    ipcAction: "RUN_GOLDEN5_STEP2_LATE_CURVE_STACK",
                    title: "CURVE SQUEEZE & SLOT-0",
                    sub: "Auto-Sized Per-Shard · 65%->79% + 84.5 SOL",
                    metric: "4 Shields + Slot-0 Snipe",
                    accent: "#5b9dff",
                  },
                  {
                    stageId: "ASYMMETRIC_HUNTERS",
                    toggleKey: "GOLDEN5_STEP3_STACK",
                    ipcAction: "RUN_GOLDEN5_STEP3_HOMERUN_STACK",
                    title: "ASYMMETRIC 3x–10x",
                    sub: "Auto-Sized From Realized Profit",
                    metric: "Bridge + :8002 Vision + CTO",
                    accent: "#a78bfa",
                  },
                ].map((stage, idx) => {
                  const stageOn = isOn(stage.toggleKey, true);
                  return (
                    <div
                      key={stage.stageId}
                      className={`rounded-lg p-2 border transition-all relative ${
                        stageOn
                          ? "bg-[#102336]/95 border-[#35e0b0] shadow-[0_0_15px_rgba(53,224,176,0.2)]"
                          : "bg-[#160d14]/80 border-[#ef6069]/45 opacity-80"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span
                          onClick={async () => {
                            await sendTitanIpcCommand(stage.ipcAction, {});
                            onSelectWorkspace(1);
                            setLastActionMsg(
                              `🛡️ [PIPELINE FOCUS] Executed ${stage.title} (Auto-Sized by Capital)`
                            );
                          }}
                          className="text-[10px] font-mono font-bold text-white hover:text-[#35e0b0] cursor-pointer truncate"
                        >
                          {idx + 1}. {stage.title}
                        </span>
                        <button
                          onClick={async () => {
                            const res = await toggleButton(
                              stage.toggleKey,
                              stage.title,
                              stage.ipcAction,
                              {}
                            );
                            setLastActionMsg(res.message);
                          }}
                          className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold flex items-center gap-1 border ${
                            stageOn
                              ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]/60"
                              : "bg-[#ef6069]/20 text-[#ef6069] border-[#ef6069]/60"
                          }`}
                        >
                          <span
                            className={
                              stageOn ? "titan-led-on" : "titan-led-off"
                            }
                          />
                          {stageOn ? "🟢 ON" : "🔴 OFF"}
                        </button>
                      </div>
                      <div className="text-[9.5px] text-[#869ab2] truncate">
                        {stage.sub}
                      </div>
                      <div className="text-[9.5px] font-mono text-[#35e0b0] mt-0.5 truncate">
                        {stage.metric}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Animated SVG Flow Line Connecting Stages to Reserve Lockbox */}
              <div className="mt-1.5 flex items-center gap-2">
                <svg viewBox="0 0 600 12" className="w-full h-3">
                  <line
                    x1="0"
                    y1="6"
                    x2="600"
                    y2="6"
                    stroke="rgba(26, 41, 61, 0.9)"
                    strokeWidth="2"
                  />
                  <line
                    x1="0"
                    y1="6"
                    x2="600"
                    y2="6"
                    stroke="#35e0b0"
                    strokeWidth="2"
                    className="titan-packet-line"
                  />
                </svg>
                <span className="text-[9.5px] font-mono text-[#35e0b0] shrink-0 font-bold">
                  🔒 LOCKBOX:{" "}
                  {privacyMode
                    ? "••• SOL"
                    : `+${houseProfitSol.toFixed(2)} SOL`}
                </span>
              </div>
            </div>

            {/* 3. Quick Interactive Autopilot & Workspace Jump Pod (3 cols) */}
            <div className="lg:col-span-3 bg-[#070d17]/90 border border-[#1a293d] rounded-xl p-2.5 flex flex-col justify-between gap-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase tracking-wider text-[#a78bfa] font-bold">
                  🤖 DUAL-CONTROL COMMAND POD
                </span>
                <span
                  className={`text-[9.5px] font-mono font-bold px-1.5 py-0.5 rounded ${
                    aiAutoEnabled
                      ? "bg-[#35e0b0]/20 text-[#35e0b0]"
                      : "bg-[#ef6069]/20 text-[#ef6069]"
                  }`}
                >
                  AI: {aiAutoEnabled ? "🟢 ON" : "🔴 OFF"}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-1.5">
                <button
                  onClick={async () => {
                    const res = await sendTitanIpcCommand(
                      "TOGGLE_AI_AUTONOMOUS_CONTROL",
                      {}
                    );
                    setLastActionMsg(
                      res.message || "Toggled AI Autonomous Control"
                    );
                  }}
                  className={`px-2 py-1.5 rounded-lg text-[10px] font-mono font-bold border flex items-center justify-between ${
                    aiAutoEnabled
                      ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]/60"
                      : "bg-[#ef6069]/20 text-[#ef6069] border-[#ef6069]/60"
                  }`}
                >
                  <span>🤖 AI Autopilot</span>
                  <span>{aiAutoEnabled ? "🟢 ON" : "🔴 OFF"}</span>
                </button>

                <button
                  onClick={async () => {
                    const res = await toggleButton(
                      "ALL_8_PROFIT_ENGINES",
                      "All 8 Profit Engines",
                      "RUN_ALL_8_PROFIT_ENGINES"
                    );
                    setLastActionMsg(res.message);
                  }}
                  className={`px-2 py-1.5 rounded-lg text-[10px] font-mono font-bold border flex items-center justify-between ${
                    isOn("ALL_8_PROFIT_ENGINES", true)
                      ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]/60"
                      : "bg-[#ef6069]/20 text-[#ef6069] border-[#ef6069]/60"
                  }`}
                >
                  <span>💎 8 Engines</span>
                  <span>
                    {isOn("ALL_8_PROFIT_ENGINES", true) ? "🟢 ON" : "🔴 OFF"}
                  </span>
                </button>

                <button
                  onClick={async () => {
                    const res = await toggleButton(
                      "AI_AUTONOMOUS_OPTIMIZER",
                      "AI Auto-Scale By Capital",
                      "APPLY_AI_AUTONOMOUS_OPTIMAL_SETTINGS",
                      {}
                    );
                    setLastActionMsg(res.message);
                  }}
                  className={`px-2 py-1.5 rounded-lg text-[10px] font-mono font-bold border flex items-center justify-between ${
                    isOn("AI_AUTONOMOUS_OPTIMIZER", true)
                      ? "bg-[#5b9dff]/20 text-[#5b9dff] border-[#5b9dff]/60"
                      : "bg-[#ef6069]/20 text-[#ef6069] border-[#ef6069]/60"
                  }`}
                >
                  <span>⚡ Auto-Scale</span>
                  <span>
                    {isOn("AI_AUTONOMOUS_OPTIMIZER", true) ? "🟢 ON" : "🔴 OFF"}
                  </span>
                </button>

                <button
                  onClick={async () => {
                    const res = await toggleButton(
                      "BIWEEKLY_CAPITAL_INJECTION",
                      "Random Any-Time Capital Split (80/20)",
                      "RECORD_CAPITAL_INJECTION",
                      { random_amount: true }
                    );
                    setLastActionMsg(res.message);
                  }}
                  className={`px-2 py-1.5 rounded-lg text-[10px] font-mono font-bold border flex items-center justify-between ${
                    isOn("BIWEEKLY_CAPITAL_INJECTION", true)
                      ? "bg-[#a78bfa]/20 text-[#a78bfa] border-[#a78bfa]/60"
                      : "bg-[#ef6069]/20 text-[#ef6069] border-[#ef6069]/60"
                  }`}
                >
                  <span>🎲 Any-$ Drop</span>
                  <span>
                    {isOn("BIWEEKLY_CAPITAL_INJECTION", true)
                      ? "🟢 ON"
                      : "🔴 OFF"}
                  </span>
                </button>
              </div>

              <div className="text-[9.5px] font-mono text-[#869ab2] flex items-center justify-between pt-0.5">
                <span>Active View: WS #{activeWorkspace}</span>
                <span className="text-[#35e0b0]">
                  All Buttons Toggle 🟢 ON / 🔴 OFF
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Collapsible Master Power Switch Matrix Drawer */}
        {showMatrix && (
          <div className="px-3.5 pb-3.5 pt-2 border-t border-[#1a293d] bg-[#060b14]/95">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[10.5px] font-mono font-bold text-white uppercase tracking-wider mr-1">
                  🎛️ MASTER INTERACTIVE MODULE SWITCHBOARD:
                </span>
                {(
                  [
                    { id: "ALL", label: "ALL (20)" },
                    { id: "GOLDEN_5", label: "CAPITAL AUTO-TIERS" },
                    { id: "PROFIT_8", label: "8 PROFIT ENGINES" },
                    { id: "SHIELDS", label: "4 PRE-ENTRY SHIELDS" },
                    { id: "ENGINES", label: "MEV & SNIPER ENGINES" },
                  ] as const
                ).map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setMatrixFilter(tab.id)}
                    className={`px-2 py-0.5 rounded text-[9.5px] font-mono font-bold border ${
                      matrixFilter === tab.id
                        ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]"
                        : "bg-[#0d1624] text-[#869ab2] border-[#1f3148] hover:text-white"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <span className="text-[10px] font-mono text-[#869ab2]">
                Click any card below to toggle its live execution state between{" "}
                <strong className="text-[#35e0b0]">🟢 ON</strong> and{" "}
                <strong className="text-[#ef6069]">🔴 OFF</strong>
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-2">
              {filteredMatrix.map((item) => {
                const enabled = isOn(item.key, true);
                return (
                  <button
                    key={item.key}
                    onClick={async () => {
                      const res = await toggleButton(
                        item.key,
                        item.label,
                        item.ipcAction,
                        item.ipcParams
                      );
                      setLastActionMsg(res.message);
                    }}
                    className={`p-2 rounded-lg border text-left flex items-center justify-between gap-2 transition-all ${
                      enabled
                        ? "bg-[#0d1d2a]/90 border-[#35e0b0]/55 hover:border-[#35e0b0]"
                        : "bg-[#190e15]/85 border-[#ef6069]/50 hover:border-[#ef6069]"
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="text-[10.5px] font-bold text-white truncate">
                        {item.label}
                      </div>
                      <div className="text-[9px] font-mono text-[#869ab2] truncate">
                        {item.sub}
                      </div>
                    </div>
                    <div className="shrink-0 flex flex-col items-end gap-1">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${
                          enabled
                            ? "bg-[#35e0b0]/20 text-[#35e0b0]"
                            : "bg-[#ef6069]/20 text-[#ef6069]"
                        }`}
                      >
                        {enabled ? "🟢 ON" : "🔴 OFF"}
                      </span>
                      <span
                        className={`titan-switch-track ${
                          enabled ? "is-on" : "is-off"
                        }`}
                      >
                        <span className="titan-switch-thumb" />
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
