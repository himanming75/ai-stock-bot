"""V24.3 offline-only audit certificate hash-chain verification.

This module consumes immutable V24.2 verification results and creates a
cryptographically linked offline chain. It never imports or calls market-data,
account, network, broker, order-submission, or live-execution APIs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional, Tuple

from backtest.offline_paper_audit_cert_ledger_integrity_v24_1 import sha256_payload
from backtest.offline_paper_audit_cert_verify_v24_2 import (
    AuditCertificateVerificationV242Result,
    verify_verification_certificate,
)


VERSION = "V24.3"
SOURCE_VERSION = "V24.2"
REQUIRED_CONFIRMATION = "BUILD OFFLINE AUDIT CERTIFICATE CHAIN V24.3"
GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditChainV243Policy:
    source_version: str = SOURCE_VERSION
    required_source_status: str = "AUDIT_CERTIFICATE_VERIFIED"
    required_confirmation: str = REQUIRED_CONFIRMATION
    minimum_source_count: int = 1
    require_unique_source_ids: bool = True
    require_chronological_order: bool = True
    require_source_certificate_hash: bool = True
    require_source_findings_hash: bool = True
    require_source_result_identity: bool = True
    require_source_safety: bool = True
    allow_market_data_api: bool = False
    allow_account_api: bool = False
    allow_network: bool = False
    allow_broker_api: bool = False
    allow_order_submission: bool = False
    allow_live_execution: bool = False


@dataclass(frozen=True)
class AuditChainFindingV243:
    sequence: int
    check_name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class AuditChainEntryV243:
    sequence: int
    source_verification_result_id: str
    source_created_at: str
    source_result_hash: str
    source_certificate_hash: str
    previous_entry_hash: str
    entry_hash: str


@dataclass(frozen=True)
class AuditChainCertificateV243:
    certificate_id: str
    issued_at: str
    certificate_status: str
    source_count: int
    first_source_result_id: str
    last_source_result_id: str
    genesis_hash: str
    final_chain_hash: str
    findings_hash: str
    operator: str
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    certificate_hash: str


@dataclass(frozen=True)
class AuditChainV243Result:
    version: str
    created_at: str
    chain_result_id: str
    result_status: str
    source_contracts_verified: bool
    source_certificate_hashes_verified: bool
    source_findings_hashes_verified: bool
    source_result_identities_verified: bool
    unique_sources_verified: bool
    chronological_order_verified: bool
    chain_linkage_verified: bool
    safety_verified: bool
    sources_remained_unchanged: bool
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
    policy: AuditChainV243Policy
    entries: Tuple[AuditChainEntryV243, ...]
    findings: Tuple[AuditChainFindingV243, ...]
    certificate: Optional[AuditChainCertificateV243]
    reasons: Tuple[str, ...]
    source_path: str = ""
    result_path: str = ""


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    parsed = parsed.astimezone(timezone.utc)
    if parsed.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must resolve to UTC")
    return parsed


def validate_policy(policy: AuditChainV243Policy) -> None:
    if not isinstance(policy, AuditChainV243Policy):
        raise TypeError("policy must be AuditChainV243Policy")
    if policy != AuditChainV243Policy():
        raise ValueError("V24.3 policy is immutable and must use safe defaults")


def _source_result_hash(source: AuditCertificateVerificationV242Result) -> str:
    payload = asdict(source)
    payload.pop("source_path", None)
    payload.pop("result_path", None)
    return sha256_payload(payload)


def _source_findings_hash(source: AuditCertificateVerificationV242Result) -> str:
    return sha256_payload({"findings": [asdict(item) for item in source.findings]})


def _expected_source_result_id(source: AuditCertificateVerificationV242Result) -> str:
    source_audit_result_id = ""
    source_result_hash = ""
    if source.certificate is not None:
        source_audit_result_id = source.certificate.source_audit_result_id
        source_result_hash = source.certificate.source_result_hash
    return sha256_payload(
        {
            "version": source.version,
            "created_at": source.created_at,
            "source_audit_result_id": source_audit_result_id,
            "source_result_hash": source_result_hash,
            "findings_hash": _source_findings_hash(source),
            "result_status": source.result_status,
        }
    )


def _entry_payload(entry: AuditChainEntryV243) -> dict:
    payload = asdict(entry)
    payload.pop("entry_hash", None)
    return payload


def verify_chain_entry(entry: AuditChainEntryV243) -> bool:
    if not isinstance(entry, AuditChainEntryV243):
        return False
    return entry.entry_hash == sha256_payload(_entry_payload(entry))


def verify_chain_links(entries: Tuple[AuditChainEntryV243, ...]) -> bool:
    if not entries:
        return False
    expected_previous = GENESIS_HASH
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.sequence != expected_sequence:
            return False
        if entry.previous_entry_hash != expected_previous:
            return False
        if not verify_chain_entry(entry):
            return False
        expected_previous = entry.entry_hash
    return True


def _findings_hash(findings: Tuple[AuditChainFindingV243, ...]) -> str:
    return sha256_payload({"findings": [asdict(item) for item in findings]})


def _certificate_payload(certificate: AuditChainCertificateV243) -> dict:
    payload = asdict(certificate)
    payload.pop("certificate_hash", None)
    return payload


def verify_chain_certificate(certificate: AuditChainCertificateV243) -> bool:
    if not isinstance(certificate, AuditChainCertificateV243):
        return False
    return certificate.certificate_hash == sha256_payload(
        _certificate_payload(certificate)
    )


def build_offline_audit_chain_v24_3(
    sources: Tuple[AuditCertificateVerificationV242Result, ...],
    *,
    operator: str,
    confirmation: str,
    chain_time: str,
    policy: AuditChainV243Policy = AuditChainV243Policy(),
    source_path: str = "",
) -> AuditChainV243Result:
    """Build and verify an offline hash chain from ordered V24.2 results."""

    validate_policy(policy)
    if not isinstance(sources, tuple):
        raise TypeError("sources must be a tuple of V24.2 results")
    if len(sources) < policy.minimum_source_count:
        raise ValueError("at least one V24.2 source result is required")
    if not all(isinstance(item, AuditCertificateVerificationV242Result) for item in sources):
        raise TypeError("every source must be a V24.2 verification result")
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("operator must be a non-empty string")
    operator = operator.strip()
    if confirmation != policy.required_confirmation:
        raise PermissionError("exact V24.3 confirmation is required")

    created_at = _parse_utc(chain_time)
    source_times = tuple(_parse_utc(item.created_at) for item in sources)
    if created_at < max(source_times):
        raise ValueError("chain time cannot be before a source creation time")

    before_hashes = tuple(_source_result_hash(item) for item in sources)

    source_contracts_verified = all(
        item.version == policy.source_version
        and item.result_status == policy.required_source_status
        and item.certificate_created
        and item.source_remained_unchanged
        and item.certificate is not None
        for item in sources
    )
    source_certificate_hashes_verified = all(
        item.certificate is not None
        and verify_verification_certificate(item.certificate)
        for item in sources
    )
    source_findings_hashes_verified = all(
        item.certificate is not None
        and item.certificate.findings_hash == _source_findings_hash(item)
        for item in sources
    )
    source_result_identities_verified = all(
        item.verification_result_id == _expected_source_result_id(item)
        for item in sources
    )

    source_ids = tuple(item.verification_result_id for item in sources)
    unique_sources_verified = len(source_ids) == len(set(source_ids))
    chronological_order_verified = all(
        source_times[index] <= source_times[index + 1]
        for index in range(len(source_times) - 1)
    )

    entries_list = []
    previous_hash = GENESIS_HASH
    for sequence, (source, source_hash) in enumerate(
        zip(sources, before_hashes), start=1
    ):
        certificate_hash = (
            source.certificate.certificate_hash if source.certificate is not None else ""
        )
        unsigned = AuditChainEntryV243(
            sequence=sequence,
            source_verification_result_id=source.verification_result_id,
            source_created_at=source.created_at,
            source_result_hash=source_hash,
            source_certificate_hash=certificate_hash,
            previous_entry_hash=previous_hash,
            entry_hash="",
        )
        entry = replace(unsigned, entry_hash=sha256_payload(_entry_payload(unsigned)))
        entries_list.append(entry)
        previous_hash = entry.entry_hash
    entries = tuple(entries_list)
    chain_linkage_verified = verify_chain_links(entries)

    safety_verified = all(
        not item.market_data_api_called
        and not item.account_api_called
        and not item.network_accessed
        and not item.broker_api_called
        and not item.broker_order_created
        and not item.order_submitted
        and not item.live_execution_authorized
        and item.execution_blocked
        and not item.funds_reserved
        and not item.holdings_reserved
        and item.certificate is not None
        and item.certificate.execution_blocked
        and not item.certificate.funds_reserved
        and not item.certificate.holdings_reserved
        for item in sources
    )

    after_hashes = tuple(_source_result_hash(item) for item in sources)
    sources_remained_unchanged = before_hashes == after_hashes

    checks = (
        ("source_contracts", source_contracts_verified, "V24.2 source contracts"),
        (
            "source_certificate_hashes",
            source_certificate_hashes_verified,
            "V24.2 certificate hashes",
        ),
        (
            "source_findings_hashes",
            source_findings_hashes_verified,
            "V24.2 findings hashes",
        ),
        (
            "source_result_identities",
            source_result_identities_verified,
            "V24.2 result identities",
        ),
        ("unique_sources", unique_sources_verified, "duplicate source prevention"),
        (
            "chronological_order",
            chronological_order_verified,
            "source chronological order",
        ),
        ("chain_linkage", chain_linkage_verified, "hash-chain linkage"),
        ("source_safety", safety_verified, "offline execution safety"),
        ("source_immutability", sources_remained_unchanged, "sources unchanged"),
    )
    findings = tuple(
        AuditChainFindingV243(index, name, passed, detail)
        for index, (name, passed, detail) in enumerate(checks, start=1)
    )
    reasons = tuple(detail for _, passed, detail in checks if not passed)
    all_passed = all(item.passed for item in findings)
    result_status = "AUDIT_CHAIN_VERIFIED" if all_passed else "AUDIT_CHAIN_FAILED"

    result_identity_payload = {
        "version": VERSION,
        "created_at": created_at.isoformat(),
        "source_result_ids": source_ids,
        "final_chain_hash": entries[-1].entry_hash,
        "findings_hash": _findings_hash(findings),
        "result_status": result_status,
    }
    chain_result_id = sha256_payload(result_identity_payload)

    output_certificate = None
    if all_passed:
        unsigned_certificate = AuditChainCertificateV243(
            certificate_id=chain_result_id,
            issued_at=created_at.isoformat(),
            certificate_status=result_status,
            source_count=len(sources),
            first_source_result_id=source_ids[0],
            last_source_result_id=source_ids[-1],
            genesis_hash=GENESIS_HASH,
            final_chain_hash=entries[-1].entry_hash,
            findings_hash=_findings_hash(findings),
            operator=operator,
            execution_blocked=True,
            funds_reserved=False,
            holdings_reserved=False,
            certificate_hash="",
        )
        output_certificate = replace(
            unsigned_certificate,
            certificate_hash=sha256_payload(
                _certificate_payload(unsigned_certificate)
            ),
        )

    return AuditChainV243Result(
        version=VERSION,
        created_at=created_at.isoformat(),
        chain_result_id=chain_result_id,
        result_status=result_status,
        source_contracts_verified=source_contracts_verified,
        source_certificate_hashes_verified=source_certificate_hashes_verified,
        source_findings_hashes_verified=source_findings_hashes_verified,
        source_result_identities_verified=source_result_identities_verified,
        unique_sources_verified=unique_sources_verified,
        chronological_order_verified=chronological_order_verified,
        chain_linkage_verified=chain_linkage_verified,
        safety_verified=safety_verified,
        sources_remained_unchanged=sources_remained_unchanged,
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
        entries=entries,
        findings=findings,
        certificate=output_certificate,
        reasons=reasons,
        source_path=str(source_path),
    )


def save_chain_result(result: AuditChainV243Result, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_chain_result(path: str | Path) -> AuditChainV243Result:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    payload["policy"] = AuditChainV243Policy(**payload["policy"])
    payload["entries"] = tuple(AuditChainEntryV243(**item) for item in payload["entries"])
    payload["findings"] = tuple(
        AuditChainFindingV243(**item) for item in payload["findings"]
    )
    if payload["certificate"] is not None:
        payload["certificate"] = AuditChainCertificateV243(**payload["certificate"])
    payload["reasons"] = tuple(payload["reasons"])
    return AuditChainV243Result(**payload)


__all__ = [
    "VERSION",
    "SOURCE_VERSION",
    "REQUIRED_CONFIRMATION",
    "GENESIS_HASH",
    "AuditChainV243Policy",
    "AuditChainFindingV243",
    "AuditChainEntryV243",
    "AuditChainCertificateV243",
    "AuditChainV243Result",
    "validate_policy",
    "verify_chain_entry",
    "verify_chain_links",
    "verify_chain_certificate",
    "build_offline_audit_chain_v24_3",
    "save_chain_result",
    "load_chain_result",
]
