from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
import os
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
class DatasetVersionConfig:
    stage: str = "V79.41"
    dataset_name: str = "alpaca_historical_bars"
    version_prefix: str = "hist"
    hash_prefix_length: int = 16
    require_quality_certificate: bool = True
    immutable_versions: bool = True
    allow_network: bool = False
    allow_credentials: bool = False
    allow_trading_client: bool = False
    allow_order_submission: bool = False
    actual_orders_submitted: int = 0

    def validate(self) -> None:
        if not self.dataset_name or not self.version_prefix:
            raise ValueError("dataset_name and version_prefix are required")
        if not 12 <= self.hash_prefix_length <= 64:
            raise ValueError("hash_prefix_length out of range")
        if not self.require_quality_certificate or not self.immutable_versions:
            raise ValueError("quality gate and immutable versions are required")
        if self.allow_network or self.allow_credentials:
            raise ValueError("dataset versioning must remain offline")
        if self.allow_trading_client or self.allow_order_submission:
            raise ValueError("trading and order APIs are prohibited")
        if self.actual_orders_submitted != 0:
            raise ValueError("actual orders must remain zero")


@dataclass(frozen=True)
class DatasetFingerprint:
    stage: str
    dataset_name: str
    byte_size: int
    row_count: int
    sha256: str
    version_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_quality_certificate(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"quality certificate missing: {path}")
    cert = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(cert)
    expected_hash = unsigned.pop("certificate_sha256", None)
    if expected_hash != sha256_json(unsigned):
        raise ValueError("quality certificate hash mismatch")
    if cert.get("stage") != "V79.40" or cert.get("status") != "PASS":
        raise ValueError("V79.40 quality certificate is not PASS")
    summary = cert.get("quality_summary", {})
    if summary.get("issue_count") != 0 or summary.get("pending_repair_count") != 0:
        raise ValueError("quality certificate contains unresolved issues")
    return cert


def fingerprint_dataset(
    dataset_path: Path, config: DatasetVersionConfig
) -> DatasetFingerprint:
    config.validate()
    if not dataset_path.is_file():
        raise FileNotFoundError(f"dataset missing: {dataset_path}")
    data = dataset_path.read_bytes()
    if not data:
        raise ValueError("dataset cannot be empty")
    lines = [line for line in data.splitlines() if line.strip()]
    for line_no, line in enumerate(lines, 1):
        try:
            json.loads(line)
        except Exception as exc:
            raise ValueError(f"invalid dataset JSONL at line {line_no}") from exc
    digest = sha256_bytes(data)
    version_id = f"{config.version_prefix}-{digest[:config.hash_prefix_length]}"
    return DatasetFingerprint(
        stage="V79.41",
        dataset_name=config.dataset_name,
        byte_size=len(data),
        row_count=len(lines),
        sha256=digest,
        version_id=version_id,
    )


def build_version_metadata(
    fingerprint: DatasetFingerprint,
    quality_certificate: dict[str, Any],
) -> dict[str, Any]:
    metadata = {
        "schema_version": "v79.42.dataset_version_metadata.1",
        "stage": "V79.42",
        "version_id": fingerprint.version_id,
        "dataset_name": fingerprint.dataset_name,
        "dataset_sha256": fingerprint.sha256,
        "dataset_byte_size": fingerprint.byte_size,
        "dataset_row_count": fingerprint.row_count,
        "quality_certificate_sha256": quality_certificate["certificate_sha256"],
        "quality_stage": quality_certificate["stage"],
        "quality_status": quality_certificate["status"],
        "immutable": True,
        "source_stage": "V79.40",
    }
    metadata["metadata_sha256"] = sha256_json(metadata)
    return metadata


def create_immutable_version(
    dataset_path: Path,
    versions_dir: Path,
    fingerprint: DatasetFingerprint,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    version_dir = versions_dir / fingerprint.version_id
    dataset_target = version_dir / f"{fingerprint.dataset_name}.jsonl"
    metadata_target = version_dir / "version_metadata.json"
    source_bytes = dataset_path.read_bytes()
    metadata_bytes = (
        json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")

    if version_dir.exists():
        if not dataset_target.is_file() or not metadata_target.is_file():
            raise ValueError("existing version directory is incomplete")
        if dataset_target.read_bytes() != source_bytes:
            raise ValueError("immutable dataset version conflict")
        if json.loads(metadata_target.read_text(encoding="utf-8")) != metadata:
            raise ValueError("immutable version metadata conflict")
        return {
            "version_id": fingerprint.version_id,
            "created": False,
            "reused_existing_version": True,
            "dataset_relative_path": f"{fingerprint.version_id}/{dataset_target.name}",
            "metadata_relative_path": f"{fingerprint.version_id}/{metadata_target.name}",
        }

    version_dir.mkdir(parents=True, exist_ok=False)
    _atomic_write(dataset_target, source_bytes)
    _atomic_write(metadata_target, metadata_bytes)
    return {
        "version_id": fingerprint.version_id,
        "created": True,
        "reused_existing_version": False,
        "dataset_relative_path": f"{fingerprint.version_id}/{dataset_target.name}",
        "metadata_relative_path": f"{fingerprint.version_id}/{metadata_target.name}",
    }


def update_version_registry(
    registry_path: Path,
    fingerprint: DatasetFingerprint,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if registry_path.is_file():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    else:
        registry = {
            "schema_version": "v79.43.dataset_version_registry.1",
            "stage": "V79.43",
            "dataset_name": fingerprint.dataset_name,
            "versions": [],
        }

    versions = registry.get("versions")
    if not isinstance(versions, list):
        raise ValueError("invalid version registry")
    matching = [item for item in versions if item.get("version_id") == fingerprint.version_id]
    entry = {
        "version_id": fingerprint.version_id,
        "dataset_sha256": fingerprint.sha256,
        "metadata_sha256": metadata["metadata_sha256"],
        "row_count": fingerprint.row_count,
        "byte_size": fingerprint.byte_size,
        "status": "ACTIVE",
    }
    if matching:
        if matching[0] != entry:
            raise ValueError("version registry conflict")
    else:
        versions.append(entry)
    versions.sort(key=lambda item: item["version_id"])
    registry["version_count"] = len(versions)
    registry["active_version_id"] = fingerprint.version_id
    unsigned = dict(registry)
    unsigned.pop("registry_sha256", None)
    registry["registry_sha256"] = sha256_json(unsigned)
    write_json(registry_path, registry)
    return registry


def build_version_manifest(
    output_dir: Path,
    versions_dir: Path,
    fingerprint: DatasetFingerprint,
    version_result: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    dataset_path = versions_dir / version_result["dataset_relative_path"]
    metadata_path = versions_dir / version_result["metadata_relative_path"]
    registry_path = output_dir / "dataset_version_registry.json"
    manifest = {
        "schema_version": "v79.44.dataset_version_manifest.1",
        "stage": "V79.44",
        "version_id": fingerprint.version_id,
        "fingerprint": fingerprint.to_dict(),
        "version_result": version_result,
        "registry_version_count": registry["version_count"],
        "active_version_id": registry["active_version_id"],
        "files": {
            "versioned_dataset": {
                "relative_path": str(dataset_path.relative_to(output_dir)).replace("\\", "/"),
                "sha256": sha256_bytes(dataset_path.read_bytes()),
                "byte_size": dataset_path.stat().st_size,
            },
            "version_metadata": {
                "relative_path": str(metadata_path.relative_to(output_dir)).replace("\\", "/"),
                "sha256": sha256_bytes(metadata_path.read_bytes()),
                "byte_size": metadata_path.stat().st_size,
            },
            "registry": {
                "relative_path": registry_path.name,
                "sha256": sha256_bytes(registry_path.read_bytes()),
                "byte_size": registry_path.stat().st_size,
            },
        },
        "immutable_version": True,
        "deterministic_version_id": True,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }
    manifest["manifest_sha256"] = sha256_json(manifest)
    write_json(output_dir / "dataset_version_manifest_v79_44.json", manifest)
    return manifest


def verify_version_manifest(output_dir: Path, manifest: dict[str, Any]) -> bool:
    unsigned = dict(manifest)
    expected = unsigned.pop("manifest_sha256", None)
    if expected != sha256_json(unsigned):
        raise ValueError("version manifest self-hash mismatch")
    for info in manifest["files"].values():
        path = output_dir / info["relative_path"]
        if not path.is_file():
            raise ValueError("version output missing")
        data = path.read_bytes()
        if sha256_bytes(data) != info["sha256"] or len(data) != info["byte_size"]:
            raise ValueError("version output integrity mismatch")
    return True


def run_dataset_versioning(
    dataset_path: Path,
    quality_certificate_path: Path,
    config: DatasetVersionConfig,
    output_dir: Path,
) -> dict[str, Any]:
    config.validate()
    quality_cert = validate_quality_certificate(quality_certificate_path)
    fingerprint = fingerprint_dataset(dataset_path, config)
    metadata = build_version_metadata(fingerprint, quality_cert)
    versions_dir = output_dir / "versions"
    version_result = create_immutable_version(
        dataset_path, versions_dir, fingerprint, metadata
    )
    registry = update_version_registry(
        output_dir / "dataset_version_registry.json", fingerprint, metadata
    )
    manifest = build_version_manifest(
        output_dir, versions_dir, fingerprint, version_result, registry
    )
    verify_version_manifest(output_dir, manifest)
    return {
        "stage": "V79.44",
        "status": "PASS",
        "fingerprint": fingerprint.to_dict(),
        "metadata": metadata,
        "version_result": version_result,
        "registry": registry,
        "manifest": manifest,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
    }


def build_version_certificate(
    repository_root: Path,
    output_dir: Path,
    config: DatasetVersionConfig,
    result: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "v79_40_certificate_present": (
            repository_root / "release/v79_40/output/historical_quality_certificate_v79_40.json"
        ).is_file(),
        "versioning_status_pass": result["status"] == "PASS",
        "version_id_deterministic": result["manifest"]["deterministic_version_id"] is True,
        "immutable_version": result["manifest"]["immutable_version"] is True,
        "dataset_hash_matches": (
            result["fingerprint"]["sha256"]
            == result["manifest"]["files"]["versioned_dataset"]["sha256"]
        ),
        "registry_active_version_matches": (
            result["registry"]["active_version_id"] == result["fingerprint"]["version_id"]
        ),
        "manifest_hash_present": len(result["manifest"].get("manifest_sha256", "")) == 64,
        "network_requests_zero": result["network_requests_executed"] == 0,
        "credentials_unused": result["credentials_used"] == 0,
        "trading_client_not_created": result["trading_client_created"] is False,
        "actual_orders_zero": result["actual_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "PASS" if not failed else "FAIL"
    cert = {
        "schema_version": "v79.45.dataset_version_certificate.1",
        "stage": "V79.45",
        "status": status,
        "scope": "OFFLINE_HISTORICAL_DATASET_VERSIONING",
        "stages_completed": ["V79.41", "V79.42", "V79.43", "V79.44", "V79.45"],
        "passed_stage_count": 5 if status == "PASS" else max(0, 5 - len(failed)),
        "failed_stage_count": 0 if status == "PASS" else len(failed),
        "config": asdict(config),
        "version_summary": {
            "version_id": result["fingerprint"]["version_id"],
            "dataset_sha256": result["fingerprint"]["sha256"],
            "row_count": result["fingerprint"]["row_count"],
            "byte_size": result["fingerprint"]["byte_size"],
            "registry_version_count": result["registry"]["version_count"],
            "active_version_id": result["registry"]["active_version_id"],
            "created": result["version_result"]["created"],
            "reused_existing_version": result["version_result"]["reused_existing_version"],
        },
        "version_manifest": result["manifest"],
        "checks": checks,
        "failed_checks": failed,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "broker_connected": False,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": "V79_46_HISTORICAL_DATASET_RETENTION",
    }
    cert["certificate_sha256"] = sha256_json(cert)
    output_dir.mkdir(parents=True, exist_ok=True)
    cert_path = output_dir / "historical_dataset_version_certificate_v79_45.json"
    write_json(cert_path, cert)
    write_json(output_dir / "historical_dataset_version_verify_v79_45.json", {
        "stage": "V79.45",
        "status": status,
        "verified": not failed,
        "certificate_sha256": cert["certificate_sha256"],
        "certificate_path": str(cert_path.relative_to(repository_root)).replace("\\", "/"),
        "failed_checks": failed,
    })
    return cert

sha256_version_json = sha256_json
