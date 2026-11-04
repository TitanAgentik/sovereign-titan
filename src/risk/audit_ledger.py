"""Sovereign Titan OS — Permanent Parquet Tax & Lot Audit Ledger (`src/risk/audit_ledger.py`).

Appends every executed trade:
  - `timestamp_ns` (nanosecond hardware timestamp)
  - `tx_signature`
  - `shard_id`
  - `engine_id`
  - `token_mint`
  - `sol_in`
  - `sol_out`
  - `jito_tip_sol`
  - `ata_rent_reclaimed_sol`
  - `sol_usd_spot_price`
  - `net_pnl_sol`
  - `net_pnl_usd`
to `/var/lib/hermes/audit_ledger.parquet`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import pyarrow as pa
import pyarrow.parquet as pq


DEFAULT_PARQUET_LEDGER_PATH = Path("/var/lib/hermes/audit_ledger.parquet")

AUDIT_LEDGER_SCHEMA = pa.schema(
    [
        ("timestamp_ns", pa.int64()),
        ("tx_signature", pa.string()),
        ("shard_id", pa.int32()),
        ("engine_id", pa.string()),
        ("token_mint", pa.string()),
        ("sol_in", pa.float64()),
        ("sol_out", pa.float64()),
        ("jito_tip_sol", pa.float64()),
        ("ata_rent_reclaimed_sol", pa.float64()),
        ("sol_usd_spot_price", pa.float64()),
        ("net_pnl_sol", pa.float64()),
        ("net_pnl_usd", pa.float64()),
    ]
)


@dataclass
class AuditTradeLotRecord:
    """Single immutable tax & execution lot record."""

    timestamp_ns: int
    tx_signature: str
    shard_id: int
    engine_id: str
    token_mint: str
    sol_in: float
    sol_out: float
    jito_tip_sol: float
    ata_rent_reclaimed_sol: float
    sol_usd_spot_price: float
    net_pnl_sol: float
    net_pnl_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuditTaxLedger:
    """Appends and queries immutable trade lots in `/var/lib/hermes/audit_ledger.parquet`."""

    def __init__(self, ledger_path: Optional[Path] = None) -> None:
        self.ledger_path = ledger_path or DEFAULT_PARQUET_LEDGER_PATH
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def append_trade(
        self,
        tx_signature: str,
        shard_id: int,
        engine_id: str,
        sol_in: float,
        sol_out: float,
        jito_tip_sol: float,
        ata_rent_reclaimed_sol: float,
        sol_usd_spot_price: float,
        token_mint: str = "So11111111111111111111111111111111111111112",
        timestamp_ns: Optional[int] = None,
    ) -> AuditTradeLotRecord:
        """Appends a trade lot to `/var/lib/hermes/audit_ledger.parquet`."""
        ts_ns = timestamp_ns if timestamp_ns is not None else time.time_ns()
        net_sol = round(
            float(sol_out) - float(sol_in) - float(jito_tip_sol) + float(ata_rent_reclaimed_sol),
            9,
        )
        net_usd = round(net_sol * float(sol_usd_spot_price), 4)

        record = AuditTradeLotRecord(
            timestamp_ns=int(ts_ns),
            tx_signature=str(tx_signature),
            shard_id=int(shard_id),
            engine_id=str(engine_id),
            token_mint=str(token_mint),
            sol_in=float(sol_in),
            sol_out=float(sol_out),
            jito_tip_sol=float(jito_tip_sol),
            ata_rent_reclaimed_sol=float(ata_rent_reclaimed_sol),
            sol_usd_spot_price=float(sol_usd_spot_price),
            net_pnl_sol=net_sol,
            net_pnl_usd=net_usd,
        )

        new_table = pa.Table.from_pylist([record.to_dict()], schema=AUDIT_LEDGER_SCHEMA)
        if self.ledger_path.exists():
            existing_table = pq.read_table(self.ledger_path)
            combined_table = pa.concat_tables([existing_table, new_table])
        else:
            combined_table = new_table

        tmp_path = self.ledger_path.with_suffix(".parquet.tmp")
        pq.write_table(combined_table, tmp_path, compression="zstd")
        tmp_path.replace(self.ledger_path)
        return record

    def read_all_trades(self) -> List[AuditTradeLotRecord]:
        """Reads all trade lots from `/var/lib/hermes/audit_ledger.parquet`."""
        if not self.ledger_path.exists():
            return []
        table = pq.read_table(self.ledger_path)
        return [AuditTradeLotRecord(**row) for row in table.to_pylist()]
