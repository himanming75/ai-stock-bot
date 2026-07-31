from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import csv
import hashlib
import json
import re

SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")
TIMEFRAMES = {"1Min", "5Min", "15Min", "1Hour", "1Day"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def utc_text(value: str | datetime) -> str:
    return parse_utc(value).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class IngestionConfig:
    stage: str = "V79.21"
    dataset_name: str = "alpaca_historical_bars"
    timeframe: str = "1Min"
    source: str = "offline_fixture"
    expected_symbols: tuple[str, ...] = ("AAPL", "MSFT", "SPY")
    allow_network: bool = False
    allow_credentials: bool = False
    allow_trading_client: bool = False
    allow_order_submission: bool = False
    actual_orders_submitted: int = 0
    reject_duplicate_keys: bool = False
    require_all_expected_symbols: bool = True

    def validate(self) -> None:
        if not self.dataset_name or "/" in self.dataset_name or "\\" in self.dataset_name:
            raise ValueError("invalid dataset_name")
        if self.timeframe not in TIMEFRAMES:
            raise ValueError("unsupported timeframe")
        if not self.expected_symbols:
            raise ValueError("expected_symbols cannot be empty")
        if any(not SYMBOL_RE.fullmatch(s) for s in self.expected_symbols):
            raise ValueError("invalid expected symbol")
        if self.allow_network or self.allow_credentials:
            raise ValueError("V79.21-V79.25 default ingestion must remain offline")
        if self.allow_trading_client or self.allow_order_submission:
            raise ValueError("trading and order APIs are prohibited")
        if self.actual_orders_submitted != 0:
            raise ValueError("actual order count must remain zero")


@dataclass(frozen=True)
class IngestionBar:
    symbol: str
    timestamp: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    trade_count: int = 0
    vwap: float | None = None
    source: str = "offline_fixture"

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not SYMBOL_RE.fullmatch(symbol):
            raise ValueError("invalid symbol")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "timestamp", utc_text(self.timestamp))
        if self.timeframe not in TIMEFRAMES:
            raise ValueError("unsupported timeframe")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC values must be positive")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high is inconsistent")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low is inconsistent")
        if self.volume < 0 or self.trade_count < 0:
            raise ValueError("volume and trade_count must be nonnegative")

    @property
    def primary_key(self) -> tuple[str, str, str]:
        return (self.symbol, self.timeframe, self.timestamp)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IngestionValidation:
    stage: str
    status: str
    row_count: int
    symbol_count: int
    symbols: tuple[str, ...]
    duplicate_count: int
    missing_expected_symbols: tuple[str, ...]
    invalid_time_order_count: int
    timeframe_mismatch_count: int
    utc_timestamp_count: int
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["symbols"] = list(self.symbols)
        value["missing_expected_symbols"] = list(self.missing_expected_symbols)
        value["errors"] = list(self.errors)
        return value


def normalize_ingestion_rows(
    rows: Iterable[dict[str, Any] | IngestionBar],
    config: IngestionConfig,
) -> list[IngestionBar]:
    config.validate()
    normalized: list[IngestionBar] = []
    for row in rows:
        if isinstance(row, IngestionBar):
            normalized.append(row)
            continue
        normalized.append(
            IngestionBar(
                symbol=str(row["symbol"]),
                timestamp=row["timestamp"],
                timeframe=str(row.get("timeframe", config.timeframe)),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
                trade_count=int(row.get("trade_count", 0) or 0),
                vwap=None if row.get("vwap") is None else float(row["vwap"]),
                source=str(row.get("source", config.source)),
            )
        )
    return sorted(normalized, key=lambda item: item.primary_key)


def deduplicate_ingestion_rows(
    rows: Iterable[IngestionBar],
) -> tuple[list[IngestionBar], int]:
    unique: dict[tuple[str, str, str], IngestionBar] = {}
    duplicate_count = 0
    for row in rows:
        if row.primary_key in unique:
            duplicate_count += 1
            if unique[row.primary_key] != row:
                raise ValueError("conflicting duplicate primary key")
            continue
        unique[row.primary_key] = row
    return sorted(unique.values(), key=lambda item: item.primary_key), duplicate_count


def validate_ingestion_dataset(
    rows: list[IngestionBar],
    config: IngestionConfig,
    duplicate_count: int = 0,
) -> IngestionValidation:
    config.validate()
    errors: list[str] = []
    symbols = tuple(sorted({row.symbol for row in rows}))
    missing = tuple(sorted(set(config.expected_symbols) - set(symbols)))
    timeframe_mismatch = sum(row.timeframe != config.timeframe for row in rows)
    utc_count = sum(parse_utc(row.timestamp).utcoffset().total_seconds() == 0 for row in rows)

    invalid_order = 0
    by_symbol: dict[str, list[IngestionBar]] = {}
    for row in rows:
        by_symbol.setdefault(row.symbol, []).append(row)
    for symbol_rows in by_symbol.values():
        timestamps = [parse_utc(row.timestamp) for row in symbol_rows]
        invalid_order += sum(a >= b for a, b in zip(timestamps, timestamps[1:]))

    if not rows:
        errors.append("dataset_empty")
    if config.require_all_expected_symbols and missing:
        errors.append("expected_symbols_missing")
    if timeframe_mismatch:
        errors.append("timeframe_mismatch")
    if invalid_order:
        errors.append("invalid_time_order")
    if utc_count != len(rows):
        errors.append("timestamps_not_utc")
    if config.reject_duplicate_keys and duplicate_count:
        errors.append("duplicate_keys_present")

    return IngestionValidation(
        stage="V79.23",
        status="PASS" if not errors else "FAIL",
        row_count=len(rows),
        symbol_count=len(symbols),
        symbols=symbols,
        duplicate_count=duplicate_count,
        missing_expected_symbols=missing,
        invalid_time_order_count=invalid_order,
        timeframe_mismatch_count=timeframe_mismatch,
        utc_timestamp_count=utc_count,
        errors=tuple(errors),
    )


class HistoricalDatasetStore:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def write(
        self,
        config: IngestionConfig,
        rows: list[IngestionBar],
        validation: IngestionValidation,
    ) -> dict[str, Any]:
        if validation.status != "PASS":
            raise ValueError("refusing to store invalid dataset")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = self.output_dir / f"{config.dataset_name}.jsonl"
        csv_path = self.output_dir / f"{config.dataset_name}.csv"

        jsonl_bytes = "".join(
            json.dumps(row.to_dict(), sort_keys=True, ensure_ascii=False) + "\n"
            for row in rows
        ).encode("utf-8")
        jsonl_path.write_bytes(jsonl_bytes)

        fieldnames = [
            "symbol", "timestamp", "timeframe", "open", "high", "low",
            "close", "volume", "trade_count", "vwap", "source",
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(row.to_dict() for row in rows)

        csv_bytes = csv_path.read_bytes()
        manifest = {
            "schema_version": "v79.24.historical_dataset_manifest.1",
            "stage": "V79.24",
            "dataset_name": config.dataset_name,
            "timeframe": config.timeframe,
            "row_count": len(rows),
            "symbol_count": validation.symbol_count,
            "symbols": list(validation.symbols),
            "duplicate_count_removed": validation.duplicate_count,
            "files": {
                "jsonl": {
                    "relative_path": jsonl_path.name,
                    "sha256": sha256_bytes(jsonl_bytes),
                    "byte_size": len(jsonl_bytes),
                },
                "csv": {
                    "relative_path": csv_path.name,
                    "sha256": sha256_bytes(csv_bytes),
                    "byte_size": len(csv_bytes),
                },
            },
            "network_requests_executed": 0,
            "credentials_used": 0,
            "trading_client_created": False,
            "actual_orders_submitted": 0,
        }
        manifest["manifest_sha256"] = sha256_json(manifest)
        write_json(self.output_dir / f"{config.dataset_name}.manifest.json", manifest)
        return manifest

    def verify(self, manifest: dict[str, Any]) -> bool:
        for info in manifest["files"].values():
            path = self.output_dir / info["relative_path"]
            if not path.is_file():
                raise ValueError("dataset file missing")
            data = path.read_bytes()
            if sha256_bytes(data) != info["sha256"]:
                raise ValueError("dataset file hash mismatch")
            if len(data) != info["byte_size"]:
                raise ValueError("dataset file size mismatch")
        return True


def run_historical_ingestion(
    raw_rows: Iterable[dict[str, Any] | IngestionBar],
    config: IngestionConfig,
    output_dir: Path,
) -> dict[str, Any]:
    normalized = normalize_ingestion_rows(raw_rows, config)
    deduplicated, duplicate_count = deduplicate_ingestion_rows(normalized)
    validation = validate_ingestion_dataset(deduplicated, config, duplicate_count)
    store = HistoricalDatasetStore(output_dir)
    manifest = store.write(config, deduplicated, validation)
    store.verify(manifest)
    return {
        "stage": "V79.24",
        "status": "PASS",
        "normalized_row_count": len(normalized),
        "stored_row_count": len(deduplicated),
        "duplicate_count_removed": duplicate_count,
        "validation": validation.to_dict(),
        "manifest": manifest,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }


def build_ingestion_certificate(
    repository_root: Path,
    output_dir: Path,
    config: IngestionConfig,
    ingestion_result: dict[str, Any],
) -> dict[str, Any]:
    config.validate()
    validation = ingestion_result["validation"]
    manifest = ingestion_result["manifest"]
    checks = {
        "v79_20_certificate_present": (
            repository_root
            / "release/v79_20/output/historical_network_smoke_certificate_v79_20.json"
        ).is_file(),
        "ingestion_status_pass": ingestion_result.get("status") == "PASS",
        "validation_status_pass": validation.get("status") == "PASS",
        "all_expected_symbols_present": not validation.get("missing_expected_symbols"),
        "rows_stored": ingestion_result.get("stored_row_count", 0) > 0,
        "manifest_hash_present": len(manifest.get("manifest_sha256", "")) == 64,
        "jsonl_hash_present": len(manifest["files"]["jsonl"]["sha256"]) == 64,
        "csv_hash_present": len(manifest["files"]["csv"]["sha256"]) == 64,
        "network_requests_zero": ingestion_result.get("network_requests_executed") == 0,
        "credentials_unused": ingestion_result.get("credentials_used") == 0,
        "trading_client_not_created": ingestion_result.get("trading_client_created") is False,
        "actual_orders_zero": ingestion_result.get("actual_orders_submitted") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failed else "FAIL"
    cert = {
        "schema_version": "v79.25.historical_ingestion_certificate.1",
        "stage": "V79.25",
        "status": status,
        "scope": "OFFLINE_HISTORICAL_DATA_INGESTION",
        "stages_completed": ["V79.21", "V79.22", "V79.23", "V79.24", "V79.25"],
        "passed_stage_count": 5 if status == "PASS" else 5 - len(failed),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "config": asdict(config),
        "ingestion_summary": {
            "normalized_row_count": ingestion_result["normalized_row_count"],
            "stored_row_count": ingestion_result["stored_row_count"],
            "duplicate_count_removed": ingestion_result["duplicate_count_removed"],
            "symbol_count": validation["symbol_count"],
            "symbols": validation["symbols"],
        },
        "dataset_manifest": manifest,
        "checks": checks,
        "failed_checks": failed,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": "V79_26_HISTORICAL_DATA_INCREMENTAL_SYNC",
    }
    cert["certificate_sha256"] = sha256_json(cert)
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "historical_ingestion_certificate_v79_25.json"
    write_json(cert_path, cert)
    verify = {
        "stage": "V79.25",
        "status": status,
        "verified": not failed,
        "certificate_sha256": cert["certificate_sha256"],
        "certificate_path": str(cert_path.relative_to(repository_root)).replace("\\", "/"),
        "failed_checks": failed,
        "next_phase": cert["next_phase"],
    }
    verify["verification_sha256"] = sha256_json(verify)
    write_json(output_dir / "historical_ingestion_verification_v79_25.json", verify)
    return cert
