import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from test_sandbox_verification_audit_ledger import (
    create_source as create_audit_source,
)
from test_sandbox_verification_audit_ledger import record

from backtest.sandbox_verification_audit_ledger_integrity_verification import (
    SandboxVerificationAuditLedgerIntegrityPolicy,
    load_verification_result,
    save_verification_result,
    verify_sandbox_verification_audit_ledger_integrity,
    verify_verification_certificate,
)


NOW = datetime(2026, 7, 28, 16, 50, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    first = record(create_audit_source())
    return record(
        create_audit_source(),
        existing=first.entries,
        now=datetime(2026, 7, 28, 16, 31, tzinfo=timezone.utc),
    )


def verify(
    source: Any,
    operator: str = "operator-001",
    text: str = (
        "VERIFY IN MEMORY SANDBOX VERIFICATION AUDIT LEDGER INTEGRITY"
    ),
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        verify_sandbox_verification_audit_ledger_integrity,
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
        "V15.8 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = verify(source)
    require(result.result_status == "VERIFIED_IN_MEMORY", "정상 Verification 실패")
    require(result.verification_status == "PASSED", "Verification Status 오류")
    require(result.verified_entry_count == 2, "검증 Entry 개수 오류")
    require(result.certificate is not None, "Verification Certificate 누락")
    require(source.to_dict() == source_before, "V15.7 Source 변경 감지")
    require(not result.ledger_modified, "Ledger Modified 값 오류")
    require(
        all(
            finding.finding_status == "PASSED"
            for finding in result.certificate.findings
        ),
        "Entry Finding 실패",
    )
    certificate_valid, certificate_errors = verify_verification_certificate(
        result.certificate
    )
    require(
        certificate_valid and not certificate_errors,
        "Verification Certificate Hash 실패",
    )
    require_safe(result)

    wrong_text = verify(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "확인 문구 미차단")
    wrong_operator = verify(source, operator="operator-999")
    require(wrong_operator.result_status == "BLOCKED", "Operator 미차단")
    empty_operator = verify(source, operator="")
    require(empty_operator.result_status == "BLOCKED", "빈 Operator 미차단")
    unsafe_policy = SandboxVerificationAuditLedgerIntegrityPolicy(
        live_execution_disabled=False
    )
    unsafe = verify(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy 미차단")
    wrong_type = verify(object())
    require(wrong_type.result_status == "FAILED", "잘못된 Source 미실패")
    backward = verify(
        source,
        now=datetime(2026, 7, 28, 16, 30, tzinfo=timezone.utc),
    )
    require(backward.result_status == "BLOCKED", "역순 시간 미차단")

    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (
        replace(
            tampered_source.entries[0],
            verification_ledger_snapshot_hash="e" * 64,
        ),
        tampered_source.entries[1],
    )
    tampered = verify(tampered_source)
    require(tampered.result_status == "FAILED", "Ledger 변조 미실패")

    broken_linkage = copy.deepcopy(source)
    broken_linkage.latest_ledger_entry_hash = "f" * 64
    broken = verify(broken_linkage)
    require(broken.result_status == "BLOCKED", "Source Linkage 미차단")

    unsafe_source = copy.deepcopy(source)
    unsafe_source.network_accessed = True
    unsafe_result = verify(unsafe_source)
    require(unsafe_result.result_status == "FAILED", "위험 Source 미실패")

    changed_certificate = replace(
        result.certificate, ledger_snapshot_hash="a" * 64
    )
    changed_valid, changed_errors = verify_verification_certificate(
        changed_certificate
    )
    require(
        not changed_valid and changed_errors,
        "Verification Certificate 변조 미탐지",
    )

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_verification_result(
            result, Path(directory)
        )
        require(report_path.exists() and latest_path.exists(), "저장 실패")
        payload = load_verification_result(latest_path)
        require(payload["version"] == "V15.8", "저장 Version 오류")
        require(payload["verified_entry_count"] == 2, "저장 Entry 개수 오류")

    for checked in (
        result, wrong_text, wrong_operator, empty_operator, unsafe,
        wrong_type, backward, tampered, broken, unsafe_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V15.8": result.version == "V15.8",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            SandboxVerificationAuditLedgerIntegrityPolicy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V15.7 verification audit ledger source passed": (
            result.source_checks_passed
        ),
        "Ledger hash chain passed": result.ledger_hash_chain_checks_passed,
        "Source linkage passed": result.source_linkage_checks_passed,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Entry safety check passed": result.entry_safety_checks_passed,
        "Ledger snapshot hash passed": result.snapshot_hash_checks_passed,
        "Verification audit ledger remained unchanged": (
            source.to_dict() == source_before
        ),
        "Verification certificate hash passed": certificate_valid,
        "Two entry findings passed": len(result.certificate.findings) == 2,
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Empty operator was blocked": empty_operator.result_status == "BLOCKED",
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered ledger failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": broken.result_status == "BLOCKED",
        "Unsafe source failed": unsafe_result.result_status == "FAILED",
        "Certificate tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V15.8",
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
        "AI STOCK BOT V15.8 SANDBOX VERIFICATION AUDIT LEDGER "
        "INTEGRITY VERIFICATION TEST"
    )
    print("=" * 108)
    print("V15.8 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V15.8 Validation Check 실패")
    print()
    print(
        "V15.8 sandbox verification audit ledger integrity verification "
        "test completed successfully."
    )
    print(
        "V15.7 Ledger Chain, Entry Findings, Snapshot Hash, 읽기 전용 검증 및 "
        "Verification Certificate Hash가 검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
