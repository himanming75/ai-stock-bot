from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import os
import tempfile

from .ingestion_v79_21_25 import IngestionBar


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", delete=False, dir=path.parent, prefix=path.name, suffix=".tmp"
    ) as handle:
        handle.write(data)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


@dataclass(frozen=True)
class QualityConfig:
    stage: str = "V79.36"
    dataset_name: str = "alpaca_historical_bars"
    timeframe: str = "1Min"
    expected_symbols: tuple[str, ...] = ("AAPL", "MSFT", "SPY")
    expected_step_seconds: int = 60
    require_unique_primary_keys: bool = True
    require_strict_time_order: bool = True
    require_zero_gaps: bool = True
    require_zero_repairs: bool = True
    allow_network: bool = False
    allow_credentials: bool = False
    allow_trading_client: bool = False
    allow_order_submission: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        if self.timeframe != "1Min" or self.expected_step_seconds != 60:
            raise ValueError("V79.36-V79.40 supports 1Min/60-second bars only")
        if not self.expected_symbols:
            raise ValueError("expected_symbols cannot be empty")
        if not all((
            self.require_unique_primary_keys,
            self.require_strict_time_order,
            self.require_zero_gaps,
            self.require_zero_repairs,
        )):
            raise ValueError("quality gates must remain strict")
        if self.allow_network or self.allow_credentials:
            raise ValueError("quality reconciliation must remain offline")
        if self.allow_trading_client or self.allow_order_submission:
            raise ValueError("trading and order APIs are prohibited")
        if self.actual_orders_submitted != 0:
            raise ValueError("actual orders must remain zero")


@dataclass(frozen=True)
class QualityIssue:
    stage: str
    code: str
    severity: str
    symbol: str
    timestamp: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_quality_dataset(path: Path) -> list[IngestionBar]:
    if not path.is_file():
        raise FileNotFoundError(f"quality dataset missing: {path}")
    rows: list[IngestionBar] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(IngestionBar(**json.loads(line)))
        except Exception as exc:
            raise ValueError(f"invalid quality JSONL row at line {line_no}") from exc
    return rows


def scan_dataset_integrity(
    rows: Iterable[IngestionBar], config: QualityConfig
) -> tuple[list[QualityIssue], dict[str, int]]:
    config.validate()
    rows = list(rows)
    issues: list[QualityIssue] = []
    seen: set[tuple[str, str, str]] = set()
    duplicate_count = 0
    unexpected_symbol_count = 0
    unexpected_timeframe_count = 0

    for row in rows:
        if row.primary_key in seen:
            duplicate_count += 1
            issues.append(QualityIssue(
                "V79.36", "DUPLICATE_PRIMARY_KEY", "ERROR",
                row.symbol, row.timestamp, "duplicate primary key",
            ))
        seen.add(row.primary_key)
        if row.symbol not in config.expected_symbols:
            unexpected_symbol_count += 1
            issues.append(QualityIssue(
                "V79.36", "UNEXPECTED_SYMBOL", "ERROR",
                row.symbol, row.timestamp, "symbol is outside configured universe",
            ))
        if row.timeframe != config.timeframe:
            unexpected_timeframe_count += 1
            issues.append(QualityIssue(
                "V79.36", "UNEXPECTED_TIMEFRAME", "ERROR",
                row.symbol, row.timestamp, "timeframe does not match configuration",
            ))
        try:
            parse_utc(row.timestamp)
        except Exception:
            issues.append(QualityIssue(
                "V79.36", "INVALID_TIMESTAMP", "ERROR",
                row.symbol, row.timestamp, "timestamp is not valid UTC ISO-8601",
            ))

    present_symbols = sorted({row.symbol for row in rows})
    missing_symbols = sorted(set(config.expected_symbols) - set(present_symbols))
    for symbol in missing_symbols:
        issues.append(QualityIssue(
            "V79.36", "MISSING_SYMBOL", "ERROR", symbol, "",
            "expected symbol has no rows",
        ))

    return issues, {
        "row_count": len(rows),
        "unique_primary_key_count": len(seen),
        "duplicate_primary_key_count": duplicate_count,
        "unexpected_symbol_count": unexpected_symbol_count,
        "unexpected_timeframe_count": unexpected_timeframe_count,
        "present_symbol_count": len(present_symbols),
        "missing_symbol_count": len(missing_symbols),
    }


def validate_ohlcv(rows: Iterable[IngestionBar]) -> tuple[list[QualityIssue], dict[str, int]]:
    issues: list[QualityIssue] = []
    invalid_price_count = 0
    invalid_ohlc_count = 0
    invalid_volume_count = 0
    invalid_trade_count = 0
    invalid_vwap_count = 0

    for row in rows:
        prices = (row.open, row.high, row.low, row.close)
        if any(not isinstance(value, (int, float)) or value <= 0 for value in prices):
            invalid_price_count += 1
            issues.append(QualityIssue(
                "V79.37", "NON_POSITIVE_PRICE", "ERROR",
                row.symbol, row.timestamp, "OHLC prices must be positive numbers",
            ))
        if row.high < max(row.open, row.close, row.low) or row.low > min(row.open, row.close, row.high):
            invalid_ohlc_count += 1
            issues.append(QualityIssue(
                "V79.37", "INVALID_OHLC_RELATIONSHIP", "ERROR",
                row.symbol, row.timestamp, "high/low do not contain open and close",
            ))
        if not isinstance(row.volume, int) or row.volume < 0:
            invalid_volume_count += 1
            issues.append(QualityIssue(
                "V79.37", "INVALID_VOLUME", "ERROR",
                row.symbol, row.timestamp, "volume must be a non-negative integer",
            ))
        if not isinstance(row.trade_count, int) or row.trade_count < 0:
            invalid_trade_count += 1
            issues.append(QualityIssue(
                "V79.37", "INVALID_TRADE_COUNT", "ERROR",
                row.symbol, row.timestamp, "trade_count must be a non-negative integer",
            ))
        if not isinstance(row.vwap, (int, float)) or row.vwap <= 0:
            invalid_vwap_count += 1
            issues.append(QualityIssue(
                "V79.37", "INVALID_VWAP", "ERROR",
                row.symbol, row.timestamp, "vwap must be positive",
            ))

    return issues, {
        "invalid_price_count": invalid_price_count,
        "invalid_ohlc_count": invalid_ohlc_count,
        "invalid_volume_count": invalid_volume_count,
        "invalid_trade_count": invalid_trade_count,
        "invalid_vwap_count": invalid_vwap_count,
    }


def reconcile_symbol_time_series(
    rows: Iterable[IngestionBar], config: QualityConfig
) -> tuple[list[QualityIssue], dict[str, Any]]:
    grouped: dict[str, list[IngestionBar]] = {}
    for row in rows:
        grouped.setdefault(row.symbol, []).append(row)

    issues: list[QualityIssue] = []
    gap_count = 0
    out_of_order_count = 0
    per_symbol: dict[str, dict[str, Any]] = {}
    step = timedelta(seconds=config.expected_step_seconds)

    for symbol in sorted(config.expected_symbols):
        original = grouped.get(symbol, [])
        ordered = sorted(original, key=lambda row: parse_utc(row.timestamp))
        original_keys = [row.timestamp for row in original]
        ordered_keys = [row.timestamp for row in ordered]
        if original_keys != ordered_keys:
            out_of_order_count += 1
            issues.append(QualityIssue(
                "V79.38", "OUT_OF_ORDER_SERIES", "ERROR", symbol, "",
                "rows are not in strict chronological order",
            ))

        symbol_gap_count = 0
        for current, following in zip(ordered, ordered[1:]):
            delta = parse_utc(following.timestamp) - parse_utc(current.timestamp)
            if delta != step:
                symbol_gap_count += 1
                gap_count += 1
                issues.append(QualityIssue(
                    "V79.38", "NON_CONTIGUOUS_SERIES", "ERROR",
                    symbol, following.timestamp,
                    f"expected {config.expected_step_seconds}s step, got {int(delta.total_seconds())}s",
                ))
        per_symbol[symbol] = {
            "row_count": len(ordered),
            "first_timestamp": ordered[0].timestamp if ordered else None,
            "last_timestamp": ordered[-1].timestamp if ordered else None,
            "gap_count": symbol_gap_count,
        }

    return issues, {
        "symbol_count": len(grouped),
        "expected_symbol_count": len(config.expected_symbols),
        "gap_count": gap_count,
        "out_of_order_series_count": out_of_order_count,
        "per_symbol": per_symbol,
    }


def build_repair_ledger(issues: Iterable[QualityIssue]) -> dict[str, Any]:
    issues = list(issues)
    repairable = [item for item in issues if item.severity == "ERROR"]
    return {
        "schema_version": "v79.39.repair_ledger.1",
        "stage": "V79.39",
        "status": "NO_REPAIRS_REQUIRED" if not repairable else "REPAIR_REQUIRED",
        "automatic_repairs_applied": 0,
        "pending_repair_count": len(repairable),
        "entries": [
            {
                "code": item.code,
                "symbol": item.symbol,
                "timestamp": item.timestamp,
                "action": "MANUAL_REVIEW_REQUIRED",
            }
            for item in repairable
        ],
    }


def write_quality_outputs(
    output_dir: Path,
    config: QualityConfig,
    rows: list[IngestionBar],
    integrity: dict[str, int],
    ohlcv: dict[str, int],
    reconciliation: dict[str, Any],
    issues: list[QualityIssue],
    repair_ledger: dict[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{config.dataset_name}.quality_report.json"
    ledger_path = output_dir / f"{config.dataset_name}.repair_ledger.json"
    snapshot_path = output_dir / f"{config.dataset_name}.quality_snapshot.jsonl"

    report = {
        "schema_version": "v79.39.quality_report.1",
        "stage": "V79.39",
        "status": "PASS" if not issues else "FAIL",
        "integrity": integrity,
        "ohlcv": ohlcv,
        "reconciliation": reconciliation,
        "issue_count": len(issues),
        "issues": [item.to_dict() for item in issues],
    }
    report_bytes = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    ledger_bytes = (json.dumps(repair_ledger, indent=2, sort_keys=True) + "\n").encode()
    snapshot_bytes = "".join(
        json.dumps(row.to_dict(), sort_keys=True, ensure_ascii=False) + "\n"
        for row in rows
    ).encode()

    _atomic_write(report_path, report_bytes)
    _atomic_write(ledger_path, ledger_bytes)
    _atomic_write(snapshot_path, snapshot_bytes)

    manifest = {
        "schema_version": "v79.39.quality_manifest.1",
        "stage": "V79.39",
        "dataset_name": config.dataset_name,
        "row_count": len(rows),
        "issue_count": len(issues),
        "pending_repair_count": repair_ledger["pending_repair_count"],
        "automatic_repairs_applied": repair_ledger["automatic_repairs_applied"],
        "files": {
            "quality_report": {
                "relative_path": report_path.name,
                "sha256": sha256_bytes(report_bytes),
                "byte_size": len(report_bytes),
            },
            "repair_ledger": {
                "relative_path": ledger_path.name,
                "sha256": sha256_bytes(ledger_bytes),
                "byte_size": len(ledger_bytes),
            },
            "quality_snapshot": {
                "relative_path": snapshot_path.name,
                "sha256": sha256_bytes(snapshot_bytes),
                "byte_size": len(snapshot_bytes),
            },
        },
        "atomic_write_used": True,
        "source_dataset_modified": False,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    manifest["manifest_sha256"] = sha256_json(manifest)
    write_json(output_dir / f"{config.dataset_name}.quality_manifest.json", manifest)
    return manifest


def verify_quality_manifest(output_dir: Path, manifest: dict[str, Any]) -> bool:
    unsigned = dict(manifest)
    expected_hash = unsigned.pop("manifest_sha256", None)
    if expected_hash != sha256_json(unsigned):
        raise ValueError("quality manifest self-hash mismatch")
    for info in manifest["files"].values():
        path = output_dir / info["relative_path"]
        if not path.is_file():
            raise ValueError("quality output missing")
        data = path.read_bytes()
        if sha256_bytes(data) != info["sha256"] or len(data) != info["byte_size"]:
            raise ValueError("quality output integrity mismatch")
    return True


def run_quality_reconciliation(
    rows: Iterable[IngestionBar], config: QualityConfig, output_dir: Path
) -> dict[str, Any]:
    config.validate()
    rows = list(rows)
    integrity_issues, integrity = scan_dataset_integrity(rows, config)
    ohlcv_issues, ohlcv = validate_ohlcv(rows)
    reconciliation_issues, reconciliation = reconcile_symbol_time_series(rows, config)
    issues = integrity_issues + ohlcv_issues + reconciliation_issues
    ledger = build_repair_ledger(issues)
    manifest = write_quality_outputs(
        output_dir, config, rows, integrity, ohlcv,
        reconciliation, issues, ledger,
    )
    verify_quality_manifest(output_dir, manifest)
    return {
        "stage": "V79.39",
        "status": "PASS" if not issues else "FAIL",
        "integrity": integrity,
        "ohlcv": ohlcv,
        "reconciliation": reconciliation,
        "issue_count": len(issues),
        "repair_ledger": ledger,
        "manifest": manifest,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }


def build_quality_certificate(
    repository_root: Path,
    output_dir: Path,
    config: QualityConfig,
    result: dict[str, Any],
) -> dict[str, Any]:
    prior = repository_root / "release/v79_35/output/historical_gap_fill_certificate_v79_35.json"
    checks = {
        "v79_35_certificate_present": prior.is_file(),
        "quality_status_pass": result["status"] == "PASS",
        "row_count_positive": result["integrity"]["row_count"] > 0,
        "unique_primary_keys": result["integrity"]["duplicate_primary_key_count"] == 0,
        "all_symbols_present": result["integrity"]["missing_symbol_count"] == 0,
        "ohlcv_valid": sum(result["ohlcv"].values()) == 0,
        "time_series_contiguous": result["reconciliation"]["gap_count"] == 0,
        "time_series_ordered": result["reconciliation"]["out_of_order_series_count"] == 0,
        "issues_zero": result["issue_count"] == 0,
        "repairs_zero": result["repair_ledger"]["pending_repair_count"] == 0,
        "source_dataset_unmodified": result["manifest"]["source_dataset_modified"] is False,
        "manifest_hash_present": len(result["manifest"].get("manifest_sha256", "")) == 64,
        "network_requests_zero": result["network_requests_executed"] == 0,
        "credentials_unused": result["credentials_used"] == 0,
        "trading_client_not_created": result["trading_client_created"] is False,
        "actual_orders_zero": result["actual_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failed else "FAIL"
    cert = {
        "schema_version": "v79.40.quality_certificate.1",
        "stage": "V79.40",
        "status": status,
        "scope": "OFFLINE_HISTORICAL_DATA_QUALITY_RECONCILIATION",
        "stages_completed": ["V79.36", "V79.37", "V79.38", "V79.39", "V79.40"],
        "passed_stage_count": 5 if status == "PASS" else max(0, 5 - len(failed)),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "config": asdict(config),
        "quality_summary": {
            "row_count": result["integrity"]["row_count"],
            "symbol_count": result["reconciliation"]["symbol_count"],
            "duplicate_primary_key_count": result["integrity"]["duplicate_primary_key_count"],
            "gap_count": result["reconciliation"]["gap_count"],
            "issue_count": result["issue_count"],
            "pending_repair_count": result["repair_ledger"]["pending_repair_count"],
        },
        "quality_manifest": result["manifest"],
        "checks": checks,
        "failed_checks": failed,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": "V79_41_HISTORICAL_DATASET_VERSIONING",
    }
    cert["certificate_sha256"] = sha256_json(cert)
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "historical_quality_certificate_v79_40.json"
    write_json(cert_path, cert)
    write_json(output_dir / "historical_quality_verify_v79_40.json", {
        "stage": "V79.40",
        "status": status,
        "verified": not failed,
        "certificate_sha256": cert["certificate_sha256"],
        "certificate_path": str(cert_path.relative_to(repository_root)).replace("\\", "/"),
        "failed_checks": failed,
    })
    return cert
