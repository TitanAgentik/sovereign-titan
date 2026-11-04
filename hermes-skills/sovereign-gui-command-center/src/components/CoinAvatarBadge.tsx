import React from "react";

export interface CoinVisualSpec {
  symbol: string;
  name: string;
  bgGradient: [string, string];
  accentColor: string;
  launchpad: "PUMP" | "PUMPSWAP" | "METEORA" | "RAYDIUM" | "BELIEVE";
  iconType:
    | "ROBOT"
    | "BRAIN"
    | "SHARK"
    | "WOLF"
    | "FROG"
    | "ROCKET"
    | "DIAMOND"
    | "BOLT";
}

const KNOWN_COINS: Record<string, CoinVisualSpec> = {
  TITAN: {
    symbol: "TITAN",
    name: "Sovereign Titan AI",
    bgGradient: ["#0d3b2e", "#071a2c"],
    accentColor: "#35e0b0",
    launchpad: "PUMPSWAP",
    iconType: "ROBOT",
  },
  NEURAL: {
    symbol: "NEURAL",
    name: "NeuralNet Solana",
    bgGradient: ["#16284c", "#0b132b"],
    accentColor: "#5b9dff",
    launchpad: "PUMP",
    iconType: "BRAIN",
  },
  SOLAI: {
    symbol: "SOLAI",
    name: "Solana Autonomous Agent",
    bgGradient: ["#2d1b4e", "#110a26"],
    accentColor: "#a78bfa",
    launchpad: "PUMPSWAP",
    iconType: "BOLT",
  },
  SHARK: {
    symbol: "SHARK",
    name: "Apex Liquidation Shark",
    bgGradient: ["#0c2d3e", "#061520"],
    accentColor: "#38bdf8",
    launchpad: "RAYDIUM",
    iconType: "SHARK",
  },
  QUANT: {
    symbol: "QUANT",
    name: "Zero-Slot Quant",
    bgGradient: ["#3b2a10", "#1a1206"],
    accentColor: "#f2b33d",
    launchpad: "METEORA",
    iconType: "DIAMOND",
  },
  PEPE26: {
    symbol: "PEPE26",
    name: "Cyber Pepe 2026",
    bgGradient: ["#0f3d23", "#061c10"],
    accentColor: "#4ade80",
    launchpad: "PUMP",
    iconType: "FROG",
  },
  WIFAI: {
    symbol: "WIFAI",
    name: "DogWifAI Agent",
    bgGradient: ["#3d1c2e", "#1c0b14"],
    accentColor: "#f472b6",
    launchpad: "PUMP",
    iconType: "WOLF",
  },
  ALPEN: {
    symbol: "ALPEN",
    name: "Alpenglow 200ms",
    bgGradient: ["#123548", "#081924"],
    accentColor: "#2dd4bf",
    launchpad: "PUMPSWAP",
    iconType: "ROCKET",
  },
  QWEN: {
    symbol: "QWEN",
    name: "Qwen Vision Sniper",
    bgGradient: ["#2b1947", "#120921"],
    accentColor: "#c084fc",
    launchpad: "BELIEVE",
    iconType: "BRAIN",
  },
};

function hashTicker(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

export function resolveCoinVisual(
  symbolOrPair: string,
  mint?: string
): CoinVisualSpec {
  const clean = symbolOrPair
    .replace("/SOL", "")
    .replace("$", "")
    .trim()
    .toUpperCase();
  if (KNOWN_COINS[clean]) {
    return KNOWN_COINS[clean];
  }
  const h = hashTicker(clean + (mint || ""));
  const palettes: Array<[string, string, string]> = [
    ["#0d3b2e", "#071a2c", "#35e0b0"],
    ["#16284c", "#0b132b", "#5b9dff"],
    ["#2d1b4e", "#110a26", "#a78bfa"],
    ["#3b2a10", "#1a1206", "#f2b33d"],
    ["#0f3d23", "#061c10", "#4ade80"],
    ["#3d1c2e", "#1c0b14", "#f472b6"],
  ];
  const icons: CoinVisualSpec["iconType"][] = [
    "ROBOT",
    "BRAIN",
    "SHARK",
    "WOLF",
    "FROG",
    "ROCKET",
    "DIAMOND",
    "BOLT",
  ];
  const pads: CoinVisualSpec["launchpad"][] = [
    "PUMP",
    "PUMPSWAP",
    "METEORA",
    "RAYDIUM",
    "BELIEVE",
  ];
  const pal = palettes[h % palettes.length];
  return {
    symbol: clean || "TOKEN",
    name: `${clean || "Solana"} Token`,
    bgGradient: [pal[0], pal[1]],
    accentColor: pal[2],
    launchpad: pads[h % pads.length],
    iconType: icons[h % icons.length],
  };
}

interface CoinAvatarBadgeProps {
  symbolOrPair: string;
  mint?: string;
  size?: number;
  isInvested?: boolean;
  bondingPct?: number;
  imageUrl?: string;
}

export const CoinAvatarBadge: React.FC<CoinAvatarBadgeProps> = ({
  symbolOrPair,
  mint,
  size = 38,
  isInvested = false,
  bondingPct,
  imageUrl,
}) => {
  const spec = resolveCoinVisual(symbolOrPair, mint);
  const gradId = `coin-grad-${spec.symbol}-${size}`;

  const renderArtwork = () => {
    const c = spec.accentColor;
    switch (spec.iconType) {
      case "ROBOT":
        return (
          <g stroke={c} strokeWidth="1.8" fill="none">
            <rect
              x="10"
              y="12"
              width="20"
              height="16"
              rx="4"
              fill="rgba(53,224,176,0.16)"
            />
            <line x1="20" y1="6" x2="20" y2="12" />
            <circle cx="20" cy="5.5" r="1.8" fill={c} />
            <circle cx="15.5" cy="19" r="2" fill={c} />
            <circle cx="24.5" cy="19" r="2" fill={c} />
            <line x1="15" y1="24" x2="25" y2="24" />
          </g>
        );
      case "BRAIN":
        return (
          <g stroke={c} strokeWidth="1.7" fill="none">
            <path
              d="M14,27 C10,27 9,22 11,19 C9,15 12,11 16,12 C18,9 22,9 24,12 C28,11 31,15 29,19 C31,22 30,27 26,27 Z"
              fill="rgba(91,157,255,0.18)"
            />
            <line x1="20" y1="11" x2="20" y2="27" />
            <circle cx="15" cy="18" r="1.5" fill={c} />
            <circle cx="25" cy="18" r="1.5" fill={c} />
          </g>
        );
      case "FROG":
        return (
          <g stroke={c} strokeWidth="1.7" fill="none">
            <ellipse
              cx="20"
              cy="22"
              rx="10"
              ry="7"
              fill="rgba(74,222,128,0.2)"
            />
            <circle cx="14" cy="14" r="3.5" fill="#071a12" />
            <circle cx="26" cy="14" r="3.5" fill="#071a12" />
            <circle cx="14" cy="14" r="1.4" fill={c} />
            <circle cx="26" cy="14" r="1.4" fill={c} />
            <path d="M14,23 Q20,27 26,23" />
          </g>
        );
      case "WOLF":
        return (
          <g stroke={c} strokeWidth="1.7" fill="none">
            <polygon
              points="11,10 15,17 25,17 29,10 28,25 20,30 12,25"
              fill="rgba(244,114,182,0.18)"
            />
            <circle cx="16" cy="21" r="1.5" fill={c} />
            <circle cx="24" cy="21" r="1.5" fill={c} />
            <polygon points="18,25 22,25 20,27.5" fill={c} />
          </g>
        );
      case "SHARK":
        return (
          <g stroke={c} strokeWidth="1.7" fill="none">
            <path
              d="M9,25 Q18,10 23,11 Q21,17 25,21 Q30,22 31,25 Q20,28 9,25 Z"
              fill="rgba(56,189,248,0.2)"
            />
            <circle cx="24" cy="21" r="1.3" fill={c} />
          </g>
        );
      case "DIAMOND":
        return (
          <g stroke={c} strokeWidth="1.7" fill="none">
            <polygon
              points="14,11 26,11 31,17 20,30 9,17"
              fill="rgba(242,179,61,0.2)"
            />
            <line x1="9" y1="17" x2="31" y2="17" />
          </g>
        );
      case "ROCKET":
        return (
          <g stroke={c} strokeWidth="1.7" fill="none">
            <path
              d="M20,9 C25,14 26,21 24,26 L16,26 C14,21 15,14 20,9 Z"
              fill="rgba(45,212,191,0.2)"
            />
            <circle cx="20" cy="18" r="2" fill={c} />
            <path d="M16,26 L13,30 M24,26 L27,30" />
          </g>
        );
      default:
        return (
          <g stroke={c} strokeWidth="1.8" fill="none">
            <polygon
              points="22,8 12,21 19,21 17,31 28,18 21,18"
              fill="rgba(167,139,250,0.24)"
            />
          </g>
        );
    }
  };

  const padBadge =
    spec.launchpad === "PUMP"
      ? { icon: "💊", bg: "#35e0b0" }
      : spec.launchpad === "PUMPSWAP"
      ? { icon: "🚀", bg: "#5b9dff" }
      : spec.launchpad === "METEORA"
      ? { icon: "☄️", bg: "#f2b33d" }
      : spec.launchpad === "RAYDIUM"
      ? { icon: "⚡", bg: "#38bdf8" }
      : { icon: "🦅", bg: "#a78bfa" };

  return (
    <div
      className="relative inline-flex items-center justify-center shrink-0 select-none"
      style={{ width: size, height: size }}
      title={`${spec.name} ($${spec.symbol}) · Launchpad: ${spec.launchpad}${
        bondingPct !== undefined ? ` · Curve: ${bondingPct.toFixed(1)}%` : ""
      }`}
    >
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={spec.symbol}
          className="w-full h-full rounded-xl object-cover border"
          style={{
            borderColor: isInvested ? "#35e0b0" : spec.accentColor,
            boxShadow: isInvested
              ? "0 0 12px rgba(53, 224, 176, 0.45)"
              : "none",
          }}
        />
      ) : (
        <svg
          viewBox="0 0 40 40"
          className="w-full h-full rounded-xl overflow-hidden"
          style={{
            boxShadow: isInvested
              ? "0 0 12px rgba(53, 224, 176, 0.4)"
              : "0 2px 8px rgba(0, 0, 0, 0.5)",
          }}
        >
          <defs>
            <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={spec.bgGradient[0]} />
              <stop offset="100%" stopColor={spec.bgGradient[1]} />
            </linearGradient>
          </defs>
          <rect
            x="1"
            y="1"
            width="38"
            height="38"
            rx="9"
            fill={`url(#${gradId})`}
            stroke={isInvested ? "#35e0b0" : spec.accentColor}
            strokeWidth={isInvested ? "2" : "1.3"}
          />
          {renderArtwork()}
          <text
            x="20"
            y="36"
            textAnchor="middle"
            fill="#e2edf8"
            fontSize="6.2"
            fontFamily="monospace"
            fontWeight="bold"
          >
            ${spec.symbol.slice(0, 5)}
          </text>
        </svg>
      )}

      {/* Launchpad Corner Pill */}
      <span
        className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center text-[8.5px] border border-[#05080f] shadow"
        style={{ backgroundColor: "#0b1422", borderColor: padBadge.bg }}
      >
        {padBadge.icon}
      </span>

      {/* Invested Green Dot */}
      {isInvested && (
        <span
          className="absolute -top-1 -left-1 w-3 h-3 rounded-full bg-[#35e0b0] border border-[#05080f] flex items-center justify-center text-[7px] font-bold text-[#05080f]"
          title="Currently Invested Position"
        >
          ✓
        </span>
      )}
    </div>
  );
};
