import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from test_sandbox_verification_audit_ledger_v18_7 import (
    create_source as create_audit_source,
)
from test_sandbox_verification_audit_ledger_v18_7 import (
    record,
)

from backtest.sandbox_verification_audit_ledger_integrity_v18_8 import (
    SandboxVerificationAuditLedgerIntegrityV188Policy,
    load_verification_result,
    save_verification_result,
    verify_sandbox_verification_audit_ledger_v18_8,
    verify_verification_certificate,
)


NOW = datetime(2026, 7, 29, 6, 0, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    first = record(create_audit_source())
    return record(
        create_audit_source(),
        existing=first.entries,
        now=datetime(2026, 7, 29, 5, 41, tzinfo=timezone.utc),
    )


def verify(
    source: Any,
    operator: str | None = None,
    text: str = (
        "VERIFY IN MEMORY SANDBOX VERIFICATION AUDIT LEDGER V18.8"
    ),
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    default_operator = (
        source.entries[-1].operator
        if getattr(source, "entries", ()) else "operator-001"
    )
    return silent(
        verify_sandbox_verification_audit_ledger_v18_8,
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
        "V18.8 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = verify(source)
    require(
        result.result_status == "VERIFIED_IN_MEMORY",
        "Integrity Verification 실패",
    )
    require(result.verification_status == "PASSED", "Status 오류")
    require(result.verification_completed, "Certificate 없음")
    require(result.certificate is not None, "Certificate 없음")
    require(result.verified_entry_count == 2, "Entry Count 오류")
    require(not result.ledger_modified, "읽기 전용 Ledger 변경")
    require(source.to_dict() == source_before, "V18.7 Source 변경")
    require(
        all(
            finding.finding_status == "PASSED"
            for finding in result.certificate.findings
        ),
        "Entry Finding 실패",
    )
    require(
        result.latest_verification_ledger_snapshot_hash
        == source.latest_verification_ledger_snapshot_hash,
        "Verification Ledger Snapshot Hash 보존 실패",
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
    certificate_valid, certificate_errors = (
        verify_verification_certificate(result.certificate)
    )
    require(
        certificate_valid and not certificate_errors,
        "Certificate Hash 실패",
    )
    require_safe(result)

    wrong_operator = verify(source, operator="wrong")
    require(
        wrong_operator.result_status == "BLOCKED",
        "Operator 미차단",
    )
    wrong_text = verify(source, text="IGNORE")
    require(
        wrong_text.result_status == "BLOCKED",
        "확인 문구 미차단",
    )
    empty_operator = verify(source, operator="")
    require(
        empty_operator.result_status == "BLOCKED",
        "빈 Operator 미차단",
    )
    unsafe_policy = (
        SandboxVerificationAuditLedgerIntegrityV188Policy(
            order_submission_disabled=False
        )
    )
    unsafe = verify(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy 미차단")
    wrong_type = verify(object())
    require(
        wrong_type.result_status == "FAILED",
        "잘못된 Source 미실패",
    )
    backward = verify(
        source,
        now=datetime.fromisoformat(source.entries[-1].recorded_at)
        - timedelta(seconds=1),
    )
    require(
        backward.result_status == "BLOCKED",
        "역순 시간 미차단",
    )

    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (
        replace(
            tampered_source.entries[0],
            verification_ledger_snapshot_hash="e" * 64,
        ),
        tampered_source.entries[1],
    )
    tampered = verify(tampered_source)
    require(
        tampered.result_status == "FAILED",
        "Ledger 변조 미실패",
    )
    broken_source = copy.deepcopy(source)
    broken_source.latest_ledger_entry_hash = "f" * 64
    broken = verify(broken_source)
    require(
        broken.result_status == "BLOCKED",
        "Source 연결 미차단",
    )
    unsafe_source = copy.deepcopy(source)
    unsafe_source.network_accessed = True
    unsafe_result = verify(unsafe_source)
    require(
        unsafe_result.result_status == "FAILED",
        "위험 Source 미실패",
    )
    changed_certificate = replace(
        result.certificate,
        verification_status="FAILED",
    )
    changed_valid, changed_errors = verify_verification_certificate(
        changed_certificate
    )
    require(
        not changed_valid and changed_errors,
        "Certificate 변조 미탐지",
    )

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_verification_result(
            result,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "저장 실패",
        )
        payload = load_verification_result(latest_path)
        require(payload["version"] == "V18.8", "저장 Version 오류")
        require(
            payload["certificate"]["certificate_hash"]
            == result.verification_certificate_hash,
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
        "Version is V18.8": result.version == "V18.8",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            SandboxVerificationAuditLedgerIntegrityV188Policy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V18.7 certificate audit ledger source passed": (
            result.source_checks_passed
        ),
        "Ledger hash chain passed": (
            result.ledger_hash_chain_checks_passed
        ),
        "Source linkage passed": result.source_linkage_checks_passed,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Audit status check passed": result.audit_status_checks_passed,
        "Entry safety check passed": result.entry_safety_checks_passed,
        "Ledger snapshot hash passed": (
            result.snapshot_hash_checks_passed
        ),
        "Ledger remained unchanged": (
            result.ledger_unchanged_checks_passed
            and source.to_dict() == source_before
        ),
        "Verification certificate hash passed": certificate_valid,
        "Two entry findings passed": (
            len(result.certificate.findings) == 2
        ),
        "Verification ledger snapshot hash was preserved": (
            result.latest_verification_ledger_snapshot_hash
            == source.latest_verification_ledger_snapshot_hash
        ),
        "Final report hash was preserved": (
            result.latest_final_report_hash
            == source.latest_final_report_hash
        ),
        "Linked final report hash was preserved": (
            result.latest_linked_final_report_hash
            == source.latest_linked_final_report_hash
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
        "Wrong operator was blocked": (
            wrong_operator.result_status == "BLOCKED"
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
        "Backward time was blocked": (
            backward.result_status == "BLOCKED"
        ),
        "Tampered ledger failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": (
            broken.result_status == "BLOCKED"
        ),
        "Unsafe ledger source failed": (
            unsafe_result.result_status == "FAILED"
        ),
        "Certificate tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V18.8",
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
        "AI STOCK BOT V18.8 SANDBOX VERIFICATION AUDIT LEDGER "
        "INTEGRITY VERIFICATION TEST"
    )
    print("=" * 108)
    print("V18.8 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V18.8 Validation Check 실패")
    print()
    print(
        "V18.8 sandbox verification audit ledger integrity "
        "verification test completed successfully."
    )
    print(
        "V18.7 Ledger Chain, Entry Findings, 연결 Hash, 읽기 전용 검증 "
        "및 Verification Certificate Hash가 검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
