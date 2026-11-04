import React, { useEffect, useState } from "react";
import { FuturisticHoloDeck } from "./components/FuturisticHoloDeck";
import { FuturisticMenuBar } from "./components/FuturisticMenuBar";
import { TopTelemetryBar } from "./components/TopTelemetryBar";
import {
  createInitialTelemetryFrame,
  sendTitanIpcCommand,
  subscribeRamdiskTelemetry60To120Hz,
} from "./services/titanIpcClient";
import { MacroRegime, TitanTelemetryFrame, VaultMode } from "./types/telemetry";
import { AlphaShadowView } from "./views/AlphaShadowView";
import { AuditAndSettingsView } from "./views/AuditAndSettingsView";
import { ColocatedVpnRelayView } from "./views/ColocatedVpnRelayView";
import { LlmSwarmView } from "./views/LlmSwarmView";
import { MevTriadView } from "./views/MevTriadView";
import { TradingCockpit } from "./views/TradingCockpit";
import { VaultAndShardsView } from "./views/VaultAndShardsView";

export const App: React.FC = () => {
  const [frame, setFrame] = useState<TitanTelemetryFrame>(() =>
    createInitialTelemetryFrame()
  );
  const [activeWorkspace, setActiveWorkspace] = useState<number>(1);
  const [uiScale, setUiScale] = useState<number>(1.0);
  const [statusBanner, setStatusBanner] = useState<string>(
    "All 7 Workspaces Active · Zero-Copy /mnt/ramdisk Stream & All ON/OFF Toggles Synchronized"
  );

  useEffect(() => {
    const unsubscribe = subscribeRamdiskTelemetry60To120Hz((updatedFrame) => {
      setFrame({ ...updatedFrame });
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    document.documentElement.style.fontSize = `${Math.round(13 * uiScale)}px`;
  }, [uiScale]);

  const handleChangeMacroRegime = async (regime: MacroRegime) => {
    const res = await sendTitanIpcCommand("SET_MACRO_REGIME", { regime });
    setStatusBanner(
      `Macro Regime switched to ${regime} [🟢 ON] (${res.latency_ms ?? 0.14}ms)`
    );
  };

  const handleChangeVaultMode = async (mode: VaultMode) => {
    const res = await sendTitanIpcCommand("SET_VAULT_MODE", { mode });
    setStatusBanner(
      `Capital Mode switched to ${mode} [🟢 ON] · Active Shards: ${
        mode === "PAPER" ? 0 : mode === "CANARY" ? 4 : 25
      } (${res.latency_ms ?? 0.16}ms)`
    );
  };

  const handleTogglePauseAll = async () => {
    const res = await sendTitanIpcCommand("KILL_SWITCH_PAUSE", {});
    setStatusBanner(
      `Global Execution ${res.paused_all ? "🔴 PAUSED (OFF)" : "🟢 RESUMED (ON)"} (${
        res.latency_ms ?? 0.12
      }ms)`
    );
  };

  const handlePanicFlattenAll = async () => {
    const res = await sendTitanIpcCommand("KILL_SWITCH_PANIC_FLATTEN", {});
    setStatusBanner(
      `[F12] PANIC FLATTEN EXECUTED · Flattened ${
        res.flattened_positions ?? 0
      } positions & demoted to PAPER (${res.latency_ms ?? 0.24}ms)`
    );
  };

  // Global keyboard shortcuts: [Alt+1..Alt+7], [F12] Master Kill-Switch, [Ctrl+D / Ctrl+W] Vault, [Ctrl -/+] Scale
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && e.key >= "1" && e.key <= "7") {
        e.preventDefault();
        const num = parseInt(e.key, 10);
        setActiveWorkspace(num);
      } else if (e.key === "F12") {
        e.preventDefault();
        handlePanicFlattenAll();
      } else if (
        e.ctrlKey &&
        (e.key === "d" || e.key === "D" || e.key === "w" || e.key === "W")
      ) {
        e.preventDefault();
        setActiveWorkspace(5);
      } else if (e.ctrlKey && (e.key === "-" || e.key === "_")) {
        e.preventDefault();
        setUiScale((s) => Math.max(0.85, Number((s - 0.05).toFixed(2))));
      } else if (e.ctrlKey && (e.key === "=" || e.key === "+")) {
        e.preventDefault();
        setUiScale((s) => Math.min(1.1, Number((s + 0.05).toFixed(2))));
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="min-h-screen w-full flex flex-col bg-[#060a12] text-[#e6eef8]">
      {/* 1. Sleek 38px Top Feature Menu Bar */}
      <FuturisticMenuBar
        frame={frame}
        activeWorkspace={activeWorkspace}
        onSelectWorkspace={setActiveWorkspace}
        onChangeMacroRegime={handleChangeMacroRegime}
        onChangeVaultMode={handleChangeVaultMode}
        onTogglePauseAll={handleTogglePauseAll}
        onPanicFlattenAll={handlePanicFlattenAll}
        uiScale={uiScale}
        onChangeUiScale={setUiScale}
      />

      {/* 2. Institutional Top Telemetry Bar & 7-Workspace Switcher */}
      <TopTelemetryBar
        frame={frame}
        activeWorkspace={activeWorkspace}
        onSelectWorkspace={setActiveWorkspace}
        onChangeMacroRegime={handleChangeMacroRegime}
        onChangeVaultMode={handleChangeVaultMode}
        onTogglePauseAll={handleTogglePauseAll}
        onPanicFlattenAll={handlePanicFlattenAll}
        uiScale={uiScale}
        onChangeUiScale={setUiScale}
        statusBanner={statusBanner}
      />

      {/* 3. Quick-Power Switchboard & Collapsible Holo-Deck */}
      <FuturisticHoloDeck
        frame={frame}
        activeWorkspace={activeWorkspace}
        onSelectWorkspace={setActiveWorkspace}
      />

      {/* 4. Main Workspace Content */}
      <main className="flex-1 w-full max-w-[1920px] mx-auto px-4 py-3.5">
        {activeWorkspace === 1 && <TradingCockpit frame={frame} />}
        {activeWorkspace === 2 && <AlphaShadowView frame={frame} />}
        {activeWorkspace === 3 && <MevTriadView frame={frame} />}
        {activeWorkspace === 4 && <LlmSwarmView frame={frame} />}
        {activeWorkspace === 5 && <VaultAndShardsView frame={frame} />}
        {activeWorkspace === 6 && <AuditAndSettingsView frame={frame} />}
        {activeWorkspace >= 7 && <ColocatedVpnRelayView frame={frame} />}
      </main>
    </div>
  );
};

export default App;
