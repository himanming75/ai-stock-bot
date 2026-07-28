import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from test_sandbox_verification_final_report_archive_certificate_audit_final_report_archive_integrity_audit_ledger_integrity_verification import (
    create_source as create_ledger_source,
)
from test_sandbox_verification_final_report_archive_certificate_audit_final_report_archive_integrity_audit_ledger_integrity_verification import (
    verify,
)

from backtest.sandbox_verification_final_report_archive_certificate_audit_final_report_archive_integrity_audit_ledger_integrity_verification_certificate_ledger import (
    SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveIntegrityAuditLedgerIntegrityVerificationCertificateLedgerPolicy,
    load_certificate_ledger_result,
    record_sandbox_verification_final_report_archive_certificate_audit_final_report_archive_integrity_audit_ledger_integrity_verification_certificate,
    save_certificate_ledger_result,
    verify_certificate_ledger_chain,
)


NOW = datetime(2026, 7, 29, 0, 30, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return verify(create_ledger_source())


def record(
    source: Any,
    operator: str = "operator-001",
    text: str = (
        "RECORD IN MEMORY SANDBOX VERIFICATION FINAL REPORT ARCHIVE "
        "CERTIFICATE AUDIT FINAL REPORT ARCHIVE INTEGRITY AUDIT LEDGER "
        "INTEGRITY VERIFICATION CERTIFICATE"
    ),
    existing: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        record_sandbox_verification_final_report_archive_certificate_audit_final_report_archive_integrity_audit_ledger_integrity_verification_certificate,
        source,
        operator,
        text,
        existing,
        policy,
        now,
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
        "V17.5 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    first_source = create_source()
    first = record(first_source)
    require(first.result_status == "RECORDED_IN_MEMORY", "첫 기록 실패")
    require(first.total_ledger_entry_count == 1, "첫 Entry 개수 오류")
    require(
        first.entries[0].verification_certificate_hash
        == first_source.verification_certificate_hash,
        "V17.4 Certificate Hash 보존 실패",
    )
    require(
        first.entries[0].latest_final_report_hash
        == first_source.latest_final_report_hash,
        "Final Report Hash 보존 실패",
    )
    require(
        first.entries[0].latest_verification_ledger_snapshot_hash
        == first_source.latest_verification_ledger_snapshot_hash,
        "Verification Ledger Snapshot Hash 보존 실패",
    )
    require(
        first.entries[0].latest_previous_final_report_hash
        == first_source.latest_previous_final_report_hash,
        "Previous Final Report Hash 보존 실패",
    )
    require(
        first.entries[0].latest_source_certificate_ledger_snapshot_hash
        == first_source.latest_source_certificate_ledger_snapshot_hash,
        "Source Certificate Ledger Snapshot Hash 보존 실패",
    )
    require(
        first.entries[0].latest_certificate_ledger_snapshot_hash
        == first_source.latest_certificate_ledger_snapshot_hash,
        "Certificate Ledger Snapshot Hash 보존 실패",
    )
    require_safe(first)

    second_source = create_source()
    second = record(
        second_source,
        existing=first.entries,
        now=NOW + timedelta(minutes=1),
    )
    require(
        second.result_status == "RECORDED_IN_MEMORY",
        "두 번째 기록 실패",
    )
    require(second.total_ledger_entry_count == 2, "두 Entry 생성 실패")
    valid_chain, chain_errors = verify_certificate_ledger_chain(
        second.entries
    )
    require(valid_chain and not chain_errors, "Hash Chain 실패")

    duplicate = record(
        first_source,
        existing=first.entries,
        now=NOW + timedelta(minutes=1),
    )
    require(
        duplicate.result_status == "BLOCKED",
        "중복 Certificate 미차단",
    )
    wrong_text = record(first_source, text="IGNORE")
    require(
        wrong_text.result_status == "BLOCKED",
        "확인 문구 미차단",
    )
    empty_operator = record(first_source, operator="")
    require(
        empty_operator.result_status == "BLOCKED",
        "빈 Operator 미차단",
    )
    unsafe_policy = (
        SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveIntegrityAuditLedgerIntegrityVerificationCertificateLedgerPolicy(
            live_execution_disabled=False
        )
    )
    unsafe = record(first_source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy 미차단")
    wrong_type = record(object())
    require(
        wrong_type.result_status == "FAILED",
        "잘못된 Source 미실패",
    )
    wrong_existing = record(
        first_source,
        existing={"invalid": True},
    )
    require(
        wrong_existing.result_status == "BLOCKED",
        "잘못된 Ledger 미차단",
    )
    backward = record(
        second_source,
        existing=first.entries,
        now=NOW - timedelta(seconds=1),
    )
    require(
        backward.result_status == "BLOCKED",
        "역순 시간 미차단",
    )

    tampered_source = copy.deepcopy(first_source)
    tampered_source.certificate = replace(
        tampered_source.certificate,
        verification_status="FAILED",
    )
    tampered = record(tampered_source)
    require(
        tampered.result_status == "FAILED",
        "변조 Certificate 미실패",
    )
    broken_source = copy.deepcopy(first_source)
    broken_source.verification_certificate_hash = "f" * 64
    broken = record(broken_source)
    require(
        broken.result_status == "BLOCKED",
        "깨진 Source 연결 미차단",
    )
    changed_entry = replace(
        second.entries[0],
        ledger_snapshot_hash="e" * 64,
    )
    changed_entries = (changed_entry, second.entries[1])
    changed_valid, changed_errors = verify_certificate_ledger_chain(
        changed_entries
    )
    require(
        not changed_valid and changed_errors,
        "Ledger 변조 미탐지",
    )
    unsafe_existing = record(
        create_source(),
        existing=changed_entries,
        now=NOW + timedelta(minutes=2),
    )
    require(
        unsafe_existing.result_status == "BLOCKED",
        "변조 Ledger 미차단",
    )
    unsafe_source = copy.deepcopy(first_source)
    unsafe_source.live_execution_authorized = True
    unsafe_source_result = record(unsafe_source)
    require(
        unsafe_source_result.result_status == "FAILED",
        "위험 Source 미실패",
    )

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_certificate_ledger_result(
            second,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "저장 실패",
        )
        payload = load_certificate_ledger_result(latest_path)
        require(payload["version"] == "V17.5", "저장 Version 오류")
        require(len(payload["entries"]) == 2, "저장 Entry 개수 오류")

    for checked in (
        first,
        second,
        duplicate,
        wrong_text,
        empty_operator,
        unsafe,
        wrong_type,
        wrong_existing,
        backward,
        tampered,
        broken,
        unsafe_existing,
        unsafe_source_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V17.5": second.version == "V17.5",
        "Default policy is valid": second.policy_checks_passed,
        "Policy is immutable": (
            SandboxVerificationFinalReportArchiveCertificateAuditFinalReportArchiveIntegrityAuditLedgerIntegrityVerificationCertificateLedgerPolicy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V17.4 verification source passed": second.source_checks_passed,
        "Certificate hash passed": (
            second.certificate_hash_checks_passed
        ),
        "Source linkage passed": second.linkage_checks_passed,
        "First certificate was recorded": first.ledger_entry_recorded,
        "Second certificate was recorded": second.ledger_entry_recorded,
        "Two ledger entries were created": (
            second.total_ledger_entry_count == 2
        ),
        "Sequences are chronological": (
            [entry.sequence for entry in second.entries] == [1, 2]
        ),
        "Verification ledger hash chain passed": valid_chain,
        "Final report hash was preserved": (
            first.entries[0].latest_final_report_hash
            == first_source.latest_final_report_hash
        ),
        "Verification ledger snapshot hash was preserved": (
            first.entries[0].latest_verification_ledger_snapshot_hash
            == first_source.latest_verification_ledger_snapshot_hash
        ),
        "Previous final report hash was preserved": (
            first.entries[0].latest_previous_final_report_hash
            == first_source.latest_previous_final_report_hash
        ),
        "Source certificate ledger snapshot hash was preserved": (
            first.entries[0].latest_source_certificate_ledger_snapshot_hash
            == first_source.latest_source_certificate_ledger_snapshot_hash
        ),
        "Certificate ledger snapshot hash was preserved": (
            first.entries[0].latest_certificate_ledger_snapshot_hash
            == first_source.latest_certificate_ledger_snapshot_hash
        ),
        "Duplicate certificate was blocked": (
            duplicate.result_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Empty operator was blocked": (
            empty_operator.result_status == "BLOCKED"
        ),
        "Wrong source type failed": (
            wrong_type.result_status == "FAILED"
        ),
        "Wrong existing ledger was blocked": (
            wrong_existing.result_status == "BLOCKED"
        ),
        "Backward time was blocked": (
            backward.result_status == "BLOCKED"
        ),
        "Tampered certificate failed": (
            tampered.result_status == "FAILED"
        ),
        "Broken source linkage was blocked": (
            broken.result_status == "BLOCKED"
        ),
        "Ledger tampering detected": not changed_valid,
        "Tampered existing ledger was blocked": (
            unsafe_existing.result_status == "BLOCKED"
        ),
        "Unsafe source failed": (
            unsafe_source_result.result_status == "FAILED"
        ),
        "Result save and load passed": payload["version"] == "V17.5",
        "Market data API was not called": (
            not second.market_data_api_called
        ),
        "Account was not accessed": not second.account_accessed,
        "Network was not accessed": not second.network_accessed,
        "Broker API was not called": not second.broker_api_called,
        "Order was not submitted": not second.order_submitted,
        "Live execution not authorized": (
            not second.live_execution_authorized
        ),
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 108)
    print(
        "AI STOCK BOT V17.5 SANDBOX VERIFICATION FINAL REPORT ARCHIVE "
        "CERTIFICATE AUDIT FINAL REPORT ARCHIVE INTEGRITY AUDIT LEDGER "
        "INTEGRITY VERIFICATION CERTIFICATE LEDGER TEST"
    )
    print("=" * 108)
    print("V17.5 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V17.5 Validation Check 실패")
    print()
    print(
        "V17.5 sandbox verification final report archive integrity "
        "verification certificate ledger test completed successfully."
    )
    print(
        "V17.4 Certificate Hash, Final Report 연결 Hash, Ledger Snapshot "
        "Hash 보존 및 SHA-256 Ledger Chain이 검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
