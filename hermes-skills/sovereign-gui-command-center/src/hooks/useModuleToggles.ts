import { useCallback, useEffect, useRef, useState } from "react";
import { sendTitanIpcCommand } from "../services/titanIpcClient";
import { TitanTelemetryFrame } from "../types/telemetry";

const STORAGE_KEY = "titan_module_toggle_states_v1";
const EVENT_NAME = "titan-module-toggle-change";

function loadInitialToggles(): Record<string, boolean> {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        return parsed as Record<string, boolean>;
      }
    }
  } catch {
    // Ignore storage read errors
  }
  return {};
}

export async function setBatchModuleToggles(
  keys: string[],
  targetState: boolean,
  labelPrefix?: string
): Promise<{ enabled: boolean; message: string }> {
  const current = loadInitialToggles();
  const updated: Record<string, boolean> = { ...current };
  for (const key of keys) {
    updated[key] = targetState;
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // Ignore storage write errors
  }
  window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: updated }));

  const res = await sendTitanIpcCommand("TOGGLE_MODULE_STATE_BATCH", {
    keys,
    enabled: targetState,
    label_prefix: labelPrefix,
    states: updated,
  });

  const badge = targetState ? "🟢 [ON]" : "🔴 [OFF]";
  const prefix = labelPrefix ? `${labelPrefix} ` : "";
  return {
    enabled: targetState,
    message:
      res?.message ||
      `${badge} ${prefix}(${keys.length} Modules) ${
        targetState ? "ENABLED" : "DISABLED"
      }`,
  };
}

export function useModuleToggles(frame?: TitanTelemetryFrame) {
  const [localToggles, setLocalToggles] = useState<Record<string, boolean>>(() =>
    loadInitialToggles()
  );
  const localTogglesRef = useRef<Record<string, boolean>>(localToggles);
  localTogglesRef.current = localToggles;

  const frameTogglesRef = useRef<Record<string, boolean> | undefined>(
    frame?.module_toggle_states
  );
  frameTogglesRef.current = frame?.module_toggle_states;

  useEffect(() => {
    const handler = (e: Event) => {
      const custom = e as CustomEvent<Record<string, boolean>>;
      if (custom.detail && typeof custom.detail === "object") {
        const next = { ...custom.detail };
        localTogglesRef.current = next;
        setLocalToggles(next);
      } else {
        const loaded = loadInitialToggles();
        localTogglesRef.current = loaded;
        setLocalToggles(loaded);
      }
    };
    window.addEventListener(EVENT_NAME, handler);
    return () => window.removeEventListener(EVENT_NAME, handler);
  }, []);

  const isOn = useCallback(
    (moduleKey: string, defaultState = true): boolean => {
      if (moduleKey in localTogglesRef.current) {
        return Boolean(localTogglesRef.current[moduleKey]);
      }
      if (moduleKey in localToggles) {
        return Boolean(localToggles[moduleKey]);
      }
      if (
        frame?.module_toggle_states &&
        moduleKey in frame.module_toggle_states
      ) {
        return Boolean(frame.module_toggle_states[moduleKey]);
      }
      return defaultState;
    },
    [localToggles, frame?.module_toggle_states]
  );

  const toggleButton = useCallback(
    async (
      moduleKey: string,
      label?: string,
      onTurnOnIpcAction?: string,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      onTurnOnParams?: Record<string, any>,
      defaultState = true
    ): Promise<{ enabled: boolean; message: string }> => {
      const currentSnapshot = {
        ...(frameTogglesRef.current ?? {}),
        ... loadInitialToggles(),
        ...localTogglesRef.current,
      };
      const currentlyOn =
        moduleKey in currentSnapshot
          ? Boolean(currentSnapshot[moduleKey])
          : defaultState;
      const nextState = !currentlyOn;

      const updated: Record<string, boolean> = {
        ...currentSnapshot,
        [moduleKey]: nextState,
      };

      if (
        moduleKey === "ALL_8_PROFIT_ENGINES" ||
        moduleKey === "RUN_ALL_8_PROFIT_ENGINES"
      ) {
        const PROFIT_ENGINE_KEYS = [
          "RUN_SANCTUM_LST_FLASH_ARB",
          "RUN_JITO_5TX_SUPERBUNDLE_COMBINER",
          "RUN_METEORA_DLMM_FEE_SURGE_HARVESTER",
          "RUN_DELTA_NEUTRAL_FUNDING_HARVESTER",
          "RUN_PROTOCOL_BUYBACK_TAX_CRANK_SNIPER",
          "RUN_CROSSCHAIN_WHALE_BRIDGE_LOOKAHEAD",
          "RUN_MULTIMODAL_GPU_VISION_CA_SNIPER",
          "RUN_CEX_POLYMARKET_STRIKE_LATENCY_ARB",
        ];
        updated.ALL_8_PROFIT_ENGINES = nextState;
        updated.RUN_ALL_8_PROFIT_ENGINES = nextState;
        for (const k of PROFIT_ENGINE_KEYS) {
          updated[k] = nextState;
        }
      }
      if (
        moduleKey === "GOLDEN5_STEP1_STACK" ||
        moduleKey === "RUN_GOLDEN5_STEP1_FLASH_STACK"
      ) {
        updated.GOLDEN5_STEP1_STACK = nextState;
        updated.RUN_GOLDEN5_STEP1_FLASH_STACK = nextState;
      } else if (
        moduleKey === "GOLDEN5_STEP2_STACK" ||
        moduleKey === "RUN_GOLDEN5_STEP2_LATE_CURVE_STACK"
      ) {
        updated.GOLDEN5_STEP2_STACK = nextState;
        updated.RUN_GOLDEN5_STEP2_LATE_CURVE_STACK = nextState;
      } else if (
        moduleKey === "GOLDEN5_STEP3_STACK" ||
        moduleKey === "RUN_GOLDEN5_STEP3_HOMERUN_STACK"
      ) {
        updated.GOLDEN5_STEP3_STACK = nextState;
        updated.RUN_GOLDEN5_STEP3_HOMERUN_STACK = nextState;
      }

      // Synchronously update ref + functional React state + localStorage before any await
      localTogglesRef.current = updated;
      setLocalToggles((prev) => ({
        ...prev,
        ...updated,
      }));
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      } catch {
        // Ignore storage write errors
      }
      window.dispatchEvent(new CustomEvent(EVENT_NAME, { detail: updated }));

      const toggleRes = await sendTitanIpcCommand("TOGGLE_MODULE_STATE", {
        module_key: moduleKey,
        enabled: nextState,
        label: label || moduleKey,
      });

      if (onTurnOnIpcAction) {
        const execRes = await sendTitanIpcCommand(onTurnOnIpcAction, {
          ...(onTurnOnParams || {}),
          enabled: nextState,
        });
        const badge = nextState ? "🟢 [ON]" : "🔴 [OFF]";
        return {
          enabled: nextState,
          message: execRes?.message
            ? `${badge} ${execRes.message}`
            : toggleRes?.message ||
              `${badge} ${label || moduleKey} ${
                nextState ? "ENABLED" : "DISABLED"
              }`,
        };
      }

      return {
        enabled: nextState,
        message:
          toggleRes?.message ||
          `${nextState ? "🟢 [ON]" : "🔴 [OFF]"} ${label || moduleKey} ${
            nextState ? "ENABLED" : "DISABLED"
          }`,
      };
    },
    []
  );

  const batchToggle = useCallback(
    async (
      keys: string[],
      targetState: boolean,
      labelPrefix?: string
    ): Promise<{ enabled: boolean; message: string }> => {
      const next: Record<string, boolean> = {
        ...(frameTogglesRef.current ?? {}),
        ...loadInitialToggles(),
        ...localTogglesRef.current,
      };
      for (const k of keys) {
        next[k] = targetState;
      }
      localTogglesRef.current = next;
      setLocalToggles((prev) => ({ ...prev, ...next }));
      return setBatchModuleToggles(keys, targetState, labelPrefix);
    },
    []
  );

  return {
    isOn,
    toggleButton,
    setBatchModuleToggles: batchToggle,
    localToggles,
  };
}
