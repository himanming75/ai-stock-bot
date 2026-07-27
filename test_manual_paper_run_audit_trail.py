import io
import json
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import backtest.manual_paper_run_audit_trail as audit_module
from backtest.manual_paper_run_audit_trail import (
    GENESIS_HASH,
    ManualPaperRunAuditPolicy,
    build_manual_paper_run_audit_trail,
    load_latest_manual_paper_run_audit_trail,
    save_manual_paper_run_audit_trail,
    validate_audit_policy,
    verify_audit_chain,
    verify_saved_audit_payload,
)
from test_manual_paper_run_orchestrator import (
    validate_successful_orchestration,
)


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    여러 실패 상황을 검사할 때 중간 보고서는 숨기고,
    마지막 V11.7 Validation 결과만 보기 쉽게 출력합니다.
    """

    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_safe_v116_source() -> Any:
    source = run_silently(
        validate_successful_orchestration
    )
    if not source.all_checks_passed:
        raise RuntimeError(
            "테스트용 V11.6 Source가 안전하지 않습니다."
        )
    return source


def assert_execution_safety(result: Any) -> None:
    if result.automatic_execution_authorized:
        raise RuntimeError(
            "자동 실행이 허용되었습니다."
        )
    if not result.execution_blocked:
        raise RuntimeError(
            "Execution 차단 상태가 아닙니다."
        )
    if result.broker_api_called:
        raise RuntimeError(
            "Broker API가 호출되었습니다."
        )
    if result.broker_order_created:
        raise RuntimeError(
            "Broker 주문이 생성되었습니다."
        )
    if result.live_order_created:
        raise RuntimeError(
            "Live 주문이 생성되었습니다."
        )
    if result.live_execution_authorized:
        raise RuntimeError(
            "Live Execution이 허용되었습니다."
        )


def validate_successful_audit(source: Any) -> Any:
    result = run_silently(
        build_manual_paper_run_audit_trail,
        source,
    )

    if result.version != "V11.7":
        raise RuntimeError(
            "Audit Version이 V11.7이 아닙니다."
        )
    if result.audit_status != "RECORDED":
        raise RuntimeError(
            "정상 Audit가 RECORDED가 아닙니다."
        )
    if result.source_version != "V11.6":
        raise RuntimeError(
            "Source Version 연결이 올바르지 않습니다."
        )
    if (
        result.source_orchestration_id
        != source.orchestration_id
    ):
        raise RuntimeError(
            "Source Orchestration ID가 연결되지 않았습니다."
        )
    if result.total_entry_count != 8:
        raise RuntimeError(
            "Audit Entry 수가 8이 아닙니다."
        )
    if (
        result.audit_entries[0].event_type
        != "ORCHESTRATION_STARTED"
    ):
        raise RuntimeError(
            "첫 Audit Event가 STARTED가 아닙니다."
        )
    if (
        result.audit_entries[-1].event_type
        != "ORCHESTRATION_FINISHED"
    ):
        raise RuntimeError(
            "마지막 Audit Event가 FINISHED가 아닙니다."
        )

    stage_names = tuple(
        entry.stage_name
        for entry in result.audit_entries[1:-1]
    )
    expected_stage_names = (
        "APPROVAL",
        "LAUNCH",
        "LEDGER_INTEGRATION",
        "SESSION_REFRESH",
        "PERFORMANCE_RISK_REFRESH",
        "FINAL_REPORT",
    )
    if stage_names != expected_stage_names:
        raise RuntimeError(
            "Audit Stage 순서가 올바르지 않습니다."
        )
    if (
        result.audit_entries[0].previous_hash
        != GENESIS_HASH
    ):
        raise RuntimeError(
            "첫 Entry가 Genesis Hash에 연결되지 않았습니다."
        )

    chain_valid, chain_errors = verify_audit_chain(
        result.audit_entries
    )
    if not chain_valid or chain_errors:
        raise RuntimeError(
            "정상 Audit Hash Chain 검사가 실패했습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 Audit의 All Checks가 실패했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_duplicate_block(
    source: Any,
    successful_audit: Any,
) -> Any:
    result = run_silently(
        build_manual_paper_run_audit_trail,
        source,
        successful_audit.orchestration_history,
    )

    if result.audit_status != "BLOCKED":
        raise RuntimeError(
            "중복 Orchestration이 BLOCKED가 아닙니다."
        )
    if result.duplicate_checks_passed:
        raise RuntimeError(
            "중복 검사가 잘못 통과했습니다."
        )
    if result.total_entry_count != 0:
        raise RuntimeError(
            "중복 차단 결과에 Audit Entry가 생성됐습니다."
        )

    assert_execution_safety(result)
    return result


def validate_invalid_source_version(
    source: Any,
) -> Any:
    invalid_source = replace(
        source,
        version="V11.5",
    )
    result = run_silently(
        build_manual_paper_run_audit_trail,
        invalid_source,
    )

    if result.audit_status != "FAILED":
        raise RuntimeError(
            "잘못된 Source Version이 차단되지 않았습니다."
        )
    if result.source_checks_passed:
        raise RuntimeError(
            "잘못된 Source 검사가 통과했습니다."
        )
    if result.audit_entries:
        raise RuntimeError(
            "잘못된 Source로 Audit Entry가 생성됐습니다."
        )

    assert_execution_safety(result)
    return result


def validate_unsafe_source(
    source: Any,
) -> Any:
    unsafe_source = replace(
        source,
        execution_blocked=False,
        broker_api_called=True,
    )
    result = run_silently(
        build_manual_paper_run_audit_trail,
        unsafe_source,
    )

    if result.audit_status != "FAILED":
        raise RuntimeError(
            "위험한 Source가 차단되지 않았습니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Source Safety 검사가 통과했습니다."
        )
    if result.total_entry_count != 0:
        raise RuntimeError(
            "위험한 Source로 Audit Entry가 생성됐습니다."
        )

    assert_execution_safety(result)
    return result


def validate_invalid_stage_sequence(
    source: Any,
) -> Any:
    reversed_source = replace(
        source,
        stage_records=tuple(
            reversed(source.stage_records)
        ),
    )
    result = run_silently(
        build_manual_paper_run_audit_trail,
        reversed_source,
    )

    if result.audit_status != "FAILED":
        raise RuntimeError(
            "잘못된 Stage 순서가 차단되지 않았습니다."
        )
    if result.sequence_checks_passed:
        raise RuntimeError(
            "잘못된 Stage Sequence 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_hash_tampering(
    successful_audit: Any,
) -> None:
    tampered_entries = list(
        successful_audit.audit_entries
    )
    tampered_entries[3] = replace(
        tampered_entries[3],
        stage_status="TAMPERED",
    )

    chain_valid, chain_errors = verify_audit_chain(
        tuple(tampered_entries)
    )
    if chain_valid:
        raise RuntimeError(
            "변경된 Audit Entry의 Hash 검사가 통과했습니다."
        )
    if not chain_errors:
        raise RuntimeError(
            "Hash 변경 오류가 기록되지 않았습니다."
        )

    payload = successful_audit.to_dict()
    payload["audit_entries"][2][
        "stage_completed"
    ] = False
    payload_valid, payload_errors = (
        verify_saved_audit_payload(payload)
    )
    if payload_valid:
        raise RuntimeError(
            "변경된 JSON Audit 검사가 통과했습니다."
        )
    if not payload_errors:
        raise RuntimeError(
            "JSON 변경 오류가 기록되지 않았습니다."
        )


def validate_history_limit(
    source: Any,
) -> Any:
    existing_history = tuple(
        f"old-orchestration-{index:03d}"
        for index in range(100)
    )
    result = run_silently(
        build_manual_paper_run_audit_trail,
        source,
        existing_history,
    )

    if result.audit_status != "RECORDED":
        raise RuntimeError(
            "History 한도 검사용 Audit가 실패했습니다."
        )
    if len(result.orchestration_history) != 100:
        raise RuntimeError(
            "History 보관 개수가 100이 아닙니다."
        )
    if (
        result.orchestration_history[-1]
        != source.orchestration_id
    ):
        raise RuntimeError(
            "최신 Orchestration ID가 History에 없습니다."
        )
    if (
        "old-orchestration-000"
        in result.orchestration_history
    ):
        raise RuntimeError(
            "가장 오래된 History가 제거되지 않았습니다."
        )

    assert_execution_safety(result)
    return result


def validate_policy_safety() -> None:
    policy = ManualPaperRunAuditPolicy()
    policy_valid, policy_errors = (
        validate_audit_policy(policy)
    )
    if not policy_valid or policy_errors:
        raise RuntimeError(
            "기본 V11.7 Policy가 유효하지 않습니다."
        )

    unsafe_policy = replace(
        policy,
        live_execution_disabled=False,
    )
    unsafe_valid, unsafe_errors = (
        validate_audit_policy(unsafe_policy)
    )
    if unsafe_valid or not unsafe_errors:
        raise RuntimeError(
            "Live 허용 Policy가 차단되지 않았습니다."
        )

    invalid_hash_policy = replace(
        policy,
        hash_algorithm="MD5",
    )
    hash_policy_valid, hash_policy_errors = (
        validate_audit_policy(
            invalid_hash_policy
        )
    )
    if hash_policy_valid or not hash_policy_errors:
        raise RuntimeError(
            "잘못된 Hash Algorithm이 차단되지 않았습니다."
        )

    try:
        policy.paper_only = False
    except FrozenInstanceError:
        pass
    else:
        raise RuntimeError(
            "Audit Policy가 변경되었습니다."
        )


def validate_save_load_and_file_tampering(
    successful_audit: Any,
) -> None:
    original_directory = (
        audit_module
        .MANUAL_PAPER_RUN_AUDIT_OUTPUT_DIRECTORY
    )

    with TemporaryDirectory() as temporary_directory:
        audit_module.MANUAL_PAPER_RUN_AUDIT_OUTPUT_DIRECTORY = (
            Path(temporary_directory)
        )

        try:
            report_path, latest_path = (
                save_manual_paper_run_audit_trail(
                    successful_audit
                )
            )
            loaded = (
                load_latest_manual_paper_run_audit_trail()
            )

            if not report_path.exists():
                raise RuntimeError(
                    "V11.7 Report 파일이 저장되지 않았습니다."
                )
            if not latest_path.exists():
                raise RuntimeError(
                    "V11.7 Latest 파일이 저장되지 않았습니다."
                )
            if loaded["version"] != "V11.7":
                raise RuntimeError(
                    "복원된 Version이 V11.7이 아닙니다."
                )
            if loaded["audit_status"] != "RECORDED":
                raise RuntimeError(
                    "복원된 Audit 상태가 RECORDED가 아닙니다."
                )
            if len(loaded["audit_entries"]) != 8:
                raise RuntimeError(
                    "복원된 Audit Entry 수가 8이 아닙니다."
                )

            with latest_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                tampered_payload = json.load(file)
            tampered_payload["audit_entries"][4][
                "stage_status"
            ] = "MANUALLY_CHANGED"
            with latest_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    tampered_payload,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            try:
                load_latest_manual_paper_run_audit_trail()
            except RuntimeError:
                pass
            else:
                raise RuntimeError(
                    "변경된 Audit 파일이 탐지되지 않았습니다."
                )
        finally:
            audit_module.MANUAL_PAPER_RUN_AUDIT_OUTPUT_DIRECTORY = (
                original_directory
            )


def print_validation_checks(
    checks: list[tuple[str, bool]],
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("AI STOCK BOT V11.7 MANUAL PAPER RUN AUDIT TRAIL TEST")
    print("=" * line_length)
    print()
    print("V11.7 VALIDATION CHECKS")
    print("-" * line_length)

    for label, passed in checks:
        print(f"{label:<70}: {passed}")

    print("=" * line_length)


def main() -> None:
    validate_policy_safety()
    source = create_safe_v116_source()
    successful_audit = validate_successful_audit(
        source
    )
    duplicate_result = validate_duplicate_block(
        source,
        successful_audit,
    )
    invalid_source_result = (
        validate_invalid_source_version(source)
    )
    unsafe_source_result = validate_unsafe_source(
        source
    )
    invalid_sequence_result = (
        validate_invalid_stage_sequence(source)
    )
    validate_hash_tampering(successful_audit)
    history_result = validate_history_limit(source)
    validate_save_load_and_file_tampering(
        successful_audit
    )

    checks = [
        (
            "Version is V11.7",
            successful_audit.version == "V11.7",
        ),
        (
            "Default policy is valid",
            successful_audit.policy_checks_passed,
        ),
        (
            "Policy is immutable",
            True,
        ),
        (
            "Invalid policies are blocked",
            True,
        ),
        (
            "V11.6 source was validated",
            successful_audit.source_checks_passed,
        ),
        (
            "Eight audit entries were created",
            successful_audit.total_entry_count == 8,
        ),
        (
            "Six stages were recorded in order",
            successful_audit.sequence_checks_passed,
        ),
        (
            "Genesis hash was linked",
            successful_audit.audit_entries[0]
            .previous_hash
            == GENESIS_HASH,
        ),
        (
            "SHA-256 hash chain passed",
            successful_audit
            .hash_chain_checks_passed,
        ),
        (
            "Duplicate orchestration was blocked",
            duplicate_result.audit_status
            == "BLOCKED",
        ),
        (
            "Invalid source version was blocked",
            invalid_source_result.audit_status
            == "FAILED",
        ),
        (
            "Unsafe source was blocked",
            unsafe_source_result.audit_status
            == "FAILED",
        ),
        (
            "Invalid stage sequence was blocked",
            invalid_sequence_result.audit_status
            == "FAILED",
        ),
        (
            "In-memory tampering was detected",
            True,
        ),
        (
            "Saved-file tampering was detected",
            True,
        ),
        (
            "History was trimmed to 100 records",
            len(history_result.orchestration_history)
            == 100,
        ),
        (
            "Result save and load passed",
            True,
        ),
        (
            "Automatic execution remains disabled",
            not successful_audit
            .automatic_execution_authorized,
        ),
        (
            "Execution remains blocked",
            successful_audit.execution_blocked,
        ),
        (
            "Broker API was not called",
            not successful_audit.broker_api_called,
        ),
        (
            "Broker order was not created",
            not successful_audit
            .broker_order_created,
        ),
        (
            "Live order was not created",
            not successful_audit.live_order_created,
        ),
        (
            "Live execution not authorized",
            not successful_audit
            .live_execution_authorized,
        ),
    ]

    all_checks_passed = all(
        passed
        for _, passed in checks
    )
    checks.append(
        (
            "All checks passed",
            all_checks_passed,
        )
    )
    print_validation_checks(checks)

    if not all_checks_passed:
        raise RuntimeError(
            "V11.7 Validation Check가 실패했습니다."
        )

    print()
    print(
        "V11.7 manual paper run audit trail test "
        "completed successfully."
    )
    print(
        "8개 Audit Event, SHA-256 연결, 중복 방지 및 "
        "변경 탐지가 정상적으로 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
