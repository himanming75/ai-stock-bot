"""V24.6 offline-only audit certificate validity and expiry verification.

Consumes an immutable V24.5 revocation result and produces an offline validity
snapshot with a cryptographically linked evaluation record. No market-data,
account, network, broker, order-submission, or live-execution activity occurs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional, Tuple

from backtest.offline_paper_audit_cert_ledger_integrity_v24_1 import sha256_payload
from backtest.offline_audit_revocation_v24_5 import (
    AuditRevocationV245Result,
    is_certificate_blocked,
    verify_revocation_certificate,
    verify_revocation_links,
)

VERSION = "V24.6"
SOURCE_VERSION = "V24.5"
REQUIRED_CONFIRMATION = "BUILD OFFLINE AUDIT VALIDITY V24.6"
GENESIS_VALIDITY_HASH = "0" * 64
VALID_STATES = ("ACTIVE", "SUSPENDED", "REVOKED", "NOT_YET_VALID", "EXPIRED")


@dataclass(frozen=True)
class AuditValidityV246Policy:
    source_version: str = SOURCE_VERSION
    required_source_status: str = "AUDIT_REVOCATION_VERIFIED"
    required_confirmation: str = REQUIRED_CONFIRMATION
    default_validity_seconds: int = 86400
    maximum_validity_seconds: int = 31536000
    require_utc_timestamps: bool = True
    require_source_certificate: bool = True
    require_revocation_links: bool = True
    deny_suspended: bool = True
    deny_revoked: bool = True
    deny_expired: bool = True
    deny_not_yet_valid: bool = True
    allow_market_data_api: bool = False
    allow_account_api: bool = False
    allow_network: bool = False
    allow_broker_api: bool = False
    allow_order_submission: bool = False
    allow_live_execution: bool = False


@dataclass(frozen=True)
class ValidityWindowV246:
    not_before: str
    not_after: str


@dataclass(frozen=True)
class ValidityEventV246:
    sequence: int
    event_id: str
    source_certificate_id: str
    source_certificate_hash: str
    evaluated_at: str
    not_before: str
    not_after: str
    source_state: str
    effective_state: str
    usage_allowed: bool
    previous_event_hash: str
    event_hash: str


@dataclass(frozen=True)
class ValidityFindingV246:
    sequence: int
    check_name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ValidityCertificateV246:
    certificate_id: str
    issued_at: str
    certificate_status: str
    source_revocation_result_id: str
    source_revocation_certificate_id: str
    source_revocation_certificate_hash: str
    effective_state: str
    usage_allowed: bool
    not_before: str
    not_after: str
    evaluation_event_hash: str
    findings_hash: str
    validity_score: int
    operator: str
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    certificate_hash: str


@dataclass(frozen=True)
class AuditValidityV246Result:
    version: str
    created_at: str
    validity_result_id: str
    result_status: str
    source_contract_verified: bool
    source_certificate_verified: bool
    source_revocation_links_verified: bool
    source_state_verified: bool
    validity_window_verified: bool
    evaluation_time_verified: bool
    effective_state_verified: bool
    usage_policy_verified: bool
    event_hash_verified: bool
    safety_verified: bool
    source_remained_unchanged: bool
    effective_state: str
    usage_allowed: bool
    validity_score: int
    certificate_created: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    policy: AuditValidityV246Policy
    window: ValidityWindowV246
    events: Tuple[ValidityEventV246, ...]
    findings: Tuple[ValidityFindingV246, ...]
    certificate: Optional[ValidityCertificateV246]
    reasons: Tuple[str, ...]
    source_path: str = ""
    result_path: str = ""


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be a non-empty string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def validate_policy(policy: AuditValidityV246Policy) -> None:
    if not isinstance(policy, AuditValidityV246Policy):
        raise TypeError("policy must be AuditValidityV246Policy")
    if policy != AuditValidityV246Policy():
        raise ValueError("V24.6 policy is immutable and must use safe defaults")


def _source_hash(source: AuditRevocationV245Result) -> str:
    payload = asdict(source)
    payload.pop("source_path", None)
    payload.pop("result_path", None)
    return sha256_payload(payload)


def _event_payload(event: ValidityEventV246) -> dict:
    payload = asdict(event)
    payload.pop("event_hash", None)
    return payload


def verify_validity_event(event: ValidityEventV246) -> bool:
    return isinstance(event, ValidityEventV246) and event.event_hash == sha256_payload(_event_payload(event))


def verify_validity_links(events: Tuple[ValidityEventV246, ...]) -> bool:
    previous = GENESIS_VALIDITY_HASH
    for sequence, event in enumerate(events, start=1):
        if event.sequence != sequence or event.previous_event_hash != previous:
            return False
        if not verify_validity_event(event):
            return False
        previous = event.event_hash
    return True


def _findings_hash(findings: Tuple[ValidityFindingV246, ...]) -> str:
    return sha256_payload({"findings": [asdict(item) for item in findings]})


def _certificate_payload(certificate: ValidityCertificateV246) -> dict:
    payload = asdict(certificate)
    payload.pop("certificate_hash", None)
    return payload


def verify_validity_certificate(certificate: ValidityCertificateV246) -> bool:
    return isinstance(certificate, ValidityCertificateV246) and certificate.certificate_hash == sha256_payload(_certificate_payload(certificate))


def _derive_state(source_state: str, evaluated_at: datetime, not_before: datetime, not_after: datetime) -> str:
    if source_state == "REVOKED":
        return "REVOKED"
    if source_state == "SUSPENDED":
        return "SUSPENDED"
    if evaluated_at < not_before:
        return "NOT_YET_VALID"
    if evaluated_at > not_after:
        return "EXPIRED"
    return "ACTIVE"


def is_usage_allowed(result: AuditValidityV246Result) -> bool:
    if not isinstance(result, AuditValidityV246Result):
        raise TypeError("result must be AuditValidityV246Result")
    return result.usage_allowed and result.effective_state == "ACTIVE" and result.certificate_created


def build_offline_audit_validity_v24_6(
    source: AuditRevocationV245Result,
    *,
    operator: str,
    confirmation: str,
    evaluation_time: str,
    not_before: str,
    not_after: str,
    policy: AuditValidityV246Policy = AuditValidityV246Policy(),
    source_path: str = "",
) -> AuditValidityV246Result:
    """Evaluate offline validity, expiry, and revocation state."""
    validate_policy(policy)
    if not isinstance(source, AuditRevocationV245Result):
        raise TypeError("source must be a V24.5 audit revocation result")
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("operator must be a non-empty string")
    operator = operator.strip()
    if confirmation != policy.required_confirmation:
        raise PermissionError("exact V24.6 confirmation is required")

    evaluated_at = _parse_utc(evaluation_time)
    window_start = _parse_utc(not_before)
    window_end = _parse_utc(not_after)
    source_created_at = _parse_utc(source.created_at)
    if evaluated_at < source_created_at:
        raise ValueError("evaluation time cannot be before source creation time")

    before_hash = _source_hash(source)
    source_certificate = source.certificate
    source_contract_verified = (
        source.version == policy.source_version
        and source.result_status == policy.required_source_status
        and source.certificate_created
        and source.source_remained_unchanged
        and source_certificate is not None
    )
    source_certificate_verified = source_certificate is not None and verify_revocation_certificate(source_certificate)
    source_revocation_links_verified = verify_revocation_links(source.events)
    source_state_verified = source.effective_certificate_state in {"ACTIVE", "SUSPENDED", "REVOKED"}

    duration_seconds = (window_end - window_start).total_seconds()
    validity_window_verified = (
        window_start <= window_end
        and duration_seconds > 0
        and duration_seconds <= policy.maximum_validity_seconds
        and window_start >= source_created_at
    )
    evaluation_time_verified = evaluated_at >= source_created_at

    effective_state = _derive_state(source.effective_certificate_state, evaluated_at, window_start, window_end)
    effective_state_verified = effective_state in VALID_STATES

    usage_allowed = effective_state == "ACTIVE" and not is_certificate_blocked(source)
    usage_policy_verified = (
        (effective_state != "SUSPENDED" or not usage_allowed)
        and (effective_state != "REVOKED" or not usage_allowed)
        and (effective_state != "EXPIRED" or not usage_allowed)
        and (effective_state != "NOT_YET_VALID" or not usage_allowed)
    )

    source_certificate_id = source_certificate.certificate_id if source_certificate else ""
    source_certificate_hash = source_certificate.certificate_hash if source_certificate else ""
    unsigned_event = ValidityEventV246(
        sequence=1,
        event_id=sha256_payload({
            "source_certificate_id": source_certificate_id,
            "evaluated_at": evaluated_at.isoformat(),
            "not_before": window_start.isoformat(),
            "not_after": window_end.isoformat(),
            "source_state": source.effective_certificate_state,
        }),
        source_certificate_id=source_certificate_id,
        source_certificate_hash=source_certificate_hash,
        evaluated_at=evaluated_at.isoformat(),
        not_before=window_start.isoformat(),
        not_after=window_end.isoformat(),
        source_state=source.effective_certificate_state,
        effective_state=effective_state,
        usage_allowed=usage_allowed,
        previous_event_hash=GENESIS_VALIDITY_HASH,
        event_hash="",
    )
    event = replace(unsigned_event, event_hash=sha256_payload(_event_payload(unsigned_event)))
    events = (event,)
    event_hash_verified = verify_validity_links(events)

    safety_verified = (
        not source.market_data_api_called
        and not source.account_api_called
        and not source.network_accessed
        and not source.broker_api_called
        and not source.broker_order_created
        and not source.order_submitted
        and not source.live_execution_authorized
        and source.execution_blocked
        and not source.funds_reserved
        and not source.holdings_reserved
        and source_certificate is not None
        and source_certificate.execution_blocked
        and not source_certificate.funds_reserved
        and not source_certificate.holdings_reserved
    )
    source_remained_unchanged = before_hash == _source_hash(source)

    checks = (
        ("source_contract", source_contract_verified, "V24.5 source contract"),
        ("source_certificate", source_certificate_verified, "V24.5 certificate integrity"),
        ("source_revocation_links", source_revocation_links_verified, "V24.5 linked revocation events"),
        ("source_state", source_state_verified, "known source certificate state"),
        ("validity_window", validity_window_verified, "valid not-before/not-after window"),
        ("evaluation_time", evaluation_time_verified, "evaluation timestamp"),
        ("effective_state", effective_state_verified, "derived certificate state"),
        ("usage_policy", usage_policy_verified, "blocked-state usage policy"),
        ("event_hash", event_hash_verified, "immutable validity event"),
        ("source_safety", safety_verified, "offline execution safety"),
        ("source_immutability", source_remained_unchanged, "source unchanged"),
    )
    findings = tuple(ValidityFindingV246(i, name, passed, detail) for i, (name, passed, detail) in enumerate(checks, start=1))
    reasons = tuple(detail for _, passed, detail in checks if not passed)
    passed_count = sum(1 for item in findings if item.passed)
    validity_score = int(round((passed_count / len(findings)) * 100))
    all_passed = all(item.passed for item in findings)
    result_status = "AUDIT_VALIDITY_VERIFIED" if all_passed else "AUDIT_VALIDITY_FAILED"
    findings_hash = _findings_hash(findings)
    validity_result_id = sha256_payload({
        "version": VERSION,
        "created_at": evaluated_at.isoformat(),
        "source_revocation_result_id": source.revocation_result_id,
        "source_certificate_hash": source_certificate_hash,
        "effective_state": effective_state,
        "usage_allowed": usage_allowed,
        "event_hash": event.event_hash,
        "findings_hash": findings_hash,
        "result_status": result_status,
    })

    output_certificate = None
    if all_passed:
        unsigned_certificate = ValidityCertificateV246(
            certificate_id=validity_result_id,
            issued_at=evaluated_at.isoformat(),
            certificate_status=result_status,
            source_revocation_result_id=source.revocation_result_id,
            source_revocation_certificate_id=source_certificate_id,
            source_revocation_certificate_hash=source_certificate_hash,
            effective_state=effective_state,
            usage_allowed=usage_allowed,
            not_before=window_start.isoformat(),
            not_after=window_end.isoformat(),
            evaluation_event_hash=event.event_hash,
            findings_hash=findings_hash,
            validity_score=validity_score,
            operator=operator,
            execution_blocked=True,
            funds_reserved=False,
            holdings_reserved=False,
            certificate_hash="",
        )
        output_certificate = replace(unsigned_certificate, certificate_hash=sha256_payload(_certificate_payload(unsigned_certificate)))

    return AuditValidityV246Result(
        version=VERSION,
        created_at=evaluated_at.isoformat(),
        validity_result_id=validity_result_id,
        result_status=result_status,
        source_contract_verified=source_contract_verified,
        source_certificate_verified=source_certificate_verified,
        source_revocation_links_verified=source_revocation_links_verified,
        source_state_verified=source_state_verified,
        validity_window_verified=validity_window_verified,
        evaluation_time_verified=evaluation_time_verified,
        effective_state_verified=effective_state_verified,
        usage_policy_verified=usage_policy_verified,
        event_hash_verified=event_hash_verified,
        safety_verified=safety_verified,
        source_remained_unchanged=source_remained_unchanged,
        effective_state=effective_state,
        usage_allowed=usage_allowed,
        validity_score=validity_score,
        certificate_created=output_certificate is not None,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_execution_authorized=False,
        execution_blocked=True,
        funds_reserved=False,
        holdings_reserved=False,
        policy=policy,
        window=ValidityWindowV246(window_start.isoformat(), window_end.isoformat()),
        events=events,
        findings=findings,
        certificate=output_certificate,
        reasons=reasons,
        source_path=str(source_path),
    )


def save_validity_result(result: AuditValidityV246Result, path: str | Path) -> None:
    if not isinstance(result, AuditValidityV246Result):
        raise TypeError("result must be AuditValidityV246Result")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def load_validity_result(path: str | Path) -> AuditValidityV246Result:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    payload["policy"] = AuditValidityV246Policy(**payload["policy"])
    payload["window"] = ValidityWindowV246(**payload["window"])
    payload["events"] = tuple(ValidityEventV246(**item) for item in payload["events"])
    payload["findings"] = tuple(ValidityFindingV246(**item) for item in payload["findings"])
    if payload["certificate"] is not None:
        payload["certificate"] = ValidityCertificateV246(**payload["certificate"])
    payload["reasons"] = tuple(payload["reasons"])
    return AuditValidityV246Result(**payload)


__all__ = [
    "VERSION", "SOURCE_VERSION", "REQUIRED_CONFIRMATION", "GENESIS_VALIDITY_HASH", "VALID_STATES",
    "AuditValidityV246Policy", "ValidityWindowV246", "ValidityEventV246", "ValidityFindingV246",
    "ValidityCertificateV246", "AuditValidityV246Result", "validate_policy", "verify_validity_event",
    "verify_validity_links", "verify_validity_certificate", "is_usage_allowed",
    "build_offline_audit_validity_v24_6", "save_validity_result", "load_validity_result",
]
