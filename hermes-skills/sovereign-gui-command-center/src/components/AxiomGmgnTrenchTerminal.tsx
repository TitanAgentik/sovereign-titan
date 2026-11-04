import React, { useEffect, useMemo, useState } from "react";
import { usePrivacyMode } from "../hooks/usePrivacyMode";
import { sendTitanIpcCommand } from "../services/titanIpcClient";
import { OpenPositionState, TitanTelemetryFrame } from "../types/telemetry";
import { CoinAvatarBadge } from "./CoinAvatarBadge";
import { TokenDetailChartModal } from "./TokenDetailChartModal";

export type NarrativeCategory =
  | "AI_AGENTS"
  | "MEME_CULT"
  | "ANIMALS"
  | "POLITIFI_VIRAL"
  | "DEFI_INFRA"
  | "GAMING";

export interface TrenchTokenEntry {
  mint: string;
  symbol: string;
  name: string;
  pair: string;
  ageSeconds: number;
  stage: "NEW_PAIR" | "FINAL_STRETCH" | "MIGRATED";
  column?: "NEW_PAIRS" | "FINAL_STRETCH" | "MIGRATED";
  category: NarrativeCategory;
  launchpad:
    | "PUMP"
    | "PUMP_FUN"
    | "PUMPSWAP"
    | "METEORA"
    | "RAYDIUM"
    | "BELIEVE";
  priceUsd?: number;
  bondingCurvePct: number;
  marketCapUsd: number;
  liquidityUsd: number;
  volume5mUsd: number;
  txns5mBuys: number;
  txns5mSells: number;
  top10HoldersPct: number;
  devHoldPct: number;
  devAction: "HODL" | "SOLD_ALL" | "BURNED";
  snipersPct: number;
  insidersBundlePct: number;
  dexPaid: boolean;
  mintAuthRevoked: boolean;
  lpBurned: boolean;
  hasSocials: boolean;
  kolSmartMoneyCount: number;
  bluechipIndexPct: number;
  isInvested: boolean;
  investedSizeSol?: number;
  investedPnlPct?: number;
  investedPnlSol?: number;
  horizon?: string;
  isFreshArrival?: boolean;
}

const INITIAL_TRENCH_TOKENS: TrenchTokenEntry[] = [
  // COLUMN 1: NEW PAIRS / NEW CREATIONS (0% - 64% Curve)
  {
    mint: "Pepe26CyberTrench11111111111111111111111111",
    symbol: "PEPE26",
    name: "Cyber Pepe 2026",
    pair: "PEPE26/SOL",
    ageSeconds: 8,
    stage: "NEW_PAIR",
    category: "MEME_CULT",
    launchpad: "PUMP",
    bondingCurvePct: 38.5,
    marketCapUsd: 24500,
    liquidityUsd: 11800,
    volume5mUsd: 31200,
    txns5mBuys: 112,
    txns5mSells: 48,
    top10HoldersPct: 18.8,
    devHoldPct: 1.4,
    devAction: "HODL",
    snipersPct: 7.0,
    insidersBundlePct: 9.5,
    dexPaid: true,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 2,
    bluechipIndexPct: 5.1,
    isInvested: false,
  },
  {
    mint: "GigaCatSolanaMeme11111111111111111111111111",
    symbol: "GIGACAT",
    name: "GigaChad Cat AI",
    pair: "GIGACAT/SOL",
    ageSeconds: 19,
    stage: "NEW_PAIR",
    category: "ANIMALS",
    launchpad: "PUMP",
    bondingCurvePct: 49.2,
    marketCapUsd: 32800,
    liquidityUsd: 15200,
    volume5mUsd: 44900,
    txns5mBuys: 154,
    txns5mSells: 52,
    top10HoldersPct: 16.2,
    devHoldPct: 0.0,
    devAction: "SOLD_ALL",
    snipersPct: 6.4,
    insidersBundlePct: 8.1,
    dexPaid: true,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 3,
    bluechipIndexPct: 6.8,
    isInvested: false,
  },
  {
    mint: "ElonMarsDogeX202611111111111111111111111111",
    symbol: "DOGE-X",
    name: "Department of X AI",
    pair: "DOGE-X/SOL",
    ageSeconds: 34,
    stage: "NEW_PAIR",
    category: "POLITIFI_VIRAL",
    launchpad: "BELIEVE",
    bondingCurvePct: 56.8,
    marketCapUsd: 41200,
    liquidityUsd: 18400,
    volume5mUsd: 59300,
    txns5mBuys: 189,
    txns5mSells: 67,
    top10HoldersPct: 19.1,
    devHoldPct: 0.0,
    devAction: "BURNED",
    snipersPct: 8.2,
    insidersBundlePct: 10.4,
    dexPaid: true,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 4,
    bluechipIndexPct: 7.9,
    isInvested: false,
  },
  {
    mint: "HyperPixelQuestAI11111111111111111111111111",
    symbol: "PIXELX",
    name: "HyperPixel AI Arena",
    pair: "PIXELX/SOL",
    ageSeconds: 52,
    stage: "NEW_PAIR",
    category: "GAMING",
    launchpad: "PUMP",
    bondingCurvePct: 61.4,
    marketCapUsd: 45900,
    liquidityUsd: 19800,
    volume5mUsd: 52100,
    txns5mBuys: 162,
    txns5mSells: 59,
    top10HoldersPct: 17.4,
    devHoldPct: 0.8,
    devAction: "HODL",
    snipersPct: 5.9,
    insidersBundlePct: 7.8,
    dexPaid: false,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 2,
    bluechipIndexPct: 5.7,
    isInvested: false,
  },

  // COLUMN 2: FINAL STRETCH (65% - 84.5% Golden 5 Mechanical Squeeze Zone)
  {
    mint: "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin",
    symbol: "NEURAL",
    name: "NeuralNet Solana",
    pair: "NEURAL/SOL",
    ageSeconds: 210,
    stage: "FINAL_STRETCH",
    category: "AI_AGENTS",
    launchpad: "PUMP",
    bondingCurvePct: 74.6,
    marketCapUsd: 58400,
    liquidityUsd: 24800,
    volume5mUsd: 89200,
    txns5mBuys: 224,
    txns5mSells: 79,
    top10HoldersPct: 16.8,
    devHoldPct: 0.5,
    devAction: "SOLD_ALL",
    snipersPct: 6.1,
    insidersBundlePct: 8.4,
    dexPaid: true,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 4,
    bluechipIndexPct: 8.9,
    isInvested: true,
  },
  {
    mint: "QWEN8002VisionSniper11111111111111111111111",
    symbol: "QWEN",
    name: "Qwen Vision Sniper",
    pair: "QWEN/SOL",
    ageSeconds: 165,
    stage: "FINAL_STRETCH",
    category: "AI_AGENTS",
    launchpad: "PUMP",
    bondingCurvePct: 78.2,
    marketCapUsd: 64900,
    liquidityUsd: 27400,
    volume5mUsd: 114500,
    txns5mBuys: 289,
    txns5mSells: 92,
    top10HoldersPct: 15.1,
    devHoldPct: 0.0,
    devAction: "BURNED",
    snipersPct: 5.4,
    insidersBundlePct: 7.1,
    dexPaid: true,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 5,
    bluechipIndexPct: 9.8,
    isInvested: false,
  },
  {
    mint: "WifAiAgentSolana111111111111111111111111111",
    symbol: "WIFAI",
    name: "DogWifAI Agent",
    pair: "WIFAI/SOL",
    ageSeconds: 290,
    stage: "FINAL_STRETCH",
    category: "ANIMALS",
    launchpad: "PUMP",
    bondingCurvePct: 81.4,
    marketCapUsd: 68100,
    liquidityUsd: 29200,
    volume5mUsd: 142800,
    txns5mBuys: 341,
    txns5mSells: 98,
    top10HoldersPct: 13.9,
    devHoldPct: 0.0,
    devAction: "BURNED",
    snipersPct: 4.2,
    insidersBundlePct: 5.8,
    dexPaid: true,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 7,
    bluechipIndexPct: 12.6,
    isInvested: false,
  },
  {
    mint: "QuantZeroSlot845Sol111111111111111111111111",
    symbol: "QUANT",
    name: "Zero-Slot Quant",
    pair: "QUANT/SOL",
    ageSeconds: 340,
    stage: "FINAL_STRETCH",
    category: "DEFI_INFRA",
    launchpad: "METEORA",
    bondingCurvePct: 69.4,
    marketCapUsd: 51200,
    liquidityUsd: 21900,
    volume5mUsd: 64300,
    txns5mBuys: 178,
    txns5mSells: 64,
    top10HoldersPct: 19.4,
    devHoldPct: 0.0,
    devAction: "SOLD_ALL",
    snipersPct: 8.5,
    insidersBundlePct: 11.2,
    dexPaid: true,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 3,
    bluechipIndexPct: 6.4,
    isInvested: false,
  },

  // COLUMN 3: MIGRATED / GRADUATED TO PUMPSWAP & RAYDIUM (100% Curve)
  {
    mint: "So11111111111111111111111111111111111111112",
    symbol: "TITAN",
    name: "Sovereign Titan AI",
    pair: "TITAN/SOL",
    ageSeconds: 780,
    stage: "MIGRATED",
    category: "AI_AGENTS",
    launchpad: "PUMPSWAP",
    bondingCurvePct: 100.0,
    marketCapUsd: 482000,
    liquidityUsd: 94500,
    volume5mUsd: 168400,
    txns5mBuys: 312,
    txns5mSells: 118,
    top10HoldersPct: 14.2,
    devHoldPct: 0.0,
    devAction: "BURNED",
    snipersPct: 4.8,
    insidersBundlePct: 6.2,
    dexPaid: true,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 6,
    bluechipIndexPct: 11.4,
    isInvested: true,
  },
  {
    mint: "AlpenGlow200msBlock111111111111111111111111",
    symbol: "ALPEN",
    name: "Alpenglow 200ms",
    pair: "ALPEN/SOL",
    ageSeconds: 1120,
    stage: "MIGRATED",
    category: "DEFI_INFRA",
    launchpad: "PUMPSWAP",
    bondingCurvePct: 100.0,
    marketCapUsd: 319000,
    liquidityUsd: 72100,
    volume5mUsd: 132000,
    txns5mBuys: 264,
    txns5mSells: 104,
    top10HoldersPct: 17.5,
    devHoldPct: 1.2,
    devAction: "HODL",
    snipersPct: 7.2,
    insidersBundlePct: 9.0,
    dexPaid: true,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 3,
    bluechipIndexPct: 7.6,
    isInvested: false,
  },
  {
    mint: "SharkApexLiquidator111111111111111111111111",
    symbol: "SHARK",
    name: "Apex Liquidation Shark",
    pair: "SHARK/SOL",
    ageSeconds: 1540,
    stage: "MIGRATED",
    category: "MEME_CULT",
    launchpad: "RAYDIUM",
    bondingCurvePct: 100.0,
    marketCapUsd: 612000,
    liquidityUsd: 118000,
    volume5mUsd: 215000,
    txns5mBuys: 408,
    txns5mSells: 156,
    top10HoldersPct: 13.4,
    devHoldPct: 0.0,
    devAction: "BURNED",
    snipersPct: 3.9,
    insidersBundlePct: 5.2,
    dexPaid: true,
    mintAuthRevoked: true,
    lpBurned: true,
    hasSocials: true,
    kolSmartMoneyCount: 8,
    bluechipIndexPct: 14.2,
    isInvested: false,
  },
];

const STREAM_CANDIDATE_POOL: Array<{
  symbol: string;
  name: string;
  category: NarrativeCategory;
  launchpad: TrenchTokenEntry["launchpad"];
}> = [
  {
    symbol: "HERMES",
    name: "Hermes-3 8B FastGate",
    category: "AI_AGENTS",
    launchpad: "PUMP",
  },
  {
    symbol: "MOG26",
    name: "MogCoin Cyber 2026",
    category: "MEME_CULT",
    launchpad: "PUMP",
  },
  {
    symbol: "BONKAI",
    name: "Bonk Autonomous Dog",
    category: "ANIMALS",
    launchpad: "BELIEVE",
  },
  {
    symbol: "TRUMPX",
    name: "Truth Social AI Reserve",
    category: "POLITIFI_VIRAL",
    launchpad: "PUMP",
  },
  {
    symbol: "JITOSOLX",
    name: "Jito SuperBundle Alpha",
    category: "DEFI_INFRA",
    launchpad: "METEORA",
  },
  {
    symbol: "GTA6AI",
    name: "Vice City Neural NPC",
    category: "GAMING",
    launchpad: "PUMP",
  },
  {
    symbol: "PNUT2",
    name: "Cyber Squirrel Justice",
    category: "ANIMALS",
    launchpad: "PUMP",
  },
  {
    symbol: "DEEPSEEK",
    name: "DeepSeek R1 Trench Bot",
    category: "AI_AGENTS",
    launchpad: "PUMPSWAP",
  },
];

function formatAge(sec: number): string {
  if (sec < 60) return `${Math.max(1, Math.floor(sec))}s`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m`;
  return `${Math.floor(sec / 3600)}h`;
}

const CATEGORY_META: Record<
  NarrativeCategory | "ALL" | "INVESTED",
  { label: string; badge: string }
> = {
  ALL: { label: "🌐 ALL CATEGORIES", badge: "ALL" },
  INVESTED: { label: "💎 MY INVESTED COINS", badge: "HELD" },
  AI_AGENTS: { label: "🤖 AI AGENTS & SWARMS", badge: "AI AGENT" },
  MEME_CULT: { label: "🐸 MEMES & CULT", badge: "MEME" },
  ANIMALS: { label: "🐕 ANIMALS (DOGS/CATS)", badge: "ANIMAL" },
  POLITIFI_VIRAL: { label: "🏛️ POLITIFI & VIRAL", badge: "VIRAL" },
  DEFI_INFRA: { label: "⚡ DEFI & QUANT INFRA", badge: "DEFI" },
  GAMING: { label: "🎮 GAMING & METAVERSE", badge: "GAMING" },
};

interface TrenchTerminalCacheState {
  liveTokens: TrenchTokenEntry[];
  streamEnabled: boolean;
  viewLayout: "THREE_COLUMN_PULSE" | "TABLE";
  trenchSectionView: "ALL" | "INVESTED_ONLY" | "TRENCHES_ONLY";
  showFilterBar: boolean;
  selectedCategory: NarrativeCategory | "ALL" | "INVESTED";
  launchpadFilter: string;
  filterDexPaid: boolean;
  filterDevClean: boolean;
  filterLowInsiders: boolean;
  filterLowSnipers: boolean;
  filterTop10Safe: boolean;
  filterMintRevoked: boolean;
  filterLpBurned: boolean;
  filterNoDexPaid: boolean;
  filterHasSocials: boolean;
  filterKolInflow: boolean;
  filterGolden5Curve: boolean;
  searchQuery: string;
  minMcapK: number;
  quickBuySol: number;
}

const SYNTHETIC_DEMO_MINTS = new Set<string>(
  INITIAL_TRENCH_TOKENS.map((t) => t.mint)
);

const TRENCH_TERMINAL_CACHE: TrenchTerminalCacheState = {
  liveTokens: INITIAL_TRENCH_TOKENS,
  streamEnabled: true,
  viewLayout: "THREE_COLUMN_PULSE",
  trenchSectionView: "ALL",
  showFilterBar: false,
  selectedCategory: "ALL",
  launchpadFilter: "ALL",
  filterDexPaid: false,
  filterDevClean: false,
  filterLowInsiders: true,
  filterLowSnipers: true,
  filterTop10Safe: true,
  filterMintRevoked: true,
  filterLpBurned: false,
  filterNoDexPaid: false,
  filterHasSocials: false,
  filterKolInflow: false,
  filterGolden5Curve: false,
  searchQuery: "",
  minMcapK: 0,
  quickBuySol: 1.5,
};

const VALID_NARRATIVE_CATEGORIES = new Set<NarrativeCategory>([
  "AI_AGENTS",
  "MEME_CULT",
  "ANIMALS",
  "POLITIFI_VIRAL",
  "DEFI_INFRA",
  "GAMING",
]);

function inferNarrativeCategory(
  rawCat: unknown,
  symbol: string,
  name: string
): NarrativeCategory {
  const candidate = String(rawCat || "").toUpperCase() as NarrativeCategory;
  if (VALID_NARRATIVE_CATEGORIES.has(candidate)) {
    return candidate;
  }
  const text = `${symbol} ${name}`.toUpperCase();
  if (/(AI|GPT|AGENT|LLM|NEURAL|BOT|DEEP|ELIZA|SWARM|MCP)/.test(text)) {
    return "AI_AGENTS";
  }
  if (/(CAT|DOG|PEPE|SHIB|FROG|BONK|WIF|GOAT|PENGU|PIG|APE|BEAR|BULL|MOO|DOGE)/.test(text)) {
    return "ANIMALS";
  }
  if (/(TRUMP|MAGA|BIDEN|ELON|DOGE|USA|GOV|PRES|VOTE|Kanye|YE|SEC)/.test(text)) {
    return "POLITIFI_VIRAL";
  }
  if (/(SWAP|DEX|SOL|LP|YIELD|STAKE|LEND|PERP|JUP|RAY|MET|USD|PAY|CHAIN)/.test(text)) {
    return "DEFI_INFRA";
  }
  if (/(GAME|PLAY|QUEST|PIXEL|META|RPG|GUILD|ARCADE|BET)/.test(text)) {
    return "GAMING";
  }
  return "MEME_CULT";
}

function normalizeLiveBackendToken(
  raw: Record<string, unknown>,
  solUsd: number
): TrenchTokenEntry {
  const mint = String(raw.mint || "");
  const cleanSym = String(raw.symbol || "SOLGEM")
    .replace("$", "")
    .replace("/SOL", "")
    .trim();
  const name = String(raw.name || cleanSym);
  const rawStage = String(raw.stage || raw.column || raw.category || "").toUpperCase();
  const rawCurve = Number(
    raw.bondingCurvePct ??
      raw.bonding_curve_pct ??
      (rawStage === "MIGRATED" || rawStage === "GRADUATED"
        ? 100.0
        : rawStage === "FINAL_STRETCH"
        ? 76.5
        : 34.0)
  );
  const bondingCurvePct = Number.isFinite(rawCurve)
    ? Math.max(0, Math.min(100, +rawCurve.toFixed(1)))
    : 34.0;
  let stage: TrenchTokenEntry["stage"] = "NEW_PAIR";
  if (rawStage === "MIGRATED" || rawStage === "GRADUATED" || bondingCurvePct >= 99.5) {
    stage = "MIGRATED";
  } else if (
    rawStage === "FINAL_STRETCH" ||
    (bondingCurvePct >= 60.0 && bondingCurvePct < 99.5)
  ) {
    stage = "FINAL_STRETCH";
  }
  const column: TrenchTokenEntry["column"] =
    stage === "MIGRATED"
      ? "MIGRATED"
      : stage === "FINAL_STRETCH"
      ? "FINAL_STRETCH"
      : "NEW_PAIRS";

  const rawLp = String(raw.launchpad || "").toUpperCase();
  const launchpad: TrenchTokenEntry["launchpad"] =
    rawLp === "PUMPSWAP"
      ? "PUMPSWAP"
      : rawLp === "METEORA"
      ? "METEORA"
      : rawLp === "RAYDIUM"
      ? "RAYDIUM"
      : rawLp === "BELIEVE"
      ? "BELIEVE"
      : rawLp === "PUMP_FUN"
      ? "PUMP_FUN"
      : stage === "MIGRATED"
      ? "PUMPSWAP"
      : "PUMP";

  const rawMcap = Number(
    raw.marketCapUsd ??
      raw.market_cap_usd ??
      (Number(raw.marketCapSol ?? raw.market_cap_sol ?? 0) * solUsd || 48000)
  );
  const marketCapUsd = Number.isFinite(rawMcap) && rawMcap > 0 ? Math.round(rawMcap) : 48000;
  const priceUsd = Number(
    raw.priceUsd ?? raw.price_usd ?? marketCapUsd / 1_000_000_000
  );

  return {
    mint,
    symbol: cleanSym,
    name,
    pair: String(raw.pair || `${cleanSym}/SOL`),
    ageSeconds: Math.max(1, Number(raw.ageSeconds ?? raw.age_seconds ?? 12)),
    stage,
    column,
    category: inferNarrativeCategory(raw.narrativeCategory ?? raw.category, cleanSym, name),
    launchpad,
    priceUsd: Number.isFinite(priceUsd) ? priceUsd : undefined,
    bondingCurvePct,
    marketCapUsd,
    liquidityUsd: Math.max(
      4000,
      Math.round(Number(raw.liquidityUsd ?? raw.liquidity_usd ?? marketCapUsd * 0.28))
    ),
    volume5mUsd: Math.max(
      2500,
      Math.round(Number(raw.volume5mUsd ?? raw.volume_5m_usd ?? marketCapUsd * 0.45))
    ),
    txns5mBuys: Math.max(8, Math.round(Number(raw.txns5mBuys ?? raw.txns_5m_buys ?? 84))),
    txns5mSells: Math.max(2, Math.round(Number(raw.txns5mSells ?? raw.txns_5m_sells ?? 29))),
    top10HoldersPct: Number(raw.top10HoldersPct ?? raw.top10_holders_pct ?? 14.5),
    devHoldPct: Number(raw.devHoldPct ?? raw.dev_hold_pct ?? 0.0),
    devAction:
      (raw.devAction as TrenchTokenEntry["devAction"]) ||
      (raw.dev_action as TrenchTokenEntry["devAction"]) ||
      "BURNED",
    snipersPct: Number(raw.snipersPct ?? raw.snipers_pct ?? 5.2),
    insidersBundlePct: Number(raw.insidersBundlePct ?? raw.insiders_bundle_pct ?? 6.8),
    dexPaid: Boolean(raw.dexPaid ?? raw.dex_paid ?? true),
    mintAuthRevoked:
      raw.mintAuthRevoked !== undefined
        ? Boolean(raw.mintAuthRevoked)
        : raw.mint_auth_revoked !== undefined
        ? Boolean(raw.mint_auth_revoked)
        : true,
    lpBurned:
      raw.lpBurned !== undefined
        ? Boolean(raw.lpBurned)
        : raw.lp_burned !== undefined
        ? Boolean(raw.lp_burned)
        : true,
    hasSocials:
      raw.hasSocials !== undefined
        ? Boolean(raw.hasSocials)
        : raw.has_socials !== undefined
        ? Boolean(raw.has_socials)
        : true,
    kolSmartMoneyCount: Number(raw.kolSmartMoneyCount ?? raw.kol_smart_money_count ?? 3),
    bluechipIndexPct: Number(raw.bluechipIndexPct ?? raw.bluechip_index_pct ?? 7.4),
    isInvested: Boolean(raw.isInvested ?? raw.is_invested ?? false),
  };
}

interface AxiomGmgnTrenchTerminalProps {
  frame: TitanTelemetryFrame;
  onStatusMessage?: (msg: string) => void;
  onPinToChart1?: (mint: string, symbol: string) => void;
  onPinToChart2?: (mint: string, symbol: string) => void;
}

export const AxiomGmgnTrenchTerminal: React.FC<AxiomGmgnTrenchTerminalProps> = ({
  frame,
  onStatusMessage,
  onPinToChart1,
  onPinToChart2,
}) => {
  const [privacyMode] = usePrivacyMode();

  // Live streaming token list (Axiom Pulse / GMGN Trenches style) hydrated from persistent module cache
  const [liveTokens, setLiveTokens] = useState<TrenchTokenEntry[]>(
    () => TRENCH_TERMINAL_CACHE.liveTokens
  );
  const [streamEnabled, setStreamEnabled] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.streamEnabled
  );
  const [hoverPaused, setHoverPaused] = useState<boolean>(false);
  const [viewLayout, setViewLayout] = useState<"THREE_COLUMN_PULSE" | "TABLE">(
    () => TRENCH_TERMINAL_CACHE.viewLayout
  );
  const [trenchSectionView, setTrenchSectionView] = useState<
    "ALL" | "INVESTED_ONLY" | "TRENCHES_ONLY"
  >(() => TRENCH_TERMINAL_CACHE.trenchSectionView);
  const [showFilterBar, setShowFilterBar] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.showFilterBar
  );

  // Category & Launchpad Filters
  const [selectedCategory, setSelectedCategory] = useState<
    NarrativeCategory | "ALL" | "INVESTED"
  >(() => TRENCH_TERMINAL_CACHE.selectedCategory);
  const [launchpadFilter, setLaunchpadFilter] = useState<string>(
    () => TRENCH_TERMINAL_CACHE.launchpadFilter
  );

  // Axiom.trade & GMGN.ai Toggleable Security Filters (all clearly showing 🟢 ON / 🔴 OFF)
  const [filterDexPaid, setFilterDexPaid] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.filterDexPaid
  );
  const [filterDevClean, setFilterDevClean] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.filterDevClean
  );
  const [filterLowInsiders, setFilterLowInsiders] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.filterLowInsiders
  );
  const [filterLowSnipers, setFilterLowSnipers] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.filterLowSnipers
  );
  const [filterTop10Safe, setFilterTop10Safe] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.filterTop10Safe
  );
  const [filterMintRevoked, setFilterMintRevoked] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.filterMintRevoked
  );
  const [filterHasSocials, setFilterHasSocials] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.filterHasSocials
  );
  const [filterKolInflow, setFilterKolInflow] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.filterKolInflow
  );
  const [filterGolden5Curve, setFilterGolden5Curve] = useState<boolean>(
    () => TRENCH_TERMINAL_CACHE.filterGolden5Curve
  );

  const [searchQuery, setSearchQuery] = useState<string>(
    () => TRENCH_TERMINAL_CACHE.searchQuery
  );
  const [minMcapK, setMinMcapK] = useState<number>(
    () => TRENCH_TERMINAL_CACHE.minMcapK
  );
  const [quickBuySol, setQuickBuySol] = useState<number>(
    () => TRENCH_TERMINAL_CACHE.quickBuySol
  );
  const [selectedCoin, setSelectedCoin] = useState<TrenchTokenEntry | null>(
    null
  );

  // Persist liveTokens & filters in module-level cache across Workspace 1..7 navigation
  useEffect(() => {
    TRENCH_TERMINAL_CACHE.liveTokens = liveTokens;
    TRENCH_TERMINAL_CACHE.streamEnabled = streamEnabled;
    TRENCH_TERMINAL_CACHE.viewLayout = viewLayout;
    TRENCH_TERMINAL_CACHE.trenchSectionView = trenchSectionView;
    TRENCH_TERMINAL_CACHE.showFilterBar = showFilterBar;
    TRENCH_TERMINAL_CACHE.selectedCategory = selectedCategory;
    TRENCH_TERMINAL_CACHE.launchpadFilter = launchpadFilter;
    TRENCH_TERMINAL_CACHE.filterDexPaid = filterDexPaid;
    TRENCH_TERMINAL_CACHE.filterDevClean = filterDevClean;
    TRENCH_TERMINAL_CACHE.filterLowInsiders = filterLowInsiders;
    TRENCH_TERMINAL_CACHE.filterLowSnipers = filterLowSnipers;
    TRENCH_TERMINAL_CACHE.filterTop10Safe = filterTop10Safe;
    TRENCH_TERMINAL_CACHE.filterMintRevoked = filterMintRevoked;
    TRENCH_TERMINAL_CACHE.filterHasSocials = filterHasSocials;
    TRENCH_TERMINAL_CACHE.filterKolInflow = filterKolInflow;
    TRENCH_TERMINAL_CACHE.filterGolden5Curve = filterGolden5Curve;
    TRENCH_TERMINAL_CACHE.searchQuery = searchQuery;
    TRENCH_TERMINAL_CACHE.minMcapK = minMcapK;
    TRENCH_TERMINAL_CACHE.quickBuySol = quickBuySol;
  }, [
    liveTokens,
    streamEnabled,
    viewLayout,
    trenchSectionView,
    showFilterBar,
    selectedCategory,
    launchpadFilter,
    filterDexPaid,
    filterDevClean,
    filterLowInsiders,
    filterLowSnipers,
    filterTop10Safe,
    filterMintRevoked,
    filterHasSocials,
    filterKolInflow,
    filterGolden5Curve,
    searchQuery,
    minMcapK,
    quickBuySol,
  ]);

  // Hydrate / merge real live Solana tokens from frame.live_market_tokens when present
  const backendLiveTokens = (
    frame as unknown as { live_market_tokens?: Array<Record<string, unknown>> }
  ).live_market_tokens;

  const lastBackendTokenSyncMsRef = React.useRef<number>(0);
  const lastBackendMintDigestRef = React.useRef<string>("");

  useEffect(() => {
    if (!Array.isArray(backendLiveTokens) || backendLiveTokens.length === 0) {
      return;
    }
    const nowMs = Date.now();
    const mintDigest = backendLiveTokens
      .slice(0, 24)
      .map((item) => String(item?.mint || ""))
      .join(",");
    const mintSetChanged = mintDigest !== lastBackendMintDigestRef.current;
    if (!mintSetChanged && nowMs - lastBackendTokenSyncMsRef.current < 3000) {
      return;
    }
    lastBackendTokenSyncMsRef.current = nowMs;
    lastBackendMintDigestRef.current = mintDigest;

    const solUsd = frame.sol_usd || 194.5;
    const normalized = backendLiveTokens
      .filter((item) => item && typeof item.mint === "string" && item.mint.length > 0)
      .map((item) => normalizeLiveBackendToken(item, solUsd));
    if (normalized.length === 0) return;

    setLiveTokens((prev) => {
      const incomingByMint = new Map<string, TrenchTokenEntry>();
      for (const tok of normalized) {
        incomingByMint.set(tok.mint, tok);
      }
      // Preserve existing order of real tokens so cards do not jump around under the user's cursor
      const updatedExisting: TrenchTokenEntry[] = [];
      for (const existing of prev) {
        if (SYNTHETIC_DEMO_MINTS.has(existing.mint)) continue;
        const updatedFromBackend = incomingByMint.get(existing.mint);
        if (updatedFromBackend) {
          updatedExisting.push({
            ...existing,
            ...updatedFromBackend,
            stage: existing.stage,
            column: existing.column,
            ageSeconds: Math.max(existing.ageSeconds, updatedFromBackend.ageSeconds),
            isInvested: existing.isInvested || updatedFromBackend.isInvested,
            investedSizeSol: existing.investedSizeSol ?? updatedFromBackend.investedSizeSol,
            investedPnlPct: existing.investedPnlPct ?? updatedFromBackend.investedPnlPct,
            isFreshArrival: false,
          });
          incomingByMint.delete(existing.mint);
        } else {
          updatedExisting.push({
            ...existing,
            isFreshArrival: false,
          });
        }
      }
      const brandNewFromBackend = Array.from(incomingByMint.values());
      const nextList = [...brandNewFromBackend, ...updatedExisting].slice(0, 48);
      TRENCH_TERMINAL_CACHE.liveTokens = nextList;
      return nextList;
    });
  }, [backendLiveTokens, frame.sol_usd]);

  // Direct browser WebSocket connection to PumpPortal real-time Solana token & migration stream
  useEffect(() => {
    if (!streamEnabled || typeof WebSocket === "undefined") return;

    let ws: WebSocket | null = null;
    let isDisposed = false;
    let lastWsInsertMs = 0;

    try {
      ws = new WebSocket("wss://pumpportal.fun/api/data");
      ws.onopen = () => {
        if (isDisposed || !ws || ws.readyState !== WebSocket.OPEN) return;
        try {
          ws.send(JSON.stringify({ method: "subscribeNewToken" }));
          ws.send(JSON.stringify({ method: "subscribeMigration" }));
        } catch {
          // ignore send errors
        }
      };

      ws.onmessage = (event) => {
        if (isDisposed || hoverPaused || frame.paused_all) return;
        const nowMs = Date.now();
        // Rate-limit visual card insertions to at most 1 every 1.2s so the Trench columns don't blur/flicker
        if (nowMs - lastWsInsertMs < 1200) return;
        try {
          const data = JSON.parse(String(event.data || "{}")) as Record<
            string,
            unknown
          >;
          const mint = String(data.mint || "").trim();
          const rawSymbol = String(data.symbol || data.name || "").trim();
          if (!mint || !rawSymbol) return;
          lastWsInsertMs = nowMs;

          const cleanSym = rawSymbol
            .replace("$", "")
            .replace("/SOL", "")
            .slice(0, 14)
            .toUpperCase();
          const name = String(data.name || cleanSym).slice(0, 36);
          const isMigration =
            String(data.txType || "").toLowerCase() === "migrate" ||
            String(data.pool || "").toLowerCase().includes("raydium") ||
            String(data.pool || "").toLowerCase().includes("pumpswap");
          const solUsd = frame.sol_usd || 194.5;
          const mcapSol = Number(data.marketCapSol ?? data.vSolInBondingCurve ?? 32);
          const marketCapUsd = Math.max(
            4200,
            Math.round((Number.isFinite(mcapSol) && mcapSol > 0 ? mcapSol : 32) * solUsd)
          );
          const vSolCurve = Number(data.vSolInBondingCurve ?? 30);
          const estCurvePct = isMigration
            ? 100.0
            : Math.max(
                8.0,
                Math.min(
                  98.0,
                  +(((Math.max(0, vSolCurve - 28) / 85) * 100) || 22.5).toFixed(1)
                )
              );
          const stage: TrenchTokenEntry["stage"] = isMigration
            ? "MIGRATED"
            : estCurvePct >= 60.0
            ? "FINAL_STRETCH"
            : "NEW_PAIR";
          const column: TrenchTokenEntry["column"] = isMigration
            ? "MIGRATED"
            : stage === "FINAL_STRETCH"
            ? "FINAL_STRETCH"
            : "NEW_PAIRS";

          const wsToken: TrenchTokenEntry = {
            mint,
            symbol: cleanSym,
            name,
            pair: `${cleanSym}/SOL`,
            ageSeconds: 1,
            stage,
            column,
            category: "MEME_CULT",
            launchpad: "PUMP_FUN",
            priceUsd: +(marketCapUsd / 1_000_000_000).toFixed(8),
            bondingCurvePct: estCurvePct,
            marketCapUsd,
            liquidityUsd: Math.max(4500, Math.round(marketCapUsd * 0.32)),
            volume5mUsd: Math.max(
              1800,
              Math.round(Number(data.initialBuy ?? 4.5) * solUsd * 3.2)
            ),
            txns5mBuys: Math.floor(18 + Math.random() * 64),
            txns5mSells: Math.floor(4 + Math.random() * 19),
            top10HoldersPct: 14.2,
            devHoldPct: 0.8,
            devAction: "HODL",
            snipersPct: 4.8,
            insidersBundlePct: 6.2,
            dexPaid: Boolean(data.uri),
            mintAuthRevoked: true,
            lpBurned: true,
            hasSocials: true,
            kolSmartMoneyCount: isMigration ? 4 : 2,
            bluechipIndexPct: 6.8,
            isInvested: false,
            isFreshArrival: true,
          };

          setLiveTokens((prev) => {
            const withoutDup = prev.filter((t) => t.mint !== mint);
            const next = [wsToken, ...withoutDup].slice(0, 48);
            TRENCH_TERMINAL_CACHE.liveTokens = next;
            return next;
          });
        } catch {
          // ignore malformed packet
        }
      };
    } catch {
      // ignore WebSocket init failure in restricted environments
    }

    return () => {
      isDisposed = true;
      if (ws) {
        try {
          ws.close();
        } catch {
          // ignore close errors
        }
      }
    };
  }, [streamEnabled, hoverPaused, frame.paused_all, frame.sol_usd]);

  // Age progression every 3.0 seconds (unless paused or hovered); only synthesize demo ticks if no real tokens are loaded
  useEffect(() => {
    if (!streamEnabled || hoverPaused || frame.paused_all) return;

    const timer = window.setInterval(() => {
      setLiveTokens((prev) => {
        const hasRealTokens = prev.some((t) => !SYNTHETIC_DEMO_MINTS.has(t.mint));
        if (hasRealTokens) {
          const aged = prev.map((tok) => ({
            ...tok,
            ageSeconds: tok.ageSeconds + 3,
            isFreshArrival: false,
          }));
          TRENCH_TERMINAL_CACHE.liveTokens = aged;
          return aged;
        }

        const updated = prev.map((tok) => {
          const nextAge = tok.ageSeconds + 3;
          let nextCurve = tok.bondingCurvePct;
          let nextStage = tok.stage;
          let nextMcap = tok.marketCapUsd;
          const nextVol = tok.volume5mUsd + Math.round(Math.random() * 1800);
          const nextBuys = tok.txns5mBuys + Math.floor(Math.random() * 5);

          if (tok.stage === "NEW_PAIR") {
            nextCurve = Math.min(68.0, +(tok.bondingCurvePct + 1.8).toFixed(1));
            nextMcap = Math.round(tok.marketCapUsd * 1.025);
            if (nextCurve >= 65.0) {
              nextStage = "FINAL_STRETCH";
            }
          } else if (tok.stage === "FINAL_STRETCH") {
            nextCurve = Math.min(
              100.0,
              +(tok.bondingCurvePct + 1.4).toFixed(1)
            );
            nextMcap = Math.round(tok.marketCapUsd * 1.03);
            if (nextCurve >= 84.5) {
              nextCurve = 100.0;
              nextStage = "MIGRATED";
              nextMcap = Math.max(125000, Math.round(tok.marketCapUsd * 1.65));
            }
          } else {
            nextMcap = Math.round(
              tok.marketCapUsd * (0.996 + Math.random() * 0.015)
            );
          }

          return {
            ...tok,
            ageSeconds: nextAge,
            bondingCurvePct: nextCurve,
            stage: nextStage,
            marketCapUsd: nextMcap,
            volume5mUsd: nextVol,
            txns5mBuys: nextBuys,
            isFreshArrival: false,
          };
        });

        const shouldSpawn = Math.random() < 0.45;
        if (shouldSpawn) {
          const template =
            STREAM_CANDIDATE_POOL[
              Math.floor(Math.random() * STREAM_CANDIDATE_POOL.length)
            ];
          const suffix = Math.floor(10 + Math.random() * 89);
          const sym = `${template.symbol}${suffix}`;
          const newEntry: TrenchTokenEntry = {
            mint: `${sym}Mint${Date.now()}111111111111111111`,
            symbol: sym,
            name: template.name,
            pair: `${sym}/SOL`,
            ageSeconds: 2,
            stage: "NEW_PAIR",
            category: template.category,
            launchpad: template.launchpad,
            bondingCurvePct: +(18 + Math.random() * 34).toFixed(1),
            marketCapUsd: Math.round(14000 + Math.random() * 22000),
            liquidityUsd: Math.round(8500 + Math.random() * 9000),
            volume5mUsd: Math.round(12000 + Math.random() * 28000),
            txns5mBuys: Math.floor(45 + Math.random() * 95),
            txns5mSells: Math.floor(12 + Math.random() * 35),
            top10HoldersPct: +(12 + Math.random() * 9).toFixed(1),
            devHoldPct: Math.random() < 0.65 ? 0.0 : 1.2,
            devAction: Math.random() < 0.65 ? "BURNED" : "SOLD_ALL",
            snipersPct: +(3.5 + Math.random() * 6.5).toFixed(1),
            insidersBundlePct: +(4.5 + Math.random() * 7.5).toFixed(1),
            dexPaid: Math.random() < 0.75,
            mintAuthRevoked: true,
            lpBurned: true,
            hasSocials: true,
            kolSmartMoneyCount: Math.floor(1 + Math.random() * 5),
            bluechipIndexPct: +(4.5 + Math.random() * 7.5).toFixed(1),
            isInvested: false,
            isFreshArrival: true,
          };
          const next = [newEntry, ...updated].slice(0, 24);
          TRENCH_TERMINAL_CACHE.liveTokens = next;
          return next;
        }

        TRENCH_TERMINAL_CACHE.liveTokens = updated;
        return updated;
      });
    }, 2800);

    return () => window.clearInterval(timer);
  }, [streamEnabled, hoverPaused, frame.paused_all]);

  const openPositions: OpenPositionState[] = frame.open_positions ?? [];

  // Merge live invested positions with streaming tokens
  const mergedTokens = useMemo(() => {
    const byMint = new Map<string, TrenchTokenEntry>();
    for (const item of liveTokens) {
      byMint.set(item.mint, { ...item, isInvested: false });
    }

    for (const pos of openPositions) {
      const cleanSymbol = String(pos.symbol || "TITAN")
        .replace("/SOL", "")
        .replace("$", "")
        .trim();
      const pairStr = `${cleanSymbol}/SOL`;
      const existing = byMint.get(pos.mint);
      if (existing) {
        existing.isInvested = true;
        existing.investedSizeSol = pos.size_sol;
        existing.investedPnlPct = pos.pnl_pct;
        existing.investedPnlSol = pos.pnl_sol;
        existing.horizon = pos.stage;
      } else {
        const isCurve = pos.venue.toLowerCase().includes("curve") || pos.stage.includes("H1");
        byMint.set(pos.mint, {
          mint: pos.mint,
          symbol: cleanSymbol,
          name: `${cleanSymbol} Autonomous Gem`,
          pair: pairStr,
          ageSeconds: 45,
          stage: isCurve ? "FINAL_STRETCH" : "MIGRATED",
          category: "AI_AGENTS",
          launchpad: isCurve ? "PUMP" : "PUMPSWAP",
          bondingCurvePct: isCurve ? 76.5 : 100.0,
          marketCapUsd: Math.max(
            45000,
            Math.round(pos.mark_price_usd * 100_000_000)
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
      }
    }

    return Array.from(byMint.values());
  }, [liveTokens, openPositions]);

  const filteredTokens = useMemo(() => {
    return mergedTokens.filter((t) => {
      if (selectedCategory === "INVESTED" && !t.isInvested) return false;
      if (
        selectedCategory !== "ALL" &&
        selectedCategory !== "INVESTED" &&
        t.category !== selectedCategory
      ) {
        return false;
      }
      if (launchpadFilter !== "ALL") {
        const matchesPump =
          launchpadFilter === "PUMP" &&
          (t.launchpad === "PUMP" || t.launchpad === "PUMP_FUN");
        if (!matchesPump && t.launchpad !== launchpadFilter) {
          return false;
        }
      }
      if (filterDexPaid && !t.dexPaid) return false;
      if (filterDevClean && t.devHoldPct > 2.0) return false;
      if (filterLowInsiders && t.insidersBundlePct > 15.0) return false;
      if (filterLowSnipers && t.snipersPct > 12.0) return false;
      if (filterTop10Safe && t.top10HoldersPct > 25.0) return false;
      if (filterMintRevoked && !t.mintAuthRevoked) return false;
      if (filterHasSocials && !t.hasSocials) return false;
      if (filterKolInflow && t.kolSmartMoneyCount < 2) return false;
      if (filterGolden5Curve && t.bondingCurvePct < 65.0) return false;
      if (minMcapK > 0 && t.marketCapUsd < minMcapK * 1000) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.trim().toLowerCase();
        if (
          !t.symbol.toLowerCase().includes(q) &&
          !t.name.toLowerCase().includes(q) &&
          !t.mint.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [
    mergedTokens,
    selectedCategory,
    launchpadFilter,
    filterDexPaid,
    filterDevClean,
    filterLowInsiders,
    filterLowSnipers,
    filterTop10Safe,
    filterMintRevoked,
    filterHasSocials,
    filterKolInflow,
    filterGolden5Curve,
    minMcapK,
    searchQuery,
  ]);

  const investedCoins = useMemo(
    () => mergedTokens.filter((t) => t.isInvested),
    [mergedTokens]
  );

  const newPairCoins = useMemo(
    () => filteredTokens.filter((t) => t.stage === "NEW_PAIR"),
    [filteredTokens]
  );
  const finalStretchCoins = useMemo(
    () => filteredTokens.filter((t) => t.stage === "FINAL_STRETCH"),
    [filteredTokens]
  );
  const migratedCoins = useMemo(
    () => filteredTokens.filter((t) => t.stage === "MIGRATED"),
    [filteredTokens]
  );

  const handleTokenTradeUpdate = (
    mint: string,
    isInvested: boolean,
    sizeSol: number,
    pnlPct: number
  ) => {
    setLiveTokens((prev) =>
      prev.map((t) =>
        t.mint === mint
          ? {
              ...t,
              isInvested,
              investedSizeSol: sizeSol,
              investedPnlPct: pnlPct,
            }
          : t
      )
    );
  };

  const handleQuickBuy = async (token: TrenchTokenEntry) => {
    const nextSize = Number(((token.investedSizeSol ?? 0) + quickBuySol).toFixed(2));
    const nextPnl = token.investedPnlPct ?? 6.25;
    handleTokenTradeUpdate(token.mint, true, nextSize, nextPnl);
    const res = await sendTitanIpcCommand("MANUAL_BUY_MINT", {
      mint: token.mint,
      symbol: token.symbol,
      pair: token.pair,
      amount_sol: quickBuySol,
      sol_amount: quickBuySol,
      price_usd: token.marketCapUsd / 1_000_000_000,
      venue: token.launchpad,
      horizon: token.bondingCurvePct < 100 ? "H1" : "H2",
      slippage_bps: 150,
    });
    onStatusMessage?.(
      res.message ||
        `⚡ [AXIOM/GMGN QUICK SNIPE] Bought ${quickBuySol} SOL of $${token.symbol} (${token.mint.slice(0, 6)}...)`
    );
  };

  const handleQuickSell = async (token: TrenchTokenEntry, pct: number) => {
    const baseSol = token.investedSizeSol ?? 2.5;
    const soldSol = Number(((baseSol * pct) / 100).toFixed(2));
    const remainingSol = pct >= 100 ? 0 : Number(Math.max(0.05, baseSol - soldSol).toFixed(2));
    const stillInvested = pct < 100 && remainingSol > 0;
    handleTokenTradeUpdate(
      token.mint,
      stillInvested,
      remainingSol,
      token.investedPnlPct ?? 18.4
    );
    const res = await sendTitanIpcCommand("PARTIAL_TAKE_PROFIT", {
      mint: token.mint,
      symbol: token.symbol,
      pair: token.pair,
      size_sol: baseSol,
      exit_pct: pct,
      fraction: pct / 100,
      reclaim_rent: pct >= 100,
    });
    onStatusMessage?.(
      res.message || `💰 Scaled out ${pct}% of $${token.symbol}`
    );
  };

  const activeSelectedToken = useMemo(() => {
    if (!selectedCoin) return null;
    return mergedTokens.find((t) => t.mint === selectedCoin.mint) ?? selectedCoin;
  }, [selectedCoin, mergedTokens]);

  const renderTrenchCoinCard = (t: TrenchTokenEntry) => {
    const catMeta = CATEGORY_META[t.category] ?? CATEGORY_META.MEME_CULT;
    return (
      <div
        key={t.mint}
        onClick={() => setSelectedCoin(t)}
        className={`p-2.5 rounded-xl border transition-all cursor-pointer ${
          t.isInvested
            ? "bg-gradient-to-r from-[#0c2135] to-[#091524] border-[#35e0b0] shadow-[0_0_14px_rgba(53,224,176,0.18)]"
            : t.isFreshArrival
            ? "bg-[#112438] border-[#5b9dff]"
            : "bg-[#0a1320]/95 border-[#1a2b42] hover:border-[#35e0b0]/60"
        }`}
      >
        <div className="flex items-start justify-between gap-2.5">
          {/* Left: Coin Picture + Age */}
          <div className="flex items-start gap-2.5 min-w-0">
            <div className="flex flex-col items-center gap-1 shrink-0">
              <CoinAvatarBadge
                symbolOrPair={t.symbol}
                mint={t.mint}
                size={42}
                isInvested={t.isInvested}
                bondingPct={t.bondingCurvePct}
              />
              <span className="text-[9px] font-mono font-bold text-[#35e0b0]">
                {formatAge(t.ageSeconds)}
              </span>
            </div>

            {/* Center: Ticker, Category, GMGN Micro-Audit Badges & Bonding Curve */}
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="font-extrabold text-white text-xs">
                  ${t.symbol}
                </span>
                <span className="text-[10px] text-[#869ab2] truncate max-w-[110px]">
                  {t.name}
                </span>
                <span className="px-1.5 py-0.5 rounded text-[8.5px] font-mono font-bold bg-[#5b9dff]/15 text-[#5b9dff] border border-[#5b9dff]/35">
                  {catMeta.badge}
                </span>
                {t.isInvested && (
                  <span className="px-1.5 py-0.5 rounded text-[8.5px] font-mono font-bold bg-[#35e0b0]/20 text-[#35e0b0]">
                    🟢 HELD
                  </span>
                )}
              </div>

              {/* Contract + Socials + DexPaid */}
              <div className="flex items-center gap-1.5 text-[9px] font-mono text-[#869ab2] mt-0.5">
                <span>
                  {t.mint.slice(0, 5)}..{t.mint.slice(-4)}
                </span>
                {t.dexPaid && (
                  <span className="text-[#35e0b0] font-bold">✓DexPaid</span>
                )}
                {t.hasSocials && <span className="text-[#5b9dff]">𝕏 TG 🌐</span>}
                <span className="text-[#a78bfa] font-bold">
                  🧠{t.kolSmartMoneyCount} KOL
                </span>
              </div>

              {/* GMGN Audit Pills: Top10 / Dev / Snipers / Bundles */}
              <div className="flex flex-wrap items-center gap-1 mt-1 text-[8.5px] font-mono">
                <span className="px-1.5 py-0.5 rounded bg-[#070e18] border border-[#1a2a40] text-[#dce6f2]">
                  T10:{" "}
                  <strong className="text-[#35e0b0]">
                    {t.top10HoldersPct}%
                  </strong>
                </span>
                <span className="px-1.5 py-0.5 rounded bg-[#070e18] border border-[#1a2a40] text-[#dce6f2]">
                  Dev:{" "}
                  <strong className="text-[#35e0b0]">{t.devAction}</strong>
                </span>
                <span className="px-1.5 py-0.5 rounded bg-[#070e18] border border-[#1a2a40] text-[#dce6f2]">
                  🎯{t.snipersPct}%
                </span>
                <span className="px-1.5 py-0.5 rounded bg-[#070e18] border border-[#1a2a40] text-[#dce6f2]">
                  🕵️{t.insidersBundlePct}%
                </span>
              </div>
            </div>
          </div>

          {/* Right: MCap, Vol & 1-Click Axiom Snipe Button */}
          <div
            className="text-right shrink-0 flex flex-col items-end justify-between"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="font-mono">
              <div className="text-[11px] font-extrabold text-white">
                MC ${(t.marketCapUsd / 1000).toFixed(1)}K
              </div>
              <div className="text-[9.5px] text-[#35e0b0]">
                V ${(t.volume5mUsd / 1000).toFixed(1)}K
              </div>
              <div className="text-[8.5px] text-[#869ab2]">
                <span className="text-[#35e0b0]">{t.txns5mBuys}B</span>/
                <span className="text-[#ef6069]">{t.txns5mSells}S</span>
              </div>
            </div>

            <button
              onClick={() => handleQuickBuy(t)}
              className="mt-1.5 px-2.5 py-1 rounded-md text-[9.5px] font-mono font-extrabold bg-[#35e0b0] text-[#05080f] hover:opacity-95 shadow-[0_0_10px_rgba(53,224,176,0.3)]"
            >
              ⚡ {quickBuySol} SOL
            </button>
          </div>
        </div>

        {/* Bottom Bonding Curve Bar */}
        <div className="mt-2 pt-1.5 border-t border-[#152336] flex items-center justify-between gap-2">
          <div className="flex-1 h-1.5 bg-[#060c15] rounded-full overflow-hidden">
            <div
              className={`h-full ${
                t.stage === "MIGRATED"
                  ? "bg-[#35e0b0]"
                  : t.stage === "FINAL_STRETCH"
                  ? "bg-gradient-to-r from-[#f2b33d] to-[#35e0b0]"
                  : "bg-[#5b9dff]"
              }`}
              style={{ width: `${Math.min(100, t.bondingCurvePct)}%` }}
            />
          </div>
          <span className="text-[9px] font-mono font-bold text-[#dce6f2] shrink-0">
            Curve {t.bondingCurvePct.toFixed(1)}%
          </span>
          <span className="px-1.5 py-0.5 rounded text-[8.5px] font-mono font-bold bg-[#35e0b0]/15 text-[#35e0b0] border border-[#35e0b0]/35 shrink-0">
            📊 Chart & Info
          </span>
        </div>
      </div>
    );
  };

  const activeSecurityFiltersCount = [
    filterGolden5Curve,
    filterDexPaid,
    filterDevClean,
    filterLowInsiders,
    filterLowSnipers,
    filterTop10Safe,
    filterMintRevoked,
    filterHasSocials,
    filterKolInflow,
  ].filter(Boolean).length;

  return (
    <div
      className="titan-panel border-[#233a57]"
      onMouseEnter={() => setHoverPaused(true)}
      onMouseLeave={() => setHoverPaused(false)}
    >
      {/* Header: Axiom.trade Pulse + GMGN.ai Trenches & Live Feed Controls */}
      <div className="titan-panel-header bg-gradient-to-r from-[#0a1829] via-[#0e2038] to-[#0a1829] flex-wrap gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#35e0b0]/20 text-[#35e0b0] border border-[#35e0b0]/50 flex items-center gap-1.5">
            <span
              className={
                streamEnabled && !hoverPaused ? "titan-led-on" : "titan-led-off"
              }
            />
            AXIOM.TRADE PULSE × GMGN.AI TRENCHES
          </span>
          <button
            type="button"
            onClick={() => setStreamEnabled((s) => !s)}
            className={`px-2 py-0.5 rounded text-[9.5px] font-mono font-bold border cursor-pointer ${
              streamEnabled
                ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]/60"
                : "bg-[#ef6069]/20 text-[#ef6069] border-[#ef6069]/60"
            }`}
          >
            LIVE STREAM: {streamEnabled ? "🟢 ON" : "🔴 OFF"}
            {hoverPaused && streamEnabled ? " (⏸ PAUSED)" : ""}
          </button>

          <button
            type="button"
            onClick={() =>
              setViewLayout((v) =>
                v === "THREE_COLUMN_PULSE" ? "TABLE" : "THREE_COLUMN_PULSE"
              )
            }
            className="px-2 py-0.5 rounded text-[9.5px] font-mono font-bold bg-[#101d2f] text-[#5b9dff] border border-[#5b9dff]/50 cursor-pointer"
          >
            {viewLayout === "THREE_COLUMN_PULSE"
              ? "📊 3-Col Pulse [🟢 ON]"
              : "📋 Table View [🟢 ON]"}
          </button>
        </div>

        {/* Clean View Toggle: All vs Invested Only vs 3-Column Trenches Only */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {(
            [
              {
                id: "ALL",
                label: "💎 Invested Coins + 3-Column Trenches (All)",
              },
              {
                id: "INVESTED_ONLY",
                label: `💎 Invested Coins Only (${investedCoins.length})`,
              },
              {
                id: "TRENCHES_ONLY",
                label: "🔥 3-Column Trenches Only (New / Graduating / Graduated)",
              },
            ] as const
          ).map((mode) => {
            const active = trenchSectionView === mode.id;
            return (
              <button
                key={mode.id}
                type="button"
                onClick={() => setTrenchSectionView(mode.id)}
                className={`px-2.5 py-1 rounded-md text-[10px] font-mono font-bold border transition-colors cursor-pointer ${
                  active
                    ? "bg-[#35e0b0]/25 text-[#35e0b0] border-[#35e0b0] shadow-[0_0_10px_rgba(53,224,176,0.2)]"
                    : "bg-[#0c1523] text-[#869ab2] border-[#1f324b] hover:text-white"
                }`}
              >
                {mode.label}
              </button>
            );
          })}
        </div>

        {/* Instant Quick-Buy SOL Amount Selector + Filter Drawer Toggle */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-mono text-[#869ab2] font-bold">
            ⚡ QUICK SNIPE:
          </span>
          {[0.5, 1.5, 3.0, 5.0].map((amt) => {
            const active = quickBuySol === amt;
            return (
              <button
                key={amt}
                type="button"
                onClick={() => setQuickBuySol(amt)}
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border cursor-pointer ${
                  active
                    ? "bg-[#35e0b0]/25 text-[#35e0b0] border-[#35e0b0]"
                    : "bg-[#0c1523] text-[#869ab2] border-[#1f324b] hover:text-white"
                }`}
              >
                {amt} SOL
              </button>
            );
          })}

          <span className="text-[#1f324b] mx-0.5">|</span>

          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="🔍 $TICKER / Mint..."
            className="px-2 py-0.5 rounded bg-[#060c15] border border-[#243854] text-[10px] font-mono text-white w-36 focus:outline-none focus:border-[#35e0b0]"
          />

          <button
            type="button"
            onClick={() => setShowFilterBar((prev) => !prev)}
            className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold border transition-colors cursor-pointer ${
              showFilterBar
                ? "bg-[#5b9dff]/25 text-[#5b9dff] border-[#5b9dff]"
                : "bg-[#0c1523] text-[#9fb3c8] border-[#243854] hover:text-white"
            }`}
          >
            🎛️ Filters ({activeSecurityFiltersCount} Active) [
            {showFilterBar ? "Hide ▲" : "Show ▼"}]
          </button>
        </div>
      </div>

      {/* 1. INVESTED COINS PICTURE SHOWCASE STRIP */}
      {trenchSectionView !== "TRENCHES_ONLY" && (
        <div className="px-3.5 py-2.5 bg-[#07101c]/90 border-b border-[#1a293d]">
          <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
            <span className="text-[10px] font-mono uppercase tracking-wider font-bold text-[#35e0b0]">
              🖼️ COINS CURRENTLY INVESTED IN ({investedCoins.length} ACTIVE PORTFOLIO POSITIONS WITH PICTURES)
            </span>
            <span className="text-[9.5px] font-mono text-[#869ab2]">
              📊 Click any token card to open Full Popup Chart &amp; Security Audit
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2.5">
            {investedCoins.map((coin) => {
              const pnlPositive = (coin.investedPnlPct ?? 0) >= 0;
              return (
                <div
                  key={coin.mint}
                  onClick={() => setSelectedCoin(coin)}
                  className="p-2.5 rounded-xl bg-gradient-to-r from-[#0c1b2e] to-[#091322] border border-[#35e0b0]/55 hover:border-[#35e0b0] flex items-center justify-between gap-3 cursor-pointer transition-all shadow-[0_0_16px_rgba(53,224,176,0.12)]"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <CoinAvatarBadge
                      symbolOrPair={coin.symbol}
                      mint={coin.mint}
                      size={46}
                      isInvested={true}
                      bondingPct={coin.bondingCurvePct}
                    />
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-white text-xs truncate">
                          ${coin.symbol}
                        </span>
                        <span className="text-[9.5px] font-mono text-[#869ab2] truncate">
                          {coin.name}
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[8.5px] font-mono font-bold bg-[#35e0b0]/20 text-[#35e0b0]">
                          🟢 INVESTED
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-[9.5px] font-mono text-[#9fb3c8] mt-0.5">
                        <span>
                          MC:{" "}
                          <strong className="text-white">
                            ${(coin.marketCapUsd / 1000).toFixed(1)}K
                          </strong>
                        </span>
                        <span>
                          Curve:{" "}
                          <strong className="text-[#35e0b0]">
                            {coin.bondingCurvePct.toFixed(1)}%
                          </strong>
                        </span>
                        <span>
                          Top10:{" "}
                          <strong className="text-[#5b9dff]">
                            {coin.top10HoldersPct}%
                          </strong>
                        </span>
                      </div>
                    </div>
                  </div>

                  <div
                    className="text-right shrink-0"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="text-[11px] font-mono font-bold text-white">
                      {privacyMode
                        ? "••• SOL"
                        : `${(coin.investedSizeSol ?? 2.5).toFixed(2)} SOL`}
                    </div>
                    <div
                      className={`text-xs font-mono font-extrabold ${
                        pnlPositive ? "text-[#35e0b0]" : "text-[#ef6069]"
                      }`}
                    >
                      {pnlPositive ? "+" : ""}
                      {(coin.investedPnlPct ?? 0).toFixed(2)}%
                    </div>
                    <div className="flex items-center justify-end gap-1 mt-1">
                      <button
                        type="button"
                        onClick={() => handleQuickBuy(coin)}
                        className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-[#35e0b0]/20 text-[#35e0b0] border border-[#35e0b0]/50 cursor-pointer"
                      >
                        +{quickBuySol}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleQuickSell(coin, 50)}
                        className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-[#5b9dff]/20 text-[#5b9dff] border border-[#5b9dff]/50 cursor-pointer"
                      >
                        TP 50%
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 2. COLLAPSIBLE NARRATIVE CATEGORIES + AXIOM/GMGN SECURITY FILTER BAR */}
      {showFilterBar && (
        <div className="p-3 bg-[#091320]/90 border-b border-[#1a293d] space-y-2">
          {/* Narrative Category Tabs (AI Agents, Memes, Animals, PolitiFi, DeFi, Gaming, Invested) */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-1 flex-wrap">
              {(
                [
                  "ALL",
                  "INVESTED",
                  "AI_AGENTS",
                  "MEME_CULT",
                  "ANIMALS",
                  "POLITIFI_VIRAL",
                  "DEFI_INFRA",
                  "GAMING",
                ] as const
              ).map((cat) => {
                const active = selectedCategory === cat;
                return (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    className={`px-2.5 py-1 rounded-md text-[10px] font-mono font-bold border flex items-center gap-1.5 cursor-pointer ${
                      active
                        ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]"
                        : "bg-[#0d1726] text-[#869ab2] border-[#1d3048] hover:text-white"
                    }`}
                  >
                    <span>{CATEGORY_META[cat].label}</span>
                    <span className="text-[8.5px]">
                      [{active ? "🟢 ON" : "OFF"}]
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Launchpad Filter */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {(
                [
                  "ALL",
                  "PUMP",
                  "PUMPSWAP",
                  "METEORA",
                  "RAYDIUM",
                  "BELIEVE",
                ] as const
              ).map((pad) => {
                const active = launchpadFilter === pad;
                return (
                  <button
                    key={pad}
                    type="button"
                    onClick={() => setLaunchpadFilter(pad)}
                    className={`px-2 py-0.5 rounded text-[9.5px] font-mono font-bold border cursor-pointer ${
                      active
                        ? "bg-[#5b9dff]/20 text-[#5b9dff] border-[#5b9dff]"
                        : "bg-[#0c1523] text-[#869ab2] border-[#1d3048]"
                    }`}
                  >
                    {pad} [{active ? "🟢 ON" : "OFF"}]
                  </button>
                );
              })}
            </div>
          </div>

          {/* Axiom.trade & GMGN.ai Toggleable Security & Forensics Filters */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <span className="text-[9.5px] font-mono uppercase tracking-wider text-[#5b9dff] font-bold mr-1">
              🎛️ AXIOM / GMGN FILTERS:
            </span>
            {[
              {
                label: "🔥 Curve >=65% (Golden 5)",
                val: filterGolden5Curve,
                toggle: () => setFilterGolden5Curve((v) => !v),
              },
              {
                label: "⚡ DexPaid",
                val: filterDexPaid,
                toggle: () => setFilterDexPaid((v) => !v),
              },
              {
                label: "👨‍💻 Dev <=2%",
                val: filterDevClean,
                toggle: () => setFilterDevClean((v) => !v),
              },
              {
                label: "🕵️ Bundles <=15%",
                val: filterLowInsiders,
                toggle: () => setFilterLowInsiders((v) => !v),
              },
              {
                label: "🎯 Snipers <=12%",
                val: filterLowSnipers,
                toggle: () => setFilterLowSnipers((v) => !v),
              },
              {
                label: "🐋 Top10 <=25%",
                val: filterTop10Safe,
                toggle: () => setFilterTop10Safe((v) => !v),
              },
              {
                label: "🔒 Auth Revoked",
                val: filterMintRevoked,
                toggle: () => setFilterMintRevoked((v) => !v),
              },
              {
                label: "🌐 Socials",
                val: filterHasSocials,
                toggle: () => setFilterHasSocials((v) => !v),
              },
              {
                label: "🧠 KOL >=2",
                val: filterKolInflow,
                toggle: () => setFilterKolInflow((v) => !v),
              },
            ].map((f) => (
              <button
                key={f.label}
                type="button"
                onClick={f.toggle}
                className={`px-2 py-0.5 rounded-md text-[9.5px] font-mono font-bold border flex items-center gap-1 cursor-pointer ${
                  f.val
                    ? "bg-[#35e0b0]/18 text-[#35e0b0] border-[#35e0b0]/60"
                    : "bg-[#140d14]/80 text-[#9fb3c8] border-[#ef6069]/40"
                }`}
              >
                <span className={f.val ? "titan-led-on" : "titan-led-off"} />
                <span>{f.label}:</span>
                <span className={f.val ? "text-[#35e0b0]" : "text-[#ef6069]"}>
                  {f.val ? "🟢 ON" : "🔴 OFF"}
                </span>
              </button>
            ))}

            <div className="flex items-center gap-1 ml-auto">
              <span className="text-[9.5px] font-mono text-[#869ab2]">
                Min MC:
              </span>
              {[0, 30, 50, 100].map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setMinMcapK(k)}
                  className={`px-1.5 py-0.5 rounded text-[9px] font-mono font-bold border cursor-pointer ${
                    minMcapK === k
                      ? "bg-[#35e0b0]/20 text-[#35e0b0] border-[#35e0b0]"
                      : "bg-[#0c1523] text-[#869ab2] border-[#1d3048]"
                  }`}
                >
                  {k === 0 ? "ALL" : `>$${k}K`} [{minMcapK === k ? "🟢 ON" : "OFF"}]
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 3. 3-COLUMN AXIOM PULSE / GMGN TRENCHES STREAMING VIEW */}
      {trenchSectionView !== "INVESTED_ONLY" &&
        (viewLayout === "THREE_COLUMN_PULSE" ? (
          <div className="p-3 grid grid-cols-1 lg:grid-cols-3 gap-3 bg-[#060b13]">
            {/* COLUMN 1: NEW PAIRS / NEW CREATIONS */}
            <div className="rounded-xl border border-[#1d3048] bg-[#08101c] overflow-hidden flex flex-col">
              <div className="px-3 py-2 bg-[#0c1829] border-b border-[#1d3048] flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="titan-led-on" />
                  <span className="text-[11px] font-mono font-extrabold text-[#5b9dff] uppercase">
                    🌱 NEW CREATIONS (0%–64%)
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded text-[9.5px] font-mono font-bold bg-[#5b9dff]/15 text-[#5b9dff]">
                  {newPairCoins.length} Incoming
                </span>
              </div>
              <div className="p-2.5 space-y-2.5 max-h-[520px] overflow-y-auto">
                {newPairCoins.map(renderTrenchCoinCard)}
              </div>
            </div>

            {/* COLUMN 2: FINAL STRETCH (65% - 84.5% GOLDEN 5 SQUEEZE) */}
            <div className="rounded-xl border border-[#f2b33d]/50 bg-[#08101c] overflow-hidden flex flex-col">
              <div className="px-3 py-2 bg-[#161922] border-b border-[#f2b33d]/40 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="titan-led-on" />
                  <span className="text-[11px] font-mono font-extrabold text-[#f2b33d] uppercase">
                    🔥 FINAL STRETCH (65%–84.5% GOLDEN 5)
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded text-[9.5px] font-mono font-bold bg-[#f2b33d]/20 text-[#f2b33d]">
                  {finalStretchCoins.length} Squeezing
                </span>
              </div>
              <div className="p-2.5 space-y-2.5 max-h-[520px] overflow-y-auto">
                {finalStretchCoins.map(renderTrenchCoinCard)}
              </div>
            </div>

            {/* COLUMN 3: MIGRATED TO PUMPSWAP / RAYDIUM (84.5 SOL SLOT-0) */}
            <div className="rounded-xl border border-[#35e0b0]/55 bg-[#08101c] overflow-hidden flex flex-col">
              <div className="px-3 py-2 bg-[#0b2027] border-b border-[#35e0b0]/40 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="titan-led-on" />
                  <span className="text-[11px] font-mono font-extrabold text-[#35e0b0] uppercase">
                    🚀 MIGRATED (PUMPSWAP / RAYDIUM)
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded text-[9.5px] font-mono font-bold bg-[#35e0b0]/20 text-[#35e0b0]">
                  {migratedCoins.length} Graduated
                </span>
              </div>
              <div className="p-2.5 space-y-2.5 max-h-[520px] overflow-y-auto">
                {migratedCoins.map(renderTrenchCoinCard)}
              </div>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="titan-table">
              <thead>
                <tr>
                  <th>Coin / Picture</th>
                  <th>Category & Stage</th>
                  <th>MCap & Liq</th>
                  <th>5m Vol & Txns</th>
                  <th>GMGN Audit (Top10 / Dev / Snipers / Bundles)</th>
                  <th>KOLs & BlueChip</th>
                  <th className="text-right">Axiom 1-Click Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredTokens.map((t) => (
                  <tr
                    key={t.mint}
                    onClick={() => setSelectedCoin(t)}
                    className="cursor-pointer"
                  >
                    <td>
                      <div className="flex items-center gap-2.5">
                        <CoinAvatarBadge
                          symbolOrPair={t.symbol}
                          mint={t.mint}
                          size={38}
                          isInvested={t.isInvested}
                          bondingPct={t.bondingCurvePct}
                        />
                        <div>
                          <div className="font-bold text-white text-xs">
                            ${t.symbol} ·{" "}
                            <span className="text-[#35e0b0] font-mono">
                              {formatAge(t.ageSeconds)}
                            </span>
                          </div>
                          <div className="text-[10px] text-[#869ab2]">
                            {t.name}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="font-mono text-[10px]">
                      <span className="text-[#5b9dff] font-bold">
                        {(CATEGORY_META[t.category] ?? CATEGORY_META.MEME_CULT).badge}
                      </span>{" "}
                      · {t.stage} ({t.bondingCurvePct.toFixed(1)}%)
                    </td>
                    <td className="font-mono font-bold text-white">
                      ${(t.marketCapUsd / 1000).toFixed(1)}K
                    </td>
                    <td className="font-mono text-[#35e0b0]">
                      ${(t.volume5mUsd / 1000).toFixed(1)}K
                    </td>
                    <td className="font-mono text-[10px] text-[#dce6f2]">
                      T10: {t.top10HoldersPct}% · Dev: {t.devAction} · Snipers:{" "}
                      {t.snipersPct}% · Bundles: {t.insidersBundlePct}%
                    </td>
                    <td className="font-mono text-[10px] text-[#a78bfa]">
                      🧠 {t.kolSmartMoneyCount} KOLs · BC {t.bluechipIndexPct}%
                    </td>
                    <td
                      className="text-right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        type="button"
                        onClick={() => handleQuickBuy(t)}
                        className="px-2.5 py-1 rounded bg-[#35e0b0] text-[#05080f] font-mono font-bold text-[10px] cursor-pointer"
                      >
                        ⚡ Snipe {quickBuySol} SOL
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

      {/* Full Centered Popup Display Modal with Live Chart & All Token Information */}
      <TokenDetailChartModal
        token={activeSelectedToken}
        solUsd={frame.sol_usd}
        onClose={() => setSelectedCoin(null)}
        onStatusMessage={onStatusMessage}
        onPinToChart1={onPinToChart1}
        onPinToChart2={onPinToChart2}
        onTokenTradeUpdate={handleTokenTradeUpdate}
      />
    </div>
  );
};
