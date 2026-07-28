import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from test_sandbox_verification_final_report_archive import archive
from test_sandbox_verification_final_report_archive import (
    create_source as create_final_report_source,
)

from backtest.sandbox_verification_final_report_archive_integrity_audit import (
    SandboxVerificationFinalReportArchiveIntegrityAuditPolicy,
    audit_sandbox_verification_final_report_archive_integrity,
    load_audit_result,
    save_audit_result,
    verify_audit_certificate,
)


NOW = datetime(2026, 7, 28, 18, 50, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    first = archive(create_final_report_source())
    return archive(
        create_final_report_source(),
        existing=first.entries,
        now=datetime(2026, 7, 28, 17, 51, tzinfo=timezone.utc),
    )


def audit(
    source: Any,
    operator: str | None = None,
    text: str = (
        "AUDIT IN MEMORY SANDBOX VERIFICATION FINAL REPORT ARCHIVE"
    ),
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    default_operator = (
        source.entries[-1].operator
        if getattr(source, "entries", ()) else "operator-001"
    )
    return silent(
        audit_sandbox_verification_final_report_archive_integrity,
        source,
        operator if operator is not None else default_operator,
        text,
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
        "V16.2 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = audit(source)
    require(
        result.result_status == "AUDITED_IN_MEMORY",
        "Archive Integrity Audit가 실패했습니다.",
    )
    require(result.audit_status == "PASSED", "Audit Status 오류")
    require(result.audit_completed, "Audit가 완료되지 않았습니다.")
    require(result.certificate is not None, "Audit Certificate 없음")
    require(result.audited_entry_count == 2, "Audit Entry 개수 오류")
    require(not result.archive_modified, "읽기 전용 Archive 변경")
    require(source.to_dict() == source_before, "V16.1 Source 변경")
    require(
        len(result.certificate.findings) == 2,
        "Entry Finding 개수 오류",
    )
    require(
        all(
            finding.finding_status == "PASSED"
            for finding in result.certificate.findings
        ),
        "Entry별 Integrity Finding 실패",
    )
    require(
        result.latest_final_report_hash
        == source.latest_final_report_hash,
        "Final Report Hash 보존 실패",
    )
    require(
        result.latest_certificate_ledger_snapshot_hash
        == source.latest_certificate_ledger_snapshot_hash,
        "Certificate Ledger Snapshot Hash 보존 실패",
    )
    certificate_valid, certificate_errors = verify_audit_certificate(
        result.certificate
    )
    require(
        certificate_valid and not certificate_errors,
        "Audit Certificate Hash 검사 실패",
    )
    require_safe(result)

    wrong_operator = audit(source, operator="wrong")
    require(
        wrong_operator.result_status == "BLOCKED",
        "잘못된 Operator 미차단",
    )
    wrong_text = audit(source, text="IGNORE")
    require(
        wrong_text.result_status == "BLOCKED",
        "잘못된 확인 문구 미차단",
    )
    empty_operator = audit(source, operator="")
    require(
        empty_operator.result_status == "BLOCKED",
        "빈 Operator 미차단",
    )
    unsafe_policy = (
        SandboxVerificationFinalReportArchiveIntegrityAuditPolicy(
            network_access_disabled=False
        )
    )
    unsafe = audit(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy 미차단")
    wrong_type = audit(object())
    require(
        wrong_type.result_status == "FAILED",
        "잘못된 Source 형식 미실패",
    )
    backward = audit(
        source,
        now=datetime.fromisoformat(source.entries[-1].archived_at)
        - timedelta(seconds=1),
    )
    require(
        backward.result_status == "BLOCKED",
        "역순 Audit 시간 미차단",
    )

    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (
        replace(
            tampered_source.entries[0],
            final_verification_status="BLOCKED",
        ),
        tampered_source.entries[1],
    )
    tampered = audit(tampered_source)
    require(
        tampered.result_status == "FAILED",
        "변조 Archive Entry 미실패",
    )

    broken_link = copy.deepcopy(source)
    broken_link.latest_archive_entry_hash = "f" * 64
    broken = audit(broken_link)
    require(
        broken.result_status == "BLOCKED",
        "잘못된 Source Linkage 미차단",
    )

    unsafe_source = copy.deepcopy(source)
    unsafe_source.broker_api_called = True
    unsafe_result = audit(unsafe_source)
    require(
        unsafe_result.result_status == "FAILED",
        "위험 Archive Source 미실패",
    )

    changed_certificate = replace(
        result.certificate,
        audit_status="FAILED",
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
            result,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "V16.2 결과 저장 실패",
        )
        payload = load_audit_result(latest_path)
        require(payload["version"] == "V16.2", "저장 Version 오류")
        require(
            payload["certificate"]["certificate_hash"]
            == result.audit_certificate_hash,
            "저장 Certificate Hash 오류",
        )

    for checked in (
        result,
        wrong_operator,
        wrong_text,
        empty_operator,
        unsafe,
        wrong_type,
        backward,
        tampered,
        broken,
        unsafe_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V16.2": result.version == "V16.2",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            SandboxVerificationFinalReportArchiveIntegrityAuditPolicy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V16.1 archive source passed": result.source_checks_passed,
        "Archive hash chain passed": (
            result.archive_hash_chain_checks_passed
        ),
        "Source linkage passed": result.source_linkage_checks_passed,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Final verification status passed": (
            result.final_verification_status_checks_passed
        ),
        "Entry safety check passed": result.entry_safety_checks_passed,
        "Archive snapshot hash passed": (
            result.snapshot_hash_checks_passed
        ),
        "Archive remained unchanged": (
            result.archive_unchanged_checks_passed
            and source.to_dict() == source_before
        ),
        "Audit certificate hash passed": (
            result.certificate_hash_checks_passed
            and certificate_valid
        ),
        "Two entry findings passed": (
            len(result.certificate.findings) == 2
        ),
        "Wrong operator was blocked": (
            wrong_operator.result_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Empty operator was blocked": (
            empty_operator.result_status == "BLOCKED"
        ),
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered archive failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": (
            broken.result_status == "BLOCKED"
        ),
        "Unsafe source failed": unsafe_result.result_status == "FAILED",
        "Certificate tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V16.2",
        "Market data API was not called": (
            not result.market_data_api_called
        ),
        "Account was not accessed": not result.account_accessed,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": (
            not result.live_execution_authorized
        ),
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 108)
    print(
        "AI STOCK BOT V16.2 SANDBOX VERIFICATION FINAL REPORT "
        "ARCHIVE INTEGRITY AUDIT TEST"
    )
    print("=" * 108)
    print("V16.2 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V16.2 Validation Check 실패")
    print()
    print(
        "V16.2 sandbox verification final report archive integrity "
        "audit test completed successfully."
    )
    print(
        "V16.1 Archive Chain, Entry Findings, Snapshot Hash, 읽기 전용 "
        "감사 및 Audit Certificate Hash가 검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
