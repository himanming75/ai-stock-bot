import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# V15.1 테스트 Helper를 먼저 불러오면 V15.0/V15.1 의존 형식이
# 전체 프로젝트와 다운로드 작업공간 모두에서 동일하게 준비됩니다.
from test_sandbox_session_report_archive import archive
from test_sandbox_session_report_archive import (
    create_source as create_final_report_source,
)

from backtest.sandbox_archive_integrity_audit import (
    SandboxArchiveIntegrityAuditPolicy,
    audit_sandbox_archive_integrity,
    load_audit_result,
    save_audit_result,
    verify_audit_certificate,
)


NOW = datetime(2026, 7, 28, 14, 50, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    first = archive(create_final_report_source())
    return archive(
        create_final_report_source(),
        existing=first.entries,
        now=datetime(2026, 7, 28, 14, 31, tzinfo=timezone.utc),
    )


def audit(
    source: Any,
    operator: str | None = None,
    text: str = "AUDIT IN MEMORY SANDBOX ARCHIVE INTEGRITY",
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    default_operator = (
        source.entries[-1].operator
        if getattr(source, "entries", ()) else "operator-001"
    )
    return silent(
        audit_sandbox_archive_integrity,
        source,
        operator or default_operator,
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
        "V15.2 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = audit(source)
    require(
        result.result_status == "AUDITED_IN_MEMORY",
        "Archive Integrity Audit가 실패했습니다.",
    )
    require(result.audit_status == "PASSED", "Audit Status가 다릅니다.")
    require(result.audit_completed, "Audit Certificate가 없습니다.")
    require(result.certificate is not None, "Audit Certificate가 없습니다.")
    require(result.audited_entry_count == 2, "감사 Entry 개수가 다릅니다.")
    require(
        not result.archive_modified,
        "읽기 전용 Audit가 Archive를 변경했습니다.",
    )
    require(
        source.to_dict() == source_before,
        "V15.1 Source가 Audit 중 변경되었습니다.",
    )
    require(
        len(result.certificate.findings) == 2,
        "Entry별 Audit Finding 개수가 다릅니다.",
    )
    require(
        all(
            finding.finding_status == "PASSED"
            for finding in result.certificate.findings
        ),
        "Entry별 Integrity Finding이 실패했습니다.",
    )
    certificate_valid, certificate_errors = verify_audit_certificate(
        result.certificate
    )
    require(
        certificate_valid and not certificate_errors,
        "Audit Certificate Hash 검사가 실패했습니다.",
    )
    require_safe(result)

    wrong_operator = audit(source, operator="wrong")
    require(
        wrong_operator.result_status == "BLOCKED",
        "잘못된 Operator가 차단되지 않았습니다.",
    )
    wrong_text = audit(source, text="IGNORE")
    require(
        wrong_text.result_status == "BLOCKED",
        "잘못된 확인 문구가 차단되지 않았습니다.",
    )
    unsafe_policy = SandboxArchiveIntegrityAuditPolicy(
        network_access_disabled=False
    )
    unsafe = audit(source, policy=unsafe_policy)
    require(
        not unsafe.all_checks_passed,
        "위험 Policy가 차단되지 않았습니다.",
    )
    wrong_type = audit(object())
    require(
        wrong_type.result_status == "FAILED",
        "잘못된 Source 형식이 실패 처리되지 않았습니다.",
    )
    backward = audit(
        source,
        now=datetime.fromisoformat(source.entries[-1].archived_at)
        - timedelta(seconds=1),
    )
    require(
        backward.result_status == "BLOCKED",
        "역순 Audit 시간이 차단되지 않았습니다.",
    )

    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (
        replace(
            tampered_source.entries[0],
            final_session_outcome="BLOCKED",
        ),
        tampered_source.entries[1],
    )
    tampered = audit(tampered_source)
    require(
        tampered.result_status == "FAILED",
        "변조 Archive Entry가 실패 처리되지 않았습니다.",
    )
    broken_link = copy.deepcopy(source)
    broken_link.latest_archive_entry_hash = "f" * 64
    broken = audit(broken_link)
    require(
        broken.result_status == "BLOCKED",
        "잘못된 Archive Source 연결이 차단되지 않았습니다.",
    )
    unsafe_source = copy.deepcopy(source)
    unsafe_source.broker_api_called = True
    unsafe_result = audit(unsafe_source)
    require(
        unsafe_result.result_status == "FAILED",
        "위험 Archive Source가 실패 처리되지 않았습니다.",
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
        "Audit Certificate 변조가 탐지되지 않았습니다.",
    )

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_audit_result(
            result,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "V15.2 결과가 저장되지 않았습니다.",
        )
        payload = load_audit_result(latest_path)
        require(payload["version"] == "V15.2", "저장 Version이 다릅니다.")
        require(
            payload["certificate"]["certificate_hash"]
            == result.audit_certificate_hash,
            "저장 Audit Certificate Hash가 다릅니다.",
        )

    for checked in (
        result,
        wrong_operator,
        wrong_text,
        unsafe,
        wrong_type,
        backward,
        tampered,
        broken,
        unsafe_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V15.2": result.version == "V15.2",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            SandboxArchiveIntegrityAuditPolicy.__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V15.1 archive source passed": result.source_checks_passed,
        "Archive hash chain passed": (
            result.archive_hash_chain_checks_passed
        ),
        "Source linkage passed": result.source_linkage_checks_passed,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Entry safety check passed": result.entry_safety_checks_passed,
        "Archive snapshot hash passed": result.snapshot_hash_checks_passed,
        "Archive remained unchanged": (
            result.archive_unchanged_checks_passed
        ),
        "Audit certificate hash passed": certificate_valid,
        "Two entry findings passed": all(
            finding.finding_status == "PASSED"
            for finding in result.certificate.findings
        ),
        "Wrong operator was blocked": (
            wrong_operator.result_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered archive failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": (
            broken.result_status == "BLOCKED"
        ),
        "Unsafe archive source failed": (
            unsafe_result.result_status == "FAILED"
        ),
        "Certificate tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V15.2",
        "Market data API was not called": not result.market_data_api_called,
        "Account was not accessed": not result.account_accessed,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": (
            not result.live_execution_authorized
        ),
    }
    checks["All checks passed"] = all(checks.values())

    print("=" * 100)
    print("AI STOCK BOT V15.2 SANDBOX ARCHIVE INTEGRITY AUDIT TEST")
    print("=" * 100)
    print("V15.2 VALIDATION CHECKS")
    print("-" * 100)
    for name, passed in checks.items():
        print(f"{name:<66}: {passed}")
    print("=" * 100)
    require(
        checks["All checks passed"],
        "V15.2 Validation Check가 실패했습니다.",
    )
    print()
    print("V15.2 sandbox archive integrity audit test completed successfully.")
    print(
        "V15.1 Archive Chain, Entry Findings, Snapshot Hash, 읽기 전용 감사 및 "
        "Certificate Hash가 검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
