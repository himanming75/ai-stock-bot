import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from test_sandbox_verification_final_report_archive_certificate_audit_certificate_ledger import (
    create_source as create_certificate_source,
)
from test_sandbox_verification_final_report_archive_certificate_audit_certificate_ledger import record

from backtest.sandbox_verification_final_report_archive_certificate_audit_final_report import (
    SandboxVerificationFinalReportArchiveCertificateAuditFinalReportPolicy,
    generate_sandbox_verification_final_report_archive_certificate_audit_final_report,
    load_final_report_result,
    save_final_report_result,
    verify_final_report,
)


NOW = datetime(2026, 7, 28, 22, 30, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    first = record(create_certificate_source())
    return record(
        create_certificate_source(),
        existing=first.entries,
        now=datetime(2026, 7, 28, 22, 1, tzinfo=timezone.utc),
    )


def finalize(
    source: Any,
    operator: str = "operator-001",
    text: str = "GENERATE IN MEMORY SANDBOX VERIFICATION FINAL REPORT ARCHIVE CERTIFICATE AUDIT FINAL REPORT",
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        generate_sandbox_verification_final_report_archive_certificate_audit_final_report,
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
        "V17.0 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = finalize(source)
    require(result.result_status == "FINALIZED_IN_MEMORY", "Final Report 실패")
    require(result.final_report_generated, "Final Report 누락")
    require(result.report is not None, "Report Object 누락")
    require(
        result.final_verification_status == "SANDBOX_VERIFICATION_COMPLETE",
        "Final Verification Status 오류",
    )
    require(result.total_certificate_count == 2, "Certificate 개수 오류")
    require(source.to_dict() == source_before, "V16.9 Source 변경 감지")
    require(
        result.latest_verification_ledger_snapshot_hash
        == source.latest_verification_ledger_snapshot_hash,
        "Verification Ledger Snapshot Hash 보존 실패",
    )
    require(
        result.latest_previous_final_report_hash
        == source.latest_final_report_hash,
        "Previous Final Report Hash 보존 실패",
    )
    require(
        result.latest_certificate_ledger_snapshot_hash
        == source.latest_certificate_ledger_snapshot_hash,
        "Certificate Ledger Snapshot Hash 보존 실패",
    )
    report_valid, report_errors = verify_final_report(result.report)
    require(report_valid and not report_errors, "Final Report Hash 실패")
    require_safe(result)

    wrong_text = finalize(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "확인 문구 미차단")
    wrong_operator = finalize(source, operator="operator-999")
    require(wrong_operator.result_status == "BLOCKED", "Operator 미차단")
    empty_operator = finalize(source, operator="")
    require(empty_operator.result_status == "BLOCKED", "빈 Operator 미차단")
    unsafe_policy = SandboxVerificationFinalReportArchiveCertificateAuditFinalReportPolicy(
        broker_api_disabled=False
    )
    unsafe = finalize(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy 미차단")
    wrong_type = finalize(object())
    require(wrong_type.result_status == "FAILED", "잘못된 Source 미실패")
    backward = finalize(
        source,
        now=datetime(2026, 7, 28, 21, 59, tzinfo=timezone.utc),
    )
    require(backward.result_status == "BLOCKED", "역순 시간 미차단")

    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (
        replace(tampered_source.entries[0], ledger_snapshot_hash="e" * 64),
        tampered_source.entries[1],
    )
    tampered = finalize(tampered_source)
    require(tampered.result_status == "FAILED", "Ledger 변조 미실패")

    broken_source = copy.deepcopy(source)
    broken_source.latest_ledger_entry_hash = "f" * 64
    broken = finalize(broken_source)
    require(broken.result_status == "BLOCKED", "Source Linkage 미차단")

    unsafe_source = copy.deepcopy(source)
    unsafe_source.account_accessed = True
    unsafe_result = finalize(unsafe_source)
    require(unsafe_result.result_status == "FAILED", "위험 Source 미실패")

    changed_report = replace(
        result.report, final_verification_status="LIVE_READY"
    )
    changed_valid, changed_errors = verify_final_report(changed_report)
    require(not changed_valid and changed_errors, "Report 변조 미탐지")

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_final_report_result(
            result, Path(directory)
        )
        require(report_path.exists() and latest_path.exists(), "저장 실패")
        payload = load_final_report_result(latest_path)
        require(payload["version"] == "V17.0", "저장 Version 오류")
        require(
            payload["final_verification_status"]
            == "SANDBOX_VERIFICATION_COMPLETE",
            "저장 Final Status 오류",
        )

    for checked in (
        result, wrong_text, wrong_operator, empty_operator, unsafe,
        wrong_type, backward, tampered, broken, unsafe_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V17.0": result.version == "V17.0",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            SandboxVerificationFinalReportArchiveCertificateAuditFinalReportPolicy.__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V16.9 certificate ledger source passed": result.source_checks_passed,
        "Certificate ledger hash chain passed": result.hash_chain_checks_passed,
        "Source linkage passed": result.linkage_checks_passed,
        "Operator check passed": result.operator_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Source remained unchanged": source.to_dict() == source_before,
        "Certificate ledger snapshot hash passed": (
            result.certificate_ledger_snapshot_hash is not None
        ),
        "Verification ledger snapshot hash was preserved": (
            result.latest_verification_ledger_snapshot_hash
            == source.latest_verification_ledger_snapshot_hash
        ),
        "Previous final report hash was preserved": (
            result.latest_previous_final_report_hash
            == source.latest_final_report_hash
        ),
        "Source certificate ledger snapshot hash was preserved": (
            result.latest_certificate_ledger_snapshot_hash
            == source.latest_certificate_ledger_snapshot_hash
        ),
        "Final report hash passed": report_valid,
        "Two certificate summaries created": (
            len(result.report.certificate_summaries) == 2
        ),
        "Sandbox verification completed": (
            result.final_verification_status
            == "SANDBOX_VERIFICATION_COMPLETE"
        ),
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Empty operator was blocked": empty_operator.result_status == "BLOCKED",
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered ledger failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": broken.result_status == "BLOCKED",
        "Unsafe source failed": unsafe_result.result_status == "FAILED",
        "Final report tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V17.0",
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
        "AI STOCK BOT V17.0 SANDBOX VERIFICATION FINAL REPORT ARCHIVE "
        "CERTIFICATE AUDIT FINAL REPORT TEST"
    )
    print("=" * 108)
    print("V17.0 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V17.0 Validation Check 실패")
    print()
    print(
        "V17.0 sandbox verification final report archive certificate audit "
        "final report test completed successfully."
    )
    print(
        "V16.9 Certificate Ledger Chain, Verification Ledger Snapshot Hash, "
        "이전 Final Report Hash, 읽기 전용 Finalization 및 새 Final Report "
        "Hash가 검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
