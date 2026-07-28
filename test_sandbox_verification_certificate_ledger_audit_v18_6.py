import contextlib
import copy
import io
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_verification_certificate_ledger_audit_v18_6 import (
    GENESIS_HASH,
    SandboxVerificationCertificateLedgerAuditV186Policy,
    audit_sandbox_verification_certificate_ledger_v18_6,
    load_audit_result,
    save_audit_result,
    sha256_payload as ledger_sha256_payload,
    verify_audit_certificate,
)


NOW = datetime(2026, 7, 29, 5, 20, tzinfo=timezone.utc)


@dataclass(frozen=True)
class OptimizedLedgerEntry:
    ledger_entry_id: str
    sequence: int
    recorded_at: str
    previous_entry_hash: str
    verification_result_id: str
    verification_certificate_id: str
    verification_certificate_hash: str
    source_audit_ledger_result_id: str
    ledger_snapshot_hash: str
    verified_entry_count: int
    latest_audit_ledger_entry_id: str
    latest_audit_ledger_entry_hash: str
    latest_final_report_hash: str
    latest_linked_final_report_hash: str
    latest_verification_ledger_snapshot_hash: str
    latest_previous_final_report_hash: str
    latest_source_certificate_ledger_snapshot_hash: str
    latest_certificate_ledger_snapshot_hash: str
    latest_archived_certificate_ledger_snapshot_hash: str
    verification_status: str
    operator: str
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    market_data_api_called: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    entry_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("entry_hash")
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizedLedgerSource:
    version: str
    created_at: str
    ledger_result_id: str
    result_status: str
    result_status_label: str
    latest_ledger_entry_id: str
    latest_ledger_entry_hash: str
    latest_verification_certificate_id: str
    latest_verification_certificate_hash: str
    latest_ledger_snapshot_hash: str
    latest_final_report_hash: str
    latest_linked_final_report_hash: str
    latest_verification_ledger_snapshot_hash: str
    latest_previous_final_report_hash: str
    latest_source_certificate_ledger_snapshot_hash: str
    latest_certificate_ledger_snapshot_hash: str
    latest_archived_certificate_ledger_snapshot_hash: str
    total_ledger_entry_count: int
    all_checks_passed: bool
    ledger_entry_recorded: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    market_data_api_called: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    entries: tuple[OptimizedLedgerEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["entries"] = [entry.to_dict() for entry in self.entries]
        return payload


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_entry(
    sequence: int,
    recorded_at: datetime,
    previous_entry_hash: str,
    marker: str,
) -> Any:
    payload = {
        "ledger_entry_id": f"ledger-entry-{sequence}",
        "sequence": sequence,
        "recorded_at": recorded_at.isoformat(),
        "previous_entry_hash": previous_entry_hash,
        "verification_result_id": f"verification-result-{sequence}",
        "verification_certificate_id": f"verification-certificate-{sequence}",
        "verification_certificate_hash": marker * 64,
        "source_audit_ledger_result_id": f"audit-ledger-result-{sequence}",
        "ledger_snapshot_hash": chr(ord(marker) + 1) * 64,
        "verified_entry_count": 2,
        "latest_audit_ledger_entry_id": f"audit-ledger-entry-{sequence}",
        "latest_audit_ledger_entry_hash": chr(ord(marker) + 2) * 64,
        "latest_final_report_hash": chr(ord(marker) + 3) * 64,
        "latest_linked_final_report_hash": chr(ord(marker) + 4) * 64,
        "latest_verification_ledger_snapshot_hash": (
            chr(ord(marker) + 5) * 64
        ),
        "latest_previous_final_report_hash": chr(ord(marker) + 6) * 64,
        "latest_source_certificate_ledger_snapshot_hash": (
            chr(ord(marker) + 7) * 64
        ),
        "latest_certificate_ledger_snapshot_hash": (
            chr(ord(marker) + 8) * 64
        ),
        "latest_archived_certificate_ledger_snapshot_hash": (
            chr(ord(marker) + 9) * 64
        ),
        "verification_status": "PASSED",
        "operator": "operator-001",
        "paper_execution_authorized": False,
        "automatic_execution_authorized": False,
        "execution_blocked": True,
        "credentials_used": False,
        "market_data_api_called": False,
        "network_accessed": False,
        "account_accessed": False,
        "broker_api_called": False,
        "order_submitted": False,
        "live_execution_authorized": False,
    }
    return (
        OptimizedLedgerEntry(
            **payload,
            entry_hash=ledger_sha256_payload(payload),
        )
    )


def create_source() -> Any:
    first = create_entry(
        1,
        datetime(2026, 7, 29, 5, 0, tzinfo=timezone.utc),
        GENESIS_HASH,
        "1",
    )
    second = create_entry(
        2,
        datetime(2026, 7, 29, 5, 1, tzinfo=timezone.utc),
        first.entry_hash,
        "2",
    )
    entries = (first, second)
    return OptimizedLedgerSource(
        version="V18.5",
        created_at=second.recorded_at,
        ledger_result_id="v17-5-optimized-test-ledger",
        result_status="RECORDED_IN_MEMORY",
        result_status_label="Optimized V18.5 test fixture",
        latest_ledger_entry_id=second.ledger_entry_id,
        latest_ledger_entry_hash=second.entry_hash,
        latest_verification_certificate_id=(
            second.verification_certificate_id
        ),
        latest_verification_certificate_hash=(
            second.verification_certificate_hash
        ),
        latest_ledger_snapshot_hash=second.ledger_snapshot_hash,
        latest_final_report_hash=second.latest_final_report_hash,
        latest_linked_final_report_hash=(
            second.latest_linked_final_report_hash
        ),
        latest_verification_ledger_snapshot_hash=(
            second.latest_verification_ledger_snapshot_hash
        ),
        latest_previous_final_report_hash=(
            second.latest_previous_final_report_hash
        ),
        latest_source_certificate_ledger_snapshot_hash=(
            second.latest_source_certificate_ledger_snapshot_hash
        ),
        latest_certificate_ledger_snapshot_hash=(
            second.latest_certificate_ledger_snapshot_hash
        ),
        latest_archived_certificate_ledger_snapshot_hash=(
            second.latest_archived_certificate_ledger_snapshot_hash
        ),
        total_ledger_entry_count=2,
        all_checks_passed=True,
        ledger_entry_recorded=True,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        credentials_used=False,
        market_data_api_called=False,
        network_accessed=False,
        account_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        entries=entries,
    )


def audit(
    source: Any,
    operator: str = "operator-001",
    text: str = (
        "AUDIT IN MEMORY SANDBOX VERIFICATION CERTIFICATE LEDGER V18.5"
    ),
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        audit_sandbox_verification_certificate_ledger_v18_6,
        source, operator, text, policy, now,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    require(
        all(
            (
                not result.paper_execution_authorized,
                not result.automatic_execution_authorized,
                result.execution_blocked,
                not result.credentials_used,
                not result.market_data_api_called,
                not result.network_accessed,
                not result.account_accessed,
                not result.broker_api_called,
                not result.broker_order_created,
                not result.order_submitted,
                not result.live_order_created,
                not result.live_execution_authorized,
            )
        ),
        "V18.6 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = audit(source)
    require(result.result_status == "AUDITED_IN_MEMORY", "정상 Audit 실패")
    require(result.audit_status == "PASSED", "Audit Status 오류")
    require(result.audited_entry_count == 2, "Audit Entry 개수 오류")
    require(result.certificate is not None, "Audit Certificate 누락")
    require(source.to_dict() == source_before, "V18.5 Source 변경")
    require(not result.ledger_modified, "Ledger Modified 값 오류")
    require(
        all(
            finding.finding_status == "PASSED"
            for finding in result.certificate.findings
        ),
        "Entry Finding 실패",
    )
    require(
        result.latest_final_report_hash
        == source.latest_final_report_hash,
        "Final Report Hash 보존 실패",
    )
    require(
        result.latest_linked_final_report_hash
        == source.latest_linked_final_report_hash,
        "Linked Final Report Hash 보존 실패",
    )
    require(
        result.latest_verification_ledger_snapshot_hash
        == source.latest_verification_ledger_snapshot_hash,
        "Verification Ledger Snapshot Hash 보존 실패",
    )
    require(
        result.latest_previous_final_report_hash
        == source.latest_previous_final_report_hash,
        "Previous Final Report Hash 보존 실패",
    )
    require(
        result.latest_source_certificate_ledger_snapshot_hash
        == source.latest_source_certificate_ledger_snapshot_hash,
        "Source Certificate Ledger Snapshot Hash 보존 실패",
    )
    require(
        result.latest_certificate_ledger_snapshot_hash
        == source.latest_certificate_ledger_snapshot_hash,
        "Certificate Ledger Snapshot Hash 보존 실패",
    )
    require(
        result.latest_archived_certificate_ledger_snapshot_hash
        == source.latest_archived_certificate_ledger_snapshot_hash,
        "Archived Certificate Ledger Snapshot Hash 보존 실패",
    )
    certificate_valid, certificate_errors = verify_audit_certificate(
        result.certificate
    )
    require(
        certificate_valid and not certificate_errors,
        "Certificate Hash 실패",
    )
    require_safe(result)

    wrong_text = audit(source, text="IGNORE")
    wrong_operator = audit(source, operator="operator-999")
    empty_operator = audit(source, operator="")
    require(wrong_text.result_status == "BLOCKED", "확인 문구 미차단")
    require(wrong_operator.result_status == "BLOCKED", "Operator 미차단")
    require(empty_operator.result_status == "BLOCKED", "빈 Operator 미차단")
    unsafe_policy = (
        SandboxVerificationCertificateLedgerAuditV186Policy(
            live_execution_disabled=False
        )
    )
    unsafe = audit(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy 미차단")
    wrong_type = audit(object())
    require(wrong_type.result_status == "FAILED", "잘못된 Source 미실패")
    backward = audit(
        source,
        now=datetime.fromisoformat(source.entries[-1].recorded_at)
        - timedelta(seconds=1),
    )
    require(backward.result_status == "BLOCKED", "역순 시간 미차단")

    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (
        replace(
            tampered_source.entries[0],
            ledger_snapshot_hash="e" * 64,
        ),
        tampered_source.entries[1],
    )
    tampered = audit(tampered_source)
    require(tampered.result_status == "FAILED", "Ledger 변조 미실패")
    broken_linkage = copy.deepcopy(source)
    broken_linkage.latest_ledger_entry_hash = "f" * 64
    broken = audit(broken_linkage)
    require(broken.result_status == "BLOCKED", "Source Linkage 미차단")
    unsafe_source = copy.deepcopy(source)
    unsafe_source.network_accessed = True
    unsafe_result = audit(unsafe_source)
    require(unsafe_result.result_status == "FAILED", "위험 Source 미실패")
    changed_certificate = replace(
        result.certificate,
        verification_ledger_snapshot_hash="a" * 64,
    )
    changed_valid, changed_errors = verify_audit_certificate(
        changed_certificate
    )
    require(
        not changed_valid and changed_errors,
        "Audit Certificate 변조 미탐지",
    )

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_audit_result(
            result, Path(directory)
        )
        require(report_path.exists() and latest_path.exists(), "저장 실패")
        payload = load_audit_result(latest_path)
        require(payload["version"] == "V18.6", "저장 Version 오류")
        require(payload["audited_entry_count"] == 2, "저장 Entry 개수 오류")

    for checked in (
        result, wrong_text, wrong_operator, empty_operator, unsafe,
        wrong_type, backward, tampered, broken, unsafe_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V18.6": result.version == "V18.6",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            SandboxVerificationCertificateLedgerAuditV186Policy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V18.5 certificate ledger source passed": result.source_checks_passed,
        "Optimized source fixture passed": (
            source.ledger_result_id == "v17-5-optimized-test-ledger"
        ),
        "Certificate ledger hash chain passed": (
            result.ledger_hash_chain_checks_passed
        ),
        "Source linkage passed": result.source_linkage_checks_passed,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Verification status passed": (
            result.verification_status_checks_passed
        ),
        "Entry safety check passed": result.entry_safety_checks_passed,
        "Ledger snapshot hash passed": result.snapshot_hash_checks_passed,
        "Certificate ledger remained unchanged": (
            source.to_dict() == source_before
        ),
        "Audit certificate hash passed": certificate_valid,
        "Two entry findings passed": len(result.certificate.findings) == 2,
        "Final report hash was preserved": (
            result.latest_final_report_hash
            == source.latest_final_report_hash
        ),
        "Linked final report hash was preserved": (
            result.latest_linked_final_report_hash
            == source.latest_linked_final_report_hash
        ),
        "Verification ledger snapshot hash was preserved": (
            result.latest_verification_ledger_snapshot_hash
            == source.latest_verification_ledger_snapshot_hash
        ),
        "Previous final report hash was preserved": (
            result.latest_previous_final_report_hash
            == source.latest_previous_final_report_hash
        ),
        "Source certificate ledger snapshot hash was preserved": (
            result.latest_source_certificate_ledger_snapshot_hash
            == source.latest_source_certificate_ledger_snapshot_hash
        ),
        "Certificate ledger snapshot hash was preserved": (
            result.latest_certificate_ledger_snapshot_hash
            == source.latest_certificate_ledger_snapshot_hash
        ),
        "Archived certificate ledger snapshot hash was preserved": (
            result.latest_archived_certificate_ledger_snapshot_hash
            == source.latest_archived_certificate_ledger_snapshot_hash
        ),
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Empty operator was blocked": empty_operator.result_status == "BLOCKED",
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered ledger failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": broken.result_status == "BLOCKED",
        "Unsafe source failed": unsafe_result.result_status == "FAILED",
        "Certificate tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V18.6",
        "Market data API was not called": not result.market_data_api_called,
        "Account was not accessed": not result.account_accessed,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 108)
    print(
        "AI STOCK BOT V18.6 SANDBOX VERIFICATION CERTIFICATE LEDGER "
        "INTEGRITY AUDIT TEST"
    )
    print("=" * 108)
    print("V18.6 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V18.6 Validation Check 실패")
    print()
    print(
        "V18.6 sandbox verification certificate ledger integrity audit "
        "test completed successfully."
    )
    print(
        "V18.5 Ledger Hash Chain, 연결 Hash, Entry Findings, 읽기 전용 "
        "Audit 및 Certificate Hash가 검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
