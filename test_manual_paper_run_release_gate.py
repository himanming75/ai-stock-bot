import io
import json
from contextlib import redirect_stdout
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

import backtest.manual_paper_run_release_gate as release_module
from backtest.manual_paper_run_release_gate import (
    REQUIRED_MANUAL_RELEASE_TEXT,
    ManualPaperRunReleaseGatePolicy,
    create_release_identity,
    load_latest_manual_paper_run_release_gate,
    release_manual_paper_run,
    save_manual_paper_run_release_gate,
    validate_release_policy,
    verify_release_seal,
    verify_saved_release_payload,
)
from test_manual_paper_run_reconciliation import (
    create_safe_source_pair,
    validate_successful_reconciliation,
)


MANUAL_ACTOR = "beginner-user"
RELEASE_NOTE = (
    "V11.9 Paper Run 검증 완료 기록 잠금"
)


def run_silently(
    function: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    with redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_safe_v116_to_v118_chain() -> tuple[
    Any,
    Any,
    Any,
]:
    (
        orchestrator_result,
        audit_result,
    ) = create_safe_source_pair()
    reconciliation_result = run_silently(
        validate_successful_reconciliation,
        orchestrator_result,
        audit_result,
    )

    if not orchestrator_result.all_checks_passed:
        raise RuntimeError(
            "V11.6 테스트 Source가 안전하지 않습니다."
        )
    if not audit_result.all_checks_passed:
        raise RuntimeError(
            "V11.7 테스트 Source가 안전하지 않습니다."
        )
    if not reconciliation_result.all_checks_passed:
        raise RuntimeError(
            "V11.8 테스트 Source가 안전하지 않습니다."
        )

    return (
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )


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


def validate_successful_release(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
) -> Any:
    result = run_silently(
        release_manual_paper_run,
        MANUAL_ACTOR,
        RELEASE_NOTE,
        REQUIRED_MANUAL_RELEASE_TEXT,
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )

    if result.version != "V11.9":
        raise RuntimeError(
            "Release Gate Version이 V11.9가 아닙니다."
        )
    if result.release_status != "PAPER_RELEASED":
        raise RuntimeError(
            "정상 Release 상태가 PAPER_RELEASED가 아닙니다."
        )
    if not result.paper_run_locked:
        raise RuntimeError(
            "정상 Paper Run이 잠기지 않았습니다."
        )
    if result.release_seal is None:
        raise RuntimeError(
            "정상 결과에 Release Seal이 없습니다."
        )
    if (
        result.release_seal.orchestration_id
        != orchestrator_result.orchestration_id
    ):
        raise RuntimeError(
            "Seal의 Orchestration ID가 다릅니다."
        )
    if (
        result.release_seal.audit_trail_id
        != audit_result.audit_trail_id
    ):
        raise RuntimeError(
            "Seal의 Audit Trail ID가 다릅니다."
        )
    if (
        result.release_seal.reconciliation_id
        != reconciliation_result
        .reconciliation_id
    ):
        raise RuntimeError(
            "Seal의 Reconciliation ID가 다릅니다."
        )

    expected_identity = create_release_identity(
        orchestrator_result.orchestration_id,
        audit_result.audit_trail_id,
        reconciliation_result.reconciliation_id,
    )
    if result.release_identity != expected_identity:
        raise RuntimeError(
            "Release Identity가 올바르지 않습니다."
        )

    seal_valid, seal_errors = verify_release_seal(
        result.release_seal
    )
    if not seal_valid or seal_errors:
        raise RuntimeError(
            "정상 Release Seal 검사가 실패했습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 Release의 All Checks가 실패했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_wrong_manual_text(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
) -> Any:
    result = run_silently(
        release_manual_paper_run,
        MANUAL_ACTOR,
        RELEASE_NOTE,
        "RELEASE PAPER RUN",
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )

    if result.release_status != "FAILED":
        raise RuntimeError(
            "잘못된 수동 문구가 FAILED가 아닙니다."
        )
    if result.manual_checks_passed:
        raise RuntimeError(
            "잘못된 수동 문구 검사가 통과했습니다."
        )
    if result.release_seal is not None:
        raise RuntimeError(
            "잘못된 수동 문구로 Seal이 생성됐습니다."
        )
    if result.paper_run_locked:
        raise RuntimeError(
            "잘못된 수동 문구로 Paper Run이 잠겼습니다."
        )

    assert_execution_safety(result)
    return result


def validate_wrong_actor(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
) -> Any:
    result = run_silently(
        release_manual_paper_run,
        "different-user",
        RELEASE_NOTE,
        REQUIRED_MANUAL_RELEASE_TEXT,
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )

    if result.release_status != "FAILED":
        raise RuntimeError(
            "다른 실행자가 FAILED로 차단되지 않았습니다."
        )
    if result.actor_checks_passed:
        raise RuntimeError(
            "다른 실행자 검사가 통과했습니다."
        )
    if result.release_seal is not None:
        raise RuntimeError(
            "다른 실행자로 Release Seal이 생성됐습니다."
        )

    assert_execution_safety(result)
    return result


def validate_incomplete_source(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
) -> Any:
    incomplete_orchestrator = replace(
        orchestrator_result,
        orchestrator_status="BLOCKED",
        all_checks_passed=False,
    )
    result = run_silently(
        release_manual_paper_run,
        MANUAL_ACTOR,
        RELEASE_NOTE,
        REQUIRED_MANUAL_RELEASE_TEXT,
        incomplete_orchestrator,
        audit_result,
        reconciliation_result,
    )

    if result.release_status != "FAILED":
        raise RuntimeError(
            "미완료 Source가 FAILED로 차단되지 않았습니다."
        )
    if result.source_checks_passed:
        raise RuntimeError(
            "미완료 Source 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_identity_mismatch(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
) -> Any:
    mismatched_reconciliation = replace(
        reconciliation_result,
        source_orchestration_id=(
            "different-orchestration-id"
        ),
    )
    result = run_silently(
        release_manual_paper_run,
        MANUAL_ACTOR,
        RELEASE_NOTE,
        REQUIRED_MANUAL_RELEASE_TEXT,
        orchestrator_result,
        audit_result,
        mismatched_reconciliation,
    )

    if result.release_status != "FAILED":
        raise RuntimeError(
            "ID 불일치가 FAILED로 차단되지 않았습니다."
        )
    if result.identity_checks_passed:
        raise RuntimeError(
            "ID 연결 검사가 잘못 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_hash_tampering(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
) -> Any:
    changed_entries = list(
        audit_result.audit_entries
    )
    changed_entries[4] = replace(
        changed_entries[4],
        stage_status="TAMPERED",
    )
    tampered_audit = replace(
        audit_result,
        audit_entries=tuple(changed_entries),
    )
    result = run_silently(
        release_manual_paper_run,
        MANUAL_ACTOR,
        RELEASE_NOTE,
        REQUIRED_MANUAL_RELEASE_TEXT,
        orchestrator_result,
        tampered_audit,
        reconciliation_result,
    )

    if result.release_status != "FAILED":
        raise RuntimeError(
            "Hash 조작이 FAILED로 차단되지 않았습니다."
        )
    if result.hash_chain_checks_passed:
        raise RuntimeError(
            "조작된 Audit Hash 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_unreconciled_source(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
) -> Any:
    unreconciled_result = replace(
        reconciliation_result,
        reconciliation_status="MISMATCH",
        mismatched_item_count=1,
        all_checks_passed=False,
    )
    result = run_silently(
        release_manual_paper_run,
        MANUAL_ACTOR,
        RELEASE_NOTE,
        REQUIRED_MANUAL_RELEASE_TEXT,
        orchestrator_result,
        audit_result,
        unreconciled_result,
    )

    if result.release_status != "FAILED":
        raise RuntimeError(
            "불일치 결과가 FAILED로 차단되지 않았습니다."
        )
    if result.source_checks_passed:
        raise RuntimeError(
            "불일치 Reconciliation 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_unsafe_source(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
) -> Any:
    unsafe_reconciliation = replace(
        reconciliation_result,
        execution_blocked=False,
        broker_api_called=True,
    )
    result = run_silently(
        release_manual_paper_run,
        MANUAL_ACTOR,
        RELEASE_NOTE,
        REQUIRED_MANUAL_RELEASE_TEXT,
        orchestrator_result,
        audit_result,
        unsafe_reconciliation,
    )

    if result.release_status != "FAILED":
        raise RuntimeError(
            "위험한 Source가 FAILED로 차단되지 않았습니다."
        )
    if result.safety_checks_passed:
        raise RuntimeError(
            "위험한 Source Safety 검사가 통과했습니다."
        )

    assert_execution_safety(result)
    return result


def validate_duplicate_release(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
    successful_result: Any,
) -> Any:
    result = run_silently(
        release_manual_paper_run,
        MANUAL_ACTOR,
        RELEASE_NOTE,
        REQUIRED_MANUAL_RELEASE_TEXT,
        orchestrator_result,
        audit_result,
        reconciliation_result,
        successful_result.release_history,
    )

    if result.release_status != "BLOCKED":
        raise RuntimeError(
            "중복 Release가 BLOCKED가 아닙니다."
        )
    if result.duplicate_checks_passed:
        raise RuntimeError(
            "중복 Release 검사가 통과했습니다."
        )
    if result.release_seal is not None:
        raise RuntimeError(
            "중복 Release에 Seal이 생성됐습니다."
        )

    assert_execution_safety(result)
    return result


def validate_seal_tampering(
    successful_result: Any,
) -> None:
    tampered_seal = replace(
        successful_result.release_seal,
        release_note="MANUALLY CHANGED",
    )
    seal_valid, seal_errors = verify_release_seal(
        tampered_seal
    )
    if seal_valid:
        raise RuntimeError(
            "변경된 Release Seal 검사가 통과했습니다."
        )
    if not seal_errors:
        raise RuntimeError(
            "Release Seal 변경 오류가 기록되지 않았습니다."
        )

    payload = successful_result.to_dict()
    payload["release_seal"][
        "manual_actor"
    ] = "changed-user"
    payload_valid, payload_errors = (
        verify_saved_release_payload(payload)
    )
    if payload_valid:
        raise RuntimeError(
            "변경된 Release JSON 검사가 통과했습니다."
        )
    if not payload_errors:
        raise RuntimeError(
            "Release JSON 변경 오류가 기록되지 않았습니다."
        )


def validate_history_limit(
    orchestrator_result: Any,
    audit_result: Any,
    reconciliation_result: Any,
) -> Any:
    existing_history = tuple(
        f"old-release-{index:03d}"
        for index in range(100)
    )
    result = run_silently(
        release_manual_paper_run,
        MANUAL_ACTOR,
        RELEASE_NOTE,
        REQUIRED_MANUAL_RELEASE_TEXT,
        orchestrator_result,
        audit_result,
        reconciliation_result,
        existing_history,
    )

    if result.release_status != "PAPER_RELEASED":
        raise RuntimeError(
            "History 한도 검사용 Release가 실패했습니다."
        )
    if len(result.release_history) != 100:
        raise RuntimeError(
            "Release History 보관 개수가 100이 아닙니다."
        )
    if (
        result.release_history[-1]
        != result.release_identity
    ):
        raise RuntimeError(
            "최신 Release Identity가 History에 없습니다."
        )
    if (
        "old-release-000"
        in result.release_history
    ):
        raise RuntimeError(
            "가장 오래된 Release History가 제거되지 않았습니다."
        )

    assert_execution_safety(result)
    return result


def validate_policy_safety() -> None:
    policy = ManualPaperRunReleaseGatePolicy()
    policy_valid, policy_errors = (
        validate_release_policy(policy)
    )
    if not policy_valid or policy_errors:
        raise RuntimeError(
            "기본 V11.9 Policy가 유효하지 않습니다."
        )

    unsafe_policy = replace(
        policy,
        live_execution_disabled=False,
    )
    unsafe_valid, unsafe_errors = (
        validate_release_policy(unsafe_policy)
    )
    if unsafe_valid or not unsafe_errors:
        raise RuntimeError(
            "Live 허용 Policy가 차단되지 않았습니다."
        )

    wrong_text_policy = replace(
        policy,
        required_manual_release_text=(
            "ALLOW LIVE TRADING"
        ),
    )
    text_valid, text_errors = (
        validate_release_policy(
            wrong_text_policy
        )
    )
    if text_valid or not text_errors:
        raise RuntimeError(
            "잘못된 Release Text Policy가 차단되지 않았습니다."
        )

    try:
        policy.paper_only = False
    except FrozenInstanceError:
        pass
    else:
        raise RuntimeError(
            "Release Gate Policy가 변경되었습니다."
        )


def validate_save_load_and_file_tampering(
    successful_result: Any,
) -> None:
    original_directory = (
        release_module
        .MANUAL_PAPER_RUN_RELEASE_GATE_OUTPUT_DIRECTORY
    )

    with TemporaryDirectory() as temporary_directory:
        release_module.MANUAL_PAPER_RUN_RELEASE_GATE_OUTPUT_DIRECTORY = (
            Path(temporary_directory)
        )

        try:
            report_path, latest_path = (
                save_manual_paper_run_release_gate(
                    successful_result
                )
            )
            loaded = (
                load_latest_manual_paper_run_release_gate()
            )

            if not report_path.exists():
                raise RuntimeError(
                    "V11.9 Report 파일이 저장되지 않았습니다."
                )
            if not latest_path.exists():
                raise RuntimeError(
                    "V11.9 Latest 파일이 저장되지 않았습니다."
                )
            if loaded["version"] != "V11.9":
                raise RuntimeError(
                    "복원된 Version이 V11.9가 아닙니다."
                )
            if (
                loaded["release_status"]
                != "PAPER_RELEASED"
            ):
                raise RuntimeError(
                    "복원된 상태가 PAPER_RELEASED가 아닙니다."
                )
            if (
                loaded["release_seal"][
                    "paper_run_locked"
                ]
                is not True
            ):
                raise RuntimeError(
                    "복원된 Paper Run이 잠겨 있지 않습니다."
                )

            with latest_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                tampered_payload = json.load(file)
            tampered_payload["release_seal"][
                "release_note"
            ] = "FILE CHANGED"
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
                load_latest_manual_paper_run_release_gate()
            except RuntimeError:
                pass
            else:
                raise RuntimeError(
                    "변경된 Release 파일이 탐지되지 않았습니다."
                )
        finally:
            release_module.MANUAL_PAPER_RUN_RELEASE_GATE_OUTPUT_DIRECTORY = (
                original_directory
            )


def print_validation_checks(
    checks: list[tuple[str, bool]],
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("AI STOCK BOT V11.9 MANUAL PAPER RUN RELEASE GATE TEST")
    print("=" * line_length)
    print()
    print("V11.9 VALIDATION CHECKS")
    print("-" * line_length)

    for label, passed in checks:
        print(f"{label:<70}: {passed}")

    print("=" * line_length)


def main() -> None:
    validate_policy_safety()
    (
        orchestrator_result,
        audit_result,
        reconciliation_result,
    ) = create_safe_v116_to_v118_chain()

    successful_result = (
        validate_successful_release(
            orchestrator_result,
            audit_result,
            reconciliation_result,
        )
    )
    manual_text_result = validate_wrong_manual_text(
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )
    actor_result = validate_wrong_actor(
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )
    incomplete_result = validate_incomplete_source(
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )
    identity_result = validate_identity_mismatch(
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )
    hash_result = validate_hash_tampering(
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )
    unreconciled_result = (
        validate_unreconciled_source(
            orchestrator_result,
            audit_result,
            reconciliation_result,
        )
    )
    unsafe_result = validate_unsafe_source(
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )
    duplicate_result = validate_duplicate_release(
        orchestrator_result,
        audit_result,
        reconciliation_result,
        successful_result,
    )
    validate_seal_tampering(successful_result)
    history_result = validate_history_limit(
        orchestrator_result,
        audit_result,
        reconciliation_result,
    )
    validate_save_load_and_file_tampering(
        successful_result
    )

    checks = [
        (
            "Version is V11.9",
            successful_result.version == "V11.9",
        ),
        (
            "Default policy is valid",
            successful_result.policy_checks_passed,
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
            "Manual release text was validated",
            successful_result.manual_checks_passed,
        ),
        (
            "V11.6 through V11.8 sources were validated",
            successful_result.source_checks_passed,
        ),
        (
            "Source identity chain passed",
            successful_result.identity_checks_passed,
        ),
        (
            "Manual actor chain passed",
            successful_result.actor_checks_passed,
        ),
        (
            "Audit hash chain passed",
            successful_result.hash_chain_checks_passed,
        ),
        (
            "Paper run was locked",
            successful_result.paper_run_locked,
        ),
        (
            "Release seal was created",
            successful_result.release_seal
            is not None,
        ),
        (
            "Release seal hash passed",
            successful_result.seal_checks_passed,
        ),
        (
            "Wrong manual text was blocked",
            manual_text_result.release_status
            == "FAILED",
        ),
        (
            "Wrong actor was blocked",
            actor_result.release_status
            == "FAILED",
        ),
        (
            "Incomplete source was blocked",
            incomplete_result.release_status
            == "FAILED",
        ),
        (
            "Identity mismatch was blocked",
            identity_result.release_status
            == "FAILED",
        ),
        (
            "Audit hash tampering was blocked",
            hash_result.release_status
            == "FAILED",
        ),
        (
            "Unreconciled source was blocked",
            unreconciled_result.release_status
            == "FAILED",
        ),
        (
            "Unsafe source was blocked",
            unsafe_result.release_status
            == "FAILED",
        ),
        (
            "Duplicate release was blocked",
            duplicate_result.release_status
            == "BLOCKED",
        ),
        (
            "In-memory seal tampering was detected",
            True,
        ),
        (
            "Saved-file tampering was detected",
            True,
        ),
        (
            "History was trimmed to 100 records",
            len(history_result.release_history)
            == 100,
        ),
        (
            "Result save and load passed",
            True,
        ),
        (
            "Automatic execution remains disabled",
            not successful_result
            .automatic_execution_authorized,
        ),
        (
            "Execution remains blocked",
            successful_result.execution_blocked,
        ),
        (
            "Broker API was not called",
            not successful_result.broker_api_called,
        ),
        (
            "Broker order was not created",
            not successful_result
            .broker_order_created,
        ),
        (
            "Live order was not created",
            not successful_result.live_order_created,
        ),
        (
            "Live execution not authorized",
            not successful_result
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
            "V11.9 Validation Check가 실패했습니다."
        )

    print()
    print(
        "V11.9 manual paper run release gate test "
        "completed successfully."
    )
    print(
        "수동 Release, Source 연결, SHA-256 Seal, "
        "중복 및 변경 차단이 정상적으로 검증되었습니다."
    )
    print(
        "PAPER_RELEASED는 Paper 기록 잠금이며 "
        "실제 Broker 주문 권한이 아닙니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
