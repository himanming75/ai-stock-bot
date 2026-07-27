from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import backtest.manual_paper_run_orchestrator as orchestrator_module
from backtest.approved_paper_run_launcher import (
    ApprovedPaperRunLauncherResult,
)
from backtest.approved_paper_run_ledger_integration import (
    ApprovedRunLedgerIntegrationResult,
)
from backtest.manual_paper_run_orchestrator import (
    ManualPaperRunOrchestratorPolicy,
    STAGE_ORDER,
    load_latest_manual_paper_run_orchestrator,
    run_manual_paper_run_orchestrator,
    save_manual_paper_run_orchestrator,
    validate_orchestrator_policy,
)
from backtest.post_run_final_report import (
    PostRunFinalReportResult,
)
from backtest.post_run_performance_risk_refresh import (
    PostRunPerformanceRiskResult,
)
from backtest.post_run_session_refresh import (
    PostRunSessionRefreshResult,
)
from backtest.scheduled_paper_run_approval import (
    ScheduledPaperRunApprovalResult,
)


EXPECTED_MANUAL_TEXT = "RUN END TO END PAPER FLOW"


STAGE_TEST_SPECIFICATIONS = {
    "APPROVAL": (
        ScheduledPaperRunApprovalResult,
        "V11.0",
        "approval_status",
        "APPROVED",
    ),
    "LAUNCH": (
        ApprovedPaperRunLauncherResult,
        "V11.1",
        "launch_status",
        "COMPLETED",
    ),
    "LEDGER_INTEGRATION": (
        ApprovedRunLedgerIntegrationResult,
        "V11.2",
        "integration_status",
        "LINKED",
    ),
    "SESSION_REFRESH": (
        PostRunSessionRefreshResult,
        "V11.3",
        "refresh_status",
        "REFRESHED",
    ),
    "PERFORMANCE_RISK_REFRESH": (
        PostRunPerformanceRiskResult,
        "V11.4",
        "refresh_status",
        "REFRESHED",
    ),
    "FINAL_REPORT": (
        PostRunFinalReportResult,
        "V11.5",
        "report_status",
        "COMPLETED",
    ),
}


def create_stage_result(
    stage_name: str,
    *,
    status: str | None = None,
    all_checks_passed: bool = True,
    execution_blocked: bool = True,
    broker_api_called: bool = False,
    broker_order_created: bool = False,
    live_order_created: bool = False,
    live_execution_authorized: bool = False,
) -> Any:
    """
    실제 V11.0~V11.5 Result 클래스의 안전 검사에 필요한 값만
    채운 테스트 전용 객체를 만듭니다.

    각 단계의 실제 실행 함수나 Broker 함수는 호출하지 않습니다.
    """

    (
        result_type,
        version,
        status_field,
        success_status,
    ) = STAGE_TEST_SPECIFICATIONS[stage_name]

    result = object.__new__(result_type)
    values = {
        "version": version,
        status_field: (
            success_status
            if status is None
            else status
        ),
        "all_checks_passed": all_checks_passed,
        "execution_blocked": execution_blocked,
        "broker_api_called": broker_api_called,
        "broker_order_created": broker_order_created,
        "live_order_created": live_order_created,
        "live_execution_authorized": (
            live_execution_authorized
        ),
    }

    for name, value in values.items():
        object.__setattr__(result, name, value)

    return result


def create_safe_runners(
    call_log: list[str],
) -> dict[str, Any]:
    runners: dict[str, Any] = {}

    for stage_index, stage_name in enumerate(
        STAGE_ORDER,
    ):

        def runner(
            context: dict[str, Any],
            *,
            current_stage: str = stage_name,
            current_index: int = stage_index,
        ) -> Any:
            call_log.append(current_stage)

            if context["manual_actor"] != "beginner-user":
                raise RuntimeError(
                    "Manual Actor가 Context에 없습니다."
                )

            for previous_stage in STAGE_ORDER[
                :current_index
            ]:
                context_key = (
                    f"{previous_stage.lower()}_result"
                )
                if context_key not in context:
                    raise RuntimeError(
                        f"{context_key}가 Context에 없습니다."
                    )

            return create_stage_result(current_stage)

        runners[stage_name] = runner

    return runners


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


def validate_successful_orchestration() -> Any:
    call_log: list[str] = []
    result = run_manual_paper_run_orchestrator(
        manual_actor="beginner-user",
        manual_note="V11.6 전체 Paper 흐름 수동 테스트",
        manual_text=EXPECTED_MANUAL_TEXT,
        stage_runners=create_safe_runners(call_log),
        initial_context={
            "test_case": "SUCCESS",
        },
    )

    if result.version != "V11.6":
        raise RuntimeError(
            "성공 결과 Version이 V11.6이 아닙니다."
        )
    if result.orchestrator_status != "COMPLETED":
        raise RuntimeError(
            "정상 Orchestrator가 완료되지 않았습니다."
        )
    if call_log != list(STAGE_ORDER):
        raise RuntimeError(
            "Stage 호출 순서가 예상과 다릅니다."
        )
    if result.called_stage_count != 6:
        raise RuntimeError(
            "호출된 Stage 수가 6이 아닙니다."
        )
    if result.completed_stage_count != 6:
        raise RuntimeError(
            "완료된 Stage 수가 6이 아닙니다."
        )
    if result.failed_stage_name is not None:
        raise RuntimeError(
            "정상 결과에 실패 Stage가 있습니다."
        )
    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 결과의 All Checks가 실패했습니다."
        )
    if tuple(result.stage_results) != STAGE_ORDER:
        raise RuntimeError(
            "Stage Result 순서가 예상과 다릅니다."
        )
    if any(
        not record.all_checks_passed
        for record in result.stage_records
    ):
        raise RuntimeError(
            "정상 Stage Record 중 실패가 있습니다."
        )

    assert_execution_safety(result)
    return result


def validate_invalid_manual_text(
    runners: dict[str, Any],
) -> Any:
    result = run_manual_paper_run_orchestrator(
        manual_actor="beginner-user",
        manual_note="잘못된 수동 문구 검사",
        manual_text="RUN PAPER FLOW",
        stage_runners=runners,
    )

    if result.orchestrator_status != "FAILED":
        raise RuntimeError(
            "잘못된 Manual Text가 차단되지 않았습니다."
        )
    if result.failed_stage_name != "PREFLIGHT":
        raise RuntimeError(
            "Manual Text 실패 위치가 PREFLIGHT가 아닙니다."
        )
    if result.called_stage_count != 0:
        raise RuntimeError(
            "사전검사 실패 후 Runner가 호출되었습니다."
        )
    if any(
        record.called
        for record in result.stage_records
    ):
        raise RuntimeError(
            "사전검사 실패 Stage가 호출 상태입니다."
        )

    assert_execution_safety(result)
    return result


def validate_missing_runner(
    runners: dict[str, Any],
) -> Any:
    incomplete_runners = dict(runners)
    del incomplete_runners["FINAL_REPORT"]

    result = run_manual_paper_run_orchestrator(
        manual_actor="beginner-user",
        manual_note="누락 Runner 사전검사",
        manual_text=EXPECTED_MANUAL_TEXT,
        stage_runners=incomplete_runners,
    )

    if result.orchestrator_status != "FAILED":
        raise RuntimeError(
            "누락 Runner가 차단되지 않았습니다."
        )
    if result.runner_checks_passed:
        raise RuntimeError(
            "누락 Runner 검사가 통과했습니다."
        )
    if result.called_stage_count != 0:
        raise RuntimeError(
            "Runner 사전검사 실패 후 Stage가 호출되었습니다."
        )

    assert_execution_safety(result)
    return result


def validate_fail_fast_behavior() -> Any:
    call_log: list[str] = []
    runners = create_safe_runners(call_log)

    def failed_ledger_runner(
        context: dict[str, Any],
    ) -> Any:
        call_log.append("LEDGER_INTEGRATION")
        return create_stage_result(
            "LEDGER_INTEGRATION",
            status="FAILED",
            all_checks_passed=False,
        )

    runners["LEDGER_INTEGRATION"] = (
        failed_ledger_runner
    )
    result = run_manual_paper_run_orchestrator(
        manual_actor="beginner-user",
        manual_note="Ledger 실패 후 즉시 중단 검사",
        manual_text=EXPECTED_MANUAL_TEXT,
        stage_runners=runners,
    )

    expected_calls = [
        "APPROVAL",
        "LAUNCH",
        "LEDGER_INTEGRATION",
    ]
    if call_log != expected_calls:
        raise RuntimeError(
            "Fail-Fast 호출 범위가 예상과 다릅니다."
        )
    if result.orchestrator_status != "BLOCKED":
        raise RuntimeError(
            "Stage 실패 결과가 BLOCKED가 아닙니다."
        )
    if (
        result.failed_stage_name
        != "LEDGER_INTEGRATION"
    ):
        raise RuntimeError(
            "실패 Stage 이름이 올바르지 않습니다."
        )
    if result.called_stage_count != 3:
        raise RuntimeError(
            "실패 전 호출 Stage 수가 올바르지 않습니다."
        )
    if result.completed_stage_count != 2:
        raise RuntimeError(
            "실패 전 완료 Stage 수가 올바르지 않습니다."
        )
    if any(
        record.called
        for record in result.stage_records[3:]
    ):
        raise RuntimeError(
            "실패 후 Stage Runner가 호출되었습니다."
        )

    assert_execution_safety(result)
    return result


def validate_runner_exception() -> Any:
    call_log: list[str] = []
    runners = create_safe_runners(call_log)

    def exception_runner(
        context: dict[str, Any],
    ) -> Any:
        call_log.append("SESSION_REFRESH")
        raise RuntimeError(
            "의도적으로 만든 Session Refresh 오류"
        )

    runners["SESSION_REFRESH"] = exception_runner
    result = run_manual_paper_run_orchestrator(
        manual_actor="beginner-user",
        manual_note="Runner 예외 안전 처리 검사",
        manual_text=EXPECTED_MANUAL_TEXT,
        stage_runners=runners,
    )

    if (
        result.failed_stage_name
        != "SESSION_REFRESH"
    ):
        raise RuntimeError(
            "Runner 예외 Stage가 올바르지 않습니다."
        )
    if result.called_stage_count != 4:
        raise RuntimeError(
            "Runner 예외 후 호출 수가 올바르지 않습니다."
        )
    if not result.stage_records[3].error_message:
        raise RuntimeError(
            "Runner 예외 메시지가 기록되지 않았습니다."
        )
    if any(
        record.called
        for record in result.stage_records[4:]
    ):
        raise RuntimeError(
            "Runner 예외 후 나머지 Stage가 호출되었습니다."
        )

    assert_execution_safety(result)
    return result


def validate_unsafe_result() -> Any:
    call_log: list[str] = []
    runners = create_safe_runners(call_log)

    def unsafe_launch_runner(
        context: dict[str, Any],
    ) -> Any:
        call_log.append("LAUNCH")
        return create_stage_result(
            "LAUNCH",
            execution_blocked=False,
            broker_api_called=True,
        )

    runners["LAUNCH"] = unsafe_launch_runner
    result = run_manual_paper_run_orchestrator(
        manual_actor="beginner-user",
        manual_note="위험한 실행 결과 차단 검사",
        manual_text=EXPECTED_MANUAL_TEXT,
        stage_runners=runners,
    )

    if result.failed_stage_name != "LAUNCH":
        raise RuntimeError(
            "위험 결과가 LAUNCH에서 차단되지 않았습니다."
        )
    if result.stage_records[1].safety_checks_passed:
        raise RuntimeError(
            "위험한 LAUNCH 안전 검사가 통과했습니다."
        )
    if call_log != ["APPROVAL", "LAUNCH"]:
        raise RuntimeError(
            "위험 결과 후 나머지 Runner가 호출되었습니다."
        )

    assert_execution_safety(result)
    return result


def validate_policy_safety() -> None:
    default_policy = ManualPaperRunOrchestratorPolicy()
    policy_valid, errors = validate_orchestrator_policy(
        default_policy
    )
    if not policy_valid or errors:
        raise RuntimeError(
            "기본 V11.6 Policy가 유효하지 않습니다."
        )

    unsafe_policy = replace(
        default_policy,
        live_execution_disabled=False,
    )
    unsafe_valid, unsafe_errors = (
        validate_orchestrator_policy(
            unsafe_policy
        )
    )
    if unsafe_valid or not unsafe_errors:
        raise RuntimeError(
            "Live 허용 Policy가 차단되지 않았습니다."
        )

    try:
        default_policy.paper_only = False
    except FrozenInstanceError:
        pass
    else:
        raise RuntimeError(
            "Orchestrator Policy가 변경되었습니다."
        )


def validate_save_and_load(
    successful_result: Any,
) -> None:
    original_directory = (
        orchestrator_module
        .MANUAL_PAPER_RUN_ORCHESTRATOR_OUTPUT_DIRECTORY
    )

    with TemporaryDirectory() as temporary_directory:
        orchestrator_module.MANUAL_PAPER_RUN_ORCHESTRATOR_OUTPUT_DIRECTORY = (
            Path(temporary_directory)
        )

        # 테스트용 Stage 객체는 전체 필드를 채운 실제 실행 결과가
        # 아니므로, Orchestrator 자체의 저장/복원만 검사합니다.
        stage_results = successful_result.stage_results
        successful_result.stage_results = {}

        try:
            report_path, latest_path = (
                save_manual_paper_run_orchestrator(
                    successful_result
                )
            )
            loaded = (
                load_latest_manual_paper_run_orchestrator()
            )
        finally:
            successful_result.stage_results = stage_results
            orchestrator_module.MANUAL_PAPER_RUN_ORCHESTRATOR_OUTPUT_DIRECTORY = (
                original_directory
            )

        if not report_path.exists():
            raise RuntimeError(
                "V11.6 Report 파일이 저장되지 않았습니다."
            )
        if not latest_path.exists():
            raise RuntimeError(
                "V11.6 Latest 파일이 저장되지 않았습니다."
            )
        if loaded["version"] != "V11.6":
            raise RuntimeError(
                "복원된 Version이 V11.6이 아닙니다."
            )
        if (
            loaded["orchestrator_status"]
            != "COMPLETED"
        ):
            raise RuntimeError(
                "복원된 상태가 COMPLETED가 아닙니다."
            )
        if len(loaded["stage_records"]) != 6:
            raise RuntimeError(
                "복원된 Stage Record 수가 6이 아닙니다."
            )


def print_validation_checks(
    checks: list[tuple[str, bool]],
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("AI STOCK BOT V11.6 MANUAL PAPER RUN ORCHESTRATOR TEST")
    print("=" * line_length)
    print()
    print("V11.6 VALIDATION CHECKS")
    print("-" * line_length)

    for label, passed in checks:
        print(f"{label:<70}: {passed}")

    print("=" * line_length)


def main() -> None:
    validate_policy_safety()

    successful_result = (
        validate_successful_orchestration()
    )

    unused_call_log: list[str] = []
    safe_runners = create_safe_runners(
        unused_call_log
    )
    invalid_text_result = (
        validate_invalid_manual_text(
            safe_runners
        )
    )
    missing_runner_result = (
        validate_missing_runner(
            safe_runners
        )
    )
    fail_fast_result = (
        validate_fail_fast_behavior()
    )
    exception_result = (
        validate_runner_exception()
    )
    unsafe_result = validate_unsafe_result()
    validate_save_and_load(successful_result)

    checks = [
        (
            "Version is V11.6",
            successful_result.version == "V11.6",
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
            "Manual start text was validated",
            successful_result.input_checks_passed,
        ),
        (
            "Six stages completed in order",
            successful_result.completed_stage_count
            == 6,
        ),
        (
            "Context was passed between stages",
            successful_result.all_checks_passed,
        ),
        (
            "Invalid manual text was blocked",
            invalid_text_result.orchestrator_status
            == "FAILED",
        ),
        (
            "Missing runner was blocked",
            missing_runner_result.orchestrator_status
            == "FAILED",
        ),
        (
            "Stage failure stopped later stages",
            fail_fast_result.failed_stage_name
            == "LEDGER_INTEGRATION",
        ),
        (
            "Runner exception was contained",
            exception_result.failed_stage_name
            == "SESSION_REFRESH",
        ),
        (
            "Unsafe stage result was blocked",
            unsafe_result.failed_stage_name
            == "LAUNCH",
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
            not successful_result.broker_order_created,
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
            "V11.6 Validation Check가 실패했습니다."
        )

    print()
    print(
        "V11.6 manual paper run orchestrator test "
        "completed successfully."
    )
    print(
        "정상 6단계 연결, 수동 입력, Fail-Fast 및 "
        "예외 차단이 정상적으로 검증되었습니다."
    )
    print(
        "실제 Broker API, 실제 주문 및 Live Execution은 "
        "호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
