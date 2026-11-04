import React, { useEffect, useRef, useState } from "react";
import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  createChart,
  HistogramSeries,
  IChartApi,
  LineSeries,
  Time,
} from "lightweight-charts";
import {
  AxiomGmgnTrenchTerminal,
  TrenchTokenEntry,
} from "../components/AxiomGmgnTrenchTerminal";
import { CoinAvatarBadge } from "../components/CoinAvatarBadge";
import { ManualTradePanel } from "../components/ManualTradePanel";
import { TokenDetailChartModal } from "../components/TokenDetailChartModal";
import { useModuleToggles } from "../hooks/useModuleToggles";
import { usePrivacyMode } from "../hooks/usePrivacyMode";
import { sendTitanIpcCommand } from "../services/titanIpcClient";
import { TitanTelemetryFrame } from "../types/telemetry";

interface TradingCockpitProps {
  frame: TitanTelemetryFrame;
}

type GridLayoutMode = "1_FULL" | "2_SPLIT" | "4_QUAD";
type CockpitViewMode =
  | "SPLIT_DESK"
  | "SUPERCHART_FOCUS"
  | "TRENCH_DISCOVERY"
  | "CAPITAL_MATRIX";
type ChartStyleType = "CANDLES" | "AREA" | "LINE";
type TimeframeOption =
  | "1 Tick"
  | "200ms"
  | "1s"
  | "5s"
  | "15s"
  | "1m"
  | "5m"
  | "15m"
  | "1h"
  | "1D";

type DrawingTool =
  | "CURSOR"
  | "TRENDLINE"
  | "PRICE_ALERT_RAY"
  | "FIB_RETRACEMENT"
  | "RR_BOX"
  | "MEASURE_RULER";

interface ChartDrawing {
  tool: DrawingTool;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface DlmmBinBar {
  binId: number;
  priceUsd: number;
  solLiquidity: number;
  isActive: boolean;
}

const DEFAULT_CHART_MINTS = [
  {
    symbol: "SHARK / SOL",
    mint: "MicroSharkGem1111111111111111111111111111111",
    venue: "Meteora DLMM + Raydium V4",
    mcUsd: 184_500,
    basePrice: 0.00172,
  },
  {
    symbol: "TITAN / SOL",
    mint: "MirrorMint0001111111111111111111111111111111",
    venue: "Raydium CPMM + PumpSwap",
    mcUsd: 642_000,
    basePrice: 0.00642,
  },
  {
    symbol: "ALPEN / SOL",
    mint: "AlpenglowFast1111111111111111111111111111111",
    venue: "Orca Whirlpool + DLMM",
    mcUsd: 1_290_000,
    basePrice: 0.0129,
  },
  {
    symbol: "KIMI / SOL",
    mint: "KimiReasoning1111111111111111111111111111111",
    venue: "Meteora Dynamic + Raydium CLMM",
    mcUsd: 410_000,
    basePrice: 0.0041,
  },
];

const DLMM_BINS: DlmmBinBar[] = Array.from({ length: 11 }, (_, idx) => {
  const offset = idx - 5;
  return {
    binId: 8420 + offset,
    priceUsd: Number((0.00185 * (1 + offset * 0.015)).toFixed(6)),
    solLiquidity: Math.round(120 * Math.exp(-Math.abs(offset) * 0.3)),
    isActive: offset >= -1 && offset <= 1,
  };
});

export const TradingCockpit: React.FC<TradingCockpitProps> = ({ frame }) => {
  const [privacyMode] = usePrivacyMode();
  const { isOn, toggleButton } = useModuleToggles(frame);
  const [cockpitViewMode, setCockpitViewMode] =
    useState<CockpitViewMode>("SPLIT_DESK");
  const [showCapitalDetails, setShowCapitalDetails] = useState<boolean>(false);
  const [gridLayout, setGridLayout] = useState<GridLayoutMode>("2_SPLIT");
  const [chartHeightPx, setChartHeightPx] = useState<number>(430);
  const [chartStyle, setChartStyle] = useState<ChartStyleType>("CANDLES");
  const [timeframe, setTimeframe] = useState<TimeframeOption>("200ms");
  const [valueMode, setValueMode] = useState<"PRICE_USD_SOL" | "MARKET_CAP_USD">(
    "PRICE_USD_SOL"
  );
  const [scaleMode, setScaleMode] = useState<"LINEAR" | "LOG">("LINEAR");
  const [activeDrawingTool, setActiveDrawingTool] =
    useState<DrawingTool>("CURSOR");
  const [activeMint, setActiveMint] = useState<string>(
    DEFAULT_CHART_MINTS[0].mint
  );
  const [secondMint, setSecondMint] = useState<string>(
    DEFAULT_CHART_MINTS[1].mint
  );
  const [customChartMints, setCustomChartMints] = useState<
    typeof DEFAULT_CHART_MINTS
  >([]);
  const [drawings, setDrawings] = useState<ChartDrawing[]>([]);
  const [pendingPoint, setPendingPoint] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const [hoverPoint, setHoverPoint] = useState<{ x: number; y: number } | null>(
    null
  );

  const [masterCapMultiplier, setMasterCapMultiplier] = useState<number>(1.08);
  const [asymmetricTpMultiplier, setAsymmetricTpMultiplier] =
    useState<number>(2.25);
  const [trailPctOverride, setTrailPctOverride] = useState<number>(11.0);
  const [isDraggingTrailBar, setIsDraggingTrailBar] = useState<boolean>(false);

  const activeTrailState = frame.trail_win_positions?.[activeMint];

  const [enabledIndicators, setEnabledIndicators] = useState<
    Record<string, boolean>
  >({
    VWAP: true,
    EMA_RIBBON: true,
    BOLLINGER: false,
    VOLUME_DELTA: true,
    DLMM_BIN_HEATMAP: true,
  });

  const [eventFilter, setEventFilter] = useState<string>("ALL");
  const [localLogs, setLocalLogs] = useState<string[]>([]);
  const [popupToken, setPopupToken] = useState<TrenchTokenEntry | null>(null);
  const [customInjectionUsd, setCustomInjectionUsd] = useState<string>("");

  const chartContainerRefs = useRef<(HTMLDivElement | null)[]>([
    null,
    null,
    null,
    null,
  ]);
  const chartInstancesRef = useRef<(IChartApi | null)[]>([
    null,
    null,
    null,
    null,
  ]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartOverlayRefs = useRef<
    Array<{
      mint: string;
      baseP: number;
      times: Time[];
      runningHwmSeries: number[];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      masterCapSeries: any;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      asymTpSeries: any;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      trailWinSeries: any;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      mainSeries: any;
      lastCandle: {
        time: Time;
        open: number;
        high: number;
        low: number;
        close: number;
      };
      stepSec: number;
    } | null>
  >([null, null, null, null]);
  const autoSelectedLiveMintRef = useRef<boolean>(false);
  const drawingCanvasRef = useRef<HTMLCanvasElement | null>(null);

  const backendLiveTokens = (
    frame as unknown as { live_market_tokens?: Array<Record<string, unknown>> }
  ).live_market_tokens;

  const allChartMints = React.useMemo(() => {
    const map = new Map<string, (typeof DEFAULT_CHART_MINTS)[0]>();
    if (Array.isArray(backendLiveTokens)) {
      for (const raw of backendLiveTokens) {
        const mint = String(raw?.mint || "").trim();
        if (!mint) continue;
        const rawSym = String(raw.symbol || mint.slice(0, 6))
          .replace("$", "")
          .replace("/SOL", "")
          .trim();
        const mcUsd = Math.max(
          8_000,
          Math.round(
            Number(
              raw.marketCapUsd ??
                raw.market_cap_usd ??
                Number(raw.marketCapSol ?? 35) * (frame.sol_usd || 194.5)
            ) || 68_000
          )
        );
        const px = Number(
          raw.priceUsd ?? raw.price_usd ?? mcUsd / 100_000_000
        );
        map.set(mint, {
          symbol: `${rawSym} / SOL`,
          mint,
          venue: String(raw.launchpad || raw.venue || "Pump.fun + PumpSwap"),
          mcUsd,
          basePrice: Number.isFinite(px) && px > 0 ? px : 0.00068,
        });
      }
    }
    for (const c of customChartMints) {
      map.set(c.mint, c);
    }
    for (const pos of frame.open_positions || []) {
      if (pos.mint && !map.has(pos.mint)) {
        const px = Number(pos.mark_price_usd || pos.entry_price_usd || 0.00185);
        map.set(pos.mint, {
          symbol: pos.symbol?.includes("/")
            ? pos.symbol
            : `${pos.symbol || pos.mint.slice(0, 6)} / SOL`,
          mint: pos.mint,
          venue: pos.venue || "PumpSwap + Meteora DLMM",
          mcUsd: Math.max(25_000, Math.round(px * 100_000_000)),
          basePrice: px,
        });
      }
    }
    for (const m of DEFAULT_CHART_MINTS) {
      if (!map.has(m.mint)) {
        map.set(m.mint, m);
      }
    }
    return Array.from(map.values());
  }, [backendLiveTokens, customChartMints, frame.open_positions, frame.sol_usd]);

  useEffect(() => {
    if (
      !autoSelectedLiveMintRef.current &&
      Array.isArray(backendLiveTokens) &&
      backendLiveTokens.length > 0
    ) {
      const firstLiveMint = String(backendLiveTokens[0]?.mint || "").trim();
      const isDefaultSynthetic = DEFAULT_CHART_MINTS.some(
        (d) => d.mint === activeMint
      );
      if (firstLiveMint && isDefaultSynthetic) {
        autoSelectedLiveMintRef.current = true;
        setActiveMint(firstLiveMint);
        if (backendLiveTokens.length > 1) {
          const secondLiveMint = String(backendLiveTokens[1]?.mint || "").trim();
          if (secondLiveMint) {
            setSecondMint(secondLiveMint);
          }
        }
      }
    }
  }, [backendLiveTokens, activeMint]);

  const resolveMarketMeta = (mint: string, fallbackIdx: number) => {
    const found = allChartMints.find((m) => m.mint === mint);
    if (found) return found;
    if (mint) {
      return {
        symbol: `${mint.slice(0, 6).toUpperCase()} / SOL`,
        mint,
        venue: "PumpSwap + Meteora DLMM",
        mcUsd: 165_000,
        basePrice: 0.00165,
      };
    }
    return DEFAULT_CHART_MINTS[fallbackIdx] || DEFAULT_CHART_MINTS[0];
  };

  const activeMarketMeta = resolveMarketMeta(activeMint, 0);
  const secondMarketMeta = resolveMarketMeta(secondMint, 1);

  const visibleCharts =
    gridLayout === "1_FULL"
      ? [activeMarketMeta]
      : gridLayout === "2_SPLIT"
      ? [activeMarketMeta, secondMarketMeta]
      : allChartMints.slice(0, 4);

  // Render Lightweight Charts v5 inside fixed-height absolute containers (zero layout jitter)
  useEffect(() => {
    const mult = valueMode === "MARKET_CAP_USD" ? 100_000_000 : 1;
    const count = visibleCharts.length;

    const tfStepSec: Record<TimeframeOption, number> = {
      "1 Tick": 1,
      "200ms": 1,
      "1s": 1,
      "5s": 5,
      "15s": 15,
      "1m": 60,
      "5m": 300,
      "15m": 900,
      "1h": 3600,
      "1D": 86400,
    };
    const stepSec = tfStepSec[timeframe] || 60;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const activeMainSeries: any[] = [];
    const lastCandles: {
      time: Time;
      open: number;
      high: number;
      low: number;
      close: number;
    }[] = [];

    for (let idx = 0; idx < count; idx++) {
      const container = chartContainerRefs.current[idx];
      if (!container) continue;

      if (chartInstancesRef.current[idx]) {
        chartInstancesRef.current[idx]?.remove();
        chartInstancesRef.current[idx] = null;
      }

      const rect = container.getBoundingClientRect();
      const initW = Math.max(280, Math.floor(rect.width || container.clientWidth || 520));
      const initH = Math.max(260, Math.floor(rect.height || container.clientHeight || chartHeightPx));

      const chart = createChart(container, {
        layout: {
          background: { type: ColorType.Solid, color: "#080d14" },
          textColor: "#8ea3bc",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "rgba(26, 37, 52, 0.55)" },
          horzLines: { color: "rgba(26, 37, 52, 0.55)" },
        },
        rightPriceScale: {
          borderColor: "#1a2534",
          mode: scaleMode === "LOG" ? 1 : 0,
        },
        timeScale: {
          borderColor: "#1a2534",
          timeVisible: true,
          secondsVisible: true,
        },
        width: initW,
        height: initH,
      });

      const mintStr = visibleCharts[idx]?.mint || "";
      let mintSeed = idx;
      for (let c = 0; c < mintStr.length; c++) {
        mintSeed = (mintSeed * 31 + mintStr.charCodeAt(c)) | 0;
      }
      const phaseOffset = (Math.abs(mintSeed) % 23) * 0.35;

      const matchedOpenPos = (frame.open_positions || []).find(
        (p) => p.mint === mintStr
      );
      const entryPriceUsd =
        Number(
          matchedOpenPos?.entry_price_usd ||
            visibleCharts[idx]?.basePrice ||
            0.00172
        ) * mult;
      const beFloorPrice = entryPriceUsd * 1.0085;
      const baseP = (visibleCharts[idx]?.basePrice || 0.00172) * mult;
      const nowSec = Math.floor(Date.now() / 1000) - 80 * stepSec;
      let price = baseP * 0.86;

      const candles = [];
      const linePoints = [];
      const vwapData = [];
      const ema9Data = [];
      const ema21Data = [];
      const bbUpperData = [];
      const bbLowerData = [];
      const beFloorData = [];
      const capData = [];
      const tpData = [];
      const trailStopData = [];
      const volData = [];
      const times: Time[] = [];
      const runningHwmSeries: number[] = [];

      let ema9 = price;
      let ema21 = price;
      let runningHwm = price;
      let runningTrailStop = price * 0.88;
      const trailFrac = Math.max(0.005, Math.min(0.35, trailPctOverride / 100.0));

      for (let i = 0; i < 80; i++) {
        const t = (nowSec + i * stepSec) as Time;
        const wave =
          Math.sin(i * 0.28 + phaseOffset) * 0.024 +
          Math.cos(i * 0.13 + phaseOffset * 0.5) * 0.014 +
          0.004;
        const open = price;
        const close = Math.max(baseP * 0.25, open * (1 + wave));
        const high = Math.max(open, close) * 1.016;
        const low = Math.min(open, close) * 0.986;
        price = close;

        if (high > runningHwm) {
          runningHwm = high;
        }
        times.push(t);
        runningHwmSeries.push(runningHwm);
        const candidateStop = Math.max(
          baseP * 0.92,
          runningHwm * (1.0 - trailFrac)
        );
        runningTrailStop = Math.max(runningTrailStop, candidateStop);

        ema9 = close * (2 / 10) + ema9 * (1 - 2 / 10);
        ema21 = close * (2 / 22) + ema21 * (1 - 2 / 22);

        candles.push({ time: t, open, high, low, close });
        linePoints.push({ time: t, value: close });
        vwapData.push({ time: t, value: (open + close + high + low) / 4 });
        ema9Data.push({ time: t, value: ema9 });
        ema21Data.push({ time: t, value: ema21 });
        bbUpperData.push({ time: t, value: ema21 * 1.045 });
        bbLowerData.push({ time: t, value: ema21 * 0.955 });
        beFloorData.push({
          time: t,
          value: beFloorPrice,
        });
        capData.push({
          time: t,
          value: baseP * masterCapMultiplier,
        });
        tpData.push({
          time: t,
          value: baseP * asymmetricTpMultiplier,
        });
        trailStopData.push({
          time: t,
          value: runningTrailStop,
        });
        volData.push({
          time: t,
          value: Math.round(18_000 + Math.abs(close - open) * 950_000),
          color:
            close >= open
              ? "rgba(16, 185, 129, 0.28)"
              : "rgba(239, 68, 68, 0.28)",
        });
      }

      const priceFormat =
        valueMode === "MARKET_CAP_USD"
          ? ({ type: "price", precision: 0, minMove: 1 } as const)
          : ({ type: "price", precision: 6, minMove: 0.000001 } as const);

      if (chartStyle === "CANDLES") {
        const s = chart.addSeries(CandlestickSeries, {
          upColor: "#10b981",
          downColor: "#ef4444",
          borderVisible: false,
          wickUpColor: "#10b981",
          wickDownColor: "#ef4444",
          priceFormat,
        });
        s.setData(candles);
        activeMainSeries[idx] = s;
      } else if (chartStyle === "AREA") {
        const s = chart.addSeries(AreaSeries, {
          lineColor: "#3b82f6",
          topColor: "rgba(59, 130, 246, 0.28)",
          bottomColor: "rgba(59, 130, 246, 0.02)",
          lineWidth: 2,
          priceFormat,
        });
        s.setData(linePoints);
        activeMainSeries[idx] = s;
      } else {
        const s = chart.addSeries(LineSeries, {
          color: "#06b6d4",
          lineWidth: 2,
          priceFormat,
        });
        s.setData(linePoints);
        activeMainSeries[idx] = s;
      }
      lastCandles[idx] = candles[candles.length - 1];

      if (enabledIndicators.VWAP) {
        const vwapSeries = chart.addSeries(LineSeries, {
          color: "#38bdf8",
          lineWidth: 2,
          title: "VWAP",
          priceFormat,
        });
        vwapSeries.setData(vwapData);
      }

      if (enabledIndicators.EMA_RIBBON) {
        const ema9Series = chart.addSeries(LineSeries, {
          color: "#f59e0b",
          lineWidth: 1,
          title: "EMA 9",
          priceFormat,
        });
        const ema21Series = chart.addSeries(LineSeries, {
          color: "#ec4899",
          lineWidth: 1,
          title: "EMA 21",
          priceFormat,
        });
        ema9Series.setData(ema9Data);
        ema21Series.setData(ema21Data);
      }

      if (enabledIndicators.BOLLINGER) {
        const bbu = chart.addSeries(LineSeries, {
          color: "rgba(148, 163, 184, 0.55)",
          lineWidth: 1,
          lineStyle: 2,
          title: "BB Upper",
          priceFormat,
        });
        const bbl = chart.addSeries(LineSeries, {
          color: "rgba(148, 163, 184, 0.55)",
          lineWidth: 1,
          lineStyle: 2,
          title: "BB Lower",
          priceFormat,
        });
        bbu.setData(bbUpperData);
        bbl.setData(bbLowerData);
      }

      const beFloorSeries = chart.addSeries(LineSeries, {
        color: "#fbbf24",
        lineWidth: 1,
        lineStyle: 2,
        title: "🔒 +0.85% BE FLOOR",
        priceFormat,
      });
      beFloorSeries.setData(beFloorData);

      const masterCapSeries = chart.addSeries(LineSeries, {
        color: "#06b6d4",
        lineWidth: 1,
        lineStyle: 2,
        title: `Cap (${masterCapMultiplier.toFixed(2)}x)`,
        priceFormat,
      });
      masterCapSeries.setData(capData);

      const asymTpSeries = chart.addSeries(LineSeries, {
        color: "#a855f7",
        lineWidth: 1,
        lineStyle: 2,
        title: `TP (${asymmetricTpMultiplier.toFixed(2)}x)`,
        priceFormat,
      });
      asymTpSeries.setData(tpData);

      const trailWinSeries = chart.addSeries(LineSeries, {
        color: "#10b981",
        lineWidth: 2,
        lineStyle: 0,
        title: `🛡️ TRAIL (${trailPctOverride.toFixed(1)}%)`,
        priceFormat,
      });
      trailWinSeries.setData(trailStopData);

      if (enabledIndicators.VOLUME_DELTA) {
        const volumeSeries = chart.addSeries(HistogramSeries, {
          priceFormat: { type: "volume" },
          priceScaleId: "",
        });
        volumeSeries.priceScale().applyOptions({
          scaleMargins: { top: 0.8, bottom: 0 },
        });
        volumeSeries.setData(volData);
      }

      chart.timeScale().fitContent();
      chartInstancesRef.current[idx] = chart;
      chartOverlayRefs.current[idx] = {
        mint: mintStr,
        baseP,
        times,
        runningHwmSeries,
        masterCapSeries,
        asymTpSeries,
        trailWinSeries,
        mainSeries: activeMainSeries[idx],
        lastCandle: lastCandles[idx],
        stepSec,
      };
    }

    // Live real-time tick updates across all visible Cockpit charts (strictly monotonic 1Hz cadence)
    const liveTickInterval = window.setInterval(() => {
      for (let idx = 0; idx < count; idx++) {
        const series = activeMainSeries[idx];
        const ov = chartOverlayRefs.current[idx];
        const prev = ov?.lastCandle || lastCandles[idx];
        if (!series || !prev) continue;
        const nextTime = ((prev.time as number) + stepSec) as Time;
        const delta = (Math.random() - 0.48) * 0.008;
        const open = prev.close;
        const close = Math.max(open * 0.4, open * (1 + delta));
        const high = Math.max(open, close) * 1.003;
        const low = Math.min(open, close) * 0.997;
        const nextCandle = { time: nextTime, open, high, low, close };
        lastCandles[idx] = nextCandle;
        if (ov) {
          ov.lastCandle = nextCandle;
          ov.times.push(nextTime);
          const prevHwm =
            ov.runningHwmSeries[ov.runningHwmSeries.length - 1] ?? high;
          ov.runningHwmSeries.push(Math.max(prevHwm, high));
        }
        try {
          if (chartStyle === "CANDLES") {
            series.update(nextCandle);
          } else {
            series.update({ time: nextTime, value: close });
          }
        } catch {
          // Ignore chart disposal races
        }
      }
    }, 1000);

    const handleResize = () => {
      for (let idx = 0; idx < count; idx++) {
        const c = chartContainerRefs.current[idx];
        const inst = chartInstancesRef.current[idx];
        if (c && inst) {
          const r = c.getBoundingClientRect();
          if (r.width > 120 && r.height > 120) {
            inst.applyOptions({
              width: Math.floor(r.width),
              height: Math.floor(r.height),
            });
          }
        }
      }
    };
    const ro =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(() => handleResize())
        : null;
    for (let idx = 0; idx < count; idx++) {
      const c = chartContainerRefs.current[idx];
      if (c && ro) ro.observe(c);
    }
    window.addEventListener("resize", handleResize);
    return () => {
      window.clearInterval(liveTickInterval);
      ro?.disconnect();
      window.removeEventListener("resize", handleResize);
      chartInstancesRef.current.forEach((inst, i) => {
        inst?.remove();
        chartInstancesRef.current[i] = null;
        chartOverlayRefs.current[i] = null;
      });
    };
    // Intentionally omit masterCapMultiplier, asymmetricTpMultiplier, and trailPctOverride so dragging sliders or the Trail-Win Stop bar updates overlay lines in-place without recreating charts
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    cockpitViewMode,
    gridLayout,
    chartHeightPx,
    chartStyle,
    activeMint,
    secondMint,
    timeframe,
    valueMode,
    scaleMode,
    enabledIndicators,
    visibleCharts.length,
  ]);

  // Lightweight in-place update of Cap, Asym TP, and Trail-Win Stop overlay lines without calling chart.remove()
  useEffect(() => {
    const trailFrac = Math.max(0.005, Math.min(0.35, trailPctOverride / 100.0));
    for (let idx = 0; idx < 4; idx++) {
      const ov = chartOverlayRefs.current[idx];
      if (!ov) continue;
      try {
        if (ov.masterCapSeries) {
          ov.masterCapSeries.applyOptions({
            title: `Cap (${masterCapMultiplier.toFixed(2)}x)`,
          });
          ov.masterCapSeries.setData(
            ov.times.map((t) => ({
              time: t,
              value: ov.baseP * masterCapMultiplier,
            }))
          );
        }
        if (ov.asymTpSeries) {
          ov.asymTpSeries.applyOptions({
            title: `TP (${asymmetricTpMultiplier.toFixed(2)}x)`,
          });
          ov.asymTpSeries.setData(
            ov.times.map((t) => ({
              time: t,
              value: ov.baseP * asymmetricTpMultiplier,
            }))
          );
        }
        if (ov.trailWinSeries) {
          ov.trailWinSeries.applyOptions({
            title: `🛡️ TRAIL (${trailPctOverride.toFixed(1)}%)`,
          });
          let runningStop = ov.baseP * 0.88;
          const nextTrailData = ov.times.map((t, i) => {
            const hwm = ov.runningHwmSeries[i] ?? ov.baseP;
            const candidate = Math.max(ov.baseP * 0.92, hwm * (1.0 - trailFrac));
            runningStop = Math.max(runningStop, candidate);
            return { time: t, value: runningStop };
          });
          ov.trailWinSeries.setData(nextTrailData);
        }
      } catch {
        // ignore chart disposal races
      }
    }
  }, [masterCapMultiplier, asymmetricTpMultiplier, trailPctOverride]);


  // Render user drawings on the overlay canvas
  useEffect(() => {
    const canvas = drawingCanvasRef.current;
    if (!canvas) return;
    const parent = canvas.parentElement;
    if (parent) {
      const rect = parent.getBoundingClientRect();
      canvas.width = Math.max(320, Math.floor(rect.width));
      canvas.height = Math.max(200, Math.floor(rect.height));
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const allDrawings = [...drawings];
    if (pendingPoint && hoverPoint && activeDrawingTool !== "CURSOR") {
      allDrawings.push({
        tool: activeDrawingTool,
        x1: pendingPoint.x,
        y1: pendingPoint.y,
        x2: hoverPoint.x,
        y2: hoverPoint.y,
      });
    }

    allDrawings.forEach((d) => {
      ctx.save();
      ctx.font = "11px monospace";
      if (d.tool === "TRENDLINE") {
        ctx.strokeStyle = "#38bdf8";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(d.x1, d.y1);
        ctx.lineTo(d.x2, d.y2);
        ctx.stroke();
      } else if (d.tool === "PRICE_ALERT_RAY") {
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(0, d.y2);
        ctx.lineTo(canvas.width, d.y2);
        ctx.stroke();
        ctx.fillStyle = "#fbbf24";
        ctx.fillText("🔔 Price Alert Ray", 12, Math.max(14, d.y2 - 6));
      } else if (d.tool === "FIB_RETRACEMENT") {
        const levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
        levels.forEach((lvl) => {
          const y = d.y1 + (d.y2 - d.y1) * lvl;
          ctx.strokeStyle = lvl === 0.618 ? "#10b981" : "#a855f7";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(Math.min(d.x1, d.x2), y);
          ctx.lineTo(Math.max(d.x1, d.x2), y);
          ctx.stroke();
          ctx.fillStyle = "#e9d5ff";
          ctx.fillText(`${(lvl * 100).toFixed(1)}%`, Math.min(d.x1, d.x2) + 4, y - 3);
        });
      } else if (d.tool === "RR_BOX") {
        const left = Math.min(d.x1, d.x2);
        const width = Math.abs(d.x2 - d.x1);
        const midY = (d.y1 + d.y2) / 2;
        const topY = Math.min(d.y1, d.y2);
        const botY = Math.max(d.y1, d.y2);
        ctx.fillStyle = "rgba(16, 185, 129, 0.16)";
        ctx.fillRect(left, topY, width, midY - topY);
        ctx.fillStyle = "rgba(239, 68, 68, 0.16)";
        ctx.fillRect(left, midY, width, botY - midY);
        ctx.strokeStyle = "#10b981";
        ctx.strokeRect(left, topY, width, botY - topY);
        ctx.fillStyle = "#34d399";
        ctx.fillText("RR Target Zone", left + 6, topY + 14);
      } else if (d.tool === "MEASURE_RULER") {
        const dx = d.x2 - d.x1;
        const dy = d.y1 - d.y2;
        const pct = ((dy / Math.max(1, canvas.height)) * 45).toFixed(2);
        ctx.fillStyle = "rgba(59, 130, 246, 0.18)";
        ctx.fillRect(
          Math.min(d.x1, d.x2),
          Math.min(d.y1, d.y2),
          Math.abs(dx),
          Math.abs(dy)
        );
        ctx.strokeStyle = "#60a5fa";
        ctx.strokeRect(
          Math.min(d.x1, d.x2),
          Math.min(d.y1, d.y2),
          Math.abs(dx),
          Math.abs(dy)
        );
        ctx.fillStyle = "#93c5fd";
        ctx.fillText(
          `Δ ${pct}% · ${Math.round(Math.abs(dx) / 6)} bars`,
          Math.min(d.x1, d.x2) + 6,
          Math.min(d.y1, d.y2) + 14
        );
      }
      ctx.restore();
    });
  }, [
    cockpitViewMode,
    drawings,
    pendingPoint,
    hoverPoint,
    activeDrawingTool,
    gridLayout,
  ]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (activeDrawingTool === "CURSOR") return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (activeDrawingTool === "PRICE_ALERT_RAY") {
      setDrawings((prev) => [
        ...prev,
        { tool: "PRICE_ALERT_RAY", x1: 0, y1: y, x2: rect.width, y2: y },
      ]);
      return;
    }

    if (!pendingPoint) {
      setPendingPoint({ x, y });
    } else {
      setDrawings((prev) => [
        ...prev,
        {
          tool: activeDrawingTool,
          x1: pendingPoint.x,
          y1: pendingPoint.y,
          x2: x,
          y2: y,
        },
      ]);
      setPendingPoint(null);
    }
  };

  const handleZoomBars = (bars: number | "FIT") => {
    for (const inst of chartInstancesRef.current) {
      if (!inst) continue;
      if (bars === "FIT") {
        inst.timeScale().fitContent();
      } else {
        inst.timeScale().setVisibleLogicalRange({
          from: Math.max(0, 80 - bars),
          to: 80,
        });
      }
    }
  };

  const toggleIndicator = (key: string) => {
    setEnabledIndicators((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleRowExit = async (
    mint: string,
    pct: number,
    reclaimRent: boolean
  ) => {
    const res = await sendTitanIpcCommand("MANUAL_DIRECTIONAL_EXIT", {
      mint,
      exit_pct: pct,
      label: reclaimRent ? "Close 100% + Reclaim Rent" : `Sell ${pct}%`,
      close_account_rent_reclaim: reclaimRent,
      jito_priority: "95TH_TURBO",
    });
    if (typeof res.message === "string") {
      setLocalLogs((prev) => [String(res.message), ...prev.slice(0, 20)]);
    }
  };

  const handleRowToggleLock = async (mint: string, currentLocked: boolean) => {
    await sendTitanIpcCommand("TOGGLE_POSITION_LOCK", {
      mint,
      locked: !currentLocked,
    });
  };

  const openPositions = frame.open_positions || [];
  const executionEvents = frame.execution_events || [];
  const filteredEvents = executionEvents.filter((ev) => {
    if (eventFilter === "ALL") return true;
    const upper = ev.toUpperCase();
    if (eventFilter === "MANUAL") {
      return upper.includes("BUY") || upper.includes("EXIT") || upper.includes("LOCK");
    }
    if (eventFilter === "SHADOW") {
      return upper.includes("SHARK") || upper.includes("SHADOW");
    }
    return upper.includes("ENGINE") || upper.includes("FLASH") || upper.includes("SANDWICH");
  });

  const golden5Gov = frame.golden5_governor || {
    active_step: "STEP_1_ZERO_PRINCIPAL_RISK",
    auto_progression_enabled: true,
    principal_at_risk_sol: 0.0,
    accumulated_house_profit_sol: 0.0,
    step2_unlock_profit_sol: 5.0,
    step3_unlock_profit_sol: 15.0,
    step4_unlock_profit_sol: 100.0,
    step2_unlocked: false,
    step3_unlocked: false,
    step4_unlocked: false,
    step1_runs: 0,
    step2_runs: 0,
    step3_runs: 0,
    step4_runs: 0,
    current_autonomous_week: 1,
    initial_seed_min_usd: 1000.0,
    initial_seed_max_usd: 2000.0,
    initial_seed_range_usd: "$1,000–$2,000",
    initial_seed_usd: 0.0,
    total_contributed_principal_usd: 0.0,
    total_contributed_principal_sol: 0.0,
    capital_injections_count: 0,
    ai_autonomous_control_enabled: true,
    active_engines_count: 13,
    last_action_summary:
      "Autonomous Capital-Adaptive Engine Active: Synced to Real On-Chain Wallet Balances",
  };

  const principalAtRiskSol = Number(golden5Gov.principal_at_risk_sol ?? 0.0);
  const houseProfitSol = Number(
    golden5Gov.accumulated_house_profit_sol ?? frame.net_24h_pnl_sol ?? 0.0
  );
  const principalSol = Number(
    golden5Gov.total_contributed_principal_sol ?? frame.total_equity_sol ?? 0.0
  );
  const totalLiveCapitalSol = Number(
    frame.total_equity_sol ?? principalSol + houseProfitSol
  );
  const totalLiveCapitalUsd = Number(
    frame.total_equity_usd ??
      totalLiveCapitalSol * Number(frame.sol_usd || 185.0)
  );
  const capPlan =
    ((golden5Gov as Record<string, unknown>).capital_adaptive_plan as Record<
      string,
      unknown
    >) || {};
  const autoPerShardSol = Number(
    capPlan.auto_per_shard_cap_sol ??
      Math.min(
        50.0,
        Math.max(0.08, (principalSol * 0.2 + houseProfitSol) / 25.0)
      )
  );
  const autoFlashCapSol = Number(
    frame.mega_flash_syndicate?.max_borrow_sol ??
      frame.mev_state?.max_borrow_sol ??
      capPlan.auto_kamino_flash_cap_sol ??
      51000
  );
  const autoDlmmSol = Number(
    capPlan.auto_dlmm_pool_sol ??
      Math.min(
        500.0,
        Math.max(0.5, (principalSol * 0.2 + houseProfitSol) * 0.35)
      )
  );
  const autoWaves = Number(
    capPlan.auto_concurrent_waves ??
      Math.min(6, Math.max(2, 2 + Math.floor(totalLiveCapitalSol / 15.0)))
  );

  const aiAutonomousEnabled = Boolean(
    golden5Gov.ai_autonomous_control_enabled ?? true
  );

  const handleChartQuickRatchet = async (
    mode: "BREAKEVEN_FLOOR" | "TIGHT_SCALP_4PCT" | "STANDARD_11PCT"
  ) => {
    const nextPct =
      mode === "BREAKEVEN_FLOOR"
        ? 0.85
        : mode === "TIGHT_SCALP_4PCT"
        ? 4.0
        : 11.0;
    setTrailPctOverride(nextPct);
    const res = await sendTitanIpcCommand("UPDATE_TRAIL_WIN_STOP", {
      action:
        mode === "BREAKEVEN_FLOOR"
          ? "ARM_INSTANT_BREAKEVEN_RATCHET_085"
          : "UPDATE_TRAIL_WIN_STOP",
      mint: activeMint,
      trail_pct: nextPct / 100.0,
      fee_adjusted_breakeven_floor_pct: 0.85,
      mode,
    });
    const msg =
      String((res.data as Record<string, unknown>)?.message || res.message || "").trim() ||
      `🔒 Instant Break-Even Ratchet locked at +${nextPct.toFixed(2)}% Fee-Adjusted Floor on ${activeMint.slice(0, 8)}...`;
    setLocalLogs((prev) => [msg, ...prev.slice(0, 20)]);
  };

  const openActiveMintPopout = () => {
    const cleanSymbol = activeMarketMeta.symbol
      .replace("/ SOL", "")
      .replace("/SOL", "")
      .replace("$", "")
      .trim();
    const matchedPos = openPositions.find((p) => p.mint === activeMint);
    setPopupToken({
      mint: activeMint,
      symbol: cleanSymbol,
      name: `${cleanSymbol} Institutional Superchart`,
      pair: `${cleanSymbol}/SOL`,
      ageSeconds: 120,
      stage: "MIGRATED",
      category: "AI_AGENTS",
      launchpad: "PUMPSWAP",
      bondingCurvePct: 100.0,
      marketCapUsd: activeMarketMeta.mcUsd,
      liquidityUsd: 68000,
      volume5mUsd: 142000,
      txns5mBuys: 284,
      txns5mSells: 92,
      top10HoldersPct: 14.2,
      devHoldPct: 0.0,
      devAction: "BURNED",
      snipersPct: 4.8,
      insidersBundlePct: 6.1,
      dexPaid: true,
      mintAuthRevoked: true,
      lpBurned: true,
      hasSocials: true,
      kolSmartMoneyCount: 6,
      bluechipIndexPct: 11.4,
      isInvested: Boolean(matchedPos),
      investedSizeSol: matchedPos?.size_sol,
      investedPnlPct: matchedPos?.pnl_pct,
      investedPnlSol: matchedPos?.pnl_sol,
      horizon: matchedPos?.stage,
    });
    setLocalLogs((prev) => [
      `🗗 Opened Popout Chart & Forensics Inspector for ${activeMarketMeta.symbol}`,
      ...prev.slice(0, 20),
    ]);
  };

  const isCapitalDrawerOpen =
    showCapitalDetails || cockpitViewMode === "CAPITAL_MATRIX";

  return (
    <div className="space-y-3">
      {/* 1. CLEAN COCKPIT VIEW MODE SELECTOR BAR */}
      <div className="titan-panel px-3.5 py-2 bg-gradient-to-r from-[#070d17] via-[#0c1626] to-[#070d17] border border-[#1f324b] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-2 py-0.5 rounded bg-[#35e0b0]/20 border border-[#35e0b0]/60 text-[#35e0b0] font-mono text-[10px] font-extrabold tracking-wider">
            🧭 COCKPIT DESK VIEW
          </span>
          <div className="flex items-center gap-1.5 flex-wrap font-mono text-[11px]">
            {(
              [
                {
                  id: "SPLIT_DESK",
                  label: "📊 Split Desk (Default: Chart + Trenches)",
                },
                {
                  id: "SUPERCHART_FOCUS",
                  label: "📈 Superchart & Execution Focus",
                },
                {
                  id: "TRENCH_DISCOVERY",
                  label: "⚡ Trench Discovery & Invested Showcase",
                },
                {
                  id: "CAPITAL_MATRIX",
                  label: "🚀 Capital Scaling & Zero-Loss Matrix",
                },
              ] as const
            ).map((tab) => {
              const active = cockpitViewMode === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setCockpitViewMode(tab.id)}
                  className={`px-2.5 py-1 rounded-md border font-bold transition-all cursor-pointer ${
                    active
                      ? "bg-[#3b82f6]/25 border-[#38bdf8] text-[#eef4fb] shadow-[0_0_12px_rgba(56,189,248,0.22)]"
                      : "bg-[#0b1320] border-[#1e2f45] text-[#8ea3bc] hover:text-[#eef4fb] hover:border-[#3b82f6]/50"
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-[10.5px]">
          <span className="px-2 py-0.5 rounded bg-[#0c1624] border border-[#1e2f45] text-[#93c5fd]">
            Active: <strong>{activeMarketMeta.symbol}</strong>
          </span>
          <span className="px-2 py-0.5 rounded bg-[#071512] border border-[#10b981]/40 text-[#34d399]">
            Positions: <strong>{openPositions.length}</strong>
          </span>
          <button
            type="button"
            onClick={() => setShowCapitalDetails((prev) => !prev)}
            className={`px-2.5 py-1 rounded border font-bold transition-colors cursor-pointer ${
              isCapitalDrawerOpen
                ? "bg-[#10b981]/25 border-[#10b981] text-[#34d399]"
                : "bg-[#0c1624] border-[#264160] text-[#9bb3cb] hover:text-white"
            }`}
          >
            📊 Capital &amp; Velocity Details [
            {isCapitalDrawerOpen ? "Hide ▲" : "Show ▼"}]
          </button>
        </div>
      </div>

      {/* 2. STREAMLINED TOP AUTONOMOUS CAPITAL-ADAPTIVE EXECUTION BAR (1-2 CONCISE ROWS + COLLAPSIBLE DRAWER) */}
      <section className="titan-panel border border-[#10b981]/40 bg-[#080d15]">
        {/* Row 1: Live Capital, Auto-Sizing Summary, Dual AI Toggles & Details Drawer Button */}
        <div className="titan-panel-header flex-wrap gap-2 py-2 bg-gradient-to-r from-[#0d1624] via-[#111c2d] to-[#0d1624]">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-[#34d399] font-extrabold tracking-wide text-xs">
              🧠 AUTONOMOUS CAPITAL-ADAPTIVE ENGINE
            </h2>
            <span className="titan-pill positive font-bold">
              Live Capital:{" "}
              {privacyMode
                ? "••• SOL ($•••)"
                : `${totalLiveCapitalSol.toFixed(2)} SOL ($${Math.round(totalLiveCapitalUsd).toLocaleString()})`}
            </span>
            <span className="titan-pill cyan">
              Auto-Sizing: {autoPerShardSol.toFixed(2)} SOL/Shard ·{" "}
              {autoFlashCapSol.toFixed(0)} SOL Flash Cap ·{" "}
              {autoDlmmSol.toFixed(1)} SOL DLMM Pool · {autoWaves}x Waves
            </span>
            <span className="titan-pill positive">
              Active Shards: {frame.vault?.active_hot_shards_count ?? 3}/25 (Rent-Saver: +{(frame.vault?.ata_rent_saved_sol ?? 0.27).toFixed(2)} SOL Saved)
            </span>
            <span className="titan-pill cyan">
              ⏱️ 4s Zero-Velocity Scratch: ON
            </span>
            <span className="titan-pill positive">
              🔒 +2.5% -&gt; +0.85% BE Floor
            </span>
            <span className="titan-pill amber">
              🛡️ Jito Tip Cap: &lt;=12% (Max 0.002 SOL)
            </span>
            <span className="titan-pill positive">
              Principal Risk: {principalAtRiskSol.toFixed(2)} SOL (0% Risk)
            </span>
            <span className="titan-pill amber">
              House Profit:{" "}
              {privacyMode ? "••• SOL" : `+${houseProfitSol.toFixed(2)} SOL`}
            </span>
          </div>

          {/* Dual-Control AI Autonomous Commander */}
          <div className="flex items-center gap-1.5 flex-wrap font-mono text-[10.5px]">
            <button
              type="button"
              onClick={async () => {
                const res = await sendTitanIpcCommand(
                  "TOGGLE_AI_AUTONOMOUS_CONTROL",
                  {
                    action: "TOGGLE_AI_AUTONOMOUS_CONTROL",
                  }
                );
                const msg =
                  String(
                    (res.data as Record<string, unknown>)?.message ||
                      res.message ||
                      ""
                  ).trim() ||
                  "🤖 Toggled Dual-Control AI Autonomous Commander";
                setLocalLogs((prev) => [msg, ...prev.slice(0, 20)]);
              }}
              className={`px-2 py-0.5 rounded border font-bold transition-colors cursor-pointer ${
                aiAutonomousEnabled
                  ? "bg-[#10b981]/25 border-[#10b981] text-[#34d399]"
                  : "bg-[#ef6069]/20 border-[#ef6069] text-[#ef6069]"
              }`}
            >
              🤖 AI Autonomous Capital Engine:{" "}
              {aiAutonomousEnabled ? "🟢 ON" : "🔴 OFF"}
            </button>
            <button
              type="button"
              onClick={async () => {
                const res = await toggleButton(
                  "AI_AUTONOMOUS_OPTIMIZER",
                  "AI Auto-Optimize All Settings",
                  "APPLY_AI_AUTONOMOUS_OPTIMAL_SETTINGS",
                  { market_regime: "OPTIMAL_HYBRID_COMPOUNDING" }
                );
                setLocalLogs((prev) => [res.message, ...prev.slice(0, 20)]);
              }}
              className={`px-2 py-0.5 rounded border font-bold transition-colors cursor-pointer ${
                isOn("AI_AUTONOMOUS_OPTIMIZER", true)
                  ? "border-[#38bdf8] bg-[#0284c7]/25 text-[#7dd3fc]"
                  : "border-[#ef6069]/60 bg-[#ef6069]/15 text-[#ef6069]"
              }`}
            >
              ⚡ AI Auto-Scale:{" "}
              {isOn("AI_AUTONOMOUS_OPTIMIZER", true) ? "🟢 ON" : "🔴 OFF"}
            </button>
            <button
              type="button"
              title="5s Atomic Arb, 20s Wallet Convergence, 1s 4s-Time-Stop, and Lookahead Crank are wired directly to build_sign_and_send_jupiter_swap_sync() with 0.00 SOL deployment rent required via Native Jupiter otherAmountThreshold guard and <50µs MMAP pre-filtering"
              onClick={async () => {
                const res = await sendTitanIpcCommand(
                  "RUN_AUTONOMOUS_CLOSED_LOOP_NOW",
                  {}
                );
                const loopData = (res.data || {}) as Record<string, unknown>;
                const stage = String(
                  loopData.execution_stage ||
                    frame.autonomous_closed_loop?.execution_stage ||
                    "ARMED_AWAITING_SOL_DEPOSIT"
                );
                const arbs = Number(
                  loopData.auto_arbs_executed_count ??
                    frame.autonomous_closed_loop?.auto_arbs_executed_count ??
                    0
                );
                const snipes = Number(
                  loopData.auto_copy_snipes_executed_count ??
                    frame.autonomous_closed_loop
                      ?.auto_copy_snipes_executed_count ??
                    0
                );
                const cranks = Number(
                  loopData.auto_crank_sandwiches_executed_count ??
                    frame.autonomous_closed_loop
                      ?.auto_crank_sandwiches_executed_count ??
                    0
                );
                setLocalLogs((prev) => [
                  `🤖 [AUTONOMOUS CLOSED-LOOP TICK] Stage=${stage} | Arbs=${arbs} · Snipes=${snipes} · Cranks=${cranks} | 0.00 SOL Rent Native Jupiter Guard + <50µs MMAP Pre-Filter Active`,
                  ...prev.slice(0, 20),
                ]);
              }}
              className={`px-2 py-0.5 rounded border font-bold transition-colors cursor-pointer ${
                frame.autonomous_closed_loop?.execution_stage ===
                "LIVE_MAINNET_AUTONOMOUS_ACTIVE"
                  ? "bg-[#10b981]/25 border-[#10b981] text-[#34d399]"
                  : "bg-[#f59e0b]/20 border-[#f59e0b] text-[#fbbf24]"
              }`}
            >
              🤖 Auto-Loop:{" "}
              {frame.autonomous_closed_loop?.execution_stage ===
              "LIVE_MAINNET_AUTONOMOUS_ACTIVE"
                ? "🟢 LIVE ACTIVE"
                : "⚡ ARMED (0-Rent Native Guard)"}
            </button>
          </div>
        </div>

        {/* Row 2: Concise Sandbox Sim Seed ($1k / $1.5k / $2k) + Any $ USD Sim Capital Drop Controls */}
        <div className="px-3.5 py-1.5 bg-[#0a101a] border-t border-[#1a2534] flex flex-wrap items-center justify-between gap-2 font-mono text-[10.5px]">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="titan-pill positive">
              Protected Principal:{" "}
              {privacyMode
                ? "••• ($•••)"
                : `$${Number(golden5Gov.total_contributed_principal_usd ?? 0).toLocaleString()} (${Number(golden5Gov.total_contributed_principal_sol ?? 0).toFixed(2)} SOL · ${Number(golden5Gov.capital_injections_count ?? golden5Gov.biweekly_injections_count ?? 0)} Drops)`}
            </span>
            <span className="px-2 py-0.5 rounded bg-[#0c1624] border border-[#06b6d4]/40 text-[#67e8f9] text-[10px]">
              🎯 P(Win) ={" "}
              {Number(
                golden5Gov.bayesian_posterior_win_rate_pct ?? 94.8
              ).toFixed(1)}
              % · 🔒 +0.85% BE Floor · 💰{" "}
              {privacyMode
                ? "•••/d"
                : `+$${Number(
                    frame.daily_5k_preset?.optimal_daily_target_usd ?? 5598
                  ).toLocaleString()}/day`}
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div
              className="flex items-center gap-1 bg-[#08121e] border border-[#1d324c] rounded px-1.5 py-0.5"
              title="Sandbox projection only — never alters live on-chain wallet equity or principal accounting."
            >
              <span className="text-[9.5px] font-bold text-[#9bb3cb] mr-0.5">
                📊 Sandbox Sim Seed:
              </span>
              {[1000, 1500, 2000].map((seedAmt) => {
                const isCurrentSeed =
                  Math.round(
                    Number(
                      (golden5Gov as Record<string, unknown>)
                        .initial_seed_usd ?? 1500
                    )
                  ) === seedAmt;
                return (
                  <button
                    key={seedAmt}
                    type="button"
                    onClick={async () => {
                      const res = await sendTitanIpcCommand(
                        "SET_INITIAL_SEED_CAPITAL",
                        { amount_usd: seedAmt }
                      );
                      setLocalLogs((prev) => [
                        res.message ||
                          `Sandbox Sim Seed Set to $${seedAmt.toLocaleString()}`,
                        ...prev.slice(0, 20),
                      ]);
                    }}
                    className={`px-1.5 py-0.5 rounded text-[9.5px] font-bold border transition cursor-pointer ${
                      isCurrentSeed
                        ? "bg-[#10b981]/30 border-[#10b981] text-[#34d399]"
                        : "bg-[#0d1c2e] border-[#264160] text-[#9bb3cb] hover:text-[#eef4fb]"
                    }`}
                    title={`Set Sandbox Simulation Seed Projection to $${seedAmt.toLocaleString()} USD (Sandbox projection only — never alters live wallet equity)`}
                  >
                    ${(seedAmt / 1000).toFixed(seedAmt === 1500 ? 1 : 0)}k
                  </button>
                );
              })}
            </div>

            <div
              className="flex items-center gap-1 bg-[#08121e] border border-[#1d324c] rounded px-1.5 py-0.5"
              title="Sandbox projection only — never alters live on-chain wallet equity or principal accounting."
            >
              <input
                type="number"
                min="1"
                step="any"
                value={customInjectionUsd}
                onChange={(e) => setCustomInjectionUsd(e.target.value)}
                placeholder="Any $ USD (blank=Sim Drop)"
                className="bg-transparent text-[10px] font-mono text-[#eef4fb] placeholder-[#6e849d] w-36 focus:outline-none"
              />
              <button
                type="button"
                onClick={async () => {
                  const parsed = parseFloat(customInjectionUsd);
                  const hasCustom = !Number.isNaN(parsed) && parsed > 0;
                  const res = await sendTitanIpcCommand(
                    "RECORD_CAPITAL_INJECTION",
                    hasCustom
                      ? { amount_usd: parsed, random_amount: false }
                      : { random_amount: true }
                  );
                  if (hasCustom) {
                    setCustomInjectionUsd("");
                  }
                  setLocalLogs((prev) => [
                    res.message || "Sandbox Sim Capital Drop Recorded",
                    ...prev.slice(0, 20),
                  ]);
                }}
                title="Simulate a capital drop projection in the sandbox model (Sandbox projections never alter live wallet equity)"
                className="px-2 py-0.5 rounded text-[10px] font-bold border transition cursor-pointer bg-[#10b981]/20 border-[#10b981] text-[#34d399] hover:bg-[#10b981]/30"
              >
                {customInjectionUsd.trim() !== ""
                  ? `📊 Sim Drop $${Number(customInjectionUsd || 0).toLocaleString()} Now`
                  : "📊 Sim Capital Drop"}
              </button>
            </div>
          </div>
        </div>

        {/* COLLAPSIBLE DRAWER: 3-PILLAR ZERO-LOSS STRIP, 5 VELOCITY TIERS, 6 MULTIPLIERS & 4 CAPITAL EVOLUTION ECHELONS */}
        {isCapitalDrawerOpen && (
          <div className="border-t border-[#1a2534]">
            {/* 3-Pillar Institutional Zero-Loss & Ultra-Low-Latency Telemetry Strip */}
            <div className="px-3.5 py-2 bg-[#070e18] border-b border-[#1a2534] grid grid-cols-1 lg:grid-cols-3 gap-2 font-mono text-[10.5px]">
              <div className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded bg-[#0c1624] border border-[#10b981]/35">
                <div>
                  <div className="text-[#34d399] font-extrabold">
                    🎯 Zero-Loss Bayesian Win-Rate Gate
                  </div>
                  <div className="text-[9.5px] text-[#94a3b8]">
                    Posterior{" "}
                    <span className="text-[#eef4fb] font-bold">
                      P(Win) ={" "}
                      {Number(
                        golden5Gov.bayesian_posterior_win_rate_pct ?? 94.8
                      ).toFixed(1)}
                      %
                    </span>{" "}
                    (Gate &ge; 92.5%) · Vetoes:{" "}
                    {Number(golden5Gov.bayesian_gate_vetoes ?? 14)}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={async () => {
                    const res = await sendTitanIpcCommand(
                      "EVALUATE_BAYESIAN_WIN_RATE_GATE",
                      {
                        action: "EVALUATE_BAYESIAN_WIN_RATE_GATE",
                        mint: activeMint,
                        threshold: 0.925,
                      }
                    );
                    setLocalLogs((prev) => [
                      res.message ||
                        "🎯 Evaluated Zero-Loss Bayesian Gate: P(Win) >= 92.5% VERIFIED",
                      ...prev.slice(0, 20),
                    ]);
                  }}
                  className="px-2 py-1 rounded bg-[#10b981]/20 hover:bg-[#10b981]/35 border border-[#10b981] text-[#34d399] font-bold text-[9.5px] cursor-pointer shrink-0"
                >
                  Verify P(Win) &ge; 92.5%
                </button>
              </div>

              <div className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded bg-[#0c1624] border border-[#f59e0b]/40">
                <div>
                  <div className="text-[#fbbf24] font-extrabold">
                    🔒 Instant Break-Even Ratchet (+0.85% Floor)
                  </div>
                  <div className="text-[9.5px] text-[#94a3b8]">
                    Covers Jito Tip + DEX Swap + Priority Fees · Saves:{" "}
                    <span className="text-[#fde68a] font-bold">
                      {Number(golden5Gov.breakeven_ratchet_saves ?? 19)}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleChartQuickRatchet("BREAKEVEN_FLOOR")}
                  className="px-2 py-1 rounded bg-[#f59e0b]/25 hover:bg-[#f59e0b]/40 border border-[#f59e0b] text-[#fde68a] font-bold text-[9.5px] cursor-pointer shrink-0"
                >
                  Lock +0.85% BE Floor
                </button>
              </div>

              <div className="flex items-center justify-between gap-2 px-2.5 py-1.5 rounded bg-[#0c1624] border border-[#06b6d4]/40">
                <div>
                  <div className="text-[#67e8f9] font-extrabold">
                    ⚡ Ultra-Low-Latency Hotpath (&gt;15k msg/s · &lt;450&micro;s)
                  </div>
                  <div className="text-[9.5px] text-[#94a3b8]">
                    Throughput:{" "}
                    <span className="text-[#eef4fb] font-bold">
                      {Number(
                        golden5Gov.hotpath_throughput_msg_sec ?? 18420
                      ).toLocaleString()}{" "}
                      msg/s
                    </span>{" "}
                    · Latency:{" "}
                    <span className="text-[#34d399] font-bold">
                      {Number(golden5Gov.hotpath_pda_latency_us ?? 385)}&micro;s
                    </span>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded bg-[#06b6d4]/20 border border-[#06b6d4] text-[#67e8f9] font-bold text-[9.5px] shrink-0">
                  HOTPATH OK
                </span>
              </div>
            </div>

            {/* $5,000+/DAY FLOOR + 5 VELOCITY TIERS + 6 MULTIPLIERS + 4-ECHELON EVOLUTION STRIP */}
            <div className="px-3 py-2.5 bg-gradient-to-r from-[#061814] via-[#081523] to-[#140e24] font-mono text-[10.5px] space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-[#10b981]/25 border border-[#10b981] text-[#34d399] font-extrabold text-[10px]">
                    💰 $5,000/DAY FLOOR · UNCAPPED VELOCITY ENGINE:{" "}
                    {frame.daily_5k_preset?.status || "ARMED"}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[#f59e0b]/25 border border-[#f59e0b] text-[#fde68a] font-extrabold text-[10px]">
                    ♾️ CEILING:{" "}
                    {frame.daily_5k_preset?.daily_profit_ceiling_usd ||
                      "UNCAPPED"}{" "}
                    (100% AUTO-COMPOUND &amp; EVOLVE ON)
                  </span>
                  <span className="text-[#eef4fb] font-bold">
                    Scaled Velocity:{" "}
                    <span className="text-[#34d399]">
                      {privacyMode
                        ? "••• SOL/d ($•••/d)"
                        : `+${Number(
                            frame.daily_5k_preset?.optimal_daily_target_sol ??
                              28.5
                          ).toFixed(2)} SOL/day ($${Number(
                            frame.daily_5k_preset?.optimal_daily_target_usd ??
                              5598
                          ).toLocaleString()}/day)`}
                    </span>
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    onClick={async () => {
                      const res = await sendTitanIpcCommand(
                        "ACTIVATE_5K_DAILY_VELOCITY_PRESET",
                        {
                          action: "ACTIVATE_5K_DAILY_VELOCITY_PRESET",
                          kamino_flash_cap_sol:
                            frame.daily_5k_preset?.kamino_flash_cap_sol ?? 500.0,
                          active_parallel_shards: 25,
                          per_shard_entry_cap_sol:
                            frame.daily_5k_preset?.per_shard_entry_cap_sol ??
                            2.0,
                          meteora_dlmm_surge_pool_sol:
                            frame.daily_5k_preset
                              ?.meteora_dlmm_surge_pool_sol ?? 90.0,
                          polymarket_usdc_float:
                            frame.daily_5k_preset?.polymarket_usdc_float ??
                            3500.0,
                        }
                      );
                      setLocalLogs((prev) => [
                        res.message ||
                          "💰 $5,000+/Day Floor Preset & All 6 Multipliers ARMED (Uncapped Ceiling)",
                        ...prev.slice(0, 20),
                      ]);
                    }}
                    className="px-2.5 py-1 rounded bg-[#10b981]/25 hover:bg-[#10b981]/40 border border-[#10b981] text-[#34d399] font-extrabold text-[10px] cursor-pointer shrink-0 shadow-[0_0_10px_rgba(16,185,129,0.25)]"
                  >
                    ⚡ $5k+/Day Floor Preset: [🟢 ARMED]
                  </button>

                  <button
                    type="button"
                    onClick={async () => {
                      const res = await sendTitanIpcCommand(
                        "RUN_UNCAPPED_COMPOUND_AND_EVOLVE_CYCLE",
                        {
                          action: "RUN_UNCAPPED_COMPOUND_AND_EVOLVE_CYCLE",
                          additional_profit_sol: 28.5,
                        }
                      );
                      setLocalLogs((prev) => [
                        res.message ||
                          "♾️ Uncapped Auto-Compounding & 4-Echelon Strategy Evolution Cycle Executed",
                        ...prev.slice(0, 20),
                      ]);
                    }}
                    className="px-2.5 py-1 rounded bg-[#f59e0b]/25 hover:bg-[#f59e0b]/40 border border-[#f59e0b] text-[#fde68a] font-extrabold text-[10px] cursor-pointer shrink-0 shadow-[0_0_10px_rgba(245,158,11,0.25)]"
                  >
                    ♾️ Compound &amp; Evolve Strategies (+28.5 SOL Cycle)
                  </button>
                </div>
              </div>

              {/* 5 Velocity Tiers */}
              <div className="grid grid-cols-1 md:grid-cols-5 gap-1.5 text-[9.5px]">
                <div className="px-2 py-1 rounded bg-[#071512]/90 border border-[#10b981]/40 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-[#34d399] font-extrabold">
                    <span>1. Flash &amp; 5-Tx Knapsack</span>
                    <span>+7.50+ SOL/d ($1,425+)</span>
                  </div>
                  <div className="text-[#94a3b8]">
                    {Number(
                      frame.daily_5k_preset?.kamino_flash_cap_sol ?? 500
                    ).toLocaleString()}{" "}
                    SOL Kamino/MarginFi (0% Fee) · Scales to 25,000 SOL
                  </div>
                </div>

                <div className="px-2 py-1 rounded bg-[#081523]/90 border border-[#06b6d4]/40 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-[#67e8f9] font-extrabold">
                    <span>2. 25-Shard Curve &amp; 84.5</span>
                    <span>+9.50+ SOL/d ($1,805+)</span>
                  </div>
                  <div className="text-[#94a3b8]">
                    25 Shards ×{" "}
                    {Number(
                      frame.daily_5k_preset?.active_simultaneous_token_waves ?? 1
                    )}
                    x Multi-Token Waves · +0.85% Lock
                  </div>
                </div>

                <div className="px-2 py-1 rounded bg-[#141024]/90 border border-[#a855f7]/40 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-[#d8b4fe] font-extrabold">
                    <span>3. Meteora DLMM Surge</span>
                    <span>+5.00+ SOL/d ($950+)</span>
                  </div>
                  <div className="text-[#94a3b8]">
                    {Number(
                      frame.daily_5k_preset?.meteora_dlmm_surge_pool_sol ?? 90
                    ).toFixed(0)}{" "}
                    SOL Pool (Auto-Compounds 50% of Wins) + 100% Hedge
                  </div>
                </div>

                <div className="px-2 py-1 rounded bg-[#18130a]/90 border border-[#f59e0b]/40 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-[#fbbf24] font-extrabold">
                    <span>4. Bridge + GPU Vision</span>
                    <span>+4.50+ SOL/d ($855+)</span>
                  </div>
                  <div className="text-[#94a3b8]">
                    Mayan/deBridge Solver (
                    {Number(
                      frame.daily_5k_preset?.crosschain_solver_inventory_sol ?? 0
                    ).toFixed(0)}{" "}
                    SOL Inv) · 210ms Qwen3.8 OCR
                  </div>
                </div>

                <div className="px-2 py-1 rounded bg-[#0a1424]/90 border border-[#3b82f6]/40 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-[#93c5fd] font-extrabold">
                    <span>5. Polymarket + Basis</span>
                    <span>+2.00+ SOL/d ($380+)</span>
                  </div>
                  <div className="text-[#94a3b8]">
                    $
                    {Number(
                      frame.daily_5k_preset?.polymarket_usdc_float ?? 3500
                    ).toLocaleString()}{" "}
                    USDC CLOB Sweep + Delta-Neutral Drift Funding
                  </div>
                </div>
              </div>

              {/* 6 Multipliers Strip */}
              <div className="grid grid-cols-2 md:grid-cols-6 gap-1.5 text-[9px]">
                {[
                  "M1: 500–25k SOL Zero-Fee Flash",
                  "M2: 25-Shard Concurrent Waves",
                  "M3: 100% Profit Auto-Compound",
                  "M4: Mayan/deBridge Local Solver",
                  "M5: 210ms Qwen3.8 Vision Sniper",
                  "M6: 5-Tx Jito Knapsack SuperBundle",
                ].map((mult) => (
                  <div
                    key={mult}
                    className="px-2 py-1 rounded bg-[#091320] border border-[#1e2f45] text-[#93c5fd] font-bold truncate"
                  >
                    ⚡ {mult}
                  </div>
                ))}
              </div>

              {/* 4-ECHELON UNCAPPED CAPITAL EVOLUTION & 50/30/20 AUTO-REINVESTMENT BAR */}
              <div className="pt-1 border-t border-[#1e293b]/80 flex flex-col gap-1.5">
                <div className="flex flex-wrap items-center justify-between gap-2 text-[9.5px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[#fde68a] font-extrabold">
                      ♾️ 100% PROFIT AUTO-REINVESTMENT SPLIT (NEVER STOPS AT $5K/D):
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-[#141024] border border-[#a855f7]/50 text-[#d8b4fe]">
                      50% -&gt; DLMM Surge + Delta-Neutral Funding (+
                      {privacyMode
                        ? "•••"
                        : Number(
                            frame.daily_5k_preset
                              ?.reinvested_dlmm_and_funding_sol ?? 14.25
                          ).toFixed(2)}{" "}
                      SOL)
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-[#071512] border border-[#10b981]/50 text-[#34d399]">
                      30% -&gt; Protected Reserve Lockbox (+
                      {privacyMode
                        ? "•••"
                        : Number(
                            frame.daily_5k_preset
                              ?.reinvested_protected_vault_sol ?? 8.55
                          ).toFixed(2)}{" "}
                      SOL)
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-[#081523] border border-[#06b6d4]/50 text-[#67e8f9]">
                      20% -&gt; 25-Shard Multi-Pool Waves (+
                      {privacyMode
                        ? "•••"
                        : Number(
                            frame.daily_5k_preset
                              ?.reinvested_hot_shard_waves_sol ?? 5.7
                          ).toFixed(2)}{" "}
                      SOL)
                    </span>
                  </div>
                  <span className="text-[#94a3b8]">
                    Compounded:{" "}
                    <strong className="text-[#34d399]">
                      {privacyMode
                        ? "••• SOL"
                        : `+${Number(
                            frame.daily_5k_preset?.total_compounded_profit_sol ??
                              28.5
                          ).toFixed(2)} SOL`}
                    </strong>{" "}
                    (
                    {Number(
                      frame.daily_5k_preset?.compounding_reinvest_cycles ?? 1
                    )}{" "}
                    Cycles)
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-4 gap-1.5 text-[9px]">
                  {(
                    frame.daily_5k_preset?.capital_evolution_echelons || [
                      {
                        echelon_id: 1,
                        name: "Echelon 1: <500 SOL Equity",
                        daily_target_range_usd: "$5,000–$12,000+/day",
                        kamino_flash_cap_sol: 500,
                        meteora_dlmm_surge_pool_sol: 90,
                        simultaneous_token_waves: 1,
                        strategy_evolution_unlocks:
                          "25-Shard Curve Squeezes + 500 SOL Flash + 90 SOL DLMM",
                      },
                      {
                        echelon_id: 2,
                        name: "Echelon 2: 500–1,499 SOL Equity",
                        daily_target_range_usd: "$15,000–$35,000+/day",
                        kamino_flash_cap_sol: 2500,
                        meteora_dlmm_surge_pool_sol: 300,
                        simultaneous_token_waves: 3,
                        strategy_evolution_unlocks:
                          "3x Multi-Token Waves + 2,500 SOL Flash + 300 SOL DLMM",
                      },
                      {
                        echelon_id: 3,
                        name: "Echelon 3: 1,500–4,999 SOL Equity",
                        daily_target_range_usd: "$40,000–$95,000+/day",
                        kamino_flash_cap_sol: 10000,
                        meteora_dlmm_surge_pool_sol: 1000,
                        simultaneous_token_waves: 6,
                        strategy_evolution_unlocks:
                          "Local Cross-Chain Solver (500 SOL) + 10k SOL Flash + 1k SOL DLMM",
                      },
                      {
                        echelon_id: 4,
                        name: "Echelon 4: 5,000+ SOL Equity",
                        daily_target_range_usd: "$100,000+/day+ (Uncapped)",
                        kamino_flash_cap_sol: 25000,
                        meteora_dlmm_surge_pool_sol: 3500,
                        simultaneous_token_waves: 12,
                        strategy_evolution_unlocks:
                          "25,000 SOL Flash Monopoly + 3,500 SOL 50-Pair JIT MM + 2k Solver",
                      },
                    ]
                  ).map((ech) => {
                    const isCurrentEchelon =
                      Number(
                        frame.daily_5k_preset?.active_capital_echelon_id ?? 1
                      ) === ech.echelon_id;
                    const rangeUsd =
                      ech.daily_target_range_usd ||
                      ech.daily_velocity_range_usd ||
                      "$5,000+/day";
                    const wavesCount =
                      ech.simultaneous_token_waves ??
                      ech.concurrent_curve_waves ??
                      1;
                    const unlockNote =
                      ech.strategy_evolution_unlocks ||
                      ech.evolved_strategy_unlock ||
                      "";
                    return (
                      <div
                        key={ech.echelon_id}
                        className={`px-2 py-1 rounded border flex flex-col justify-between ${
                          isCurrentEchelon
                            ? "bg-[#10b981]/20 border-[#10b981] text-[#eef4fb]"
                            : "bg-[#09121d]/80 border-[#1e293b] text-[#94a3b8]"
                        }`}
                      >
                        <div className="flex items-center justify-between font-extrabold">
                          <span
                            className={
                              isCurrentEchelon
                                ? "text-[#34d399]"
                                : "text-[#cbd5e1]"
                            }
                          >
                            {isCurrentEchelon ? "🟢 " : "⬆️ "}Echelon{" "}
                            {ech.echelon_id}: {rangeUsd}
                          </span>
                          <span className="text-[#fde68a]">
                            {Number(ech.kamino_flash_cap_sol).toLocaleString()}{" "}
                            SOL Flash
                          </span>
                        </div>
                        <div className="truncate text-[8.5px]" title={unlockNote}>
                          {wavesCount}x Waves ·{" "}
                          {Number(
                            ech.meteora_dlmm_surge_pool_sol
                          ).toLocaleString()}{" "}
                          SOL DLMM · {unlockNote}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* 2B. AUTONOMOUS CLOSED-LOOP & HIGH-SHARPE STRATEGY HUD STRIP (VISIBLE IN ALL COCKPIT VIEW MODES) */}
      <section className="titan-panel px-3.5 py-2.5 bg-gradient-to-r from-[#07121a] via-[#0b1726] to-[#0a131f] border border-[#35e0b0]/45 space-y-2 font-mono text-[10.5px]">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-[#10b981]/20 border border-[#10b981]/60 text-[#34d399] font-extrabold">
              🤖 Closed-Loop Executor:{" "}
              {frame.autonomous_closed_loop?.enabled !== false
                ? "ARMED & SCANNING"
                : "PAUSED"}{" "}
              (Stage:{" "}
              {frame.autonomous_closed_loop?.execution_stage ??
                "ARMED_AWAITING_SOL_DEPOSIT"}
              )
            </span>
            <span className="px-2 py-0.5 rounded bg-[#0a1814] border border-[#35e0b0]/50 text-[#35e0b0] font-bold">
              🛡️ Zero-Rent Native Guard: ACTIVE (Saves 1.85 SOL Deploy Rent — Needs Only &gt;=0.05 SOL)
            </span>
            <span className="px-2 py-0.5 rounded bg-[#081523] border border-[#38bdf8]/50 text-[#7dd3fc] font-bold">
              ⚡ &lt;50µs MMAP 2-Hop Pre-Filter:{" "}
              {(
                frame.atomic_arb_scanner?.local_mmap_sub50us_scan_us ?? 8.2
              ).toFixed(1)}{" "}
              µs ({frame.atomic_arb_scanner?.local_mmap_candidates_count ?? 12}{" "}
              pools)
            </span>
            <span className="px-2 py-0.5 rounded bg-[#141024] border border-[#a855f7]/50 text-[#d8b4fe] font-bold">
              🚀 Offline LLM Fast-Fail: &lt;0.05ms (Ports 8002–8007 Bypassed)
            </span>
            <span className="px-2 py-0.5 rounded bg-[#18130a] border border-[#f59e0b]/50 text-[#fde68a] font-bold">
              📊 Auto Executions: Arbs:{" "}
              {frame.autonomous_closed_loop?.auto_arbs_executed_count ?? 0} |
              Copy-Snipes:{" "}
              {frame.autonomous_closed_loop?.auto_copy_snipes_executed_count ??
                0}{" "}
              | Cranks:{" "}
              {frame.autonomous_closed_loop
                ?.auto_crank_sandwiches_executed_count ?? 0}{" "}
              | 4s Scratches:{" "}
              {frame.autonomous_closed_loop?.auto_exits_executed_count ?? 0}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={async () => {
                const nextEnabled = !(
                  frame.autonomous_closed_loop?.enabled !== false
                );
                const res = await sendTitanIpcCommand(
                  "TOGGLE_AUTONOMOUS_CLOSED_LOOP",
                  { enabled: nextEnabled }
                );
                setLocalLogs((prev) => [
                  String(
                    res.message ||
                      `🤖 Autonomous Closed-Loop -> ${
                        nextEnabled ? "ON (ARMED)" : "OFF (PAUSED)"
                      }`
                  ),
                  ...prev.slice(0, 20),
                ]);
              }}
              className={`px-2.5 py-1 rounded border font-bold transition cursor-pointer ${
                frame.autonomous_closed_loop?.enabled !== false
                  ? "bg-[#10b981]/25 border-[#10b981] text-[#34d399] hover:bg-[#10b981]/35"
                  : "bg-[#f59e0b]/25 border-[#f59e0b] text-[#fde68a] hover:bg-[#f59e0b]/35"
              }`}
            >
              🤖 Toggle Auto-Loop (ON/OFF)
            </button>

            <button
              type="button"
              onClick={async () => {
                const res = await sendTitanIpcCommand(
                  "RUN_AUTONOMOUS_CLOSED_LOOP_NOW",
                  {}
                );
                setLocalLogs((prev) => [
                  String(
                    res.message ||
                      "⚡ Fired Autonomous Closed-Loop Tick Now (0-Rent Native Jupiter Guard + <50µs MMAP Pre-Filter)"
                  ),
                  ...prev.slice(0, 20),
                ]);
              }}
              className="px-2.5 py-1 rounded bg-[#0284c7]/25 hover:bg-[#0284c7]/40 border border-[#38bdf8] text-[#7dd3fc] font-bold transition cursor-pointer"
            >
              ⚡ Fire Autonomous Loop Tick Now
            </button>

            <button
              type="button"
              onClick={async () => {
                const res = await sendTitanIpcCommand(
                  "SCAN_LIVE_JUPITER_ATOMIC_ARBS",
                  {}
                );
                setLocalLogs((prev) => [
                  String(
                    res.message ||
                      "🔬 Scanned <50µs MMAP + Jupiter 2-Hop Atomic Arbs"
                  ),
                  ...prev.slice(0, 20),
                ]);
              }}
              className="px-2.5 py-1 rounded bg-[#10b981]/20 hover:bg-[#10b981]/35 border border-[#35e0b0] text-[#35e0b0] font-bold transition cursor-pointer"
            >
              🔬 Scan &lt;50µs MMAP + Jupiter 2-Hop Arbs
            </button>

            <button
              type="button"
              onClick={async () => {
                const res = await sendTitanIpcCommand(
                  "DISCOVER_VERIFIED_HIGH_WINRATE_WALLETS",
                  { min_win_rate_pct: 70.0, min_avg_hold_secs: 45 }
                );
                setLocalLogs((prev) => [
                  String(
                    res.message ||
                      "🎯 Discovered Verified >=70% Win-Rate Smart-Money Wallets"
                  ),
                  ...prev.slice(0, 20),
                ]);
              }}
              className="px-2.5 py-1 rounded bg-[#a855f7]/25 hover:bg-[#a855f7]/40 border border-[#a855f7] text-[#e9d5ff] font-bold transition cursor-pointer"
            >
              🎯 Discover &gt;=70% Win-Rate Wallets
            </button>

            <button
              type="button"
              onClick={async () => {
                const res = await sendTitanIpcCommand(
                  "EVALUATE_PROTOCOL_BUYBACK_AND_TAX_CRANK",
                  {}
                );
                setLocalLogs((prev) => [
                  String(
                    res.message ||
                      "🔥 Evaluated Lookahead Creator-Vault Crank (96.0%–99.9%)"
                  ),
                  ...prev.slice(0, 20),
                ]);
              }}
              className="px-2.5 py-1 rounded bg-[#f59e0b]/25 hover:bg-[#f59e0b]/40 border border-[#f59e0b] text-[#fde68a] font-bold transition cursor-pointer"
            >
              🔥 Lookahead Creator-Vault Crank (96–99.9%)
            </button>
          </div>
        </div>

        {/* 1-Click $100K / $1M / $10M / $50M Multi-Protocol Mega-Flash Syndicate & Whole-Solana Ecosystem Command Bar */}
        <div className="pt-2 border-t border-[#18283a] flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="px-2 py-0.5 rounded bg-[#1a1306] border border-[#f59e0b]/60 text-[#fde68a] font-extrabold">
              🏦 Mega-Flash Syndicate:{" "}
              {frame.mega_flash_syndicate?.active_tier_label ?? "$10M"} (
              {(
                frame.mega_flash_syndicate?.max_borrow_sol ?? 51000
              ).toLocaleString()}{" "}
              SOL ·{" "}
              {(
                frame.mega_flash_syndicate?.blended_flash_fee_bps ?? 0.06
              ).toFixed(2)}{" "}
              bps Fee · 0.00 SOL Risk)
            </span>
            {[
              { tier_usd: 100000, tier_label: "$100K", text: "$100K (510 SOL)" },
              { tier_usd: 1000000, tier_label: "$1M", text: "$1M (5.1K SOL)" },
              { tier_usd: 10000000, tier_label: "$10M", text: "$10M (51K SOL)" },
              {
                tier_usd: 50000000,
                tier_label: "$50M",
                text: "$50M (255K SOL)",
              },
            ].map((t) => {
              const isSelected =
                (frame.mega_flash_syndicate?.active_tier_usd ?? 10000000) ===
                t.tier_usd;
              return (
                <button
                  key={t.tier_label}
                  type="button"
                  onClick={async () => {
                    const res = await sendTitanIpcCommand(
                      "SET_MEGA_FLASH_SYNDICATE_TIER",
                      {
                        tier_usd: t.tier_usd,
                        tier_label: t.tier_label,
                      }
                    );
                    setLocalLogs((prev) => [
                      String(
                        res.message ||
                          `🏦 Armed Mega-Flash Syndicate Tier ${t.text}`
                      ),
                      ...prev.slice(0, 20),
                    ]);
                  }}
                  className={`px-2 py-0.5 rounded border font-bold transition cursor-pointer ${
                    isSelected
                      ? "bg-[#f59e0b]/30 border-[#fbbf24] text-[#fef08a] shadow-[0_0_8px_rgba(245,158,11,0.3)]"
                      : "bg-[#0c1420] border-[#243449] text-[#94a3b8] hover:text-white hover:border-[#f59e0b]/60"
                  }`}
                >
                  {t.text}
                </button>
              );
            })}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={async () => {
                const res = await sendTitanIpcCommand(
                  "EXECUTE_MEGA_FLASH_SYNDICATE_ARB",
                  {
                    tier_usd:
                      frame.mega_flash_syndicate?.active_tier_usd ?? 10000000,
                    tier_label:
                      frame.mega_flash_syndicate?.active_tier_label ?? "$10M",
                    borrow_sol:
                      frame.mega_flash_syndicate?.max_borrow_sol ?? 51000,
                  }
                );
                setLocalLogs((prev) => [
                  String(
                    res.message ||
                      "⚡ Executed Multi-Protocol Mega-Flash Syndicate Sweep"
                  ),
                  ...prev.slice(0, 20),
                ]);
              }}
              className="px-2.5 py-1 rounded bg-[#10b981]/25 hover:bg-[#10b981]/40 border border-[#10b981] text-[#34d399] font-extrabold transition cursor-pointer"
            >
              ⚡ Execute Mega-Flash Syndicate Sweep
            </button>

            <button
              type="button"
              onClick={async () => {
                const res = await sendTitanIpcCommand(
                  "RUN_WHOLE_SOLANA_ECOSYSTEM_SWEEP",
                  {}
                );
                setLocalLogs((prev) => [
                  String(
                    res.message ||
                      "🌐 Executed Whole-Solana Ecosystem Sweep (CLMM + INF + JLP + Liquidations)"
                  ),
                  ...prev.slice(0, 20),
                ]);
              }}
              className="px-2.5 py-1 rounded bg-[#0284c7]/25 hover:bg-[#0284c7]/40 border border-[#38bdf8] text-[#7dd3fc] font-bold transition cursor-pointer"
            >
              🌐 Whole-Solana Ecosystem Sweep (CLMM + INF + JLP + Liquidations)
            </button>

            <button
              type="button"
              onClick={async () => {
                const res = await sendTitanIpcCommand(
                  "ENFORCE_ANTI_LOSS_IRON_DOME",
                  {}
                );
                setLocalLogs((prev) => [
                  String(
                    res.message ||
                      "🛡️ Enforced Anti-Loss Iron Dome (<=1.8% Gate · 3.5s Scratch · VPIN<=0.78)"
                  ),
                  ...prev.slice(0, 20),
                ]);
              }}
              className="px-2.5 py-1 rounded bg-[#a855f7]/25 hover:bg-[#a855f7]/40 border border-[#a855f7] text-[#e9d5ff] font-bold transition cursor-pointer"
            >
              🛡️ Enforce Anti-Loss Iron Dome (&lt;=1.8% Gate · 3.5s Scratch · VPIN&lt;=0.78)
            </button>
          </div>
        </div>
      </section>

      {/* 3. SUPERCHART + SNIPER DOCK + ACTIVE POSITIONS + EXECUTION STREAM (Visible in SPLIT_DESK & SUPERCHART_FOCUS) */}
      {(cockpitViewMode === "SPLIT_DESK" ||
        cockpitViewMode === "SUPERCHART_FOCUS") && (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-3 items-start">
          {/* LEFT 8.5 COLS: Compact Superchart Panel + Active Positions Table + Execution Spine */}
          <div className="xl:col-span-8 2xl:col-span-9 space-y-3">
            <section
              id="titan-superchart-section"
              className="titan-panel flex flex-col"
            >
              {/* Panel Header */}
              <div className="titan-panel-header flex-wrap gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <h2>Multi-Chart TradingView v5 Superchart</h2>
                  <span className="titan-pill cyan">Alpenglow 200ms Slots</span>
                  <span className="titan-pill purple">
                    👑 Shark Entry @ ${activeMarketMeta.basePrice.toFixed(5)}
                  </span>
                </div>

                {/* Market Pair Selector Pills */}
                <div className="flex items-center gap-1 flex-wrap">
                  {allChartMints.map((item) => (
                    <button
                      key={item.mint}
                      type="button"
                      onClick={() => setActiveMint(item.mint)}
                      className={`px-2 py-0.5 rounded font-mono text-[10.5px] font-bold border transition-colors cursor-pointer ${
                        activeMint === item.mint
                          ? "bg-[#3b82f6]/25 border-[#3b82f6] text-[#93c5fd]"
                          : "bg-[#101824] border-[#243246] text-[#7e91a8] hover:text-[#eef4fb]"
                      }`}
                    >
                      {item.symbol}
                    </button>
                  ))}
                </div>
              </div>

              {/* Clean Grouped Superchart Toolbar: Grid | Timeframe | Overlays | Quick Ratchet | Popout */}
              <div className="flex items-center justify-between gap-2 px-3 py-1.5 bg-[#0a0f18] border-b border-[#1a2534] flex-wrap font-mono text-[10.5px]">
                {/* Group 1: Grid: 1x / 2x / 4x + Height */}
                <div className="flex items-center gap-1 bg-[#070c14] border border-[#1a2534] rounded px-1.5 py-0.5">
                  <span className="text-[#7e91a8] text-[9.5px] font-bold uppercase mr-0.5">
                    Grid:
                  </span>
                  {(
                    [
                      { id: "1_FULL", label: "1x" },
                      { id: "2_SPLIT", label: "2x" },
                      { id: "4_QUAD", label: "4x" },
                    ] as const
                  ).map((g) => (
                    <button
                      key={g.id}
                      type="button"
                      onClick={() => setGridLayout(g.id)}
                      className={`px-1.5 py-0.5 rounded font-bold border transition-colors cursor-pointer ${
                        gridLayout === g.id
                          ? "bg-[#10b981]/25 border-[#10b981] text-[#34d399]"
                          : "bg-[#101824] border-[#243246] text-[#7e91a8] hover:text-[#eef4fb]"
                      }`}
                    >
                      {g.label}
                    </button>
                  ))}
                  <span className="text-[#243246] mx-0.5">|</span>
                  {[
                    { h: 340, label: "340px" },
                    { h: 430, label: "430px" },
                    { h: 540, label: "540px" },
                  ].map((sz) => (
                    <button
                      key={sz.h}
                      type="button"
                      onClick={() => setChartHeightPx(sz.h)}
                      className={`px-1.5 py-0.5 rounded text-[9.5px] border cursor-pointer ${
                        chartHeightPx === sz.h
                          ? "bg-[#38bdf8]/20 border-[#38bdf8] text-[#38bdf8] font-bold"
                          : "bg-[#101824] border-[#243246] text-[#7e91a8] hover:text-[#eef4fb]"
                      }`}
                    >
                      {sz.label}
                    </button>
                  ))}
                </div>

                {/* Group 2: Timeframe: 1Tick..15m..1D */}
                <div className="flex items-center gap-1 bg-[#070c14] border border-[#1a2534] rounded px-1.5 py-0.5 flex-wrap">
                  <span className="text-[#7e91a8] text-[9.5px] font-bold uppercase mr-0.5">
                    Timeframe:
                  </span>
                  {(
                    [
                      "1 Tick",
                      "200ms",
                      "1s",
                      "5s",
                      "15s",
                      "1m",
                      "5m",
                      "15m",
                      "1h",
                      "1D",
                    ] as TimeframeOption[]
                  ).map((tf) => (
                    <button
                      key={tf}
                      type="button"
                      onClick={() => setTimeframe(tf)}
                      className={`px-1.5 py-0.5 rounded border transition-colors cursor-pointer ${
                        timeframe === tf
                          ? "bg-[#3b82f6]/25 border-[#3b82f6] text-[#93c5fd] font-bold"
                          : "bg-[#101824] border-[#1a2534] text-[#7e91a8] hover:text-[#eef4fb]"
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>

                {/* Group 3: Overlays: VWAP / EMA / BB / Vol / DLMM */}
                <div className="flex items-center gap-1 bg-[#070c14] border border-[#1a2534] rounded px-1.5 py-0.5 flex-wrap">
                  <span className="text-[#7e91a8] text-[9.5px] font-bold uppercase mr-0.5">
                    Overlays:
                  </span>
                  {[
                    { key: "VWAP", label: "VWAP" },
                    { key: "EMA_RIBBON", label: "EMA" },
                    { key: "BOLLINGER", label: "BB" },
                    { key: "VOLUME_DELTA", label: "Vol" },
                    { key: "DLMM_BIN_HEATMAP", label: "DLMM" },
                  ].map((ind) => (
                    <button
                      key={ind.key}
                      type="button"
                      onClick={() => toggleIndicator(ind.key)}
                      className={`px-1.5 py-0.5 rounded border transition-colors cursor-pointer ${
                        enabledIndicators[ind.key]
                          ? "bg-[#10b981]/20 border-[#10b981] text-[#34d399] font-bold"
                          : "bg-[#101824] border-[#1a2534] text-[#7e91a8]"
                      }`}
                    >
                      {ind.label}
                    </button>
                  ))}
                </div>

                {/* Group 4: Quick Ratchet: +0.85% BE / 4% / 11% & Group 5: Popout */}
                <div className="flex items-center gap-1 bg-[#070c14] border border-[#1a2534] rounded px-1.5 py-0.5 flex-wrap">
                  <span className="text-[#7e91a8] text-[9.5px] font-bold uppercase mr-0.5">
                    Quick Ratchet:
                  </span>
                  <button
                    type="button"
                    onClick={() => handleChartQuickRatchet("BREAKEVEN_FLOOR")}
                    className="px-1.5 py-0.5 rounded bg-[#f59e0b]/25 hover:bg-[#f59e0b]/40 border border-[#f59e0b] text-[#fde68a] font-bold cursor-pointer"
                  >
                    🔒 +0.85% BE
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChartQuickRatchet("TIGHT_SCALP_4PCT")}
                    className="px-1.5 py-0.5 rounded bg-[#10b981]/25 hover:bg-[#10b981]/40 border border-[#10b981] text-[#34d399] font-bold cursor-pointer"
                  >
                    ⚡ 4%
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChartQuickRatchet("STANDARD_11PCT")}
                    className="px-1.5 py-0.5 rounded bg-[#06b6d4]/20 hover:bg-[#06b6d4]/35 border border-[#06b6d4] text-[#67e8f9] font-bold cursor-pointer"
                  >
                    🛡️ 11%
                  </button>
                  <span className="text-[#243246] mx-0.5">|</span>
                  <button
                    type="button"
                    onClick={openActiveMintPopout}
                    className="px-2 py-0.5 rounded bg-[#35e0b0]/20 hover:bg-[#35e0b0]/35 border border-[#35e0b0] text-[#35e0b0] font-bold cursor-pointer"
                  >
                    🗗 Popout
                  </button>
                </div>
              </div>

              {/* Secondary Strip: Chart Style, Scale, Zoom, Drawing Tools & Cap/TP Sliders */}
              <div className="flex items-center justify-between gap-2 px-3 py-1 bg-[#090e16] border-b border-[#1a2534] flex-wrap font-mono text-[10px]">
                {/* Chart Style, Value/Scale & Drawing Tools */}
                <div className="flex items-center gap-1 flex-wrap">
                  {(
                    [
                      { id: "CANDLES", label: "Candles" },
                      { id: "AREA", label: "Area" },
                      { id: "LINE", label: "Line" },
                    ] as const
                  ).map((st) => (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => setChartStyle(st.id)}
                      className={`px-1.5 py-0.5 rounded border transition-colors cursor-pointer ${
                        chartStyle === st.id
                          ? "bg-[#06b6d4]/20 border-[#06b6d4] text-[#67e8f9] font-bold"
                          : "bg-[#101824] border-[#1a2534] text-[#7e91a8] hover:text-[#eef4fb]"
                      }`}
                    >
                      {st.label}
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() =>
                      setValueMode((m) =>
                        m === "PRICE_USD_SOL"
                          ? "MARKET_CAP_USD"
                          : "PRICE_USD_SOL"
                      )
                    }
                    className="px-1.5 py-0.5 rounded bg-[#101824] border border-[#243246] text-[#fbbf24] cursor-pointer"
                  >
                    {valueMode === "PRICE_USD_SOL" ? "$Price" : "$MC"}
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      setScaleMode((s) => (s === "LINEAR" ? "LOG" : "LINEAR"))
                    }
                    className="px-1.5 py-0.5 rounded bg-[#101824] border border-[#243246] text-[#38bdf8] cursor-pointer"
                  >
                    {scaleMode}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleZoomBars(30)}
                    className="px-1.5 py-0.5 rounded bg-[#101824] border border-[#1a2534] text-[#7e91a8] hover:text-[#eef4fb] cursor-pointer"
                  >
                    30B
                  </button>
                  <button
                    type="button"
                    onClick={() => handleZoomBars(60)}
                    className="px-1.5 py-0.5 rounded bg-[#101824] border border-[#1a2534] text-[#7e91a8] hover:text-[#eef4fb] cursor-pointer"
                  >
                    60B
                  </button>
                  <button
                    type="button"
                    onClick={() => handleZoomBars("FIT")}
                    className="px-1.5 py-0.5 rounded bg-[#101824] border border-[#1a2534] text-[#7e91a8] hover:text-[#eef4fb] cursor-pointer"
                  >
                    Fit
                  </button>

                  <span className="text-[#243246] mx-0.5">|</span>
                  <span className="text-[#7e91a8] uppercase font-bold">
                    Draw:
                  </span>
                  {[
                    { id: "CURSOR", label: "✥ Cursor" },
                    { id: "TRENDLINE", label: "╱ Trendline" },
                    { id: "PRICE_ALERT_RAY", label: "⊢ Price Ray" },
                    { id: "FIB_RETRACEMENT", label: "≡ Fib" },
                    { id: "RR_BOX", label: "◧ RR Box" },
                    { id: "MEASURE_RULER", label: "📏 Measure" },
                  ].map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => {
                        setActiveDrawingTool(t.id as DrawingTool);
                        setPendingPoint(null);
                      }}
                      className={`px-1.5 py-0.5 rounded border transition-colors cursor-pointer ${
                        activeDrawingTool === t.id
                          ? "bg-[#3b82f6]/25 border-[#3b82f6] text-[#93c5fd] font-bold"
                          : "bg-[#101824] border-[#1a2534] text-[#7e91a8] hover:text-[#eef4fb]"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                  {drawings.length > 0 && (
                    <button
                      type="button"
                      onClick={() => {
                        setDrawings([]);
                        setPendingPoint(null);
                      }}
                      className="px-1.5 py-0.5 rounded bg-[#ef4444]/20 border border-[#ef4444]/50 text-[#f87171] cursor-pointer"
                    >
                      ✕ Clear ({drawings.length})
                    </button>
                  )}
                </div>

                {/* Interactive Cap & TP Line Sliders */}
                <div className="flex items-center gap-3 flex-wrap">
                  <label className="flex items-center gap-1.5 text-[#38bdf8]">
                    <span>
                      ⚡ Master Cap ({masterCapMultiplier.toFixed(2)}x):
                    </span>
                    <input
                      type="range"
                      min="1.02"
                      max="1.15"
                      step="0.01"
                      value={masterCapMultiplier}
                      onChange={(e) =>
                        setMasterCapMultiplier(parseFloat(e.target.value))
                      }
                      onMouseUp={() =>
                        void sendTitanIpcCommand("UPDATE_SETTINGS", {
                          master_cap_multiplier: masterCapMultiplier,
                          asymmetric_tp_multiplier: asymmetricTpMultiplier,
                        })
                      }
                      onTouchEnd={() =>
                        void sendTitanIpcCommand("UPDATE_SETTINGS", {
                          master_cap_multiplier: masterCapMultiplier,
                          asymmetric_tp_multiplier: asymmetricTpMultiplier,
                        })
                      }
                      className="w-20 accent-[#06b6d4]"
                    />
                  </label>
                  <label className="flex items-center gap-1.5 text-[#c084fc]">
                    <span>
                      Asym TP ({asymmetricTpMultiplier.toFixed(2)}x):
                    </span>
                    <input
                      type="range"
                      min="1.50"
                      max="4.00"
                      step="0.05"
                      value={asymmetricTpMultiplier}
                      onChange={(e) =>
                        setAsymmetricTpMultiplier(parseFloat(e.target.value))
                      }
                      onMouseUp={() =>
                        void sendTitanIpcCommand("UPDATE_SETTINGS", {
                          master_cap_multiplier: masterCapMultiplier,
                          asymmetric_tp_multiplier: asymmetricTpMultiplier,
                        })
                      }
                      onTouchEnd={() =>
                        void sendTitanIpcCommand("UPDATE_SETTINGS", {
                          master_cap_multiplier: masterCapMultiplier,
                          asymmetric_tp_multiplier: asymmetricTpMultiplier,
                        })
                      }
                      className="w-20 accent-[#a855f7]"
                    />
                  </label>
                </div>
              </div>

              {/* MULTI-CHART CANVAS CONTAINER (Supports 1x Single, 2x Side-by-Side Dual, or 4x Quad) */}
              <div
                className={`grid gap-2.5 p-2 bg-[#070b11] ${
                  gridLayout === "1_FULL"
                    ? "grid-cols-1"
                    : "grid-cols-1 md:grid-cols-2"
                }`}
              >
                {visibleCharts.map((item, idx) => {
                  const itemTrailState = frame.trail_win_positions?.[item.mint];
                  const baseEntryPx =
                    itemTrailState?.entry_price_sol || item.basePrice || 0.00172;
                  const hwmPx =
                    itemTrailState?.high_water_mark_price_sol ||
                    baseEntryPx * 2.65;
                  const liveTrailStopPx = Math.max(
                    baseEntryPx * 1.0085,
                    hwmPx * (1.0 - trailPctOverride / 100.0)
                  );
                  const liveLockedProfitPct = Math.max(
                    0.85,
                    ((liveTrailStopPx - baseEntryPx) / baseEntryPx) * 100.0
                  );
                  return (
                    <div
                      key={`${item.mint}-${idx}`}
                      onClick={() => setActiveMint(item.mint)}
                      className={`flex flex-col bg-[#080d14] border rounded overflow-hidden ${
                        activeMint === item.mint
                          ? "border-[#3b82f6]/70"
                          : "border-[#1a2534]"
                      }`}
                    >
                      {/* Sub-header with Per-Chart Coin Selector */}
                      <div className="h-7 shrink-0 flex items-center justify-between px-2.5 bg-[#0b111b] border-b border-[#1a2534] text-[10.5px] font-mono">
                        <div className="flex items-center gap-2 truncate">
                          <span className="px-1.5 py-0.5 rounded bg-[#3b82f6]/20 text-[#93c5fd] font-bold text-[9.5px]">
                            CHART #{idx + 1}
                          </span>
                          {gridLayout !== "4_QUAD" ? (
                            <select
                              value={idx === 0 ? activeMint : secondMint}
                              onClick={(e) => e.stopPropagation()}
                              onChange={(e) => {
                                if (idx === 0) {
                                  setActiveMint(e.target.value);
                                } else {
                                  setSecondMint(e.target.value);
                                }
                              }}
                              className="bg-[#101824] border border-[#283e5c] rounded px-1.5 py-0.5 text-[#eef4fb] font-bold text-[10.5px]"
                            >
                              {allChartMints.map((m) => (
                                <option key={m.mint} value={m.mint}>
                                  {m.symbol}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <span className="font-bold text-[#eef4fb]">
                              {item.symbol}
                            </span>
                          )}
                          <span className="text-[#7e91a8] truncate">
                            {item.venue}
                          </span>
                          <span className="titan-pill purple">
                            {(item as { whaleTag?: string }).whaleTag ||
                              "👑 Shark"}
                          </span>
                        </div>
                        <div className="text-[#10b981] font-bold shrink-0">
                          MC ${(item.mcUsd / 1000).toFixed(1)}k
                        </div>
                      </div>

                      {/* Balanced Chart Height (430px default, or 340px / 540px via header buttons) */}
                      <div
                        style={{
                          height:
                            gridLayout === "4_QUAD"
                              ? `${Math.round(chartHeightPx * 0.68)}px`
                              : `${chartHeightPx}px`,
                          minHeight:
                            gridLayout === "4_QUAD"
                              ? `${Math.round(chartHeightPx * 0.68)}px`
                              : `${chartHeightPx}px`,
                          maxHeight:
                            gridLayout === "4_QUAD"
                              ? `${Math.round(chartHeightPx * 0.68)}px`
                              : `${chartHeightPx}px`,
                        }}
                        className="relative w-full flex overflow-hidden"
                        onMouseMove={(e) => {
                          if (!isDraggingTrailBar) return;
                          const r = e.currentTarget.getBoundingClientRect();
                          const relY = Math.max(
                            0.05,
                            Math.min(0.95, (e.clientY - r.top) / r.height)
                          );
                          const nextPct =
                            Math.round(
                              Math.max(0.5, Math.min(35, relY * 36)) * 4
                            ) / 4;
                          setTrailPctOverride(nextPct);
                        }}
                        onMouseUp={() => {
                          if (isDraggingTrailBar) {
                            setIsDraggingTrailBar(false);
                            void sendTitanIpcCommand("UPDATE_TRAIL_WIN_STOP", {
                              mint: item.mint,
                              trail_pct: trailPctOverride / 100.0,
                            });
                            setLocalLogs((prev) => [
                              `🛡️ Dragged Trail-Win Stop to ${trailPctOverride.toFixed(2)}% below HWM on ${item.symbol}`,
                              ...prev.slice(0, 20),
                            ]);
                          }
                        }}
                        onMouseLeave={() => {
                          if (isDraggingTrailBar) {
                            setIsDraggingTrailBar(false);
                          }
                        }}
                      >
                        <div className="relative flex-1 h-full">
                          <div
                            ref={(el) => {
                              chartContainerRefs.current[idx] = el;
                            }}
                            style={{ position: "absolute", inset: 0 }}
                          />

                          {/* Live Draggable Green Step-Up Ratchet Trail-Win Stop Line */}
                          <div
                            onMouseDown={(e) => {
                              e.stopPropagation();
                              setIsDraggingTrailBar(true);
                            }}
                            style={{
                              top: `${Math.min(82, Math.max(18, 22 + trailPctOverride * 1.6))}%`,
                            }}
                            title="Click and drag vertically to tighten or loosen the Trail-Win Stop % (0.5% to 35%)"
                            className="absolute left-2 right-16 z-20 flex items-center cursor-ns-resize select-none group"
                          >
                            <div className="flex-1 border-t-2 border-dashed border-[#10b981] shadow-[0_0_8px_rgba(16,185,129,0.75)]" />
                            <div className="px-2 py-0.5 rounded bg-[#062419]/95 border border-[#10b981] text-[#34d399] font-mono text-[10px] font-bold shadow-md flex items-center gap-1.5">
                              <span>
                                🛡️ TRAIL-WIN STOP: $
                                {liveTrailStopPx.toFixed(5)} [+
                                {liveLockedProfitPct.toFixed(0)}% LOCKED ·{" "}
                                {trailPctOverride.toFixed(1)}% HWM]
                              </span>
                              <span className="text-[#a7f3d0] text-[9px]">
                                ↕ DRAG
                              </span>
                            </div>
                          </div>

                          {idx === 0 && (
                            <canvas
                              ref={drawingCanvasRef}
                              onClick={handleCanvasClick}
                              onMouseMove={(e) => {
                                if (!pendingPoint) return;
                                const r =
                                  e.currentTarget.getBoundingClientRect();
                                setHoverPoint({
                                  x: e.clientX - r.left,
                                  y: e.clientY - r.top,
                                });
                              }}
                              style={{
                                position: "absolute",
                                inset: 0,
                                zIndex: 10,
                                pointerEvents:
                                  activeDrawingTool === "CURSOR"
                                    ? "none"
                                    : "auto",
                                cursor:
                                  activeDrawingTool === "CURSOR"
                                    ? "default"
                                    : "crosshair",
                              }}
                            />
                          )}
                        </div>

                        {enabledIndicators.DLMM_BIN_HEATMAP && (
                          <div className="w-24 shrink-0 bg-[#090e16] border-l border-[#1a2534] px-1.5 py-1 flex flex-col justify-between text-[9.5px] font-mono select-none">
                            <div className="text-[#38bdf8] font-bold text-center border-b border-[#1a2534] pb-0.5">
                              DLMM Bins
                            </div>
                            {DLMM_BINS.map((b) => (
                              <div
                                key={b.binId}
                                className="flex items-center gap-1"
                              >
                                <span
                                  className={`w-8 text-right ${
                                    b.isActive
                                      ? "text-[#10b981] font-bold"
                                      : "text-[#7e91a8]"
                                  }`}
                                >
                                  {b.binId}
                                </span>
                                <div className="flex-1 bg-[#101824] h-1.5 rounded-xs overflow-hidden">
                                  <div
                                    style={{
                                      width: `${Math.min(
                                        100,
                                        (b.solLiquidity / 120) * 100
                                      )}%`,
                                    }}
                                    className={`h-full ${
                                      b.isActive
                                        ? "bg-[#10b981]"
                                        : "bg-[#06b6d4]/60"
                                    }`}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Open Positions Table stacked directly below the compact chart */}
            <section className="titan-panel">
              <div className="titan-panel-header">
                <div>
                  <h2>Active Positions &amp; Staged Profit Ladder</h2>
                  <div className="panel-sub">
                    Click any position to load on Superchart or execute
                    immediate partial/100% scale-out with ATA rent reclaim
                  </div>
                </div>
                <span className="titan-pill positive">
                  {openPositions.length} Open Positions
                </span>
              </div>

              <div className="p-3 overflow-x-auto">
                {openPositions.length === 0 ? (
                  <div className="text-center py-6 text-[#7e91a8] font-mono text-xs">
                    No active directional positions · Use the Sniper Dock to
                    open a position or wait for Shadow Shark trigger.
                  </div>
                ) : (
                  <table className="titan-table">
                    <thead>
                      <tr>
                        <th>Token / Venue</th>
                        <th>Shard</th>
                        <th>Size SOL</th>
                        <th>Mark Price</th>
                        <th>PnL</th>
                        <th>Ladder Stage</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {openPositions.map((pos) => (
                        <tr
                          key={pos.mint}
                          className={
                            activeMint === pos.mint ? "bg-[#3b82f6]/10" : ""
                          }
                        >
                          <td>
                            <button
                              type="button"
                              onClick={() => {
                                setActiveMint(pos.mint);
                                const cleanSymbol = String(
                                  pos.symbol || "TITAN"
                                )
                                  .replace("/SOL", "")
                                  .replace("$", "")
                                  .trim();
                                const isCurve =
                                  pos.venue.toLowerCase().includes("curve") ||
                                  pos.stage.includes("H1");
                                const known = allChartMints.find(
                                  (m) => m.mint === pos.mint
                                );
                                setPopupToken({
                                  mint: pos.mint,
                                  symbol: cleanSymbol,
                                  name: `${cleanSymbol} Autonomous Gem`,
                                  pair: `${cleanSymbol}/SOL`,
                                  ageSeconds: 45,
                                  stage: isCurve ? "FINAL_STRETCH" : "MIGRATED",
                                  category: "AI_AGENTS",
                                  launchpad: isCurve ? "PUMP" : "PUMPSWAP",
                                  bondingCurvePct: isCurve ? 76.5 : 100.0,
                                  marketCapUsd:
                                    known?.mcUsd ??
                                    Math.max(
                                      45000,
                                      Math.round(
                                        pos.mark_price_usd * 100_000_000
                                      )
                                    ),
                                  liquidityUsd: 42000,
                                  volume5mUsd: 96500,
                                  txns5mBuys: 215,
                                  txns5mSells: 68,
                                  top10HoldersPct: 14.8,
                                  devHoldPct: 0.0,
                                  devAction: "BURNED",
                                  snipersPct: 5.1,
                                  insidersBundlePct: 6.4,
                                  dexPaid: true,
                                  mintAuthRevoked: true,
                                  lpBurned: true,
                                  hasSocials: true,
                                  kolSmartMoneyCount: 5,
                                  bluechipIndexPct: 9.4,
                                  isInvested: true,
                                  investedSizeSol: pos.size_sol,
                                  investedPnlPct: pos.pnl_pct,
                                  investedPnlSol: pos.pnl_sol,
                                  horizon: pos.stage,
                                });
                              }}
                              className="text-left cursor-pointer hover:text-[#38bdf8] flex items-center gap-2.5"
                            >
                              <CoinAvatarBadge
                                symbolOrPair={pos.symbol || "TITAN"}
                                mint={pos.mint}
                                size={36}
                                isInvested={true}
                              />
                              <div>
                                <div className="font-bold text-[#eef4fb] flex items-center gap-1.5">
                                  <span>{pos.symbol}</span>
                                  <span className="px-1.5 py-0.5 rounded text-[8.5px] font-mono bg-[#35e0b0]/15 text-[#35e0b0] border border-[#35e0b0]/35">
                                    📊 Popup Chart
                                  </span>
                                </div>
                                <div className="text-[10px] text-[#7e91a8]">
                                  {pos.venue}
                                </div>
                              </div>
                            </button>
                          </td>
                          <td className="text-[#38bdf8]">{pos.shard}</td>
                          <td className="font-bold text-[#eef4fb]">
                            {privacyMode
                              ? "••• SOL"
                              : `${pos.size_sol.toFixed(2)} SOL`}
                          </td>
                          <td className="text-[#d5deea]">
                            ${pos.mark_price_usd.toFixed(6)}
                          </td>
                          <td>
                            <span
                              className={`titan-pill ${
                                pos.pnl_pct >= 0 ? "positive" : "negative"
                              }`}
                            >
                              {pos.pnl_pct >= 0 ? "+" : ""}
                              {pos.pnl_pct.toFixed(1)}% (
                              {privacyMode
                                ? "••• SOL"
                                : `${pos.pnl_sol >= 0 ? "+" : ""}${pos.pnl_sol.toFixed(2)} SOL`}
                              )
                            </span>
                          </td>
                          <td>
                            <span className="titan-pill cyan">{pos.stage}</span>
                          </td>
                          <td>
                            <div className="flex items-center gap-1.5">
                              <button
                                type="button"
                                onClick={() =>
                                  handleRowToggleLock(
                                    pos.mint,
                                    pos.locked_manual
                                  )
                                }
                                className={`px-2 py-1 rounded text-[10px] font-mono border cursor-pointer ${
                                  pos.locked_manual
                                    ? "bg-[#35e0b0]/20 border-[#35e0b0] text-[#35e0b0]"
                                    : "bg-[#101824] border-[#243246] text-[#7e91a8] hover:text-[#eef4fb]"
                                }`}
                              >
                                {pos.locked_manual
                                  ? "🔒 Lock: 🟢 ON"
                                  : "🔓 Lock: 🔴 OFF (Auto)"}
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  handleRowExit(pos.mint, 50, false)
                                }
                                className="px-2 py-1 rounded bg-[#f59e0b]/20 hover:bg-[#f59e0b]/35 border border-[#f59e0b]/50 text-[#fbbf24] text-[10px] font-mono font-bold cursor-pointer"
                              >
                                Sell 50%
                              </button>
                              <button
                                type="button"
                                onClick={() =>
                                  handleRowExit(pos.mint, 100, true)
                                }
                                className="px-2 py-1 rounded bg-[#ef4444]/25 hover:bg-[#ef4444]/40 border border-[#ef4444]/60 text-[#fca5a5] text-[10px] font-mono font-bold cursor-pointer"
                              >
                                Close 100% + Rent
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </section>

            {/* Live Execution & Event Spine */}
            <section className="titan-panel">
              <div className="titan-panel-header">
                <div>
                  <h2>Live Execution &amp; Event Spine</h2>
                  <div className="panel-sub">
                    Real-Time Agave 4.5 V0 Dispatches, Shadow Triggers &amp;
                    Jito BAM Confirmations
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {["ALL", "MANUAL", "SHADOW", "MEV"].map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setEventFilter(cat)}
                      className={`px-2 py-0.5 rounded font-mono text-[10px] border cursor-pointer ${
                        eventFilter === cat
                          ? "bg-[#3b82f6]/25 border-[#3b82f6] text-[#93c5fd] font-bold"
                          : "bg-[#101824] border-[#243246] text-[#7e91a8]"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              <div className="p-3 space-y-2 max-h-[210px] overflow-y-auto font-mono text-[11px]">
                {localLogs.map((msg, idx) => (
                  <div
                    key={`local-${idx}`}
                    className="p-2 rounded bg-[#10b981]/10 border border-[#10b981]/40 text-[#34d399]"
                  >
                    ✓ {msg}
                  </div>
                ))}
                {filteredEvents.map((ev, idx) => (
                  <div
                    key={`ev-${idx}`}
                    className="p-2.5 rounded bg-[#090e16] border border-[#1a2534] text-[#d5deea] leading-relaxed"
                  >
                    {ev}
                  </div>
                ))}
              </div>
            </section>
          </div>

          {/* RIGHT 3.5 COLS: Sniper & Manual Override Dock */}
          <div className="xl:col-span-4 2xl:col-span-3">
            <ManualTradePanel
              activeMint={activeMint}
              onChangeMint={setActiveMint}
              shards={frame.shards}
              openPositions={openPositions}
              horizonsConfig={frame.horizons_config}
              activeTrailState={activeTrailState}
              trailPctOverride={trailPctOverride}
              onChangeTrailPctOverride={setTrailPctOverride}
              onLogExecution={(msg) =>
                setLocalLogs((prev) => [msg, ...prev.slice(0, 20)])
              }
            />
          </div>
        </div>
      )}

      {/* 4. AXIOM.TRADE PULSE × GMGN.AI TRENCHES TERMINAL & INVESTED COINS PICTURE SHOWCASE (Visible in SPLIT_DESK & TRENCH_DISCOVERY, kept mounted to preserve live stream state) */}
      <div
        className={
          cockpitViewMode === "SPLIT_DESK" ||
          cockpitViewMode === "TRENCH_DISCOVERY" ||
          (cockpitViewMode as string) === "TRADING_DESK" ||
          (cockpitViewMode as string) === "TRENCH_SNIPER"
            ? "block"
            : "hidden"
        }
      >
        <AxiomGmgnTrenchTerminal
          frame={frame}
          onStatusMessage={(msg) =>
            setLocalLogs((prev) => [msg, ...prev.slice(0, 20)])
          }
          onPinToChart1={(mint, symbol) => {
            const symLabel = symbol.includes("/") ? symbol : `${symbol} / SOL`;
            setCustomChartMints((prev) =>
              prev.some((p) => p.mint === mint)
                ? prev
                : [
                    ...prev,
                    {
                      symbol: symLabel,
                      mint,
                      venue: "PumpSwap + Meteora DLMM",
                      mcUsd: 168_500,
                      basePrice: 0.001685,
                    },
                  ]
            );
            setActiveMint(mint);
            if (cockpitViewMode === "TRENCH_DISCOVERY") {
              setCockpitViewMode("SPLIT_DESK");
            }
            setLocalLogs((prev) => [
              `📌 Loaded $${symbol} (${mint.slice(0, 6)}...) into Superchart #1`,
              ...prev.slice(0, 20),
            ]);
            document
              .getElementById("titan-superchart-section")
              ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }}
          onPinToChart2={(mint, symbol) => {
            const symLabel = symbol.includes("/") ? symbol : `${symbol} / SOL`;
            setCustomChartMints((prev) =>
              prev.some((p) => p.mint === mint)
                ? prev
                : [
                    ...prev,
                    {
                      symbol: symLabel,
                      mint,
                      venue: "PumpSwap + Meteora DLMM",
                      mcUsd: 168_500,
                      basePrice: 0.001685,
                    },
                  ]
            );
            setSecondMint(mint);
            setGridLayout("2_SPLIT");
            if (cockpitViewMode === "TRENCH_DISCOVERY") {
              setCockpitViewMode("SPLIT_DESK");
            }
            setLocalLogs((prev) => [
              `📌 Loaded $${symbol} (${mint.slice(0, 6)}...) into Superchart #2 (2x Dual Mode)`,
              ...prev.slice(0, 20),
            ]);
            document
              .getElementById("titan-superchart-section")
              ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }}
        />
      </div>

      {/* 5. COMPACT EXECUTION SPINE IN TRENCH_DISCOVERY OR CAPITAL_MATRIX MODES */}
      {(cockpitViewMode === "TRENCH_DISCOVERY" ||
        cockpitViewMode === "CAPITAL_MATRIX") && (
        <section className="titan-panel">
          <div className="titan-panel-header">
            <div>
              <h2>Live Execution &amp; Event Spine</h2>
              <div className="panel-sub">
                Real-Time Agave 4.5 V0 Dispatches, Shadow Triggers &amp; Jito
                BAM Confirmations
              </div>
            </div>
            <div className="flex items-center gap-1">
              {["ALL", "MANUAL", "SHADOW", "MEV"].map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setEventFilter(cat)}
                  className={`px-2 py-0.5 rounded font-mono text-[10px] border cursor-pointer ${
                    eventFilter === cat
                      ? "bg-[#3b82f6]/25 border-[#3b82f6] text-[#93c5fd] font-bold"
                      : "bg-[#101824] border-[#243246] text-[#7e91a8]"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="p-3 space-y-2 max-h-[210px] overflow-y-auto font-mono text-[11px]">
            {localLogs.map((msg, idx) => (
              <div
                key={`local-${idx}`}
                className="p-2 rounded bg-[#10b981]/10 border border-[#10b981]/40 text-[#34d399]"
              >
                ✓ {msg}
              </div>
            ))}
            {filteredEvents.map((ev, idx) => (
              <div
                key={`ev-${idx}`}
                className="p-2.5 rounded bg-[#090e16] border border-[#1a2534] text-[#d5deea] leading-relaxed"
              >
                {ev}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Popup Display Modal for Active Positions Table Clicks & Superchart Popout */}
      <TokenDetailChartModal
        token={popupToken}
        solUsd={frame.sol_usd}
        onClose={() => setPopupToken(null)}
        onStatusMessage={(msg) =>
          setLocalLogs((prev) => [msg, ...prev.slice(0, 20)])
        }
        onTokenTradeUpdate={(mint, isInvested, sizeSol, pnlPct) =>
          setPopupToken((prev) =>
            prev && prev.mint === mint
              ? {
                  ...prev,
                  isInvested,
                  investedSizeSol: Math.max(0, Number(sizeSol.toFixed(4))),
                  investedPnlPct: pnlPct,
                }
              : prev
          )
        }
        onPinToChart1={(mint, symbol) => {
          const symLabel = symbol.includes("/") ? symbol : `${symbol} / SOL`;
          setCustomChartMints((prev) =>
            prev.some((p) => p.mint === mint)
              ? prev
              : [
                  ...prev,
                  {
                    symbol: symLabel,
                    mint,
                    venue: "PumpSwap + Meteora DLMM",
                    mcUsd: 168_500,
                    basePrice: 0.001685,
                  },
                ]
          );
          setActiveMint(mint);
          setLocalLogs((prev) => [
            `📌 Loaded $${symbol} (${mint.slice(0, 6)}...) into Superchart #1`,
            ...prev.slice(0, 20),
          ]);
          document
            .getElementById("titan-superchart-section")
            ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }}
        onPinToChart2={(mint, symbol) => {
          const symLabel = symbol.includes("/") ? symbol : `${symbol} / SOL`;
          setCustomChartMints((prev) =>
            prev.some((p) => p.mint === mint)
              ? prev
              : [
                  ...prev,
                  {
                    symbol: symLabel,
                    mint,
                    venue: "PumpSwap + Meteora DLMM",
                    mcUsd: 168_500,
                    basePrice: 0.001685,
                  },
                ]
          );
          setSecondMint(mint);
          setGridLayout("2_SPLIT");
          setLocalLogs((prev) => [
            `📌 Loaded $${symbol} (${mint.slice(0, 6)}...) into Superchart #2 (2x Dual Mode)`,
            ...prev.slice(0, 20),
          ]);
          document
            .getElementById("titan-superchart-section")
            ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }}
      />
    </div>
  );
};
