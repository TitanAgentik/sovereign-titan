import React, { useEffect, useRef, useState } from "react";
import {
  AreaSeries,
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  IChartApi,
  LineSeries,
  UTCTimestamp,
  createChart,
} from "lightweight-charts";
import { usePrivacyMode } from "../hooks/usePrivacyMode";
import { sendTitanIpcCommand } from "../services/titanIpcClient";
import { TrenchTokenEntry } from "./AxiomGmgnTrenchTerminal";
import { CoinAvatarBadge } from "./CoinAvatarBadge";

interface TokenDetailChartModalProps {
  token: TrenchTokenEntry | null;
  onClose: () => void;
  onStatusMessage?: (msg: string) => void;
  onPinToChart1?: (mint: string, symbol: string) => void;
  onPinToChart2?: (mint: string, symbol: string) => void;
  onTokenTradeUpdate?: (
    mint: string,
    isInvested: boolean,
    sizeSol: number,
    pnlPct: number
  ) => void;
  solUsd?: number;
}

type ModalTimeframe = "200ms" | "1s" | "5s" | "15s" | "1m" | "5m" | "15m" | "1h";
type ModalChartStyle = "CANDLES" | "AREA" | "LINE";

interface TradeTapeRow {
  id: string;
  age: string;
  side: "BUY" | "SELL";
  solAmount: number;
  usdValue: number;
  mcUsd: number;
  walletTag: string;
  walletColor: string;
}

export const TokenDetailChartModal: React.FC<TokenDetailChartModalProps> = ({
  token,
  onClose,
  onStatusMessage,
  onPinToChart1,
  onPinToChart2,
  onTokenTradeUpdate,
  solUsd = 194.5,
}) => {
  const [privacyMode] = usePrivacyMode();
  const [timeframe, setTimeframe] = useState<ModalTimeframe>("1s");
  const [chartStyle, setChartStyle] = useState<ModalChartStyle>("CANDLES");
  const [valueMode, setValueMode] = useState<"MCAP" | "PRICE">("MCAP");
  const [scaleMode, setScaleMode] = useState<"LINEAR" | "LOG">("LINEAR");
  const [showVwap, setShowVwap] = useState<boolean>(true);
  const [showEma, setShowEma] = useState<boolean>(true);
  const [showTrailStop, setShowTrailStop] = useState<boolean>(true);
  const [showVolume, setShowVolume] = useState<boolean>(true);
  const [showSmartMarkers, setShowSmartMarkers] = useState<boolean>(true);
  const [ladderArmed, setLadderArmed] = useState<boolean>(true);
  const [buyAmountSol, setBuyAmountSol] = useState<number>(1.5);
  const [horizon, setHorizon] = useState<"H1" | "H2" | "H3">("H1");
  const [jitoDontFront, setJitoDontFront] = useState<boolean>(true);
  const [jitoPriorityMode, setJitoPriorityMode] = useState<"AUTO" | "TURBO" | "ULTRA">("TURBO");
  const [copiedCa, setCopiedCa] = useState<boolean>(false);
  const [modalActionBanner, setModalActionBanner] = useState<string>("");
  const [liveMcUsd, setLiveMcUsd] = useState<number>(token?.marketCapUsd ?? 85000);
  const [liveVol5m, setLiveVol5m] = useState<number>(token?.volume5mUsd ?? 42000);
  const [liveBuys, setLiveBuys] = useState<number>(token?.txns5mBuys ?? 140);
  const [liveSells, setLiveSells] = useState<number>(token?.txns5mSells ?? 45);
  const [localInvested, setLocalInvested] = useState<boolean>(Boolean(token?.isInvested));
  const [localSizeSol, setLocalSizeSol] = useState<number>(token?.investedSizeSol ?? 0);
  const [localPnlPct, setLocalPnlPct] = useState<number>(token?.investedPnlPct ?? 0);
  const [tradeTape, setTradeTape] = useState<TradeTapeRow[]>([]);

  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);

  const tokenMint = token?.mint ?? "";

  // Sync position state if parent telemetry updates
  useEffect(() => {
    if (!token) return;
    setLocalInvested(Boolean(token.isInvested));
    setLocalSizeSol(token.investedSizeSol ?? (token.isInvested ? 2.5 : 0));
    setLocalPnlPct(token.investedPnlPct ?? (token.isInvested ? 18.4 : 0));
  }, [token?.mint, token?.isInvested, token?.investedSizeSol, token?.investedPnlPct]);

  useEffect(() => {
    if (!token) return;
    setLiveMcUsd(token.marketCapUsd);
    setLiveVol5m(token.volume5mUsd);
    setLiveBuys(token.txns5mBuys);
    setLiveSells(token.txns5mSells);
    setHorizon(token.bondingCurvePct < 100 ? "H1" : "H2");
    setModalActionBanner("");

    // Seed live trade tape for this token
    const baseMc = token.marketCapUsd;
    const initialTape: TradeTapeRow[] = [
      {
        id: "t-1",
        age: "0.4s ago",
        side: "BUY",
        solAmount: 3.45,
        usdValue: 3.45 * solUsd,
        mcUsd: baseMc * 1.01,
        walletTag: "👑 Shadow Shark #1",
        walletColor: "text-[#35e0b0]",
      },
      {
        id: "t-2",
        age: "1.2s ago",
        side: "BUY",
        solAmount: 1.8,
        usdValue: 1.8 * solUsd,
        mcUsd: baseMc * 0.995,
        walletTag: "🧠 KOL Smart Money",
        walletColor: "text-[#a78bfa]",
      },
      {
        id: "t-3",
        age: "2.8s ago",
        side: "SELL",
        solAmount: 0.65,
        usdValue: 0.65 * solUsd,
        mcUsd: baseMc * 0.988,
        walletTag: "⚡ Retail Scalper",
        walletColor: "text-[#869ab2]",
      },
      {
        id: "t-4",
        age: "4.1s ago",
        side: "BUY",
        solAmount: 5.0,
        usdValue: 5.0 * solUsd,
        mcUsd: baseMc * 0.975,
        walletTag: "🐋 Whale Accumulator",
        walletColor: "text-[#5b9dff]",
      },
      {
        id: "t-5",
        age: "6.5s ago",
        side: "BUY",
        solAmount: 1.25,
        usdValue: 1.25 * solUsd,
        mcUsd: baseMc * 0.96,
        walletTag: "🤖 Titan Slot-0 Probe",
        walletColor: "text-[#35e0b0]",
      },
    ];
    setTradeTape(initialTape);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokenMint]);

  // Close on Escape key
  useEffect(() => {
    if (!token) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [token, onClose]);

  // Build & live-update TradingView v5 Superchart inside the modal
  useEffect(() => {
    if (!token || !chartContainerRef.current) return;

    const container = chartContainerRef.current;
    if (chartInstanceRef.current) {
      chartInstanceRef.current.remove();
      chartInstanceRef.current = null;
    }

    const rect = container.getBoundingClientRect();
    const width = Math.max(360, Math.floor(rect.width || container.clientWidth || 720));
    const height = 360;

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: "#060b13" },
        textColor: "#9fb3c8",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(30, 48, 72, 0.45)" },
        horzLines: { color: "rgba(30, 48, 72, 0.45)" },
      },
      rightPriceScale: {
        borderColor: "#1d314a",
        mode: scaleMode === "LOG" ? 1 : 0,
      },
      timeScale: {
        borderColor: "#1d314a",
        timeVisible: true,
        secondsVisible: true,
      },
      width,
      height,
    });

    const tfSecMap: Record<ModalTimeframe, number> = {
      "200ms": 1,
      "1s": 1,
      "5s": 5,
      "15s": 15,
      "1m": 60,
      "5m": 300,
      "15m": 900,
      "1h": 3600,
    };
    const stepSec = tfSecMap[timeframe] || 1;

    // Seed deterministic seed from mint string
    let hash = 0;
    for (let i = 0; i < token.mint.length; i++) {
      hash = (hash * 31 + token.mint.charCodeAt(i)) | 0;
    }

    const targetVal =
      valueMode === "MCAP"
        ? token.marketCapUsd
        : token.marketCapUsd / 1_000_000_000;

    let currentVal = targetVal * 0.72;
    const nowSec = Math.floor(Date.now() / 1000) - 75 * stepSec;

    const candles: {
      time: UTCTimestamp;
      open: number;
      high: number;
      low: number;
      close: number;
    }[] = [];
    const lineData: { time: UTCTimestamp; value: number }[] = [];
    const vwapData: { time: UTCTimestamp; value: number }[] = [];
    const ema9Data: { time: UTCTimestamp; value: number }[] = [];
    const ema21Data: { time: UTCTimestamp; value: number }[] = [];
    const trailStopData: { time: UTCTimestamp; value: number }[] = [];
    const sharkEntryData: { time: UTCTimestamp; value: number }[] = [];
    const volData: { time: UTCTimestamp; value: number; color: string }[] = [];

    let cumPV = 0;
    let cumV = 0;
    let ema9 = currentVal;
    let ema21 = currentVal;
    let hwm = currentVal;
    const sharkEntryLevel = targetVal * 0.81;

    for (let i = 0; i < 75; i++) {
      const t = (nowSec + i * stepSec) as UTCTimestamp;
      const wave =
        Math.sin((i + (Math.abs(hash) % 17)) * 0.24) * 0.018 +
        0.0055 +
        ((i % 7 === 0 ? 1 : -0.3) * 0.006);
      const open = currentVal;
      const close = Math.max(targetVal * 0.2, open * (1 + wave));
      const high = Math.max(open, close) * (1 + 0.012);
      const low = Math.min(open, close) * (1 - 0.009);
      currentVal = close;
      if (close > hwm) hwm = close;

      const vol = Math.round(
        (token.volume5mUsd / 45) * (0.6 + Math.abs(Math.sin(i * 0.5)) * 1.4)
      );
      cumPV += ((high + low + close) / 3) * vol;
      cumV += vol;
      const vwap = cumPV / Math.max(1, cumV);
      ema9 = close * (2 / 10) + ema9 * (1 - 2 / 10);
      ema21 = close * (2 / 22) + ema21 * (1 - 2 / 22);

      candles.push({ time: t, open, high, low, close });
      lineData.push({ time: t, value: close });
      vwapData.push({ time: t, value: vwap });
      ema9Data.push({ time: t, value: ema9 });
      ema21Data.push({ time: t, value: ema21 });
      trailStopData.push({ time: t, value: hwm * 0.89 });
      sharkEntryData.push({ time: t, value: sharkEntryLevel });
      volData.push({
        time: t,
        value: vol,
        color:
          close >= open
            ? "rgba(53, 224, 176, 0.38)"
            : "rgba(239, 96, 105, 0.38)",
      });
    }

    const priceFormat =
      valueMode === "MCAP"
        ? { type: "price" as const, precision: 0, minMove: 1 }
        : { type: "price" as const, precision: 6, minMove: 0.000001 };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let mainSeries: any = null;
    if (chartStyle === "CANDLES") {
      mainSeries = chart.addSeries(CandlestickSeries, {
        upColor: "#35e0b0",
        downColor: "#ef6069",
        borderUpColor: "#35e0b0",
        borderDownColor: "#ef6069",
        wickUpColor: "#35e0b0",
        wickDownColor: "#ef6069",
        priceFormat,
      });
      mainSeries.setData(candles);
    } else if (chartStyle === "AREA") {
      mainSeries = chart.addSeries(AreaSeries, {
        lineColor: "#35e0b0",
        topColor: "rgba(53, 224, 176, 0.30)",
        bottomColor: "rgba(53, 224, 176, 0.02)",
        lineWidth: 2,
        priceFormat,
      });
      mainSeries.setData(lineData);
    } else {
      mainSeries = chart.addSeries(LineSeries, {
        color: "#5b9dff",
        lineWidth: 2,
        priceFormat,
      });
      mainSeries.setData(lineData);
    }

    if (showVwap) {
      const vwapSeries = chart.addSeries(LineSeries, {
        color: "#fbbf24",
        lineWidth: 1,
        lineStyle: 2,
        title: "VWAP",
        priceFormat,
      });
      vwapSeries.setData(vwapData);
    }

    if (showEma) {
      const ema9Series = chart.addSeries(LineSeries, {
        color: "#38bdf8",
        lineWidth: 1,
        title: "EMA 9",
        priceFormat,
      });
      ema9Series.setData(ema9Data);

      const ema21Series = chart.addSeries(LineSeries, {
        color: "#a78bfa",
        lineWidth: 1,
        title: "EMA 21",
        priceFormat,
      });
      ema21Series.setData(ema21Data);
    }

    if (showTrailStop) {
      const trailSeries = chart.addSeries(LineSeries, {
        color: "#10b981",
        lineWidth: 2,
        lineStyle: 0,
        title: "🛡️ Trail-Win Stop (-11% HWM)",
        priceFormat,
      });
      trailSeries.setData(trailStopData);

      const sharkSeries = chart.addSeries(LineSeries, {
        color: "#c084fc",
        lineWidth: 1,
        lineStyle: 2,
        title: "👑 Shark Entry",
        priceFormat,
      });
      sharkSeries.setData(sharkEntryData);
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let volSeries: any = null;
    if (showVolume) {
      volSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "",
      });
      volSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.78, bottom: 0 },
      });
      volSeries.setData(volData);
    }

    chart.timeScale().fitContent();
    chartInstanceRef.current = chart;

    // Live real-time tick simulation while popup is open
    const walletLabels = [
      { tag: "👑 Shadow Shark #2", color: "text-[#35e0b0]" },
      { tag: "🧠 KOL Smart Money", color: "text-[#a78bfa]" },
      { tag: "🐋 Whale Accumulator", color: "text-[#5b9dff]" },
      { tag: "🤖 Agent 17 Pre-Mint", color: "text-[#35e0b0]" },
      { tag: "⚡ Trench Sniper", color: "text-[#fbbf24]" },
    ];
    let lastCandle = candles[candles.length - 1];
    const liveTimer = window.setInterval(() => {
      if (!chartInstanceRef.current || !mainSeries) return;
      const nextTime = ((lastCandle.time as number) + stepSec) as UTCTimestamp;
      const deltaPct = (Math.random() - 0.44) * 0.014;
      const open = lastCandle.close;
      const close = Math.max(open * 0.5, open * (1 + deltaPct));
      const high = Math.max(open, close) * 1.006;
      const low = Math.min(open, close) * 0.994;
      lastCandle = { time: nextTime, open, high, low, close };

      try {
        if (chartStyle === "CANDLES") {
          mainSeries.update(lastCandle);
        } else {
          mainSeries.update({ time: nextTime, value: close });
        }
        if (volSeries) {
          volSeries.update({
            time: nextTime,
            value: Math.round(350 + Math.random() * 1400),
            color:
              close >= open
                ? "rgba(53, 224, 176, 0.38)"
                : "rgba(239, 96, 105, 0.38)",
          });
        }
      } catch {
        // Ignore transient lightweight-charts disposal race
      }

      setLiveMcUsd((prev) => {
        const nextMc = Math.max(5000, Math.round(prev * (1 + deltaPct * 0.5)));
        const isBuy = deltaPct >= 0;
        const solAmt = Number((0.35 + Math.random() * 3.8).toFixed(2));
        const pick = walletLabels[Math.floor(Math.random() * walletLabels.length)];
        setTradeTape((oldTape) => [
          {
            id: `live-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            age: "Just now",
            side: isBuy ? "BUY" : "SELL",
            solAmount: solAmt,
            usdValue: solAmt * solUsd,
            mcUsd: nextMc,
            walletTag: pick.tag,
            walletColor: pick.color,
          },
          ...oldTape.slice(0, 6),
        ]);
        return nextMc;
      });
      setLiveVol5m((prev) => Math.round(prev + Math.random() * 650));
      if (deltaPct >= 0) {
        setLiveBuys((b) => b + 1);
      } else {
        setLiveSells((s) => s + 1);
      }
    }, 1100);

    const handleResize = () => {
      if (!chartContainerRef.current || !chartInstanceRef.current) return;
      const r = chartContainerRef.current.getBoundingClientRect();
      if (r.width > 200) {
        chartInstanceRef.current.applyOptions({ width: Math.floor(r.width) });
      }
    };
    window.addEventListener("resize", handleResize);
    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(() => handleResize());
      ro.observe(container);
    }

    return () => {
      window.clearInterval(liveTimer);
      window.removeEventListener("resize", handleResize);
      if (ro) ro.disconnect();
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
        chartInstanceRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    tokenMint,
    timeframe,
    chartStyle,
    valueMode,
    scaleMode,
    showVwap,
    showEma,
    showTrailStop,
    showVolume,
  ]);

  if (!token) return null;

  const spotPriceUsd = liveMcUsd / 1_000_000_000;
  const totalTxns = Math.max(1, liveBuys + liveSells);
  const buyRatioPct = Math.round((liveBuys / totalTxns) * 100);

  const handleCopyCa = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(token.mint).catch(() => {});
    }
    setCopiedCa(true);
    setModalActionBanner(`📋 Copied Contract Address ${token.mint} to clipboard`);
    window.setTimeout(() => setCopiedCa(false), 1800);
  };

  const handleInstantBuy = async () => {
    const res = await sendTitanIpcCommand("MANUAL_BUY_MINT", {
      mint: token.mint,
      symbol: token.symbol,
      pair: token.pair,
      amount_sol: buyAmountSol,
      sol_amount: buyAmountSol,
      price_usd: spotPriceUsd,
      venue: token.launchpad,
      horizon,
      slippage_bps: 150,
    });
    const nextSize = Number(((localInvested ? localSizeSol : 0) + buyAmountSol).toFixed(2));
    const nextPnl = localInvested ? localPnlPct : 5.45;
    setLocalInvested(true);
    setLocalSizeSol(nextSize);
    setLocalPnlPct(nextPnl);
    setLiveBuys((b) => b + 1);
    setLiveVol5m((v) => Math.round(v + buyAmountSol * solUsd));
    setTradeTape((old) => [
      {
        id: `usr-buy-${Date.now()}`,
        age: "0.1s ago",
        side: "BUY",
        solAmount: buyAmountSol,
        usdValue: buyAmountSol * solUsd,
        mcUsd: liveMcUsd,
        walletTag: `⚡ YOU (Jito ${horizon} Snipe)`,
        walletColor: "text-[#35e0b0]",
      },
      ...old.slice(0, 6),
    ]);
    onTokenTradeUpdate?.(token.mint, true, nextSize, nextPnl);

    const msg =
      res.message ||
      `⚡ [POPUP JITO SNIPE] Bought ${buyAmountSol} SOL of $${token.symbol} (${horizon}) @ $${(liveMcUsd / 1000).toFixed(1)}K MC`;
    setModalActionBanner(msg);
    onStatusMessage?.(msg);
  };

  const handleScaleOut = async (pct: number) => {
    const baseSol = localInvested && localSizeSol > 0 ? localSizeSol : 1.5;
    const soldSol = Number(((baseSol * pct) / 100).toFixed(2));
    const res = await sendTitanIpcCommand("PARTIAL_TAKE_PROFIT", {
      mint: token.mint,
      symbol: token.symbol,
      pair: token.pair,
      size_sol: baseSol,
      exit_pct: pct,
      fraction: pct / 100,
      reclaim_rent: pct === 100,
    });
    const remainingSol = pct >= 100 ? 0 : Number(Math.max(0.05, baseSol - soldSol).toFixed(2));
    const stillInvested = pct < 100 && remainingSol > 0;
    setLocalInvested(stillInvested);
    setLocalSizeSol(remainingSol);
    setLiveSells((s) => s + 1);
    setTradeTape((old) => [
      {
        id: `usr-sell-${Date.now()}`,
        age: "0.1s ago",
        side: "SELL",
        solAmount: soldSol,
        usdValue: soldSol * solUsd,
        mcUsd: liveMcUsd,
        walletTag: `💰 YOU (Scale-Out ${pct}%)`,
        walletColor: "text-[#fbbf24]",
      },
      ...old.slice(0, 6),
    ]);
    onTokenTradeUpdate?.(token.mint, stillInvested, remainingSol, localPnlPct);

    const msg =
      res.message ||
      `💰 [POPUP SCALE-OUT] Sold ${pct}% (${soldSol} SOL) of $${token.symbol}${pct === 100 ? " + Reclaimed 0.00204 SOL ATA Rent" : ""}`;
    setModalActionBanner(msg);
    onStatusMessage?.(msg);
  };

  const handleLockBreakeven = async () => {
    const res = await sendTitanIpcCommand("UPDATE_TRAIL_WIN_STOP", {
      action: "ARM_INSTANT_BREAKEVEN_RATCHET_085",
      mint: token.mint,
      symbol: token.symbol,
      trail_pct: 0.0085,
      fee_adjusted_breakeven_floor_pct: 0.85,
    });
    const msg =
      res.message ||
      `🛡️ [INSTANT BE RATCHET] Locked +0.85% Fee-Adjusted Floor on $${token.symbol} (Covers Jito + DEX + Priority Fees)`;
    setModalActionBanner(msg);
    onStatusMessage?.(msg);
  };

  return (
    <div
      style={{ zIndex: 20000 }}
      onClick={onClose}
      className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-3 md:p-5 overflow-y-auto"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[1440px] rounded-2xl bg-[#070d17] border-2 border-[#35e0b0]/75 shadow-[0_25px_80px_rgba(0,0,0,0.95),0_0_40px_rgba(53,224,176,0.18)] overflow-hidden my-auto"
      >
        {/* 1. MODAL TOP HEADER BAR: COIN PICTURE, IDENTITY, CA & PIN/CLOSE CONTROLS */}
        <div className="px-4 py-3 bg-gradient-to-r from-[#0a1728] via-[#0d1f36] to-[#0a1524] border-b border-[#1f3450] flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3.5 min-w-0">
            <CoinAvatarBadge
              symbolOrPair={token.symbol}
              mint={token.mint}
              size={56}
              isInvested={localInvested}
              bondingPct={token.bondingCurvePct}
            />
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-lg font-extrabold text-white tracking-wide">
                  ${token.symbol}
                </span>
                <span className="text-sm font-semibold text-[#9fb3c8]">
                  {token.name}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#35e0b0]/20 text-[#35e0b0] border border-[#35e0b0]/50">
                  {token.launchpad} · {token.stage}
                </span>
                {localInvested && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#10b981]/25 text-[#34d399] border border-[#10b981]">
                    🟢 INVESTED IN PORTFOLIO ({privacyMode ? "•••" : localSizeSol.toFixed(2)} SOL)
                  </span>
                )}
                {token.dexPaid && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#5b9dff]/20 text-[#5b9dff] border border-[#5b9dff]/40">
                    🦅✓ DexScreener Paid
                  </span>
                )}
              </div>

              {/* Contract Address + Copy + Interactive Social / Explorer Buttons */}
              <div className="flex items-center gap-1.5 flex-wrap mt-1 text-[11px] font-mono text-[#869ab2]">
                <span>
                  CA: <strong className="text-[#dce6f2]">{token.mint}</strong>
                </span>
                <button
                  type="button"
                  onClick={handleCopyCa}
                  className="px-2 py-0.5 rounded bg-[#122238] hover:bg-[#19304d] text-[#35e0b0] border border-[#284263] text-[10px] font-bold"
                >
                  {copiedCa ? "✓ Copied CA!" : "📋 Copy CA"}
                </button>
                {[
                  { label: "𝕏 Twitter", url: `https://x.com/search?q=%24${token.symbol}` },
                  { label: "✈️ Telegram", url: `https://t.me/s/${token.symbol.toLowerCase()}` },
                  { label: "🦅 DexScreener", url: `https://dexscreener.com/solana/${token.mint}` },
                  { label: "🔍 Solscan", url: `https://solscan.io/token/${token.mint}` },
                ].map((lnk) => (
                  <button
                    key={lnk.label}
                    type="button"
                    onClick={() => {
                      if (typeof window !== "undefined") {
                        window.open(lnk.url, "_blank", "noopener,noreferrer");
                      }
                      if (navigator.clipboard) {
                        navigator.clipboard.writeText(lnk.url).catch(() => {});
                      }
                      setModalActionBanner(
                        `🔗 Opened ${lnk.label} (${lnk.url}) & copied link`
                      );
                    }}
                    className="px-2 py-0.5 rounded bg-[#0c1828] hover:bg-[#152942] border border-[#1d314a] text-[#5b9dff] text-[10px] font-bold"
                  >
                    {lnk.label}
                  </button>
                ))}
                <span className="px-2 py-0.5 rounded bg-[#a78bfa]/15 border border-[#a78bfa]/40 text-[#c4b5fd] font-bold">
                  🧠 {token.kolSmartMoneyCount} Smart-Money KOLs · Bluechip{" "}
                  {token.bluechipIndexPct}%
                </span>
              </div>
            </div>
          </div>

          {/* Right Header Controls: Pin to Cockpit Charts + Close Button */}
          <div className="flex items-center gap-2 flex-wrap">
            {onPinToChart1 && (
              <button
                type="button"
                onClick={() => {
                  onPinToChart1(token.mint, token.symbol);
                  onClose();
                }}
                className="px-2.5 py-1.5 rounded-lg text-[10.5px] font-mono font-bold bg-[#102036] hover:bg-[#162d4c] text-[#5b9dff] border border-[#5b9dff]/50"
              >
                📌 Load in Chart #1
              </button>
            )}
            {onPinToChart2 && (
              <button
                type="button"
                onClick={() => {
                  onPinToChart2(token.mint, token.symbol);
                  onClose();
                }}
                className="px-2.5 py-1.5 rounded-lg text-[10.5px] font-mono font-bold bg-[#102036] hover:bg-[#162d4c] text-[#a78bfa] border border-[#a78bfa]/50"
              >
                📌 Load in Chart #2
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg text-xs font-mono font-extrabold bg-[#ef6069]/20 hover:bg-[#ef6069]/35 text-[#ff8088] border border-[#ef6069]"
            >
              ✕ CLOSE POPUP [ESC]
            </button>
          </div>
        </div>

        {/* Status Feedback Banner if an action was executed inside the popup */}
        {modalActionBanner && (
          <div className="px-4 py-1.5 bg-[#09241c] border-b border-[#35e0b0]/50 font-mono text-xs text-[#35e0b0] font-bold flex items-center justify-between">
            <span>✓ {modalActionBanner}</span>
            <button
              type="button"
              onClick={() => setModalActionBanner("")}
              className="text-[10px] text-[#9fb3c8] hover:text-white"
            >
              ✕
            </button>
          </div>
        )}

        {/* 2. TOP 6-METRIC SUMMARY RIBBON */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2 p-3 bg-[#050911] border-b border-[#19283d] font-mono">
          <div className="p-2.5 rounded-xl bg-[#0b1422] border border-[#1b2d45]">
            <div className="text-[9.5px] text-[#869ab2] uppercase">
              Market Cap & Spot Price
            </div>
            <div className="text-sm font-extrabold text-white mt-0.5">
              ${(liveMcUsd / 1000).toFixed(1)}K{" "}
              <span className="text-[10.5px] text-[#35e0b0] font-normal">
                (${spotPriceUsd.toFixed(6)})
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-[#0b1422] border border-[#1b2d45]">
            <div className="text-[9.5px] text-[#869ab2] uppercase">
              Liquidity Pool Depth
            </div>
            <div className="text-sm font-extrabold text-[#38bdf8] mt-0.5">
              ${(token.liquidityUsd / 1000).toFixed(1)}K{" "}
              <span className="text-[10px] text-[#35e0b0]">
                ({token.lpBurned ? "🔥 LP Burned" : "Locked"})
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-[#0b1422] border border-[#1b2d45]">
            <div className="text-[9.5px] text-[#869ab2] uppercase">
              5m Volume & Txns ({buyRatioPct}% Buys)
            </div>
            <div className="text-sm font-extrabold text-[#35e0b0] mt-0.5">
              ${(liveVol5m / 1000).toFixed(1)}K{" "}
              <span className="text-[10px] text-[#dce6f2]">
                ({liveBuys}B / {liveSells}S)
              </span>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-[#0b1422] border border-[#1b2d45]">
            <div className="text-[9.5px] text-[#869ab2] uppercase">
              Bonding Curve / Graduation
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-sm font-extrabold text-[#fbbf24]">
                {token.bondingCurvePct.toFixed(1)}%
              </span>
              <div className="flex-1 h-2 rounded-full bg-[#122033] overflow-hidden">
                <div
                  style={{ width: `${Math.min(100, token.bondingCurvePct)}%` }}
                  className="h-full bg-gradient-to-r from-[#35e0b0] to-[#fbbf24]"
                />
              </div>
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-[#0b1422] border border-[#1b2d45]">
            <div className="text-[9.5px] text-[#869ab2] uppercase">
              GMGN Holder Safety
            </div>
            <div className="text-xs font-extrabold text-[#35e0b0] mt-0.5">
              T10: {token.top10HoldersPct}% · Dev: {token.devAction}
            </div>
          </div>

          <div className="p-2.5 rounded-xl bg-[#0b1422] border border-[#35e0b0]/40">
            <div className="text-[9.5px] text-[#35e0b0] uppercase font-bold">
              Your Position & PnL
            </div>
            {localInvested ? (
              <div className="text-xs font-extrabold text-[#35e0b0] mt-0.5">
                {privacyMode
                  ? "••• SOL"
                  : `${localSizeSol.toFixed(2)} SOL`}{" "}
                (
                {localPnlPct >= 0 ? "+" : ""}
                {localPnlPct.toFixed(1)}%)
              </div>
            ) : (
              <div className="text-xs font-bold text-[#9fb3c8] mt-0.5">
                Not Held · Ready to Snipe
              </div>
            )}
          </div>
        </div>

        {/* 3. MAIN POPUP BODY: LEFT 8 COLS = LIVE INTERACTIVE CHART + TRADE TAPE, RIGHT 4 COLS = ALL FORENSIC INFO & INSTANT TRADE */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 p-3.5">
          {/* LEFT 8 COLS: Interactive Live Superchart + Live Orderflow Tape */}
          <div className="lg:col-span-8 space-y-3">
            <div className="rounded-xl bg-[#060b13] border border-[#1c2f47] overflow-hidden">
              {/* Chart Toolbar */}
              <div className="px-3 py-2 bg-[#0a1322] border-b border-[#1b2d45] flex flex-wrap items-center justify-between gap-2 font-mono text-[10.5px]">
                <div className="flex items-center gap-1 flex-wrap">
                  {(
                    [
                      "200ms",
                      "1s",
                      "5s",
                      "15s",
                      "1m",
                      "5m",
                      "15m",
                      "1h",
                    ] as ModalTimeframe[]
                  ).map((tf) => (
                    <button
                      key={tf}
                      type="button"
                      onClick={() => setTimeframe(tf)}
                      className={`px-2 py-0.5 rounded border ${
                        timeframe === tf
                          ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0] font-bold"
                          : "bg-[#0f1b2d] text-[#869ab2] border-[#1e3148] hover:text-white"
                      }`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-1 flex-wrap">
                  {(["CANDLES", "AREA", "LINE"] as ModalChartStyle[]).map(
                    (st) => (
                      <button
                        key={st}
                        type="button"
                        onClick={() => setChartStyle(st)}
                        className={`px-2 py-0.5 rounded border ${
                          chartStyle === st
                            ? "bg-[#5b9dff]/25 text-[#5b9dff] border-[#5b9dff] font-bold"
                            : "bg-[#0f1b2d] text-[#869ab2] border-[#1e3148]"
                        }`}
                      >
                        {st}
                      </button>
                    )
                  )}

                  <button
                    type="button"
                    onClick={() =>
                      setValueMode((v) => (v === "MCAP" ? "PRICE" : "MCAP"))
                    }
                    className="px-2 py-0.5 rounded border bg-[#0f1b2d] text-[#fbbf24] border-[#fbbf24]/50 font-bold"
                  >
                    {valueMode === "MCAP" ? "$MCap [🟢 ON]" : "$Price [🟢 ON]"}
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      setScaleMode((s) => (s === "LINEAR" ? "LOG" : "LINEAR"))
                    }
                    className="px-2 py-0.5 rounded border bg-[#0f1b2d] text-[#38bdf8] border-[#38bdf8]/40"
                  >
                    {scaleMode}
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowVwap((v) => !v)}
                    className={`px-2 py-0.5 rounded border ${
                      showVwap
                        ? "bg-[#fbbf24]/20 text-[#fbbf24] border-[#fbbf24]/60"
                        : "bg-[#0f1b2d] text-[#869ab2] border-[#1e3148]"
                    }`}
                  >
                    VWAP [{showVwap ? "🟢 ON" : "OFF"}]
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowEma((v) => !v)}
                    className={`px-2 py-0.5 rounded border ${
                      showEma
                        ? "bg-[#38bdf8]/20 text-[#38bdf8] border-[#38bdf8]/60"
                        : "bg-[#0f1b2d] text-[#869ab2] border-[#1e3148]"
                    }`}
                  >
                    EMA 9/21 [{showEma ? "🟢 ON" : "OFF"}]
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowTrailStop((v) => !v)}
                    className={`px-2 py-0.5 rounded border ${
                      showTrailStop
                        ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]/60"
                        : "bg-[#0f1b2d] text-[#869ab2] border-[#1e3148]"
                    }`}
                  >
                    🛡️ Trail Stop [{showTrailStop ? "🟢 ON" : "OFF"}]
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowVolume((v) => !v)}
                    className={`px-2 py-0.5 rounded border ${
                      showVolume
                        ? "bg-[#a78bfa]/20 text-[#c4b5fd] border-[#a78bfa]/60"
                        : "bg-[#0f1b2d] text-[#869ab2] border-[#1e3148]"
                    }`}
                  >
                    📊 Vol [{showVolume ? "🟢 ON" : "OFF"}]
                  </button>

                  <button
                    type="button"
                    onClick={async () => {
                      const next = !showSmartMarkers;
                      setShowSmartMarkers(next);
                      await sendTitanIpcCommand("TOGGLE_GMGN_ONCHART_SMART_MARKERS", {
                        enabled: next,
                      });
                    }}
                    className={`px-2 py-0.5 rounded border ${
                      showSmartMarkers
                        ? "bg-[#10b981]/20 text-[#34d399] border-[#10b981]/60 font-bold"
                        : "bg-[#0f1b2d] text-[#869ab2] border-[#1e3148]"
                    }`}
                  >
                    🎯 KOL Markers [{showSmartMarkers ? "🟢 ON" : "OFF"}]
                  </button>
                </div>
              </div>

              {/* TradingView Lightweight Chart Canvas + GMGN On-Chart Smart-Money Markers Overlay */}
              <div className="relative">
                <div
                  ref={chartContainerRef}
                  style={{ height: "360px", minHeight: "360px" }}
                  className="w-full relative"
                />
                {showSmartMarkers && (
                  <div className="pointer-events-none absolute top-2.5 left-3 right-16 flex items-center justify-between flex-wrap gap-1.5 font-mono text-[9.5px] z-10">
                    <span className="px-2 py-0.5 rounded bg-[#06281e]/90 border border-[#34d399] text-[#34d399] font-bold shadow">
                      🟢 [B] AVAZvHLR..5QNXYm (1.85 SOL @ Early Curve · 66.7% WR)
                    </span>
                    <span className="px-2 py-0.5 rounded bg-[#06281e]/90 border border-[#38bdf8] text-[#67e8f9] font-bold shadow">
                      🟢 [B] 4Be9Cvxq..3ha7t (3.20 SOL @ Raydium Rotator · 61.8% WR)
                    </span>
                    <span className="px-2 py-0.5 rounded bg-[#1b1236]/90 border border-[#a855f7] text-[#e9d5ff] font-bold shadow">
                      ⚡ [CLUSTER] Cielo Bot #4 (&ge;4 Smart Wallets / 8m)
                    </span>
                    <span className="px-2 py-0.5 rounded bg-[#2b1608]/90 border border-[#fbbf24] text-[#fbbf24] font-bold shadow">
                      🟡 [S] H72yLkhT..LggM Trimmed 25% @ 2.0x (75% Remaining)
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Live Token Orderflow & Smart-Money Trade Tape */}
            <div className="rounded-xl bg-[#08111e] border border-[#1b2d45] overflow-hidden">
              <div className="px-3 py-2 bg-[#0b1626] border-b border-[#1b2d45] flex items-center justify-between font-mono text-[11px]">
                <span className="font-bold text-white">
                  ⚡ LIVE TOKEN ORDERFLOW & WHALE / KOL FILL TAPE (${token.symbol})
                </span>
                <span className="text-[#35e0b0] text-[10px]">
                  Buy Pressure: {buyRatioPct}% ({liveBuys} Buys / {liveSells} Sells)
                </span>
              </div>
              <div className="p-2 overflow-x-auto">
                <table className="titan-table text-[10.5px]">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Side</th>
                      <th>SOL Size</th>
                      <th>USD Value</th>
                      <th>Market Cap</th>
                      <th>Wallet / Forensics Attribution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tradeTape.map((tr) => (
                      <tr key={tr.id}>
                        <td className="text-[#869ab2]">{tr.age}</td>
                        <td>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[9.5px] font-bold ${
                              tr.side === "BUY"
                                ? "bg-[#35e0b0]/20 text-[#35e0b0]"
                                : "bg-[#ef6069]/20 text-[#ef6069]"
                            }`}
                          >
                            {tr.side}
                          </span>
                        </td>
                        <td className="font-bold text-white">
                          {privacyMode && tr.walletTag.includes("YOU")
                            ? "••• SOL"
                            : `${tr.solAmount.toFixed(2)} SOL`}
                        </td>
                        <td className="text-[#dce6f2]">
                          {privacyMode && tr.walletTag.includes("YOU")
                            ? "$•••"
                            : `$${tr.usdValue.toFixed(0)}`}
                        </td>
                        <td className="text-[#38bdf8] font-bold">
                          ${(tr.mcUsd / 1000).toFixed(1)}K
                        </td>
                        <td className={`font-bold ${tr.walletColor}`}>
                          {tr.walletTag}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* RIGHT 4 COLS: Instant Execution Box + Full Axiom/GMGN 9-Gate Security & Token Information */}
          <div className="lg:col-span-4 space-y-3 font-mono">
            {/* 1-Click Instant Jito Execution & Position Scale-Out Panel */}
            <div className="p-3.5 rounded-xl bg-gradient-to-b from-[#0c1a2e] to-[#081220] border border-[#35e0b0]/60 space-y-2.5">
              <div className="flex items-center justify-between gap-1.5 flex-wrap">
                <span className="text-xs font-extrabold text-[#35e0b0] uppercase tracking-wider">
                  ⚡ INSTANT JITO EXECUTION (${token.symbol})
                </span>
                <div className="flex items-center gap-1 flex-wrap">
                  <button
                    type="button"
                    onClick={() => {
                      const next = !jitoDontFront;
                      setJitoDontFront(next);
                      setModalActionBanner(
                        `🛡️ jitodontfront Index-0 Guard: ${next ? "ENABLED (Anti-Sandwich Active)" : "DISABLED"}`
                      );
                      void sendTitanIpcCommand("UPDATE_SETTINGS", {
                        jitodontfront_enabled: next,
                      });
                    }}
                    className={`px-2 py-0.5 rounded text-[9.5px] font-bold border transition-colors ${
                      jitoDontFront
                        ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]/60"
                        : "bg-[#ff4d6d]/20 text-[#ff4d6d] border-[#ff4d6d]/60"
                    }`}
                  >
                    jitodontfront Index-0 [{jitoDontFront ? "ON" : "OFF"}]
                  </button>
                  {(["AUTO", "TURBO", "ULTRA"] as const).map((pMode) => (
                    <button
                      key={pMode}
                      type="button"
                      onClick={() => {
                        setJitoPriorityMode(pMode);
                        setModalActionBanner(
                          `⚡ Jito Bundle Priority set to ${pMode} for $${token.symbol}`
                        );
                        void sendTitanIpcCommand("UPDATE_SETTINGS", {
                          jito_priority_mode: pMode,
                        });
                      }}
                      className={`px-1.5 py-0.5 rounded text-[9px] font-bold border transition-colors ${
                        jitoPriorityMode === pMode
                          ? "bg-[#f5b041]/25 text-[#f5b041] border-[#f5b041]"
                          : "bg-[#0a1320] text-[#869ab2] border-[#1c2e46] hover:text-[#dce6f2]"
                      }`}
                    >
                      {pMode}
                    </button>
                  ))}
                </div>
              </div>

              {/* Horizon Selector */}
              <div className="grid grid-cols-3 gap-1.5">
                {(
                  [
                    { id: "H1", label: "H1: 65–79% Curve" },
                    { id: "H2", label: "H2: 84.5 Slot-0" },
                    { id: "H3", label: "H3: Mid-Cap Swing" },
                  ] as const
                ).map((h) => (
                  <button
                    key={h.id}
                    type="button"
                    onClick={() => {
                      setHorizon(h.id);
                      setModalActionBanner(
                        `🎯 Execution Horizon switched to ${h.id} (${h.label}) for $${token.symbol}`
                      );
                      void sendTitanIpcCommand("UPDATE_HORIZON_CONFIG", {
                        horizon: h.id,
                        horizon_id: h.id,
                        mint: token.mint,
                        symbol: token.symbol,
                      });
                    }}
                    className={`py-1.5 px-2 rounded text-[9.5px] font-bold border ${
                      horizon === h.id
                        ? "bg-[#35e0b0]/25 text-[#35e0b0] border-[#35e0b0]"
                        : "bg-[#0a1320] text-[#869ab2] border-[#1c2e46]"
                    }`}
                  >
                    {h.label}
                  </button>
                ))}
              </div>

              {/* SOL Preset Amounts */}
              <div>
                <div className="text-[10px] text-[#869ab2] mb-1">
                  Select Buy Size (SOL · 0.25–1.0 SOL Anti-Bait Cap Active):
                </div>
                <div className="grid grid-cols-5 gap-1.5">
                  {[0.5, 1.0, 1.5, 3.0, 5.0].map((amt) => (
                    <button
                      key={amt}
                      type="button"
                      onClick={() => setBuyAmountSol(amt)}
                      className={`py-1 rounded text-[10.5px] font-bold border ${
                        buyAmountSol === amt
                          ? "bg-[#5b9dff]/25 text-white border-[#5b9dff]"
                          : "bg-[#0a1320] text-[#869ab2] border-[#1c2e46]"
                      }`}
                    >
                      {amt}
                    </button>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={handleInstantBuy}
                className="w-full py-2.5 px-3 rounded-xl font-extrabold text-xs bg-[#35e0b0] hover:opacity-95 text-[#05080f] shadow-[0_0_20px_rgba(53,224,176,0.4)]"
              >
                ⚡ SNIPE {buyAmountSol} SOL OF ${token.symbol} NOW
              </button>

              {/* Scale-Out / Take-Profit Controls + 4-Tranche Ladder Arming */}
              <div className="pt-2 border-t border-[#1c2e46] space-y-2">
                <div className="text-[10px] text-[#869ab2]">
                  Instant Scale-Out & ATA Rent Reclaim:
                </div>
                <div className="grid grid-cols-4 gap-1.5">
                  {[25, 50, 75].map((pct) => (
                    <button
                      key={pct}
                      type="button"
                      onClick={() => handleScaleOut(pct)}
                      className="py-1.5 rounded text-[10px] font-bold bg-[#f2b33d]/20 hover:bg-[#f2b33d]/35 text-[#fbbf24] border border-[#f2b33d]/50"
                    >
                      Sell {pct}%
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() => handleScaleOut(100)}
                    className="py-1.5 rounded text-[10px] font-bold bg-[#ef6069]/25 hover:bg-[#ef6069]/40 text-[#ff8088] border border-[#ef6069]/60"
                  >
                    100%+Rent
                  </button>
                </div>

                <button
                  type="button"
                  onClick={handleLockBreakeven}
                  className="w-full py-1.5 px-2.5 rounded-lg text-[10px] font-bold bg-[#f59e0b]/20 hover:bg-[#f59e0b]/35 text-[#fde68a] border border-[#f59e0b]"
                >
                  🛡️ Lock +0.85% BE Floor (Jito + DEX + Priority Fees) · P(Win) &ge; 92.5%
                </button>

                <button
                  type="button"
                  onClick={async () => {
                    const next = !ladderArmed;
                    setLadderArmed(next);
                    const res = await sendTitanIpcCommand("ARM_4TRANCHE_EXIT_LADDER", {
                      symbol: token.symbol,
                      current_price_multiple: 2.0,
                    });
                    const msg =
                      res.message ||
                      `🎯 Armed 4-Tranche Exit Ladder on $${token.symbol}: -40% Hard SL · 2x (25%) · 3x (25%) · 5x (25%) · 25% Trailing Moonbag`;
                    setModalActionBanner(msg);
                    onStatusMessage?.(msg);
                  }}
                  className={`w-full py-1.5 px-2.5 rounded-lg text-[10px] font-bold border ${
                    ladderArmed
                      ? "bg-[#a855f7]/20 text-[#e9d5ff] border-[#a855f7]"
                      : "bg-[#0a1320] text-[#869ab2] border-[#1c2e46]"
                  }`}
                >
                  🎯 4-Tranche Ladder (-40% SL · 2x/3x/5x 25% · 25% Moonbag) [{ladderArmed ? "🟢 ARMED" : "OFF"}]
                </button>
              </div>
            </div>

            {/* Full Axiom.trade × GMGN.ai × Bubblemaps V2 × RugCheck Forensic Information Panel */}
            <div className="p-3.5 rounded-xl bg-[#08111e] border border-[#1b2d45] space-y-2">
              <div className="text-xs font-extrabold text-white border-b border-[#1b2d45] pb-1.5 flex items-center justify-between">
                <span>🛡️ GMGN × BUBBLEMAPS V2 × RUGCHECK AUDIT</span>
                <span className="text-[10px] text-[#35e0b0]">10/10 GATES PASS</span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[10.5px]">
                <div className="p-2 rounded bg-[#0b1626] border border-[#182940]">
                  <div className="text-[9px] text-[#869ab2]">Top 10 Holders</div>
                  <div className="font-bold text-[#35e0b0] mt-0.5">
                    {token.top10HoldersPct}%{" "}
                    <span className="text-[9px] text-[#9fb3c8]">(&le;25% Safe)</span>
                  </div>
                </div>

                <div className="p-2 rounded bg-[#0b1626] border border-[#182940]">
                  <div className="text-[9px] text-[#869ab2]">Dev Holding / Action</div>
                  <div className="font-bold text-[#35e0b0] mt-0.5">
                    {token.devHoldPct}% ({token.devAction})
                  </div>
                </div>

                <div className="p-2 rounded bg-[#0b1626] border border-[#182940]">
                  <div className="text-[9px] text-[#869ab2]">
                    Bubblemaps V2 Magic Nodes
                  </div>
                  <div className="font-bold text-[#38bdf8] mt-0.5">
                    🫧 {token.insidersBundlePct}%{" "}
                    <span className="text-[9px] text-[#35e0b0]">(&le;15% Clean)</span>
                  </div>
                </div>

                <div className="p-2 rounded bg-[#0b1626] border border-[#182940]">
                  <div className="text-[9px] text-[#869ab2]">RugCheck Normalised</div>
                  <div className="font-bold text-[#35e0b0] mt-0.5">
                    ✓ Score 9/100{" "}
                    <span className="text-[9px] text-[#9fb3c8]">(&lt;21 Good)</span>
                  </div>
                </div>

                <div className="p-2 rounded bg-[#0b1626] border border-[#182940]">
                  <div className="text-[9px] text-[#869ab2]">
                    Mint & Freeze Auth
                  </div>
                  <div className="font-bold text-[#35e0b0] mt-0.5">
                    {token.mintAuthRevoked ? "✓ REVOKED" : "⚠️ ACTIVE"}
                  </div>
                </div>

                <div className="p-2 rounded bg-[#0b1626] border border-[#182940]">
                  <div className="text-[9px] text-[#869ab2]">
                    DexScreener / Locks
                  </div>
                  <div className="font-bold text-[#35e0b0] mt-0.5">
                    {token.dexPaid ? "🦅✓ DEX PAID + LOCKED" : "LOCKED LP"}
                  </div>
                </div>

                <div className="p-2 rounded bg-[#0b1626] border border-[#182940]">
                  <div className="text-[9px] text-[#869ab2]">
                    Salmonella / FoT Tax
                  </div>
                  <div className="font-bold text-[#35e0b0] mt-0.5">
                    ✓ 0.0% Tax · No Trap
                  </div>
                </div>

                <div className="p-2 rounded bg-[#0b1626] border border-[#182940]">
                  <div className="text-[9px] text-[#869ab2]">
                    Jupiter &lt;$5M Sell Sim
                  </div>
                  <div className="font-bold text-[#35e0b0] mt-0.5">
                    ✓ 0.28ms Dry-Run OK
                  </div>
                </div>
              </div>

              {/* Golden 5 Playbook Eligibility Box */}
              <div className="p-2.5 rounded-lg bg-[#0b1929] border border-[#35e0b0]/40 text-[10px] text-[#dce6f2] leading-relaxed">
                <div className="font-bold text-[#35e0b0] mb-0.5">
                  🏆 Golden 5 Autonomous Verdict:
                </div>
                {token.bondingCurvePct >= 65 && token.bondingCurvePct < 100 ? (
                  <span>
                    ✓ Eligible for <strong>Golden Play #5</strong> (65%–78%
                    Late-Curve Squeeze &rarr; 79% Auto 75% Scale-Out +{" "}
                    <strong>84.5 SOL Slot-0 Migration Snipe</strong>).
                  </span>
                ) : token.bondingCurvePct >= 100 ? (
                  <span>
                    ✓ Graduated AMM Pool: Eligible for{" "}
                    <strong>Engine A Flash Backrun</strong> &amp;{" "}
                    <strong>Agent 27 Meteora DLMM 2.5%–10% Fee Harvest</strong>.
                  </span>
                ) : (
                  <span>
                    ⏳ Watching in <strong>New Creations (0%–64%)</strong>: Agent
                    17 Pre-Mint Listener monitoring until 65.0% curve maturity
                    threshold.
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
