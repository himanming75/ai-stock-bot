from __future__ import annotations

"""
V28.2 Offline Model Registry

Features:
- semantic model versions
- candidate / production / archived / rejected states
- parent-model lineage
- duplicate version and duplicate model-hash blocking
- promotion and rollback history
- current production model tracking
- immutable registry updates
- model fingerprint verification
- SHA-256 integrity verification
- JSON persistence and tamper detection

Safety boundary:
- no network access
- no market/account/broker APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json
import re

VERSION = "28.2"

_ALLOWED_STATUSES = {"CANDIDATE", "PRODUCTION", "ARCHIVED", "REJECTED"}
_ALLOWED_ACTIONS = {"REGISTER", "PROMOTE", "ARCHIVE", "REJECT", "ROLLBACK"}
_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class RegistryError(ValueError):
    pass


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _validate_sha256(value: str, field_name: str) -> str:
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise RegistryError(f"{field_name} must be a SHA-256 hex digest")
    return digest


def _validate_version(value: str) -> str:
    version = value.strip()
    if not _SEMVER_RE.fullmatch(version):
        raise RegistryError("model_version must use semantic versioning: MAJOR.MINOR.PATCH")
    return version


@dataclass(frozen=True)
class ModelRecord:
    model_id: str
    model_version: str
    model_hash: str
    experiment_id: str
    pipeline_version: str
    dataset_hash: str
    feature_schema_hash: str
    parent_model_id: str
    status: str
    metadata: tuple[tuple[str, str], ...]
    fingerprint: str
    record_hash: str


@dataclass(frozen=True)
class RegistryEvent:
    sequence: int
    action: str
    model_id: str
    previous_production_id: str
    note: str
    event_hash: str


@dataclass(frozen=True)
class ModelRegistry:
    version: str
    records: tuple[ModelRecord, ...]
    events: tuple[RegistryEvent, ...]
    production_model_id: str
    registry_hash: str


def _record_payload(record: ModelRecord, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "model_id": record.model_id,
        "model_version": record.model_version,
        "model_hash": record.model_hash,
        "experiment_id": record.experiment_id,
        "pipeline_version": record.pipeline_version,
        "dataset_hash": record.dataset_hash,
        "feature_schema_hash": record.feature_schema_hash,
        "parent_model_id": record.parent_model_id,
        "status": record.status,
        "metadata": dict(record.metadata),
        "fingerprint": record.fingerprint,
    }
    if include_hash:
        payload["record_hash"] = record.record_hash
    return payload


def _event_payload(event: RegistryEvent, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "sequence": event.sequence,
        "action": event.action,
        "model_id": event.model_id,
        "previous_production_id": event.previous_production_id,
        "note": event.note,
    }
    if include_hash:
        payload["event_hash"] = event.event_hash
    return payload


def _registry_payload(registry: ModelRegistry, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": registry.version,
        "records": [_record_payload(record, include_hash=True) for record in registry.records],
        "events": [_event_payload(event, include_hash=True) for event in registry.events],
        "production_model_id": registry.production_model_id,
    }
    if include_hash:
        payload["registry_hash"] = registry.registry_hash
    return payload


def _fingerprint_payload(
    *,
    model_version: str,
    model_hash: str,
    experiment_id: str,
    pipeline_version: str,
    dataset_hash: str,
    feature_schema_hash: str,
    parent_model_id: str,
    metadata: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    return {
        "model_version": model_version,
        "model_hash": model_hash,
        "experiment_id": experiment_id,
        "pipeline_version": pipeline_version,
        "dataset_hash": dataset_hash,
        "feature_schema_hash": feature_schema_hash,
        "parent_model_id": parent_model_id,
        "metadata": dict(metadata),
    }


def create_model_record(
    *,
    model_version: str,
    model_hash: str,
    experiment_id: str,
    pipeline_version: str,
    dataset_hash: str,
    feature_schema_hash: str,
    parent_model_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> ModelRecord:
    version = _validate_version(model_version)
    model_digest = _validate_sha256(model_hash, "model_hash")
    dataset_digest = _validate_sha256(dataset_hash, "dataset_hash")
    schema_digest = _validate_sha256(feature_schema_hash, "feature_schema_hash")

    experiment = experiment_id.strip()
    pipeline = pipeline_version.strip()
    parent = parent_model_id.strip()
    if not experiment.startswith("EXP-"):
        raise RegistryError("experiment_id must start with EXP-")
    if not pipeline:
        raise RegistryError("pipeline_version is required")

    metadata_items = tuple(sorted(
        (str(key).strip(), str(value))
        for key, value in (metadata or {}).items()
    ))
    if any(not key for key, _ in metadata_items):
        raise RegistryError("metadata keys cannot be empty")

    fingerprint = _hash(_fingerprint_payload(
        model_version=version,
        model_hash=model_digest,
        experiment_id=experiment,
        pipeline_version=pipeline,
        dataset_hash=dataset_digest,
        feature_schema_hash=schema_digest,
        parent_model_id=parent,
        metadata=metadata_items,
    ))
    model_id = f"MODEL-{fingerprint[:16].upper()}"

    record = ModelRecord(
        model_id=model_id,
        model_version=version,
        model_hash=model_digest,
        experiment_id=experiment,
        pipeline_version=pipeline,
        dataset_hash=dataset_digest,
        feature_schema_hash=schema_digest,
        parent_model_id=parent,
        status="CANDIDATE",
        metadata=metadata_items,
        fingerprint=fingerprint,
        record_hash="",
    )
    return replace(record, record_hash=_hash(_record_payload(record)))


def verify_record(record: ModelRecord) -> bool:
    _validate_version(record.model_version)
    _validate_sha256(record.model_hash, "model_hash")
    _validate_sha256(record.dataset_hash, "dataset_hash")
    _validate_sha256(record.feature_schema_hash, "feature_schema_hash")

    if record.status not in _ALLOWED_STATUSES:
        raise RegistryError("invalid model status")
    if not record.model_id.startswith("MODEL-"):
        raise RegistryError("invalid model ID")

    expected_fingerprint = _hash(_fingerprint_payload(
        model_version=record.model_version,
        model_hash=record.model_hash,
        experiment_id=record.experiment_id,
        pipeline_version=record.pipeline_version,
        dataset_hash=record.dataset_hash,
        feature_schema_hash=record.feature_schema_hash,
        parent_model_id=record.parent_model_id,
        metadata=record.metadata,
    ))
    if record.fingerprint != expected_fingerprint:
        raise RegistryError("model fingerprint mismatch")
    if record.model_id != f"MODEL-{expected_fingerprint[:16].upper()}":
        raise RegistryError("model ID does not match fingerprint")

    clean = replace(record, record_hash="")
    if record.record_hash != _hash(_record_payload(clean)):
        raise RegistryError("model record hash mismatch")
    return True


def _make_event(
    sequence: int,
    action: str,
    model_id: str,
    previous_production_id: str = "",
    note: str = "",
) -> RegistryEvent:
    action_value = action.upper()
    if action_value not in _ALLOWED_ACTIONS:
        raise RegistryError("invalid registry action")
    event = RegistryEvent(
        sequence=sequence,
        action=action_value,
        model_id=model_id,
        previous_production_id=previous_production_id,
        note=note.strip(),
        event_hash="",
    )
    return replace(event, event_hash=_hash(_event_payload(event)))


def verify_event(event: RegistryEvent) -> bool:
    if event.sequence <= 0:
        raise RegistryError("event sequence must be positive")
    if event.action not in _ALLOWED_ACTIONS:
        raise RegistryError("invalid event action")
    clean = replace(event, event_hash="")
    if event.event_hash != _hash(_event_payload(clean)):
        raise RegistryError("event hash mismatch")
    return True


def create_registry(records: Iterable[ModelRecord] = ()) -> ModelRegistry:
    registry = ModelRegistry(
        version=VERSION,
        records=(),
        events=(),
        production_model_id="",
        registry_hash="",
    )
    registry = replace(registry, registry_hash=_hash(_registry_payload(registry)))
    for record in records:
        registry = register_model(registry, record)
    return registry


def _replace_record(
    records: tuple[ModelRecord, ...],
    updated: ModelRecord,
) -> tuple[ModelRecord, ...]:
    output = []
    found = False
    for record in records:
        if record.model_id == updated.model_id:
            output.append(updated)
            found = True
        else:
            output.append(record)
    if not found:
        raise RegistryError("model is not registered")
    return tuple(sorted(output, key=lambda item: item.model_version))


def _with_registry_hash(registry: ModelRegistry) -> ModelRegistry:
    clean = replace(registry, registry_hash="")
    return replace(clean, registry_hash=_hash(_registry_payload(clean)))


def register_model(registry: ModelRegistry, record: ModelRecord) -> ModelRegistry:
    verify_registry(registry)
    verify_record(record)

    if record.status != "CANDIDATE":
        raise RegistryError("new models must be registered as CANDIDATE")
    if record.model_id in {item.model_id for item in registry.records}:
        raise RegistryError("duplicate model ID detected")
    if record.model_version in {item.model_version for item in registry.records}:
        raise RegistryError("duplicate model version detected")
    if record.model_hash in {item.model_hash for item in registry.records}:
        raise RegistryError("duplicate model hash detected")
    if record.parent_model_id and record.parent_model_id not in {
        item.model_id for item in registry.records
    }:
        raise RegistryError("parent model is not registered")

    event = _make_event(
        sequence=len(registry.events) + 1,
        action="REGISTER",
        model_id=record.model_id,
    )
    updated = ModelRegistry(
        version=VERSION,
        records=tuple(sorted(registry.records + (record,), key=lambda item: item.model_version)),
        events=registry.events + (event,),
        production_model_id=registry.production_model_id,
        registry_hash="",
    )
    return _with_registry_hash(updated)


def promote_model(
    registry: ModelRegistry,
    model_id: str,
    note: str = "",
) -> ModelRegistry:
    verify_registry(registry)
    target = next((record for record in registry.records if record.model_id == model_id), None)
    if target is None:
        raise RegistryError("model is not registered")
    if target.status != "CANDIDATE":
        raise RegistryError("only CANDIDATE models can be promoted")

    previous_id = registry.production_model_id
    records = registry.records

    if previous_id:
        previous = next(record for record in records if record.model_id == previous_id)
        previous_archived = replace(previous, status="ARCHIVED", record_hash="")
        previous_archived = replace(
            previous_archived,
            record_hash=_hash(_record_payload(previous_archived)),
        )
        records = _replace_record(records, previous_archived)

    promoted = replace(target, status="PRODUCTION", record_hash="")
    promoted = replace(promoted, record_hash=_hash(_record_payload(promoted)))
    records = _replace_record(records, promoted)

    event = _make_event(
        sequence=len(registry.events) + 1,
        action="PROMOTE",
        model_id=model_id,
        previous_production_id=previous_id,
        note=note,
    )
    return _with_registry_hash(ModelRegistry(
        version=VERSION,
        records=records,
        events=registry.events + (event,),
        production_model_id=model_id,
        registry_hash="",
    ))


def archive_model(registry: ModelRegistry, model_id: str, note: str = "") -> ModelRegistry:
    verify_registry(registry)
    target = next((record for record in registry.records if record.model_id == model_id), None)
    if target is None:
        raise RegistryError("model is not registered")
    if target.status == "PRODUCTION":
        raise RegistryError("production model cannot be archived directly")
    if target.status == "ARCHIVED":
        raise RegistryError("model is already archived")

    archived = replace(target, status="ARCHIVED", record_hash="")
    archived = replace(archived, record_hash=_hash(_record_payload(archived)))
    event = _make_event(len(registry.events) + 1, "ARCHIVE", model_id, note=note)

    return _with_registry_hash(ModelRegistry(
        VERSION,
        _replace_record(registry.records, archived),
        registry.events + (event,),
        registry.production_model_id,
        "",
    ))


def reject_model(registry: ModelRegistry, model_id: str, note: str = "") -> ModelRegistry:
    verify_registry(registry)
    target = next((record for record in registry.records if record.model_id == model_id), None)
    if target is None:
        raise RegistryError("model is not registered")
    if target.status != "CANDIDATE":
        raise RegistryError("only CANDIDATE models can be rejected")

    rejected = replace(target, status="REJECTED", record_hash="")
    rejected = replace(rejected, record_hash=_hash(_record_payload(rejected)))
    event = _make_event(len(registry.events) + 1, "REJECT", model_id, note=note)

    return _with_registry_hash(ModelRegistry(
        VERSION,
        _replace_record(registry.records, rejected),
        registry.events + (event,),
        registry.production_model_id,
        "",
    ))


def rollback_to_model(
    registry: ModelRegistry,
    model_id: str,
    note: str = "",
) -> ModelRegistry:
    verify_registry(registry)
    if not registry.production_model_id:
        raise RegistryError("no production model exists")

    target = next((record for record in registry.records if record.model_id == model_id), None)
    if target is None:
        raise RegistryError("rollback target is not registered")
    if target.status != "ARCHIVED":
        raise RegistryError("rollback target must be ARCHIVED")
    if target.model_id == registry.production_model_id:
        raise RegistryError("rollback target is already in production")

    current = next(
        record for record in registry.records
        if record.model_id == registry.production_model_id
    )

    current_archived = replace(current, status="ARCHIVED", record_hash="")
    current_archived = replace(
        current_archived,
        record_hash=_hash(_record_payload(current_archived)),
    )
    target_production = replace(target, status="PRODUCTION", record_hash="")
    target_production = replace(
        target_production,
        record_hash=_hash(_record_payload(target_production)),
    )

    records = _replace_record(registry.records, current_archived)
    records = _replace_record(records, target_production)

    event = _make_event(
        sequence=len(registry.events) + 1,
        action="ROLLBACK",
        model_id=model_id,
        previous_production_id=current.model_id,
        note=note,
    )

    return _with_registry_hash(ModelRegistry(
        VERSION,
        records,
        registry.events + (event,),
        model_id,
        "",
    ))


def verify_registry(registry: ModelRegistry) -> bool:
    if registry.version != VERSION:
        raise RegistryError("unsupported registry version")

    ids = [record.model_id for record in registry.records]
    versions = [record.model_version for record in registry.records]
    hashes = [record.model_hash for record in registry.records]

    if len(ids) != len(set(ids)):
        raise RegistryError("duplicate model IDs detected")
    if len(versions) != len(set(versions)):
        raise RegistryError("duplicate model versions detected")
    if len(hashes) != len(set(hashes)):
        raise RegistryError("duplicate model hashes detected")

    for record in registry.records:
        verify_record(record)
        if record.parent_model_id and record.parent_model_id not in set(ids):
            raise RegistryError("missing parent model")

    for expected, event in enumerate(registry.events, start=1):
        verify_event(event)
        if event.sequence != expected:
            raise RegistryError("event sequence mismatch")
        if event.model_id not in set(ids):
            raise RegistryError("event references unknown model")

    production_records = [
        record for record in registry.records
        if record.status == "PRODUCTION"
    ]
    if registry.production_model_id:
        if len(production_records) != 1:
            raise RegistryError("registry must contain exactly one production model")
        if production_records[0].model_id != registry.production_model_id:
            raise RegistryError("production model ID mismatch")
    elif production_records:
        raise RegistryError("production record exists without production_model_id")

    clean = replace(registry, registry_hash="")
    if registry.registry_hash != _hash(_registry_payload(clean)):
        raise RegistryError("registry hash mismatch")
    return True


def save_registry(registry: ModelRegistry, path: str | Path) -> Path:
    verify_registry(registry)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_registry_payload(registry, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_registry(path: str | Path) -> ModelRegistry:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))

    records = tuple(ModelRecord(
        model_id=item["model_id"],
        model_version=item["model_version"],
        model_hash=item["model_hash"],
        experiment_id=item["experiment_id"],
        pipeline_version=item["pipeline_version"],
        dataset_hash=item["dataset_hash"],
        feature_schema_hash=item["feature_schema_hash"],
        parent_model_id=item["parent_model_id"],
        status=item["status"],
        metadata=tuple(sorted(item["metadata"].items())),
        fingerprint=item["fingerprint"],
        record_hash=item["record_hash"],
    ) for item in payload["records"])

    events = tuple(RegistryEvent(
        sequence=int(item["sequence"]),
        action=item["action"],
        model_id=item["model_id"],
        previous_production_id=item["previous_production_id"],
        note=item["note"],
        event_hash=item["event_hash"],
    ) for item in payload["events"])

    registry = ModelRegistry(
        version=payload["version"],
        records=records,
        events=events,
        production_model_id=payload["production_model_id"],
        registry_hash=payload["registry_hash"],
    )
    verify_registry(registry)
    return registry


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
