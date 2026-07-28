import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from test_sandbox_verification_final_report import (
    create_source as create_final_source,
)
from test_sandbox_verification_final_report import finalize

from backtest.sandbox_verification_final_report_archive import (
    SandboxVerificationFinalReportArchivePolicy,
    archive_sandbox_verification_final_report,
    load_archive_result,
    save_archive_result,
    verify_archive_chain,
)


NOW = datetime(2026, 7, 28, 17, 50, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return finalize(create_final_source())


def archive(
    source: Any,
    operator: str = "operator-001",
    text: str = "ARCHIVE IN MEMORY SANDBOX VERIFICATION FINAL REPORT",
    existing: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        archive_sandbox_verification_final_report,
        source, operator, text, existing, policy, now,
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
        "V16.1 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    first = archive(source)
    require(first.result_status == "ARCHIVED_IN_MEMORY", "첫 Archive 실패")
    require(first.total_archive_entry_count == 1, "첫 Entry 개수 오류")
    require(first.entries[0].sequence == 1, "Genesis Sequence 오류")
    require(
        first.entries[0].final_report_hash == source.report_hash,
        "V16.0 Final Report Hash 보존 실패",
    )
    require(
        first.entries[0].certificate_ledger_snapshot_hash
        == source.certificate_ledger_snapshot_hash,
        "Certificate Ledger Snapshot Hash 보존 실패",
    )
    require(source.to_dict() == source_before, "V16.0 Source 변경 감지")
    require_safe(first)

    second_source = create_source()
    second = archive(
        second_source,
        existing=first.entries,
        now=NOW + timedelta(minutes=1),
    )
    require(second.result_status == "ARCHIVED_IN_MEMORY", "두 번째 Archive 실패")
    require(second.total_archive_entry_count == 2, "두 Entry 생성 실패")
    valid_chain, chain_errors = verify_archive_chain(second.entries)
    require(valid_chain and not chain_errors, "Archive Hash Chain 실패")

    duplicate = archive(
        source, existing=first.entries, now=NOW + timedelta(minutes=1)
    )
    require(duplicate.result_status == "BLOCKED", "중복 Report 미차단")
    wrong_operator = archive(source, operator="operator-999")
    require(wrong_operator.result_status == "BLOCKED", "Operator 미차단")
    wrong_text = archive(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "확인 문구 미차단")
    empty_operator = archive(source, operator="")
    require(empty_operator.result_status == "BLOCKED", "빈 Operator 미차단")
    unsafe_policy = SandboxVerificationFinalReportArchivePolicy(
        order_submission_disabled=False
    )
    unsafe = archive(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy 미차단")
    wrong_type = archive(object())
    require(wrong_type.result_status == "FAILED", "잘못된 Source 미실패")
    wrong_existing = archive(source, existing={"invalid": True})
    require(wrong_existing.result_status == "BLOCKED", "잘못된 Archive 미차단")
    backward = archive(
        second_source,
        existing=first.entries,
        now=NOW - timedelta(seconds=1),
    )
    require(backward.result_status == "BLOCKED", "역순 시간 미차단")

    tampered_source = copy.deepcopy(source)
    tampered_source.report = replace(
        tampered_source.report, final_verification_status="BLOCKED"
    )
    tampered = archive(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Report 미실패")

    broken_source = copy.deepcopy(source)
    broken_source.report_hash = "f" * 64
    broken = archive(broken_source)
    require(broken.result_status == "BLOCKED", "Source Linkage 미차단")

    changed_entry = replace(
        second.entries[0], final_verification_status="BLOCKED"
    )
    changed_entries = (changed_entry, second.entries[1])
    changed_valid, changed_errors = verify_archive_chain(changed_entries)
    require(not changed_valid and changed_errors, "Archive 변조 미탐지")
    unsafe_existing = archive(
        create_source(),
        existing=changed_entries,
        now=NOW + timedelta(minutes=2),
    )
    require(unsafe_existing.result_status == "BLOCKED", "변조 Archive 미차단")

    unsafe_source = copy.deepcopy(source)
    unsafe_source.live_execution_authorized = True
    unsafe_source_result = archive(unsafe_source)
    require(unsafe_source_result.result_status == "FAILED", "위험 Source 미실패")

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_archive_result(second, Path(directory))
        require(report_path.exists() and latest_path.exists(), "저장 실패")
        payload = load_archive_result(latest_path)
        require(payload["version"] == "V16.1", "저장 Version 오류")
        require(len(payload["entries"]) == 2, "저장 Entry 개수 오류")

    for checked in (
        first, second, duplicate, wrong_operator, wrong_text, empty_operator,
        unsafe, wrong_type, wrong_existing, backward, tampered, broken,
        unsafe_existing, unsafe_source_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V16.1": second.version == "V16.1",
        "Default policy is valid": second.policy_checks_passed,
        "Policy is immutable": (
            SandboxVerificationFinalReportArchivePolicy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V16.0 final report source passed": second.source_checks_passed,
        "V16.0 final report hash passed": second.report_hash_checks_passed,
        "Source linkage passed": second.linkage_checks_passed,
        "First report was archived": first.archive_entry_recorded,
        "Second report was archived": second.archive_entry_recorded,
        "Two archive entries were created": (
            second.total_archive_entry_count == 2
        ),
        "Sequences are chronological": (
            [entry.sequence for entry in second.entries] == [1, 2]
        ),
        "Archive SHA-256 hash chain passed": valid_chain,
        "Final report hash was preserved": (
            first.entries[0].final_report_hash == source.report_hash
        ),
        "Certificate ledger snapshot hash was preserved": (
            first.entries[0].certificate_ledger_snapshot_hash
            == source.certificate_ledger_snapshot_hash
        ),
        "Duplicate report was blocked": duplicate.result_status == "BLOCKED",
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Empty operator was blocked": empty_operator.result_status == "BLOCKED",
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Wrong existing archive was blocked": (
            wrong_existing.result_status == "BLOCKED"
        ),
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered final report failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": broken.result_status == "BLOCKED",
        "Archive tampering detected": not changed_valid,
        "Tampered existing archive was blocked": (
            unsafe_existing.result_status == "BLOCKED"
        ),
        "Unsafe source failed": unsafe_source_result.result_status == "FAILED",
        "Result save and load passed": payload["version"] == "V16.1",
        "Market data API was not called": not second.market_data_api_called,
        "Account was not accessed": not second.account_accessed,
        "Network was not accessed": not second.network_accessed,
        "Broker API was not called": not second.broker_api_called,
        "Order was not submitted": not second.order_submitted,
        "Live execution not authorized": not second.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 108)
    print("AI STOCK BOT V16.1 SANDBOX VERIFICATION FINAL REPORT ARCHIVE TEST")
    print("=" * 108)
    print("V16.1 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V16.1 Validation Check 실패")
    print()
    print(
        "V16.1 sandbox verification final report archive test "
        "completed successfully."
    )
    print(
        "V16.0 Final Report Hash와 Certificate Ledger Snapshot Hash 보존, "
        "Archive Sequence, SHA-256 Hash Chain 및 중복·역순·변조 차단이 "
        "검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
