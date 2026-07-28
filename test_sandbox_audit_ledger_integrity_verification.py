import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from test_sandbox_archive_audit_ledger import (
    create_source as create_audit_source,
)
from test_sandbox_archive_audit_ledger import record

from backtest.sandbox_audit_ledger_integrity_verification import (
    SandboxAuditLedgerIntegrityPolicy,
    load_verification_result,
    save_verification_result,
    verify_sandbox_audit_ledger_integrity,
    verify_verification_certificate,
)


NOW = datetime(2026, 7, 28, 15, 30, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    first = record(create_audit_source())
    return record(
        create_audit_source(),
        existing=first.entries,
        now=datetime(2026, 7, 28, 15, 11, tzinfo=timezone.utc),
    )


def verify(
    source: Any,
    operator: str | None = None,
    text: str = "VERIFY IN MEMORY SANDBOX AUDIT LEDGER INTEGRITY",
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    default_operator = (
        source.entries[-1].operator
        if getattr(source, "entries", ()) else "operator-001"
    )
    return silent(
        verify_sandbox_audit_ledger_integrity,
        source, operator or default_operator, text, policy, now,
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
        "V15.4 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = verify(source)
    require(result.result_status == "VERIFIED_IN_MEMORY", "Verification 실패")
    require(result.verification_status == "PASSED", "Status 오류")
    require(result.verification_completed, "Certificate 없음")
    require(result.certificate is not None, "Certificate 없음")
    require(result.verified_entry_count == 2, "Entry Count 오류")
    require(not result.ledger_modified, "읽기 전용 Ledger 변경")
    require(source.to_dict() == source_before, "Source 변경")
    require(
        all(x.finding_status == "PASSED" for x in result.certificate.findings),
        "Entry Finding 실패",
    )
    certificate_valid, certificate_errors = (
        verify_verification_certificate(result.certificate)
    )
    require(
        certificate_valid and not certificate_errors,
        "Certificate Hash 실패",
    )
    require_safe(result)

    wrong_operator = verify(source, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "Operator 미차단")
    wrong_text = verify(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "확인 문구 미차단")
    unsafe_policy = SandboxAuditLedgerIntegrityPolicy(
        order_submission_disabled=False
    )
    unsafe = verify(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy 미차단")
    wrong_type = verify(object())
    require(wrong_type.result_status == "FAILED", "잘못된 Source 미실패")
    backward = verify(
        source,
        now=datetime.fromisoformat(source.entries[-1].recorded_at)
        - timedelta(seconds=1),
    )
    require(backward.result_status == "BLOCKED", "역순 시간 미차단")

    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (
        replace(
            tampered_source.entries[0],
            archive_snapshot_hash="e" * 64,
        ),
        tampered_source.entries[1],
    )
    tampered = verify(tampered_source)
    require(tampered.result_status == "FAILED", "Ledger 변조 미실패")
    broken_source = copy.deepcopy(source)
    broken_source.latest_ledger_entry_hash = "f" * 64
    broken = verify(broken_source)
    require(broken.result_status == "BLOCKED", "Source 연결 미차단")
    unsafe_source = copy.deepcopy(source)
    unsafe_source.network_accessed = True
    unsafe_result = verify(unsafe_source)
    require(unsafe_result.result_status == "FAILED", "위험 Source 미실패")

    changed_certificate = replace(
        result.certificate, verification_status="FAILED"
    )
    changed_valid, changed_errors = verify_verification_certificate(
        changed_certificate
    )
    require(not changed_valid and changed_errors, "Certificate 변조 미탐지")

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_verification_result(
            result, Path(directory)
        )
        require(report_path.exists() and latest_path.exists(), "저장 실패")
        payload = load_verification_result(latest_path)
        require(payload["version"] == "V15.4", "저장 Version 오류")
        require(
            payload["certificate"]["certificate_hash"]
            == result.verification_certificate_hash,
            "저장 Certificate Hash 오류",
        )

    for checked in (
        result, wrong_operator, wrong_text, unsafe, wrong_type,
        backward, tampered, broken, unsafe_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V15.4": result.version == "V15.4",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            SandboxAuditLedgerIntegrityPolicy.__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V15.3 audit ledger source passed": result.source_checks_passed,
        "Ledger hash chain passed": result.ledger_hash_chain_checks_passed,
        "Source linkage passed": result.source_linkage_checks_passed,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Entry safety check passed": result.entry_safety_checks_passed,
        "Ledger snapshot hash passed": result.snapshot_hash_checks_passed,
        "Ledger remained unchanged": result.ledger_unchanged_checks_passed,
        "Verification certificate hash passed": certificate_valid,
        "Two entry findings passed": all(
            x.finding_status == "PASSED" for x in result.certificate.findings
        ),
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered ledger failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": broken.result_status == "BLOCKED",
        "Unsafe ledger source failed": unsafe_result.result_status == "FAILED",
        "Certificate tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V15.4",
        "Market data API was not called": not result.market_data_api_called,
        "Account was not accessed": not result.account_accessed,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 104)
    print("AI STOCK BOT V15.4 SANDBOX AUDIT LEDGER INTEGRITY VERIFICATION TEST")
    print("=" * 104)
    print("V15.4 VALIDATION CHECKS")
    print("-" * 104)
    for name, passed in checks.items():
        print(f"{name:<70}: {passed}")
    print("=" * 104)
    require(checks["All checks passed"], "V15.4 Validation Check 실패")
    print()
    print(
        "V15.4 sandbox audit ledger integrity verification test "
        "completed successfully."
    )
    print(
        "V15.3 Ledger Chain, Entry Findings, Snapshot Hash, 읽기 전용 검증 및 "
        "Certificate Hash가 검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
