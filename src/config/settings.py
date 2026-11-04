"""Sovereign Titan OS — Pydantic Settings & Architectural Invariant Validator.

Validates all Paid 4 APIs, Free 7 APIs/Streams, Telegram MTProto credentials,
Threadripper PRO 9995WX Core/RAMDisk partitions, Alpenglow 200ms / Jito BAM 25ms
timing rules, and 4-Lane Local LLM Swarm endpoints.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


WORKSPACE_ROOT = Path("/home/titanagentik/sovereign-titan")


class Settings(BaseSettings):
    """Production configuration and invariant enforcement for Sovereign Titan OS."""

    model_config = SettingsConfigDict(
        env_file=(str(WORKSPACE_ROOT / ".env.example"), str(WORKSPACE_ROOT / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --------------------------------------------------------------------------
    # 1. Paid Core 4 APIs
    # --------------------------------------------------------------------------
    HELIUS_API_KEY: str = Field(
        default="YOUR_HELIUS_BUSINESS_API_KEY",
        description="Helius Business tier key (preconfSubscribe, LaserStream gRPC, Enhanced Webhooks, Helius Sender, DAS RPC)",
    )
    HELIUS_RPC_URL: str = Field(
        default="https://mainnet.helius-rpc.com/?api-key=YOUR_HELIUS_BUSINESS_API_KEY"
    )
    HELIUS_GATEKEEPER_RPC_URL: str = Field(
        default="https://beta.helius-rpc.com/?api-key=YOUR_HELIUS_BUSINESS_API_KEY"
    )
    HELIUS_WS_URL: str = Field(
        default="wss://mainnet.helius-rpc.com/?api-key=YOUR_HELIUS_BUSINESS_API_KEY"
    )
    HELIUS_LASERSTREAM_GRPC_URL: str = Field(
        default="https://laserstream-mainnet-ny.helius-rpc.com:443"
    )
    HELIUS_SENDER_URL: str = Field(
        default="https://sender.helius-rpc.com/fast"
    )
    HELIUS_ENHANCED_WEBHOOK_SECRET: str = Field(
        default="YOUR_HELIUS_WEBHOOK_HMAC_SECRET"
    )
    HELIUS_MCP_URL: str = Field(default="http://127.0.0.1:8090/sse")

    BIRDEYE_API_KEY: str = Field(
        default="YOUR_BIRDEYE_PRO_API_KEY",
        description="Birdeye Paid REST + dev-mcp.birdeye.so key",
    )
    BIRDEYE_REST_URL: str = Field(default="https://public-api.birdeye.so")
    BIRDEYE_MCP_URL: str = Field(default="https://dev-mcp.birdeye.so/sse")

    JUPITER_API_KEY: str = Field(
        default="YOUR_JUPITER_V2_PAID_API_KEY",
        description="Jupiter Swap API V2 paid high-RPS tier key",
    )
    JUPITER_SWAP_V2_URL: str = Field(default="https://api.jup.ag/swap/v2")
    JUPITER_MCP_URL: str = Field(default="http://127.0.0.1:8091/sse")

    SOCIALDATA_API_KEY: str = Field(
        default="YOUR_SOCIALDATA_API_KEY",
        description="SocialData X/Twitter CA velocity & influencer scraper key",
    )
    SOCIALDATA_API_URL: str = Field(default="https://api.socialdata.tools")

    # --------------------------------------------------------------------------
    # 2. Free 7 APIs & Real-Time Streams + Telegram MTProto
    # --------------------------------------------------------------------------
    RUGCHECK_SUMMARY_URL_TEMPLATE: str = Field(
        default="https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary"
    )
    GOPLUS_API_KEY: str = Field(default="YOUR_GOPLUS_FREE_API_KEY")
    GOPLUS_SOLANA_SECURITY_URL: str = Field(
        default="https://api.gopluslabs.io/api/v1/solana/token_security"
    )
    DEXSCREENER_BOOSTS_URL: str = Field(
        default="https://api.dexscreener.com/token-boosts/latest/v1"
    )
    DEXSCREENER_ORDERS_URL_TEMPLATE: str = Field(
        default="https://api.dexscreener.com/orders/v1/solana/{mint}"
    )
    DEXSCREENER_TOKENS_URL_TEMPLATE: str = Field(
        default="https://api.dexscreener.com/latest/dex/tokens/{mint}"
    )
    PUMPPORTAL_WS_URL: str = Field(default="wss://pumpportal.fun/api/data")
    GECKOTERMINAL_API_URL: str = Field(
        default="https://api.geckoterminal.com/api/v2/networks/solana"
    )
    JITO_TIP_STREAM_WS_URL: str = Field(
        default="wss://bundles-api-rest.jito.wtf/api/v1/bundles/tip_stream"
    )
    JITO_NY_BLOCK_ENGINE_URL: str = Field(
        default="https://ny.mainnet.block-engine.jito.wtf/api/v1/bundles"
    )
    JITO_FRANKFURT_BLOCK_ENGINE_URL: str = Field(
        default="https://frankfurt.mainnet.block-engine.jito.wtf/api/v1/bundles"
    )
    JITO_AMSTERDAM_BLOCK_ENGINE_URL: str = Field(
        default="https://amsterdam.mainnet.block-engine.jito.wtf/api/v1/bundles"
    )
    JITO_TOKYO_BLOCK_ENGINE_URL: str = Field(
        default="https://tokyo.mainnet.block-engine.jito.wtf/api/v1/bundles"
    )
    ASTRALANE_DISPATCH_URL: str = Field(
        default="https://ny.gateway.astralane.io/iris"
    )
    COINSTATS_API_KEY: str = Field(default="YOUR_COINSTATS_FREE_API_KEY")
    COINSTATS_REST_URL: str = Field(default="https://openapiv1.coinstats.app")
    COINSTATS_MCP_URL: str = Field(default="https://mcp.coinstats.app/sse")

    # Telegram MTProto & Alert Bot
    TELEGRAM_API_ID: int = Field(default=12345678)
    TELEGRAM_API_HASH: str = Field(default="0123456789abcdef0123456789abcdef")
    TELEGRAM_SESSION_PATH: str = Field(
        default="/mnt/ramdisk/execution_state/titan_telethon.session"
    )
    TELEGRAM_MONITORED_CHANNELS: str = Field(
        default="solana_trench_alpha,pump_migrations_live,whale_shadow_feed"
    )
    TELEGRAM_BOT_TOKEN: str = Field(
        default="0000000000:AAH_YOUR_PERSONAL_ALERT_BOT_TOKEN"
    )
    TELEGRAM_CHAT_ID: str = Field(default="-1001234567890")

    # --------------------------------------------------------------------------
    # 3. Hardware, Protocol Timing & Capital Defaults
    # --------------------------------------------------------------------------
    PRIMARY_NIC_INTERFACE: str = Field(default="enp210s0f0np0")
    INITIAL_EXECUTION_MODE: Literal["PAPER", "CANARY", "LIVE"] = Field(default="PAPER")
    INITIAL_PAPER_SOL: float = Field(default=25.0, gt=0.0)
    WITHDRAW_ADDRESS: str = Field(default="DEFERRED")
    ENABLE_BAM_DBI: bool = Field(default=False)
    MAX_VERSIONED_TX_ACCOUNTS: int = Field(default=64)
    AGAVE_45_MAX_TX_ACCOUNTS: int = Field(default=96)
    MAX_TX_SIZE_BYTES: int = Field(default=1150, le=1232)
    SOLANA_MTU_LIMIT_BYTES: int = Field(default=1232)

    # Solana Alpenglow & Jito BAM Timing Invariants
    ALPENGLOW_SLOT_MS: int = Field(default=200)
    JITO_BAM_TICK_MS: int = Field(default=25)
    JITO_DONT_FRONT_PUBKEY: str = Field(
        default="jitodontfront111111111111111111111111111111"
    )
    ATA_RENT_RECLAIM_SOL: float = Field(default=0.00203928)
    ENGINE_C_UNLOCK_PROFIT_SOL: float = Field(default=100.0)

    # Two-Tranche Hot-Path Execution Thresholds
    SCOUT_TRANCHE_RATIO: float = Field(default=0.25)
    CONVICTION_TRANCHE_RATIO: float = Field(default=0.75)
    SCOUT_MAX_LATENCY_MS: float = Field(default=2.0)

    # --------------------------------------------------------------------------
    # 4. 128GB DDR5 RAMDisk Partition Paths
    # --------------------------------------------------------------------------
    RAMDISK_ROOT: Path = Field(default=Path("/mnt/ramdisk"))
    RAMDISK_ALPHA_GRAPH: Path = Field(default=Path("/mnt/ramdisk/alpha_graph"))
    RAMDISK_MEV_POOL_MIRROR: Path = Field(default=Path("/mnt/ramdisk/mev_pool_mirror"))
    RAMDISK_PRE_APPROVED_TOKENS: Path = Field(
        default=Path("/mnt/ramdisk/pre_approved_tokens")
    )
    RAMDISK_IMAGE_PHASH_INDEX: Path = Field(
        default=Path("/mnt/ramdisk/image_phash_index")
    )
    RAMDISK_EXECUTION_STATE: Path = Field(
        default=Path("/mnt/ramdisk/execution_state")
    )
    TITAN_IPC_SOCKET: Path = Field(default=Path("/mnt/ramdisk/titan_ipc.sock"))
    PRE_APPROVED_TOKEN_TTL_SEC: int = Field(default=120, gt=0)

    # --------------------------------------------------------------------------
    # 5. 4-Lane Local LLM Swarm Endpoints & Circuit Breakers (Live Onboard Fleet)
    # --------------------------------------------------------------------------
    LLM_GATEKEEPER_URL: str = Field(default="http://127.0.0.1:8005/v1")
    LLM_GATEKEEPER_MODEL: str = Field(default="hermes3-8b-awq")
    LLM_GATEKEEPER_TIMEOUT_MS: float = Field(default=45.0, le=45.0, gt=0.0)

    LLM_VISION_URL: str = Field(default="http://127.0.0.1:8002/v1")
    LLM_VISION_MODEL: str = Field(
        default="Huihui-Qwen3.8-27B-abliterated-bf16"
    )
    LLM_VISION_TIMEOUT_MS: float = Field(default=15000.0, gt=0.0)

    LLM_DEEP_REASONER_URL: str = Field(default="http://127.0.0.1:8002/v1")
    LLM_DEEP_REASONER_MODEL: str = Field(default="Huihui-Qwen3.8-27B-abliterated-bf16")
    LLM_DEEP_REASONER_TIMEOUT_MS: float = Field(default=30000.0, gt=0.0)

    LLM_FAST_L3_URL: str = Field(default="http://127.0.0.1:8006/v1")
    LLM_FAST_L3_MODEL: str = Field(default="qwen2.5-3b")
    LLM_FAST_L3_TIMEOUT_MS: float = Field(default=25.0, gt=0.0)

    LLM_EMBED_URL: str = Field(default="http://127.0.0.1:8007")
    LLM_EMBED_MODEL: str = Field(default="BGE-M3")
    LLM_RERANK_MODEL: str = Field(default="bge-reranker-v2")
    LLM_EMBED_TIMEOUT_MS: float = Field(default=2000.0, gt=0.0)

    # --------------------------------------------------------------------------
    # 6. Live Mainnet Broadcast, Keystore, Jito SLC, Drift, Polymarket & x402
    # --------------------------------------------------------------------------
    LIVE_MAINNET_BROADCAST_ENABLED: bool = Field(default=False)
    TITAN_KEYSTORE_PASSPHRASE: str = Field(
        default="SOVEREIGN_TITAN_BLACKWELL_9995WX_KEYRING"
    )
    PROFIT_GUARD_PROGRAM_ID: str = Field(
        default="PrftGrd111111111111111111111111111111111111"
    )
    MAINNET_ALT_ADDRESS: str = Field(default="")
    JITO_SLC_BLOCK_ENGINE_URL: str = Field(
        default="https://slc.mainnet.block-engine.jito.wtf/api/v1/bundles"
    )
    JITO_BLOCK_ENGINE_AUTH_KEYPAIR_PATH: str = Field(default="")
    DRIFT_MAINNET_SUBACCOUNT_ID: int = Field(default=0)
    POLYMARKET_CLOB_HOST: str = Field(default="https://clob.polymarket.com")
    POLYMARKET_API_KEY: str = Field(default="")
    POLYMARKET_API_SECRET: str = Field(default="")
    POLYMARKET_API_PASSPHRASE: str = Field(default="")
    POLYMARKET_POLYGON_PRIVATE_KEY: str = Field(default="")
    POLYMARKET_FUNDER_ADDRESS: str = Field(default="")
    CABAL_HUNTER_X402_WALLET_PUBKEY: str = Field(default="")

    # --------------------------------------------------------------------------
    # 7. $5,000+/Day (28.5 SOL/Day) 5-Tier Institutional Velocity Preset
    # --------------------------------------------------------------------------
    LOCAL_JUPITER_QUOTE_URL: str = Field(
        default="http://127.0.0.1:8080/quote",
        description="Self-hosted local jupiter-swap-api binary fed by Yellowstone gRPC (<0.4ms quote latency)",
    )
    KAMINO_FLASH_LOAN_MAX_SOL: float = Field(default=500.0, gt=0.0)
    MEGA_FLASH_SYNDICATE_MAX_SOL: float = Field(default=255000.0, gt=0.0)
    MEGA_FLASH_SYNDICATE_MAX_USD: float = Field(default=50000000.0, gt=0.0)
    METEORA_DLMM_SURGE_POOL_SOL: float = Field(default=90.0, gt=0.0)
    ACTIVE_PARALLEL_SHARDS_COUNT: int = Field(default=25, ge=1, le=25)
    PER_SHARD_CURVE_ENTRY_CAP_SOL: float = Field(default=2.0, gt=0.0)
    DAILY_PROFIT_TARGET_USD: float = Field(default=5000.0, gt=0.0)
    DAILY_PROFIT_TARGET_SOL: float = Field(default=28.50, gt=0.0)
    UNCAPPED_DAILY_COMPOUNDING_ENABLED: bool = Field(
        default=True,
        description="$5,000/day is strictly a floor, never a cap; system continuously reinvests and scales up with 0 ceiling",
    )
    DAILY_PROFIT_CEILING_MODE: str = Field(
        default="UNCAPPED_FLOOR_5K_ONLY",
        description="Explicitly disables any daily profit throttle or ceiling once $5,000/day is reached",
    )
    AUTO_REINVEST_PROFIT_RATIO: float = Field(default=1.0, ge=0.0, le=1.0)
    AUTO_EVOLVE_STRATEGIES_WITH_CAPITAL: bool = Field(default=True)
    KAMINO_FLASH_LOAN_MAX_ECHELON_SOL: float = Field(default=25000.0, gt=0.0)
    INITIAL_SEED_CAPITAL_USD: float = Field(
        default=1500.0,
        ge=100.0,
        description="Initial Day-1 starting seed capital ($1,000–$2,000 range, e.g. $1,000, $1,500, or $2,000)",
    )
    INITIAL_SEED_MIN_USD: float = Field(default=1000.0, gt=0.0)
    INITIAL_SEED_MAX_USD: float = Field(default=2000.0, gt=0.0)
    RANDOM_CAPITAL_INJECTION_MODE: str = Field(
        default="ANY_RANDOM_AMOUNT_ANY_RANDOM_TIME",
        description="Allows injecting any random or custom amount of capital at any random time with automatic 80/20 routing",
    )

    # --------------------------------------------------------------------------
    # Validators enforcing /AGENTS.md invariants
    # --------------------------------------------------------------------------
    @field_validator("ALPENGLOW_SLOT_MS")
    @classmethod
    def validate_alpenglow_slot_ms(cls, v: int) -> int:
        if v != 200:
            raise ValueError(
                f"Alpenglow consensus requires slot duration of 200ms (got {v}ms). Legacy 400ms constants are forbidden."
            )
        return v

    @field_validator("JITO_BAM_TICK_MS")
    @classmethod
    def validate_jito_bam_tick_ms(cls, v: int) -> int:
        if v != 25:
            raise ValueError(
                f"Jito BAM market tick must be 25ms (8 ticks per 200ms slot), got {v}ms."
            )
        return v

    @field_validator("MAX_VERSIONED_TX_ACCOUNTS")
    @classmethod
    def validate_max_tx_accounts(cls, v: int) -> int:
        if v not in (64, 96):
            raise ValueError(
                f"MAX_VERSIONED_TX_ACCOUNTS must be 64 (standard) or 96 (Agave 4.5 auto-upgrade), got {v}."
            )
        return v

    @field_validator("JITO_DONT_FRONT_PUBKEY")
    @classmethod
    def validate_jito_dont_front(cls, v: str) -> str:
        expected = "jitodontfront111111111111111111111111111111"
        if v != expected:
            raise ValueError(f"JITO_DONT_FRONT_PUBKEY must equal {expected}")
        return v

    @model_validator(mode="after")
    def validate_tranche_and_tx_invariants(self) -> "Settings":
        total_ratio = round(self.SCOUT_TRANCHE_RATIO + self.CONVICTION_TRANCHE_RATIO, 6)
        if total_ratio != 1.0:
            raise ValueError(
                f"SCOUT_TRANCHE_RATIO ({self.SCOUT_TRANCHE_RATIO}) + CONVICTION_TRANCHE_RATIO ({self.CONVICTION_TRANCHE_RATIO}) must sum to 1.0"
            )
        if self.MAX_TX_SIZE_BYTES >= self.SOLANA_MTU_LIMIT_BYTES:
            raise ValueError(
                f"MAX_TX_SIZE_BYTES ({self.MAX_TX_SIZE_BYTES}) must stay strictly below SOLANA_MTU_LIMIT_BYTES ({self.SOLANA_MTU_LIMIT_BYTES})"
            )
        return self

    # --------------------------------------------------------------------------
    # Helper Properties
    # --------------------------------------------------------------------------
    @property
    def jito_regional_endpoints(self) -> Dict[str, str]:
        """Returns the 4 regional Jito Block Engine endpoints required for simultaneous outbound dispatch."""
        return {
            "ny": self.JITO_NY_BLOCK_ENGINE_URL,
            "frankfurt": self.JITO_FRANKFURT_BLOCK_ENGINE_URL,
            "amsterdam": self.JITO_AMSTERDAM_BLOCK_ENGINE_URL,
            "tokyo": self.JITO_TOKYO_BLOCK_ENGINE_URL,
        }

    @property
    def ramdisk_directories(self) -> List[Path]:
        """Returns the 5 required subdirectories inside /mnt/ramdisk."""
        return [
            self.RAMDISK_ALPHA_GRAPH,
            self.RAMDISK_MEV_POOL_MIRROR,
            self.RAMDISK_PRE_APPROVED_TOKENS,
            self.RAMDISK_IMAGE_PHASH_INDEX,
            self.RAMDISK_EXECUTION_STATE,
        ]

    @property
    def cpu_core_partition_map(self) -> Dict[str, Tuple[int, int]]:
        """Returns the Threadripper PRO 9995WX (96 Zen 5 Cores) strict core partition map."""
        return {
            "nic_ptp_and_risk_watchdog": (0, 3),
            "engine_a_pool_mirror_flash_arb": (4, 15),
            "engine_b_whale_copy_twap_sandwich": (16, 23),
            "alpha_shadow_and_engine_c_dlmm": (24, 31),
            "tauri_gui_command_center": (32, 35),
            "port_8003_l3_llm_and_graph_workers": (36, 47),
            "port_8002_ktransformers_avx512_experts": (48, 95),
        }

    @property
    def monitored_telegram_channels_list(self) -> List[str]:
        return [
            ch.strip()
            for ch in self.TELEGRAM_MONITORED_CHANNELS.split(",")
            if ch.strip()
        ]

    @property
    def ramdisk_root(self) -> Path:
        return self.RAMDISK_ROOT

    @property
    def execution_state_dir(self) -> Path:
        return self.RAMDISK_EXECUTION_STATE

    @property
    def helius_rpc_url(self) -> str:
        return self.HELIUS_RPC_URL

    @property
    def helius_ws_url(self) -> str:
        return self.HELIUS_WS_URL

    def ensure_ramdisk_directories(self) -> None:
        for d in self.ramdisk_directories:
            d.mkdir(parents=True, exist_ok=True)

    def effective_max_tx_accounts(self, agave_45_enabled: bool = False) -> int:
        """Returns 64 by default or auto-upgrades to 96 when Agave 4.5 mode is active."""
        if agave_45_enabled:
            return self.AGAVE_45_MAX_TX_ACCOUNTS
        return self.MAX_VERSIONED_TX_ACCOUNTS

    def evaluate_mainnet_readiness(self) -> Dict[str, Any]:
        """Evaluates Live Mainnet production readiness across API keys, keystore, ProfitGuard .so, and RAMDisk."""
        return {
            "helius_configured": not self.HELIUS_API_KEY.startswith("YOUR_")
            and bool(self.HELIUS_API_KEY),
            "jupiter_configured": not self.JUPITER_API_KEY.startswith("YOUR_")
            and bool(self.JUPITER_API_KEY),
            "birdeye_configured": not self.BIRDEYE_API_KEY.startswith("YOUR_")
            and bool(self.BIRDEYE_API_KEY),
            "withdraw_address_bound": self.WITHDRAW_ADDRESS != "DEFERRED"
            and len(self.WITHDRAW_ADDRESS) >= 32,
            "keystore_persisted": (
                Path.home() / ".hermes" / "skills" / "solana-mev-titan" / ".keystore.enc"
            ).exists(),
            "profit_guard_compiled": (
                WORKSPACE_ROOT
                / "anchor_profit_guard"
                / "target"
                / "deploy"
                / "profit_guard.so"
            ).exists(),
            "ramdisk_mounted": self.RAMDISK_ROOT.exists(),
            "live_broadcast_enabled": bool(self.LIVE_MAINNET_BROADCAST_ENABLED),
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton settings loader."""
    return Settings()


settings = get_settings()
