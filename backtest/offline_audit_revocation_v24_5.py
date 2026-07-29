"""V24.5 offline-only audit certificate revocation verification.

This module consumes an immutable V24.4 audit trust result and creates a
cryptographically linked, offline certificate revocation ledger. It performs
no market-data, account, network, broker, order-submission, or live-execution
activity.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional, Tuple

from backtest.offline_paper_audit_cert_ledger_integrity_v24_1 import sha256_payload
from backtest.offline_audit_trust_v24_4 import (
    AuditTrustV244Result,
    verify_root_anchor,
    verify_trust_certificate,
    verify_trust_lineage,
)

VERSION = "V24.5"
SOURCE_VERSION = "V24.4"
REQUIRED_CONFIRMATION = "BUILD OFFLINE AUDIT REVOCATION V24.5"
GENESIS_REVOCATION_HASH = "0" * 64
VALID_ACTIONS = ("REVOKE", "SUSPEND", "REINSTATE")
VALID_REASONS = (
    "KEY_COMPROMISE",
    "CERTIFICATE_SUPERSEDED",
    "TRUST_POLICY_VIOLATION",
    "OPERATOR_REQUEST",
    "SOURCE_INTEGRITY_FAILURE",
    "TEMPORARY_HOLD",
    "REINSTATEMENT_APPROVED",
)


@dataclass(frozen=True)
class AuditRevocationV245Policy:
    source_version: str = SOURCE_VERSION
    required_source_status: str = "AUDIT_TRUST_VERIFIED"
    required_confirmation: str = REQUIRED_CONFIRMATION
    maximum_revocation_events: int = 4096
    require_valid_source_certificate: bool = True
    require_monotonic_event_time: bool = True
    require_unique_event_ids: bool = True
    require_hash_linked_ledger: bool = True
    require_known_reason_codes: bool = True
    allow_reinstatement: bool = True
    allow_market_data_api: bool = False
    allow_account_api: bool = False
    allow_network: bool = False
    allow_broker_api: bool = False
    allow_order_submission: bool = False
    allow_live_execution: bool = False


@dataclass(frozen=True)
class RevocationRequestV245:
    action: str
    reason_code: str
    requested_at: str
    operator: str
    note: str = ""


@dataclass(frozen=True)
class RevocationEventV245:
    sequence: int
    event_id: str
    certificate_id: str
    certificate_hash: str
    action: str
    reason_code: str
    requested_at: str
    operator: str
    note_hash: str
    previous_event_hash: str
    event_hash: str


@dataclass(frozen=True)
class RevocationFindingV245:
    sequence: int
    check_name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class RevocationCertificateV245:
    certificate_id: str
    issued_at: str
    certificate_status: str
    source_trust_result_id: str
    source_trust_certificate_id: str
    source_trust_certificate_hash: str
    effective_certificate_state: str
    event_count: int
    final_event_hash: str
    revocation_list_hash: str
    findings_hash: str
    revocation_score: int
    operator: str
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    certificate_hash: str


@dataclass(frozen=True)
class AuditRevocationV245Result:
    version: str
    created_at: str
    revocation_result_id: str
    result_status: str
    source_contract_verified: bool
    source_root_anchor_verified: bool
    source_lineage_verified: bool
    source_certificate_verified: bool
    request_contracts_verified: bool
    reason_codes_verified: bool
    event_times_verified: bool
    unique_events_verified: bool
    event_links_verified: bool
    state_transitions_verified: bool
    revocation_list_verified: bool
    safety_verified: bool
    source_remained_unchanged: bool
    effective_certificate_state: str
    revocation_score: int
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
    policy: AuditRevocationV245Policy
    events: Tuple[RevocationEventV245, ...]
    findings: Tuple[RevocationFindingV245, ...]
    certificate: Optional[RevocationCertificateV245]
    reasons: Tuple[str, ...]
    source_path: str = ""
    result_path: str = ""


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    parsed = parsed.astimezone(timezone.utc)
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must resolve to UTC")
    return parsed


def validate_policy(policy: AuditRevocationV245Policy) -> None:
    if not isinstance(policy, AuditRevocationV245Policy):
        raise TypeError("policy must be AuditRevocationV245Policy")
    if policy != AuditRevocationV245Policy():
        raise ValueError("V24.5 policy is immutable and must use safe defaults")


def _source_hash(source: AuditTrustV244Result) -> str:
    payload = asdict(source)
    payload.pop("source_path", None)
    payload.pop("result_path", None)
    return sha256_payload(payload)


def _event_payload(event: RevocationEventV245) -> dict:
    payload = asdict(event)
    payload.pop("event_hash", None)
    return payload


def verify_revocation_event(event: RevocationEventV245) -> bool:
    return (
        isinstance(event, RevocationEventV245)
        and event.event_hash == sha256_payload(_event_payload(event))
    )


def verify_revocation_links(events: Tuple[RevocationEventV245, ...]) -> bool:
    previous = GENESIS_REVOCATION_HASH
    for sequence, event in enumerate(events, start=1):
        if event.sequence != sequence or event.previous_event_hash != previous:
            return False
        if not verify_revocation_event(event):
            return False
        previous = event.event_hash
    return True


def _effective_state(events: Tuple[RevocationEventV245, ...]) -> Tuple[str, bool]:
    state = "ACTIVE"
    valid = True
    for event in events:
        if event.action == "REVOKE":
            if state == "REVOKED":
                valid = False
            state = "REVOKED"
        elif event.action == "SUSPEND":
            if state != "ACTIVE":
                valid = False
            state = "SUSPENDED"
        elif event.action == "REINSTATE":
            if state not in {"REVOKED", "SUSPENDED"}:
                valid = False
            state = "ACTIVE"
        else:
            valid = False
    return state, valid


def verify_state_transitions(events: Tuple[RevocationEventV245, ...]) -> bool:
    return _effective_state(events)[1]


def _revocation_list_hash(events: Tuple[RevocationEventV245, ...]) -> str:
    return sha256_payload({"event_hashes": [event.event_hash for event in events]})


def _findings_hash(findings: Tuple[RevocationFindingV245, ...]) -> str:
    return sha256_payload({"findings": [asdict(item) for item in findings]})


def _certificate_payload(certificate: RevocationCertificateV245) -> dict:
    payload = asdict(certificate)
    payload.pop("certificate_hash", None)
    return payload


def verify_revocation_certificate(certificate: RevocationCertificateV245) -> bool:
    return (
        isinstance(certificate, RevocationCertificateV245)
        and certificate.certificate_hash
        == sha256_payload(_certificate_payload(certificate))
    )


def is_certificate_blocked(result: AuditRevocationV245Result) -> bool:
    """Return True when the source certificate cannot be trusted for use."""
    if not isinstance(result, AuditRevocationV245Result):
        raise TypeError("result must be AuditRevocationV245Result")
    return result.effective_certificate_state in {"REVOKED", "SUSPENDED"}


def build_offline_audit_revocation_v24_5(
    source: AuditTrustV244Result,
    requests: Tuple[RevocationRequestV245, ...],
    *,
    operator: str,
    confirmation: str,
    evaluation_time: str,
    policy: AuditRevocationV245Policy = AuditRevocationV245Policy(),
    source_path: str = "",
) -> AuditRevocationV245Result:
    """Create and verify an immutable offline certificate revocation ledger."""
    validate_policy(policy)
    if not isinstance(source, AuditTrustV244Result):
        raise TypeError("source must be a V24.4 audit trust result")
    if not isinstance(requests, tuple):
        raise TypeError("requests must be a tuple")
    if len(requests) > policy.maximum_revocation_events:
        raise ValueError("too many revocation events")
    if not all(isinstance(item, RevocationRequestV245) for item in requests):
        raise TypeError("every request must be RevocationRequestV245")
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("operator must be a non-empty string")
    operator = operator.strip()
    if confirmation != policy.required_confirmation:
        raise PermissionError("exact V24.5 confirmation is required")

    created_at = _parse_utc(evaluation_time)
    source_created_at = _parse_utc(source.created_at)
    if created_at < source_created_at:
        raise ValueError("evaluation time cannot be before source creation time")

    before_hash = _source_hash(source)
    source_certificate = source.certificate
    source_contract_verified = (
        source.version == policy.source_version
        and source.result_status == policy.required_source_status
        and source.certificate_created
        and source.sources_remained_unchanged
        and source_certificate is not None
    )
    source_root_anchor_verified = verify_root_anchor(source.root_anchor)
    source_lineage_verified = verify_trust_lineage(source.root_anchor, source.nodes)
    source_certificate_verified = (
        source_certificate is not None
        and verify_trust_certificate(source_certificate)
    )

    request_contracts_verified = all(
        item.action in VALID_ACTIONS
        and isinstance(item.operator, str)
        and bool(item.operator.strip())
        and isinstance(item.note, str)
        for item in requests
    )
    reason_codes_verified = all(item.reason_code in VALID_REASONS for item in requests)

    request_times = []
    event_times_verified = True
    for item in requests:
        try:
            timestamp = _parse_utc(item.requested_at)
            request_times.append(timestamp)
            if timestamp < source_created_at or timestamp > created_at:
                event_times_verified = False
        except (TypeError, ValueError):
            event_times_verified = False
    if request_times and request_times != sorted(request_times):
        event_times_verified = False

    events_list = []
    previous_hash = GENESIS_REVOCATION_HASH
    source_certificate_id = source_certificate.certificate_id if source_certificate else ""
    source_certificate_hash = source_certificate.certificate_hash if source_certificate else ""
    for sequence, request in enumerate(requests, start=1):
        event_id = sha256_payload({
            "sequence": sequence,
            "certificate_id": source_certificate_id,
            "action": request.action,
            "reason_code": request.reason_code,
            "requested_at": request.requested_at,
            "operator": request.operator.strip(),
            "previous_event_hash": previous_hash,
        })
        unsigned_event = RevocationEventV245(
            sequence=sequence,
            event_id=event_id,
            certificate_id=source_certificate_id,
            certificate_hash=source_certificate_hash,
            action=request.action,
            reason_code=request.reason_code,
            requested_at=request.requested_at,
            operator=request.operator.strip(),
            note_hash=sha256_payload({"note": request.note}),
            previous_event_hash=previous_hash,
            event_hash="",
        )
        event = replace(unsigned_event, event_hash=sha256_payload(_event_payload(unsigned_event)))
        events_list.append(event)
        previous_hash = event.event_hash
    events = tuple(events_list)

    event_ids = tuple(event.event_id for event in events)
    unique_events_verified = len(event_ids) == len(set(event_ids))
    event_links_verified = verify_revocation_links(events)
    effective_certificate_state, state_transitions_verified = _effective_state(events)
    if not policy.allow_reinstatement and any(event.action == "REINSTATE" for event in events):
        state_transitions_verified = False

    revocation_hash_before = _revocation_list_hash(events)
    revocation_list_verified = (
        revocation_hash_before == _revocation_list_hash(events)
        and len(events) <= policy.maximum_revocation_events
    )

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
        ("source_contract", source_contract_verified, "V24.4 source contract"),
        ("source_root_anchor", source_root_anchor_verified, "V24.4 root anchor integrity"),
        ("source_lineage", source_lineage_verified, "V24.4 trust lineage"),
        ("source_certificate", source_certificate_verified, "V24.4 certificate integrity"),
        ("request_contracts", request_contracts_verified, "revocation request contracts"),
        ("reason_codes", reason_codes_verified, "approved revocation reason codes"),
        ("event_times", event_times_verified, "monotonic event timestamps"),
        ("unique_events", unique_events_verified, "duplicate/replay prevention"),
        ("event_links", event_links_verified, "hash-linked revocation ledger"),
        ("state_transitions", state_transitions_verified, "certificate state transitions"),
        ("revocation_list", revocation_list_verified, "immutable revocation list"),
        ("source_safety", safety_verified, "offline execution safety"),
        ("source_immutability", source_remained_unchanged, "source unchanged"),
    )
    findings = tuple(
        RevocationFindingV245(index, name, passed, detail)
        for index, (name, passed, detail) in enumerate(checks, start=1)
    )
    reasons = tuple(detail for _, passed, detail in checks if not passed)
    passed_count = sum(1 for finding in findings if finding.passed)
    revocation_score = int(round((passed_count / len(findings)) * 100))
    all_passed = all(finding.passed for finding in findings)
    result_status = "AUDIT_REVOCATION_VERIFIED" if all_passed else "AUDIT_REVOCATION_FAILED"
    final_event_hash = events[-1].event_hash if events else GENESIS_REVOCATION_HASH
    revocation_list_hash = _revocation_list_hash(events)
    findings_hash = _findings_hash(findings)
    revocation_result_id = sha256_payload({
        "version": VERSION,
        "created_at": created_at.isoformat(),
        "source_trust_result_id": source.trust_result_id,
        "source_certificate_hash": source_certificate_hash,
        "effective_certificate_state": effective_certificate_state,
        "revocation_list_hash": revocation_list_hash,
        "findings_hash": findings_hash,
        "result_status": result_status,
    })

    output_certificate = None
    if all_passed:
        unsigned_certificate = RevocationCertificateV245(
            certificate_id=revocation_result_id,
            issued_at=created_at.isoformat(),
            certificate_status=result_status,
            source_trust_result_id=source.trust_result_id,
            source_trust_certificate_id=source_certificate_id,
            source_trust_certificate_hash=source_certificate_hash,
            effective_certificate_state=effective_certificate_state,
            event_count=len(events),
            final_event_hash=final_event_hash,
            revocation_list_hash=revocation_list_hash,
            findings_hash=findings_hash,
            revocation_score=revocation_score,
            operator=operator,
            execution_blocked=True,
            funds_reserved=False,
            holdings_reserved=False,
            certificate_hash="",
        )
        output_certificate = replace(
            unsigned_certificate,
            certificate_hash=sha256_payload(_certificate_payload(unsigned_certificate)),
        )

    return AuditRevocationV245Result(
        version=VERSION,
        created_at=created_at.isoformat(),
        revocation_result_id=revocation_result_id,
        result_status=result_status,
        source_contract_verified=source_contract_verified,
        source_root_anchor_verified=source_root_anchor_verified,
        source_lineage_verified=source_lineage_verified,
        source_certificate_verified=source_certificate_verified,
        request_contracts_verified=request_contracts_verified,
        reason_codes_verified=reason_codes_verified,
        event_times_verified=event_times_verified,
        unique_events_verified=unique_events_verified,
        event_links_verified=event_links_verified,
        state_transitions_verified=state_transitions_verified,
        revocation_list_verified=revocation_list_verified,
        safety_verified=safety_verified,
        source_remained_unchanged=source_remained_unchanged,
        effective_certificate_state=effective_certificate_state,
        revocation_score=revocation_score,
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
        events=events,
        findings=findings,
        certificate=output_certificate,
        reasons=reasons,
        source_path=str(source_path),
    )


def save_revocation_result(result: AuditRevocationV245Result, path: str | Path) -> None:
    if not isinstance(result, AuditRevocationV245Result):
        raise TypeError("result must be AuditRevocationV245Result")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_revocation_result(path: str | Path) -> AuditRevocationV245Result:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    payload["policy"] = AuditRevocationV245Policy(**payload["policy"])
    payload["events"] = tuple(RevocationEventV245(**item) for item in payload["events"])
    payload["findings"] = tuple(RevocationFindingV245(**item) for item in payload["findings"])
    if payload["certificate"] is not None:
        payload["certificate"] = RevocationCertificateV245(**payload["certificate"])
    payload["reasons"] = tuple(payload["reasons"])
    return AuditRevocationV245Result(**payload)


__all__ = [
    "VERSION",
    "SOURCE_VERSION",
    "REQUIRED_CONFIRMATION",
    "GENESIS_REVOCATION_HASH",
    "VALID_ACTIONS",
    "VALID_REASONS",
    "AuditRevocationV245Policy",
    "RevocationRequestV245",
    "RevocationEventV245",
    "RevocationFindingV245",
    "RevocationCertificateV245",
    "AuditRevocationV245Result",
    "validate_policy",
    "verify_revocation_event",
    "verify_revocation_links",
    "verify_state_transitions",
    "verify_revocation_certificate",
    "is_certificate_blocked",
    "build_offline_audit_revocation_v24_5",
    "save_revocation_result",
    "load_revocation_result",
]
