from __future__ import annotations

from dataclasses import asdict, dataclass
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
class GapFillConfig:
    stage: str = "V79.31"
    dataset_name: str = "alpaca_historical_bars"
    timeframe: str = "1Min"
    expected_symbols: tuple[str, ...] = ("AAPL", "MSFT", "SPY")
    max_gap_tasks: int = 100
    require_all_tasks_filled: bool = True
    allow_network: bool = False
    allow_credentials: bool = False
    allow_trading_client: bool = False
    allow_order_submission: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        if self.timeframe != "1Min":
            raise ValueError("V79.31-V79.35 supports 1Min only")
        if not self.expected_symbols:
            raise ValueError("expected_symbols cannot be empty")
        if not 1 <= self.max_gap_tasks <= 1000:
            raise ValueError("max_gap_tasks out of range")
        if self.allow_network or self.allow_credentials:
            raise ValueError("gap fill execution must remain offline")
        if self.allow_trading_client or self.allow_order_submission:
            raise ValueError("trading and order APIs are prohibited")
        if self.actual_orders_submitted != 0:
            raise ValueError("actual orders must remain zero")


@dataclass(frozen=True)
class GapFillExecution:
    task_index: int
    symbol: str
    timeframe: str
    start: str
    end: str
    expected_bar_count: int
    fetched_bar_count: int
    status: str
    source: str = "OFFLINE_FIXTURE"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"required file missing: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_jsonl_bars(path: Path) -> list[IngestionBar]:
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


def load_gap_tasks(queue_path: Path, config: GapFillConfig) -> list[dict[str, Any]]:
    config.validate()
    doc = load_json(queue_path)
    tasks = doc.get("tasks")
    if doc.get("stage") != "V79.28" or not isinstance(tasks, list):
        raise ValueError("invalid V79.28 gap-fill queue")
    if doc.get("task_count") != len(tasks):
        raise ValueError("gap-fill queue count mismatch")
    if len(tasks) > config.max_gap_tasks:
        raise ValueError("gap-fill queue exceeds configured maximum")

    normalized: list[dict[str, Any]] = []
    for index, task in enumerate(tasks):
        required = {"symbol", "timeframe", "start", "end", "expected_bar_count", "status"}
        if not isinstance(task, dict) or not required.issubset(task):
            raise ValueError(f"invalid gap task at index {index}")
        if task["symbol"] not in config.expected_symbols:
            raise ValueError("unexpected symbol in gap-fill queue")
        if task["timeframe"] != config.timeframe:
            raise ValueError("unexpected timeframe in gap-fill queue")
        if task["status"] != "PENDING":
            raise ValueError("only PENDING tasks may be executed")
        if int(task["expected_bar_count"]) <= 0:
            raise ValueError("expected_bar_count must be positive")
        normalized.append(dict(task))
    return normalized


def load_fixture_bars(fixture_path: Path) -> list[IngestionBar]:
    doc = load_json(fixture_path)
    rows = doc.get("rows")
    if doc.get("source") != "OFFLINE_FIXTURE" or not isinstance(rows, list):
        raise ValueError("invalid offline gap-fill fixture")
    result = [IngestionBar(**row) for row in rows]
    keys = [row.primary_key for row in result]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate primary key in gap-fill fixture")
    return sorted(result, key=lambda row: row.primary_key)


def select_fixture_rows_for_task(
    task: dict[str, Any],
    fixture_rows: Iterable[IngestionBar],
) -> list[IngestionBar]:
    selected = [
        row for row in fixture_rows
        if row.symbol == task["symbol"]
        and row.timeframe == task["timeframe"]
        and task["start"] <= row.timestamp <= task["end"]
    ]
    selected = sorted(selected, key=lambda row: row.primary_key)
    if len(selected) != int(task["expected_bar_count"]):
        raise ValueError(
            f"fixture count mismatch for {task['symbol']} "
            f"{task['start']}..{task['end']}: "
            f"expected {task['expected_bar_count']}, got {len(selected)}"
        )
    return selected


def execute_gap_fill_tasks(
    tasks: Iterable[dict[str, Any]],
    fixture_rows: Iterable[IngestionBar],
    config: GapFillConfig,
) -> tuple[list[IngestionBar], list[GapFillExecution]]:
    config.validate()
    fetched: list[IngestionBar] = []
    executions: list[GapFillExecution] = []
    fixture_rows = list(fixture_rows)

    for index, task in enumerate(tasks):
        rows = select_fixture_rows_for_task(task, fixture_rows)
        fetched.extend(rows)
        executions.append(
            GapFillExecution(
                task_index=index,
                symbol=task["symbol"],
                timeframe=task["timeframe"],
                start=task["start"],
                end=task["end"],
                expected_bar_count=int(task["expected_bar_count"]),
                fetched_bar_count=len(rows),
                status="FILLED",
            )
        )

    keys = [row.primary_key for row in fetched]
    if len(keys) != len(set(keys)):
        raise ValueError("gap-fill tasks produced overlapping rows")
    return sorted(fetched, key=lambda row: row.primary_key), executions


def merge_gap_fill_rows(
    existing_rows: Iterable[IngestionBar],
    gap_rows: Iterable[IngestionBar],
) -> tuple[list[IngestionBar], dict[str, int]]:
    merged: dict[tuple[str, str, str], IngestionBar] = {}
    existing_count = 0
    duplicate_count = 0

    for row in existing_rows:
        if row.primary_key in merged and merged[row.primary_key] != row:
            raise ValueError("conflicting duplicate in existing dataset")
        merged[row.primary_key] = row
        existing_count += 1

    gap_count = 0
    for row in gap_rows:
        gap_count += 1
        current = merged.get(row.primary_key)
        if current is not None:
            if current != row:
                raise ValueError("conflicting gap-fill primary key")
            duplicate_count += 1
            continue
        merged[row.primary_key] = row

    ordered = sorted(merged.values(), key=lambda row: row.primary_key)
    return ordered, {
        "existing_row_count": existing_count,
        "gap_row_count": gap_count,
        "filled_new_row_count": len(ordered) - len(set(
            row.primary_key for row in list(existing_rows)
        )),
        "duplicate_row_count": duplicate_count,
        "merged_row_count": len(ordered),
    }


def validate_tasks_completed(
    tasks: Iterable[dict[str, Any]],
    executions: Iterable[GapFillExecution],
) -> dict[str, int]:
    tasks = list(tasks)
    executions = list(executions)
    expected = sum(int(task["expected_bar_count"]) for task in tasks)
    fetched = sum(item.fetched_bar_count for item in executions)
    completed = sum(item.status == "FILLED" for item in executions)
    if completed != len(tasks) or fetched != expected:
        raise ValueError("not all gap-fill tasks completed")
    return {
        "gap_task_count": len(tasks),
        "completed_task_count": completed,
        "expected_gap_bar_count": expected,
        "fetched_gap_bar_count": fetched,
        "remaining_gap_task_count": len(tasks) - completed,
    }


def write_gap_fill_outputs(
    output_dir: Path,
    config: GapFillConfig,
    rows: list[IngestionBar],
    executions: list[GapFillExecution],
    stats: dict[str, int],
    completion: dict[str, int],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = output_dir / f"{config.dataset_name}.gap_filled.jsonl"
    execution_path = output_dir / f"{config.dataset_name}.gap_fill_executions.json"

    dataset_bytes = "".join(
        json.dumps(row.to_dict(), sort_keys=True, ensure_ascii=False) + "\n"
        for row in rows
    ).encode("utf-8")
    execution_doc = {
        "stage": "V79.32",
        **completion,
        "executions": [item.to_dict() for item in executions],
    }
    execution_bytes = (
        json.dumps(execution_doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")

    _atomic_write(dataset_path, dataset_bytes)
    _atomic_write(execution_path, execution_bytes)

    manifest = {
        "schema_version": "v79.34.gap_fill_manifest.1",
        "stage": "V79.34",
        "dataset_name": config.dataset_name,
        "timeframe": config.timeframe,
        "row_count": len(rows),
        "stats": stats,
        "completion": completion,
        "files": {
            "dataset": {
                "relative_path": dataset_path.name,
                "sha256": sha256_bytes(dataset_bytes),
                "byte_size": len(dataset_bytes),
            },
            "executions": {
                "relative_path": execution_path.name,
                "sha256": sha256_bytes(execution_bytes),
                "byte_size": len(execution_bytes),
            },
        },
        "atomic_write_used": True,
        "idempotent_reexecution_supported": True,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    manifest["manifest_sha256"] = sha256_json(manifest)
    write_json(output_dir / f"{config.dataset_name}.gap_fill_manifest.json", manifest)
    return manifest


def verify_gap_fill_manifest(output_dir: Path, manifest: dict[str, Any]) -> bool:
    expected_hash = manifest.get("manifest_sha256")
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256", None)
    if expected_hash != sha256_json(unsigned):
        raise ValueError("gap-fill manifest self-hash mismatch")

    for info in manifest["files"].values():
        path = output_dir / info["relative_path"]
        if not path.is_file():
            raise ValueError("gap-fill output missing")
        data = path.read_bytes()
        if sha256_bytes(data) != info["sha256"]:
            raise ValueError("gap-fill output hash mismatch")
        if len(data) != info["byte_size"]:
            raise ValueError("gap-fill output size mismatch")
    return True


def run_gap_fill(
    existing_rows: Iterable[IngestionBar],
    tasks: Iterable[dict[str, Any]],
    fixture_rows: Iterable[IngestionBar],
    config: GapFillConfig,
    output_dir: Path,
) -> dict[str, Any]:
    config.validate()
    existing_rows = list(existing_rows)
    tasks = list(tasks)
    gap_rows, executions = execute_gap_fill_tasks(tasks, fixture_rows, config)
    merged, stats = merge_gap_fill_rows(existing_rows, gap_rows)
    completion = validate_tasks_completed(tasks, executions)
    manifest = write_gap_fill_outputs(
        output_dir, config, merged, executions, stats, completion
    )
    verify_gap_fill_manifest(output_dir, manifest)
    return {
        "stage": "V79.34",
        "status": "PASS",
        "stats": stats,
        "completion": completion,
        "executions": [item.to_dict() for item in executions],
        "manifest": manifest,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }


def build_gap_fill_certificate(
    repository_root: Path,
    output_dir: Path,
    config: GapFillConfig,
    result: dict[str, Any],
) -> dict[str, Any]:
    config.validate()
    prior_certificate = (
        repository_root
        / "release/v79_30/output/historical_incremental_sync_certificate_v79_30.json"
    )
    checks = {
        "v79_30_certificate_present": prior_certificate.is_file(),
        "gap_fill_status_pass": result.get("status") == "PASS",
        "all_tasks_completed": result["completion"]["remaining_gap_task_count"] == 0,
        "expected_and_fetched_counts_match": (
            result["completion"]["expected_gap_bar_count"]
            == result["completion"]["fetched_gap_bar_count"]
        ),
        "new_rows_filled": result["stats"]["filled_new_row_count"] > 0,
        "manifest_hash_present": len(result["manifest"].get("manifest_sha256", "")) == 64,
        "atomic_write_used": result["manifest"].get("atomic_write_used") is True,
        "idempotent_reexecution_supported": (
            result["manifest"].get("idempotent_reexecution_supported") is True
        ),
        "network_requests_zero": result.get("network_requests_executed") == 0,
        "credentials_unused": result.get("credentials_used") == 0,
        "trading_client_not_created": result.get("trading_client_created") is False,
        "actual_orders_zero": result.get("actual_orders_submitted") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failed else "FAIL"
    cert = {
        "schema_version": "v79.35.gap_fill_certificate.1",
        "stage": "V79.35",
        "status": status,
        "scope": "OFFLINE_HISTORICAL_GAP_FILL_EXECUTION",
        "stages_completed": ["V79.31", "V79.32", "V79.33", "V79.34", "V79.35"],
        "passed_stage_count": 5 if status == "PASS" else max(0, 5 - len(failed)),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "config": asdict(config),
        "gap_fill_summary": {
            **result["stats"],
            **result["completion"],
        },
        "executions": result["executions"],
        "gap_fill_manifest": result["manifest"],
        "checks": checks,
        "failed_checks": failed,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": "V79_36_HISTORICAL_DATA_QUALITY_RECONCILIATION",
    }
    cert["certificate_sha256"] = sha256_json(cert)
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "historical_gap_fill_certificate_v79_35.json"
    write_json(cert_path, cert)
    write_json(
        output_dir / "historical_gap_fill_verify_v79_35.json",
        {
            "stage": "V79.35",
            "status": status,
            "verified": not failed,
            "certificate_sha256": cert["certificate_sha256"],
            "certificate_path": str(cert_path.relative_to(repository_root)).replace("\\", "/"),
            "failed_checks": failed,
        },
    )
    return cert
