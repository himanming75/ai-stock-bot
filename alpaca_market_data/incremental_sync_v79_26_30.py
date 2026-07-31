from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import os
import tempfile

from .ingestion_v79_21_25 import IngestionBar, IngestionConfig, normalize_ingestion_rows


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def utc_text(value: str | datetime) -> str:
    return parse_utc(value).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class IncrementalSyncConfig:
    stage: str = "V79.26"
    dataset_name: str = "alpaca_historical_bars"
    timeframe: str = "1Min"
    expected_symbols: tuple[str, ...] = ("AAPL", "MSFT", "SPY")
    max_gap_tasks: int = 100
    allow_network: bool = False
    allow_credentials: bool = False
    allow_trading_client: bool = False
    allow_order_submission: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        if self.timeframe != "1Min":
            raise ValueError("V79.26-V79.30 supports 1Min only")
        if not self.expected_symbols:
            raise ValueError("expected_symbols cannot be empty")
        if not 1 <= self.max_gap_tasks <= 1000:
            raise ValueError("max_gap_tasks out of range")
        if self.allow_network or self.allow_credentials:
            raise ValueError("default sync must remain offline")
        if self.allow_trading_client or self.allow_order_submission:
            raise ValueError("trading and order APIs are prohibited")
        if self.actual_orders_submitted != 0:
            raise ValueError("actual orders must remain zero")


@dataclass(frozen=True)
class SyncCheckpoint:
    stage: str
    symbol: str
    timeframe: str
    last_timestamp: str
    row_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GapFillTask:
    stage: str
    symbol: str
    timeframe: str
    start: str
    end: str
    expected_bar_count: int
    status: str = "PENDING"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_existing_dataset(path: Path) -> list[IngestionBar]:
    if not path.is_file():
        raise FileNotFoundError(f"dataset missing: {path}")
    rows: list[IngestionBar] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(IngestionBar(**json.loads(line)))
        except Exception as exc:
            raise ValueError(f"invalid JSONL row at line {line_no}") from exc
    return sorted(rows, key=lambda row: row.primary_key)


def build_checkpoints(rows: Iterable[IngestionBar]) -> dict[str, SyncCheckpoint]:
    grouped: dict[str, list[IngestionBar]] = {}
    for row in rows:
        grouped.setdefault(row.symbol, []).append(row)
    checkpoints: dict[str, SyncCheckpoint] = {}
    for symbol, items in grouped.items():
        ordered = sorted(items, key=lambda row: parse_utc(row.timestamp))
        checkpoints[symbol] = SyncCheckpoint(
            stage="V79.26",
            symbol=symbol,
            timeframe=ordered[-1].timeframe,
            last_timestamp=ordered[-1].timestamp,
            row_count=len(ordered),
        )
    return checkpoints


def merge_incremental_rows(
    existing: Iterable[IngestionBar],
    incoming: Iterable[IngestionBar],
) -> tuple[list[IngestionBar], dict[str, int]]:
    merged: dict[tuple[str, str, str], IngestionBar] = {}
    existing_count = 0
    incoming_count = 0
    duplicate_count = 0
    stale_count = 0

    checkpoints = build_checkpoints(existing)
    for row in existing:
        merged[row.primary_key] = row
        existing_count += 1

    for row in incoming:
        incoming_count += 1
        checkpoint = checkpoints.get(row.symbol)
        if checkpoint and parse_utc(row.timestamp) <= parse_utc(checkpoint.last_timestamp):
            if row.primary_key in merged:
                if merged[row.primary_key] != row:
                    raise ValueError("conflicting incremental duplicate")
                duplicate_count += 1
            else:
                stale_count += 1
            continue
        if row.primary_key in merged:
            if merged[row.primary_key] != row:
                raise ValueError("conflicting primary key")
            duplicate_count += 1
            continue
        merged[row.primary_key] = row

    ordered = sorted(merged.values(), key=lambda row: row.primary_key)
    return ordered, {
        "existing_row_count": existing_count,
        "incoming_row_count": incoming_count,
        "merged_row_count": len(ordered),
        "new_row_count": len(ordered) - existing_count,
        "duplicate_row_count": duplicate_count,
        "stale_row_count": stale_count,
    }


def detect_missing_bars(
    rows: Iterable[IngestionBar],
    *,
    step: timedelta = timedelta(minutes=1),
) -> list[tuple[str, datetime, datetime, int]]:
    grouped: dict[str, list[datetime]] = {}
    for row in rows:
        grouped.setdefault(row.symbol, []).append(parse_utc(row.timestamp))

    gaps: list[tuple[str, datetime, datetime, int]] = []
    for symbol, timestamps in grouped.items():
        ordered = sorted(set(timestamps))
        for current, following in zip(ordered, ordered[1:]):
            delta = following - current
            if delta > step:
                missing = int(delta / step) - 1
                gaps.append((symbol, current + step, following - step, missing))
    return gaps


def build_gap_fill_queue(
    gaps: Iterable[tuple[str, datetime, datetime, int]],
    config: IncrementalSyncConfig,
) -> list[GapFillTask]:
    config.validate()
    tasks: list[GapFillTask] = []
    for symbol, start, end, count in gaps:
        tasks.append(
            GapFillTask(
                stage="V79.28",
                symbol=symbol,
                timeframe=config.timeframe,
                start=utc_text(start),
                end=utc_text(end),
                expected_bar_count=count,
            )
        )
    if len(tasks) > config.max_gap_tasks:
        raise ValueError("gap-fill queue exceeds configured maximum")
    return tasks


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", delete=False, dir=path.parent, prefix=path.name, suffix=".tmp"
    ) as handle:
        handle.write(data)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def write_incremental_dataset(
    output_dir: Path,
    config: IncrementalSyncConfig,
    rows: list[IngestionBar],
    checkpoints: dict[str, SyncCheckpoint],
    gap_tasks: list[GapFillTask],
    stats: dict[str, int],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / f"{config.dataset_name}.jsonl"
    checkpoint_path = output_dir / f"{config.dataset_name}.checkpoints.json"
    queue_path = output_dir / f"{config.dataset_name}.gap_fill_queue.json"

    dataset_bytes = "".join(
        json.dumps(row.to_dict(), sort_keys=True, ensure_ascii=False) + "\n"
        for row in rows
    ).encode("utf-8")
    checkpoint_doc = {
        "stage": "V79.27",
        "checkpoints": {
            symbol: checkpoint.to_dict()
            for symbol, checkpoint in sorted(checkpoints.items())
        },
    }
    checkpoint_bytes = (
        json.dumps(checkpoint_doc, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    queue_doc = {
        "stage": "V79.28",
        "task_count": len(gap_tasks),
        "tasks": [task.to_dict() for task in gap_tasks],
    }
    queue_bytes = (json.dumps(queue_doc, indent=2, sort_keys=True) + "\n").encode("utf-8")

    _atomic_write(dataset_path, dataset_bytes)
    _atomic_write(checkpoint_path, checkpoint_bytes)
    _atomic_write(queue_path, queue_bytes)

    manifest = {
        "schema_version": "v79.29.incremental_sync_manifest.1",
        "stage": "V79.29",
        "dataset_name": config.dataset_name,
        "timeframe": config.timeframe,
        "row_count": len(rows),
        "checkpoint_count": len(checkpoints),
        "gap_task_count": len(gap_tasks),
        "stats": stats,
        "files": {
            "dataset": {
                "relative_path": dataset_path.name,
                "sha256": sha256_bytes(dataset_bytes),
                "byte_size": len(dataset_bytes),
            },
            "checkpoints": {
                "relative_path": checkpoint_path.name,
                "sha256": sha256_bytes(checkpoint_bytes),
                "byte_size": len(checkpoint_bytes),
            },
            "gap_fill_queue": {
                "relative_path": queue_path.name,
                "sha256": sha256_bytes(queue_bytes),
                "byte_size": len(queue_bytes),
            },
        },
        "atomic_write_used": True,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    manifest["manifest_sha256"] = sha256_json(manifest)
    write_json(output_dir / f"{config.dataset_name}.incremental_manifest.json", manifest)
    return manifest


def verify_incremental_manifest(output_dir: Path, manifest: dict[str, Any]) -> bool:
    for info in manifest["files"].values():
        path = output_dir / info["relative_path"]
        if not path.is_file():
            raise ValueError("incremental output missing")
        data = path.read_bytes()
        if sha256_bytes(data) != info["sha256"]:
            raise ValueError("incremental output hash mismatch")
        if len(data) != info["byte_size"]:
            raise ValueError("incremental output size mismatch")
    return True


def run_incremental_sync(
    existing_rows: Iterable[IngestionBar],
    incoming_rows: Iterable[IngestionBar],
    config: IncrementalSyncConfig,
    output_dir: Path,
) -> dict[str, Any]:
    config.validate()
    merged, stats = merge_incremental_rows(existing_rows, incoming_rows)
    gaps = detect_missing_bars(merged)
    tasks = build_gap_fill_queue(gaps, config)
    checkpoints = build_checkpoints(merged)
    manifest = write_incremental_dataset(
        output_dir, config, merged, checkpoints, tasks, stats
    )
    verify_incremental_manifest(output_dir, manifest)
    return {
        "stage": "V79.29",
        "status": "PASS",
        "stats": stats,
        "checkpoint_count": len(checkpoints),
        "gap_task_count": len(tasks),
        "gap_expected_bar_count": sum(task.expected_bar_count for task in tasks),
        "checkpoints": {
            symbol: checkpoint.to_dict()
            for symbol, checkpoint in sorted(checkpoints.items())
        },
        "gap_fill_queue": [task.to_dict() for task in tasks],
        "manifest": manifest,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }


def build_incremental_sync_certificate(
    repository_root: Path,
    output_dir: Path,
    config: IncrementalSyncConfig,
    result: dict[str, Any],
) -> dict[str, Any]:
    config.validate()
    checks = {
        "v79_25_certificate_present": (
            repository_root
            / "release/v79_25/output/historical_ingestion_certificate_v79_25.json"
        ).is_file(),
        "sync_status_pass": result.get("status") == "PASS",
        "new_rows_added": result.get("stats", {}).get("new_row_count", 0) > 0,
        "all_expected_checkpoints_present": sorted(result["checkpoints"]) == sorted(config.expected_symbols),
        "gap_queue_created": result.get("gap_task_count", 0) > 0,
        "manifest_hash_present": len(result["manifest"].get("manifest_sha256", "")) == 64,
        "atomic_write_used": result["manifest"].get("atomic_write_used") is True,
        "network_requests_zero": result.get("network_requests_executed") == 0,
        "credentials_unused": result.get("credentials_used") == 0,
        "trading_client_not_created": result.get("trading_client_created") is False,
        "actual_orders_zero": result.get("actual_orders_submitted") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failed else "FAIL"
    cert = {
        "schema_version": "v79.30.incremental_sync_certificate.1",
        "stage": "V79.30",
        "status": status,
        "scope": "OFFLINE_HISTORICAL_INCREMENTAL_SYNC",
        "stages_completed": ["V79.26", "V79.27", "V79.28", "V79.29", "V79.30"],
        "passed_stage_count": 5 if status == "PASS" else 5 - len(failed),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "config": asdict(config),
        "sync_summary": {
            **result["stats"],
            "checkpoint_count": result["checkpoint_count"],
            "gap_task_count": result["gap_task_count"],
            "gap_expected_bar_count": result["gap_expected_bar_count"],
        },
        "checkpoints": result["checkpoints"],
        "gap_fill_queue": result["gap_fill_queue"],
        "incremental_manifest": result["manifest"],
        "checks": checks,
        "failed_checks": failed,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": "V79_31_HISTORICAL_GAP_FILL_EXECUTION",
    }
    cert["certificate_sha256"] = sha256_json(cert)
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "historical_incremental_sync_certificate_v79_30.json"
    write_json(cert_path, cert)
    verify = {
        "stage": "V79.30",
        "status": status,
        "verified": not failed,
        "certificate_sha256": cert["certificate_sha256"],
        "certificate_path": str(cert_path.relative_to(repository_root)).replace("\\", "/"),
        "failed_checks": failed,
        "next_phase": cert["next_phase"],
    }
    verify["verification_sha256"] = sha256_json(verify)
    write_json(output_dir / "historical_incremental_sync_verification_v79_30.json", verify)
    return cert
