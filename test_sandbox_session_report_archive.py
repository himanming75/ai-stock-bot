import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# V15.0 테스트 Helper를 먼저 불러오면, 과거 의존 파일이 빠진
# 다운로드 작업공간에서도 V15.0 최소 형식이 안전하게 준비됩니다.
from test_sandbox_session_final_report import (
    create_source as create_ledger_source,
)
from test_sandbox_session_final_report import finalize

from backtest.sandbox_session_report_archive import (
    SandboxSessionReportArchivePolicy,
    archive_sandbox_session_report,
    load_archive_result,
    save_archive_result,
    verify_archive_chain,
)


NOW = datetime(2026, 7, 28, 14, 30, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return finalize(create_ledger_source())


def archive(
    source: Any,
    operator: str | None = None,
    text: str = "ARCHIVE IN MEMORY SANDBOX SESSION FINAL REPORT",
    existing: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    default_operator = (
        source.report.operator
        if getattr(source, "report", None) is not None
        else "operator-001"
    )
    return silent(
        archive_sandbox_session_report,
        source,
        operator or default_operator,
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
        "V15.1 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    first = archive(source)
    require(
        first.result_status == "ARCHIVED_IN_MEMORY",
        "첫 Archive 기록이 실패했습니다.",
    )
    require(first.archive_entry_recorded, "Archive Entry가 없습니다.")
    require(first.total_archive_entry_count == 1, "첫 Entry 개수가 다릅니다.")
    require(first.entries[0].sequence == 1, "Genesis Sequence가 다릅니다.")
    require(
        first.entries[0].session_report_hash == source.report_hash,
        "V15.0 Report Hash가 보존되지 않았습니다.",
    )
    require_safe(first)

    second_source = create_source()
    second = archive(
        second_source,
        existing=first.entries,
        now=NOW + timedelta(minutes=1),
    )
    require(
        second.result_status == "ARCHIVED_IN_MEMORY",
        "두 번째 Archive 기록이 실패했습니다.",
    )
    require(
        second.total_archive_entry_count == 2,
        "두 Archive Entry가 생성되지 않았습니다.",
    )
    valid_chain, chain_errors = verify_archive_chain(second.entries)
    require(
        valid_chain and not chain_errors,
        "Archive SHA-256 Hash Chain이 실패했습니다.",
    )

    duplicate = archive(
        source,
        existing=first.entries,
        now=NOW + timedelta(minutes=1),
    )
    require(
        duplicate.result_status == "BLOCKED",
        "중복 Session Report가 차단되지 않았습니다.",
    )
    wrong_operator = archive(source, operator="wrong")
    require(
        wrong_operator.result_status == "BLOCKED",
        "잘못된 Operator가 차단되지 않았습니다.",
    )
    wrong_text = archive(source, text="IGNORE")
    require(
        wrong_text.result_status == "BLOCKED",
        "잘못된 확인 문구가 차단되지 않았습니다.",
    )
    unsafe_policy = SandboxSessionReportArchivePolicy(
        order_submission_disabled=False
    )
    unsafe = archive(source, policy=unsafe_policy)
    require(
        not unsafe.all_checks_passed,
        "위험 Policy가 차단되지 않았습니다.",
    )
    wrong_type = archive(object())
    require(
        wrong_type.result_status == "FAILED",
        "잘못된 Source 형식이 실패 처리되지 않았습니다.",
    )
    wrong_existing = archive(source, existing={"invalid": True})
    require(
        wrong_existing.result_status == "BLOCKED",
        "잘못된 Existing Archive가 차단되지 않았습니다.",
    )
    backward = archive(
        second_source,
        existing=first.entries,
        now=NOW - timedelta(seconds=1),
    )
    require(
        backward.result_status == "BLOCKED",
        "역순 Archive 시간이 차단되지 않았습니다.",
    )

    tampered_source = copy.deepcopy(source)
    tampered_source.report = replace(
        tampered_source.report,
        final_session_outcome="BLOCKED",
    )
    tampered = archive(tampered_source)
    require(
        tampered.result_status == "FAILED",
        "변조 Final Report가 실패 처리되지 않았습니다.",
    )
    broken_link = copy.deepcopy(source)
    broken_link.report_hash = "f" * 64
    broken = archive(broken_link)
    require(
        broken.result_status == "BLOCKED",
        "잘못된 Source 연결이 차단되지 않았습니다.",
    )

    changed_entry = replace(
        second.entries[0],
        final_session_outcome="BLOCKED",
    )
    changed_entries = (changed_entry, second.entries[1])
    changed_valid, changed_errors = verify_archive_chain(changed_entries)
    require(
        not changed_valid and changed_errors,
        "Archive 변조가 탐지되지 않았습니다.",
    )
    unsafe_existing = archive(
        create_source(),
        existing=changed_entries,
        now=NOW + timedelta(minutes=2),
    )
    require(
        unsafe_existing.result_status == "BLOCKED",
        "변조 Existing Archive가 차단되지 않았습니다.",
    )

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_archive_result(
            second,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "V15.1 결과가 저장되지 않았습니다.",
        )
        payload = load_archive_result(latest_path)
        require(payload["version"] == "V15.1", "저장 Version이 다릅니다.")
        require(
            len(payload["entries"]) == 2,
            "저장 Archive Entry 개수가 다릅니다.",
        )

    for checked in (
        first,
        second,
        duplicate,
        wrong_operator,
        wrong_text,
        unsafe,
        wrong_type,
        wrong_existing,
        backward,
        tampered,
        broken,
        unsafe_existing,
    ):
        require_safe(checked)

    checks = {
        "Version is V15.1": second.version == "V15.1",
        "Default policy is valid": second.policy_checks_passed,
        "Policy is immutable": (
            SandboxSessionReportArchivePolicy.__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V15.0 final report source passed": second.source_checks_passed,
        "V15.0 report hash passed": second.report_hash_checks_passed,
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
        "Duplicate report was blocked": duplicate.result_status == "BLOCKED",
        "Wrong operator was blocked": (
            wrong_operator.result_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Wrong existing archive was blocked": (
            wrong_existing.result_status == "BLOCKED"
        ),
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered final report failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": (
            broken.result_status == "BLOCKED"
        ),
        "Archive tampering detected": not changed_valid,
        "Tampered existing archive was blocked": (
            unsafe_existing.result_status == "BLOCKED"
        ),
        "Result save and load passed": payload["version"] == "V15.1",
        "Market data API was not called": not second.market_data_api_called,
        "Account was not accessed": not second.account_accessed,
        "Network was not accessed": not second.network_accessed,
        "Broker API was not called": not second.broker_api_called,
        "Order was not submitted": not second.order_submitted,
        "Live execution not authorized": (
            not second.live_execution_authorized
        ),
    }
    checks["All checks passed"] = all(checks.values())

    print("=" * 100)
    print("AI STOCK BOT V15.1 SANDBOX SESSION REPORT ARCHIVE TEST")
    print("=" * 100)
    print("V15.1 VALIDATION CHECKS")
    print("-" * 100)
    for name, passed in checks.items():
        print(f"{name:<66}: {passed}")
    print("=" * 100)
    require(
        checks["All checks passed"],
        "V15.1 Validation Check가 실패했습니다.",
    )
    print()
    print("V15.1 sandbox session report archive test completed successfully.")
    print(
        "V15.0 Report Hash 보존, Archive Sequence, SHA-256 Hash Chain 및 "
        "중복·역순·변조 차단이 검증되었습니다."
    )
    print(
        "Broker API, 계좌, Network, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
