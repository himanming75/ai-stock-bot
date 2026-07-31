from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import shutil
import tempfile


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
class RetentionConfig:
    stage: str = "V79.46"
    minimum_versions_to_keep: int = 1
    maximum_active_versions: int = 5
    preserve_active_version: bool = True
    archive_before_delete: bool = True
    allow_physical_delete: bool = False
    dry_run: bool = False
    allow_network: bool = False
    allow_credentials: bool = False
    allow_trading_client: bool = False
    allow_order_submission: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        if not 1 <= self.minimum_versions_to_keep <= self.maximum_active_versions:
            raise ValueError("invalid retention count range")
        if not self.preserve_active_version:
            raise ValueError("active version must always be preserved")
        if not self.archive_before_delete:
            raise ValueError("archive-before-delete is required")
        if self.allow_physical_delete:
            raise ValueError("physical deletion is prohibited in V79.46-V79.50")
        if self.allow_network or self.allow_credentials:
            raise ValueError("retention must remain offline")
        if self.allow_trading_client or self.allow_order_submission:
            raise ValueError("trading and order APIs are prohibited")
        if self.actual_orders_submitted != 0:
            raise ValueError("actual orders must remain zero")


@dataclass(frozen=True)
class RetentionAction:
    version_id: str
    action: str
    reason: str
    protected: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_version_certificate(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"version certificate missing: {path}")
    cert = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(cert)
    expected = unsigned.pop("certificate_sha256", None)
    if expected != sha256_json(unsigned):
        raise ValueError("version certificate hash mismatch")
    if cert.get("stage") != "V79.45" or cert.get("status") != "PASS":
        raise ValueError("V79.45 version certificate is not PASS")
    return cert


def load_version_registry(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"version registry missing: {path}")
    registry = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(registry)
    expected = unsigned.pop("registry_sha256", None)
    if expected != sha256_json(unsigned):
        raise ValueError("version registry hash mismatch")
    versions = registry.get("versions")
    if not isinstance(versions, list):
        raise ValueError("invalid version registry")
    if registry.get("version_count") != len(versions):
        raise ValueError("version registry count mismatch")
    active = registry.get("active_version_id")
    if active not in {item.get("version_id") for item in versions}:
        raise ValueError("active version missing from registry")
    return registry


def inventory_versions(
    versions_dir: Path,
    registry: dict[str, Any],
) -> dict[str, Any]:
    registry_ids = {item["version_id"] for item in registry["versions"]}
    disk_ids = {
        path.name for path in versions_dir.iterdir()
        if path.is_dir()
    } if versions_dir.is_dir() else set()

    missing_on_disk = sorted(registry_ids - disk_ids)
    unregistered_on_disk = sorted(disk_ids - registry_ids)
    if missing_on_disk or unregistered_on_disk:
        raise ValueError("version inventory and registry are inconsistent")

    entries = []
    total_bytes = 0
    for item in sorted(registry["versions"], key=lambda value: value["version_id"]):
        version_dir = versions_dir / item["version_id"]
        dataset_path = version_dir / "alpaca_historical_bars.jsonl"
        metadata_path = version_dir / "version_metadata.json"
        if not dataset_path.is_file() or not metadata_path.is_file():
            raise ValueError("version directory is incomplete")
        dataset_bytes = dataset_path.read_bytes()
        if sha256_bytes(dataset_bytes) != item["dataset_sha256"]:
            raise ValueError("version dataset hash mismatch")
        total_bytes += dataset_path.stat().st_size + metadata_path.stat().st_size
        entries.append({
            "version_id": item["version_id"],
            "status": item["status"],
            "row_count": item["row_count"],
            "dataset_sha256": item["dataset_sha256"],
            "dataset_byte_size": dataset_path.stat().st_size,
            "metadata_byte_size": metadata_path.stat().st_size,
            "is_active": item["version_id"] == registry["active_version_id"],
        })
    return {
        "stage": "V79.47",
        "version_count": len(entries),
        "active_version_id": registry["active_version_id"],
        "total_version_bytes": total_bytes,
        "missing_on_disk_count": 0,
        "unregistered_on_disk_count": 0,
        "versions": entries,
    }


def build_retention_plan(
    inventory: dict[str, Any],
    config: RetentionConfig,
) -> dict[str, Any]:
    config.validate()
    versions = list(inventory["versions"])
    active_id = inventory["active_version_id"]

    ordered = sorted(
        versions,
        key=lambda item: (not item["is_active"], item["version_id"]),
    )
    protected_ids = {active_id}
    for item in ordered:
        if len(protected_ids) >= config.minimum_versions_to_keep:
            break
        protected_ids.add(item["version_id"])

    additional_keep_slots = max(0, config.maximum_active_versions - len(protected_ids))
    for item in sorted(versions, key=lambda value: value["version_id"], reverse=True):
        if item["version_id"] in protected_ids:
            continue
        if additional_keep_slots <= 0:
            break
        protected_ids.add(item["version_id"])
        additional_keep_slots -= 1

    actions: list[RetentionAction] = []
    for item in sorted(versions, key=lambda value: value["version_id"]):
        version_id = item["version_id"]
        if version_id == active_id:
            actions.append(RetentionAction(
                version_id, "KEEP", "ACTIVE_VERSION", True
            ))
        elif version_id in protected_ids:
            actions.append(RetentionAction(
                version_id, "KEEP", "WITHIN_RETENTION_LIMIT", True
            ))
        else:
            actions.append(RetentionAction(
                version_id, "ARCHIVE", "EXCEEDS_ACTIVE_RETENTION_LIMIT", False
            ))

    if not any(item.version_id == active_id and item.action == "KEEP" for item in actions):
        raise ValueError("retention plan does not preserve active version")

    return {
        "schema_version": "v79.48.retention_plan.1",
        "stage": "V79.48",
        "active_version_id": active_id,
        "version_count": len(versions),
        "keep_count": sum(item.action == "KEEP" for item in actions),
        "archive_count": sum(item.action == "ARCHIVE" for item in actions),
        "delete_count": 0,
        "physical_delete_allowed": False,
        "actions": [item.to_dict() for item in actions],
    }


def execute_retention_plan(
    versions_dir: Path,
    archive_dir: Path,
    plan: dict[str, Any],
    config: RetentionConfig,
) -> dict[str, Any]:
    config.validate()
    archive_dir.mkdir(parents=True, exist_ok=True)
    ledger_entries = []
    archived_count = 0

    for action in plan["actions"]:
        version_id = action["version_id"]
        source = versions_dir / version_id
        target = archive_dir / version_id
        if action["action"] == "KEEP":
            if not source.is_dir():
                raise ValueError("kept version directory missing")
            ledger_entries.append({
                "version_id": version_id,
                "requested_action": "KEEP",
                "executed_action": "KEEP",
                "status": "PASS",
            })
            continue

        if action["action"] != "ARCHIVE":
            raise ValueError("unsupported retention action")
        if action["protected"]:
            raise ValueError("protected version cannot be archived")
        if not source.is_dir():
            raise ValueError("archive source version missing")
        if target.exists():
            if not target.is_dir():
                raise ValueError("archive target conflict")
            executed = "ARCHIVE_REUSED"
        else:
            shutil.copytree(source, target)
            executed = "ARCHIVE_COPY"
        archived_count += 1
        ledger_entries.append({
            "version_id": version_id,
            "requested_action": "ARCHIVE",
            "executed_action": executed,
            "status": "PASS",
            "source_preserved": True,
        })

    ledger = {
        "schema_version": "v79.49.retention_execution_ledger.1",
        "stage": "V79.49",
        "status": "PASS",
        "kept_version_count": plan["keep_count"],
        "archived_version_count": archived_count,
        "deleted_version_count": 0,
        "source_versions_preserved": True,
        "entries": ledger_entries,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    ledger["ledger_sha256"] = sha256_json(ledger)
    return ledger


def write_retention_outputs(
    output_dir: Path,
    inventory: dict[str, Any],
    plan: dict[str, Any],
    ledger: dict[str, Any],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory_path = output_dir / "dataset_retention_inventory.json"
    plan_path = output_dir / "dataset_retention_plan.json"
    ledger_path = output_dir / "dataset_retention_execution_ledger.json"

    write_json(inventory_path, inventory)
    write_json(plan_path, plan)
    write_json(ledger_path, ledger)

    manifest = {
        "schema_version": "v79.49.retention_manifest.1",
        "stage": "V79.49",
        "active_version_id": inventory["active_version_id"],
        "version_count": inventory["version_count"],
        "keep_count": plan["keep_count"],
        "archive_count": plan["archive_count"],
        "delete_count": 0,
        "source_versions_preserved": ledger["source_versions_preserved"],
        "files": {},
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    for name, path in (
        ("inventory", inventory_path),
        ("plan", plan_path),
        ("execution_ledger", ledger_path),
    ):
        data = path.read_bytes()
        manifest["files"][name] = {
            "relative_path": path.name,
            "sha256": sha256_bytes(data),
            "byte_size": len(data),
        }
    manifest["manifest_sha256"] = sha256_json(manifest)
    write_json(output_dir / "dataset_retention_manifest_v79_49.json", manifest)
    return manifest


def verify_retention_manifest(output_dir: Path, manifest: dict[str, Any]) -> bool:
    unsigned = dict(manifest)
    expected = unsigned.pop("manifest_sha256", None)
    if expected != sha256_json(unsigned):
        raise ValueError("retention manifest self-hash mismatch")
    for info in manifest["files"].values():
        path = output_dir / info["relative_path"]
        if not path.is_file():
            raise ValueError("retention output missing")
        data = path.read_bytes()
        if sha256_bytes(data) != info["sha256"] or len(data) != info["byte_size"]:
            raise ValueError("retention output integrity mismatch")
    return True


def run_dataset_retention(
    registry_path: Path,
    versions_dir: Path,
    version_certificate_path: Path,
    config: RetentionConfig,
    output_dir: Path,
) -> dict[str, Any]:
    config.validate()
    validate_version_certificate(version_certificate_path)
    registry = load_version_registry(registry_path)
    inventory = inventory_versions(versions_dir, registry)
    plan = build_retention_plan(inventory, config)
    ledger = execute_retention_plan(
        versions_dir, output_dir / "archive", plan, config
    )
    manifest = write_retention_outputs(output_dir, inventory, plan, ledger)
    verify_retention_manifest(output_dir, manifest)
    return {
        "stage": "V79.49",
        "status": "PASS",
        "inventory": inventory,
        "plan": plan,
        "ledger": ledger,
        "manifest": manifest,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }


def build_retention_certificate(
    repository_root: Path,
    output_dir: Path,
    config: RetentionConfig,
    result: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "v79_45_certificate_present": (
            repository_root
            / "release/v79_45/output/historical_dataset_version_certificate_v79_45.json"
        ).is_file(),
        "retention_status_pass": result["status"] == "PASS",
        "active_version_preserved": any(
            item["version_id"] == result["inventory"]["active_version_id"]
            and item["executed_action"] == "KEEP"
            for item in result["ledger"]["entries"]
        ),
        "minimum_versions_preserved": (
            result["ledger"]["kept_version_count"] >= config.minimum_versions_to_keep
        ),
        "physical_deletes_zero": result["ledger"]["deleted_version_count"] == 0,
        "source_versions_preserved": result["ledger"]["source_versions_preserved"] is True,
        "manifest_hash_present": len(result["manifest"].get("manifest_sha256", "")) == 64,
        "network_requests_zero": result["network_requests_executed"] == 0,
        "credentials_unused": result["credentials_used"] == 0,
        "trading_client_not_created": result["trading_client_created"] is False,
        "actual_orders_zero": result["actual_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failed else "FAIL"
    cert = {
        "schema_version": "v79.50.retention_certificate.1",
        "stage": "V79.50",
        "status": status,
        "scope": "OFFLINE_HISTORICAL_DATASET_RETENTION",
        "stages_completed": ["V79.46", "V79.47", "V79.48", "V79.49", "V79.50"],
        "passed_stage_count": 5 if status == "PASS" else max(0, 5 - len(failed)),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "config": asdict(config),
        "retention_summary": {
            "active_version_id": result["inventory"]["active_version_id"],
            "version_count": result["inventory"]["version_count"],
            "kept_version_count": result["ledger"]["kept_version_count"],
            "archived_version_count": result["ledger"]["archived_version_count"],
            "deleted_version_count": result["ledger"]["deleted_version_count"],
            "source_versions_preserved": result["ledger"]["source_versions_preserved"],
        },
        "retention_manifest": result["manifest"],
        "checks": checks,
        "failed_checks": failed,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": "V79_51_HISTORICAL_DATASET_RECOVERY",
    }
    cert["certificate_sha256"] = sha256_json(cert)
    cert_path = output_dir / "historical_dataset_retention_certificate_v79_50.json"
    write_json(cert_path, cert)
    write_json(
        output_dir / "historical_dataset_retention_verify_v79_50.json",
        {
            "stage": "V79.50",
            "status": status,
            "verified": not failed,
            "certificate_sha256": cert["certificate_sha256"],
            "certificate_path": str(cert_path.relative_to(repository_root)).replace("\\", "/"),
            "failed_checks": failed,
        },
    )
    return cert


sha256_retention_json = sha256_json
