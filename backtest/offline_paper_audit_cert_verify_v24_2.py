"""V24.2 offline-only verification of a V24.1 audit certificate.

This module never imports or calls market-data, account, network, or broker APIs.
It verifies immutable offline dataclass snapshots only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Optional, Tuple

from backtest.offline_paper_audit_cert_ledger_integrity_v24_1 import (
    AuditCertificateLedgerIntegrityV241Result,
    sha256_payload,
    verify_audit_certificate,
)


VERSION = "V24.2"
SOURCE_VERSION = "V24.1"
REQUIRED_CONFIRMATION = "VERIFY OFFLINE PAPER AUDIT CERTIFICATE V24.2"


@dataclass(frozen=True)
class AuditCertificateVerificationV242Policy:
    source_version: str = SOURCE_VERSION
    required_source_status: str = "INTEGRITY_VERIFIED"
    required_certificate_status: str = "INTEGRITY_VERIFIED"
    required_confirmation: str = REQUIRED_CONFIRMATION
    require_certificate_hash: bool = True
    require_findings_hash: bool = True
    require_result_identity: bool = True
    require_source_linkage: bool = True
    require_source_safety: bool = True
    require_source_immutability: bool = True
    allow_market_data_api: bool = False
    allow_account_api: bool = False
    allow_network: bool = False
    allow_broker_api: bool = False
    allow_order_submission: bool = False
    allow_live_execution: bool = False


@dataclass(frozen=True)
class VerificationFindingV242:
    sequence: int
    check_name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class AuditCertificateVerificationCertificateV242:
    certificate_id: str
    issued_at: str
    certificate_status: str
    source_audit_result_id: str
    source_integrity_certificate_id: str
    source_integrity_certificate_hash: str
    source_findings_hash: str
    source_result_hash: str
    findings_hash: str
    operator: str
    execution_blocked: bool
    funds_reserved: bool
    holdings_reserved: bool
    certificate_hash: str


@dataclass(frozen=True)
class AuditCertificateVerificationV242Result:
    version: str
    created_at: str
    verification_result_id: str
    result_status: str
    source_contract_verified: bool
    certificate_hash_verified: bool
    findings_hash_verified: bool
    result_identity_verified: bool
    linkage_verified: bool
    safety_verified: bool
    source_remained_unchanged: bool
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
    policy: AuditCertificateVerificationV242Policy
    findings: Tuple[VerificationFindingV242, ...]
    certificate: Optional[AuditCertificateVerificationCertificateV242]
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


def validate_policy(policy: AuditCertificateVerificationV242Policy) -> None:
    if not isinstance(policy, AuditCertificateVerificationV242Policy):
        raise TypeError("policy must be AuditCertificateVerificationV242Policy")
    expected = AuditCertificateVerificationV242Policy()
    if policy != expected:
        raise ValueError("V24.2 policy is immutable and must use safe defaults")


def _source_result_hash(source: AuditCertificateLedgerIntegrityV241Result) -> str:
    payload = asdict(source)
    payload.pop("source_path", None)
    payload.pop("result_path", None)
    return sha256_payload(payload)


def _findings_hash(findings: tuple) -> str:
    return sha256_payload({"findings": [asdict(item) for item in findings]})


def _certificate_payload(
    certificate: AuditCertificateVerificationCertificateV242,
) -> dict:
    payload = asdict(certificate)
    payload.pop("certificate_hash", None)
    return payload


def verify_verification_certificate(
    certificate: AuditCertificateVerificationCertificateV242,
) -> bool:
    if not isinstance(certificate, AuditCertificateVerificationCertificateV242):
        return False
    return certificate.certificate_hash == sha256_payload(
        _certificate_payload(certificate)
    )


def verify_audit_certificate_v24_2(
    source: AuditCertificateLedgerIntegrityV241Result,
    *,
    operator: str,
    confirmation: str,
    verification_time: str,
    policy: AuditCertificateVerificationV242Policy = AuditCertificateVerificationV242Policy(),
    source_path: str = "",
) -> AuditCertificateVerificationV242Result:
    """Verify a V24.1 result without changing it or using external services."""

    validate_policy(policy)
    if not isinstance(source, AuditCertificateLedgerIntegrityV241Result):
        raise TypeError("source must be a V24.1 audit certificate ledger result")
    if not isinstance(operator, str) or not operator.strip():
        raise ValueError("operator must be a non-empty string")
    operator = operator.strip()
    if confirmation != policy.required_confirmation:
        raise PermissionError("exact V24.2 confirmation is required")

    verified_at = _parse_utc(verification_time)
    source_time = _parse_utc(source.created_at)
    if verified_at < source_time:
        raise ValueError("verification time cannot be before source creation time")

    before_hash = _source_result_hash(source)
    certificate = source.certificate

    source_contract_verified = bool(
        source.version == policy.source_version
        and source.result_status == policy.required_source_status
        and source.certificate_created
        and source.source_remained_unchanged
        and certificate is not None
        and certificate.certificate_status == policy.required_certificate_status
    )
    certificate_hash_verified = bool(
        certificate is not None and not verify_audit_certificate(certificate)
    )

    recalculated_findings_hash = _findings_hash(source.findings)
    findings_hash_verified = bool(
        certificate is not None
        and certificate.findings_hash == recalculated_findings_hash
    )

    expected_result_id = ""
    if certificate is not None:
        expected_result_id = sha256_payload(
            {
                "version": source.version,
                "created_at": source.created_at,
                "source_ledger_result_id": certificate.source_ledger_result_id,
                "source_result_hash": certificate.source_result_hash,
                "findings_hash": recalculated_findings_hash,
                "result_status": source.result_status,
            }
        )
    result_identity_verified = source.audit_result_id == expected_result_id

    linkage_verified = bool(
        certificate is not None
        and certificate.source_ledger_result_id
        and certificate.source_ledger_snapshot_hash
        and certificate.source_latest_entry_hash
        and certificate.source_total_entry_count > 0
        and len(certificate.source_result_hash) == 64
    )
    safety_verified = bool(
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
        and certificate is not None
        and certificate.execution_blocked
        and not certificate.funds_reserved
        and not certificate.holdings_reserved
    )
    after_hash = _source_result_hash(source)
    source_remained_unchanged = before_hash == after_hash

    checks = (
        ("source_contract", source_contract_verified, "V24.1 result contract"),
        ("certificate_hash", certificate_hash_verified, "V24.1 certificate hash"),
        ("findings_hash", findings_hash_verified, "V24.1 findings hash"),
        ("result_identity", result_identity_verified, "V24.1 result identity"),
        ("source_linkage", linkage_verified, "ledger source linkage"),
        ("source_safety", safety_verified, "offline execution safety"),
        ("source_immutability", source_remained_unchanged, "source unchanged"),
    )
    findings = tuple(
        VerificationFindingV242(index, name, passed, detail)
        for index, (name, passed, detail) in enumerate(checks, start=1)
    )
    reasons = tuple(detail for _, passed, detail in checks if not passed)
    all_passed = all(item.passed for item in findings)
    result_status = (
        "AUDIT_CERTIFICATE_VERIFIED"
        if all_passed
        else "AUDIT_CERTIFICATE_VERIFICATION_FAILED"
    )

    result_identity_payload = {
        "version": VERSION,
        "created_at": verified_at.isoformat(),
        "source_audit_result_id": source.audit_result_id,
        "source_result_hash": before_hash,
        "findings_hash": _findings_hash(findings),
        "result_status": result_status,
    }
    verification_result_id = sha256_payload(result_identity_payload)

    output_certificate = None
    if all_passed and certificate is not None:
        unsigned = AuditCertificateVerificationCertificateV242(
            certificate_id=verification_result_id,
            issued_at=verified_at.isoformat(),
            certificate_status=result_status,
            source_audit_result_id=source.audit_result_id,
            source_integrity_certificate_id=certificate.certificate_id,
            source_integrity_certificate_hash=certificate.certificate_hash,
            source_findings_hash=certificate.findings_hash,
            source_result_hash=before_hash,
            findings_hash=_findings_hash(findings),
            operator=operator,
            execution_blocked=True,
            funds_reserved=False,
            holdings_reserved=False,
            certificate_hash="",
        )
        output_certificate = replace(
            unsigned,
            certificate_hash=sha256_payload(_certificate_payload(unsigned)),
        )

    return AuditCertificateVerificationV242Result(
        version=VERSION,
        created_at=verified_at.isoformat(),
        verification_result_id=verification_result_id,
        result_status=result_status,
        source_contract_verified=source_contract_verified,
        certificate_hash_verified=certificate_hash_verified,
        findings_hash_verified=findings_hash_verified,
        result_identity_verified=result_identity_verified,
        linkage_verified=linkage_verified,
        safety_verified=safety_verified,
        source_remained_unchanged=source_remained_unchanged,
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
        findings=findings,
        certificate=output_certificate,
        reasons=reasons,
        source_path=str(source_path),
    )


def save_verification_result(
    result: AuditCertificateVerificationV242Result, path: str | Path
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def load_verification_result(
    path: str | Path,
) -> AuditCertificateVerificationV242Result:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    payload["policy"] = AuditCertificateVerificationV242Policy(**payload["policy"])
    payload["findings"] = tuple(
        VerificationFindingV242(**item) for item in payload["findings"]
    )
    if payload["certificate"] is not None:
        payload["certificate"] = AuditCertificateVerificationCertificateV242(
            **payload["certificate"]
        )
    payload["reasons"] = tuple(payload["reasons"])
    return AuditCertificateVerificationV242Result(**payload)


__all__ = [
    "VERSION",
    "SOURCE_VERSION",
    "REQUIRED_CONFIRMATION",
    "AuditCertificateVerificationV242Policy",
    "VerificationFindingV242",
    "AuditCertificateVerificationCertificateV242",
    "AuditCertificateVerificationV242Result",
    "validate_policy",
    "verify_verification_certificate",
    "verify_audit_certificate_v24_2",
    "save_verification_result",
    "load_verification_result",
]
