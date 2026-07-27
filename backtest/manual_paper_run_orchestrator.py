import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from backtest.approved_paper_run_launcher import (
    ApprovedPaperRunLauncherResult,
)
from backtest.approved_paper_run_ledger_integration import (
    ApprovedRunLedgerIntegrationResult,
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


PROJECT_ROOT = Path(__file__).resolve().parent.parent

MANUAL_PAPER_RUN_ORCHESTRATOR_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "manual_paper_run_orchestrator"
)

STAGE_ORDER = (
    "APPROVAL",
    "LAUNCH",
    "LEDGER_INTEGRATION",
    "SESSION_REFRESH",
    "PERFORMANCE_RISK_REFRESH",
    "FINAL_REPORT",
)

VALID_ORCHESTRATOR_STATUSES = {
    "COMPLETED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class ManualPaperRunOrchestratorPolicy:
    """
    V11.6 End-to-End Manual Paper Run Orchestrator 정책입니다.
    """

    required_manual_text: str = (
        "RUN END TO END PAPER FLOW"
    )
    minimum_manual_note_length: int = 5

    require_all_stage_runners: bool = True
    stop_on_stage_failure: bool = True
    require_stage_type_validation: bool = True
    require_stage_safety: bool = True

    manual_start_required: bool = True
    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualPaperRunStageRecord:
    stage_name: str
    stage_order: int
    expected_version: str

    started_at: str
    completed_at: str
    duration_seconds: float

    called: bool
    completed: bool
    result_type: str | None
    result_version: str | None
    result_status: str | None

    type_checks_passed: bool
    status_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    error_message: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass
class ManualPaperRunOrchestratorResult:
    version: str
    created_at: str
    orchestration_id: str

    orchestrator_status: str
    orchestrator_status_label: str

    manual_actor: str
    manual_note: str
    manual_text: str
    started_at: str
    completed_at: str
    total_duration_seconds: float

    total_stage_count: int
    called_stage_count: int
    completed_stage_count: int
    failed_stage_name: str | None

    policy_checks_passed: bool
    input_checks_passed: bool
    runner_checks_passed: bool
    stage_checks_passed: bool
    sequence_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    orchestrator_policy: (
        ManualPaperRunOrchestratorPolicy
    )
    stage_records: tuple[
        ManualPaperRunStageRecord,
        ...,
    ]
    stage_results: dict[str, Any]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["orchestrator_policy"] = (
            self.orchestrator_policy.to_dict()
        )
        payload["stage_records"] = [
            record.to_dict()
            for record in self.stage_records
        ]
        payload["stage_results"] = {}

        for name, result in self.stage_results.items():
            if hasattr(result, "to_dict"):
                payload["stage_results"][name] = (
                    result.to_dict()
                )
            else:
                try:
                    json.dumps(result)
                    payload["stage_results"][name] = (
                        result
                    )
                except (TypeError, ValueError):
                    payload["stage_results"][name] = (
                        repr(result)
                    )

        return payload


def write_json_file(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )
    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )
    temporary_path.replace(path)


def read_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(
            "JSON 최상위 값은 object여야 합니다."
        )
    return payload


def validate_orchestrator_policy(
    policy: ManualPaperRunOrchestratorPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        ManualPaperRunOrchestratorPolicy,
    ):
        return (
            False,
            ["Orchestrator Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    if (
        not isinstance(
            policy.required_manual_text,
            str,
        )
        or not policy.required_manual_text.strip()
    ):
        errors.append(
            "Required Manual Text가 비어 있습니다."
        )
    if (
        not isinstance(
            policy.minimum_manual_note_length,
            int,
        )
        or policy.minimum_manual_note_length <= 0
    ):
        errors.append(
            "Minimum Manual Note Length가 올바르지 않습니다."
        )

    for name, value in {
        "require_all_stage_runners": (
            policy.require_all_stage_runners
        ),
        "stop_on_stage_failure": (
            policy.stop_on_stage_failure
        ),
        "require_stage_type_validation": (
            policy.require_stage_type_validation
        ),
        "require_stage_safety": (
            policy.require_stage_safety
        ),
        "manual_start_required": (
            policy.manual_start_required
        ),
        "automatic_execution_disabled": (
            policy.automatic_execution_disabled
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }.items():
        if value is not True:
            errors.append(
                f"{name}는 V11.6에서 True여야 합니다."
            )
    return (not errors, errors)


def validate_manual_input(
    actor: str,
    note: str,
    manual_text: str,
    policy: ManualPaperRunOrchestratorPolicy,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(actor, str) or not actor.strip():
        errors.append(
            "Manual Actor가 비어 있습니다."
        )
    if (
        not isinstance(note, str)
        or len(note.strip())
        < policy.minimum_manual_note_length
    ):
        errors.append(
            "Manual Note가 너무 짧습니다."
        )
    if (
        not isinstance(manual_text, str)
        or manual_text.strip().upper()
        != policy.required_manual_text.upper()
    ):
        errors.append(
            (
                "Required Manual Text가 일치하지 않습니다. "
                f"필요 문구: {policy.required_manual_text}"
            )
        )
    return (not errors, errors)


def stage_specifications() -> dict[
    str,
    tuple[type, str, str, str],
]:
    """
    Stage Name:
      Result Type, Version, Status Field, Success Status
    """

    return {
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


def validate_stage_result(
    stage_name: str,
    result: Any,
) -> tuple[
    bool,
    bool,
    bool,
    list[str],
]:
    expected_type, version, status_field, success_status = (
        stage_specifications()[stage_name]
    )
    warnings: list[str] = []

    type_valid = isinstance(
        result,
        expected_type,
    )
    if not type_valid:
        warnings.append(
            (
                f"{stage_name} Result Type이 "
                f"{expected_type.__name__}이 아닙니다."
            )
        )

    status_valid = bool(
        type_valid
        and result.version == version
        and getattr(result, status_field, None)
        == success_status
        and result.all_checks_passed is True
    )
    if type_valid and not status_valid:
        warnings.append(
            (
                f"{stage_name} Version, Status 또는 "
                "All Checks가 올바르지 않습니다."
            )
        )

    safety_valid = bool(
        type_valid
        and result.execution_blocked is True
        and not any(
            (
                result.broker_api_called,
                result.broker_order_created,
                result.live_order_created,
                result.live_execution_authorized,
            )
        )
    )
    if type_valid and not safety_valid:
        warnings.append(
            f"{stage_name} Result에 실거래 안전 오류가 있습니다."
        )

    return (
        type_valid,
        status_valid,
        safety_valid,
        warnings,
    )


def create_skipped_stage_record(
    stage_name: str,
    stage_order: int,
    reason: str,
) -> ManualPaperRunStageRecord:
    now = datetime.now().isoformat()
    expected_version = (
        stage_specifications()[stage_name][1]
    )
    return ManualPaperRunStageRecord(
        stage_name=stage_name,
        stage_order=stage_order,
        expected_version=expected_version,
        started_at=now,
        completed_at=now,
        duration_seconds=0.0,
        called=False,
        completed=False,
        result_type=None,
        result_version=None,
        result_status=None,
        type_checks_passed=False,
        status_checks_passed=False,
        safety_checks_passed=True,
        all_checks_passed=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        error_message=reason,
        warnings=(reason,),
    )


def run_manual_paper_run_orchestrator(
    manual_actor: str,
    manual_note: str,
    manual_text: str,
    stage_runners: dict[
        str,
        Callable[[dict[str, Any]], Any],
    ],
    initial_context: (
        dict[str, Any]
        | None
    ) = None,
    orchestrator_policy: (
        ManualPaperRunOrchestratorPolicy
        | None
    ) = None,
) -> ManualPaperRunOrchestratorResult:
    """
    V11.0~V11.5 Runner를 순서대로 한 번씩 호출합니다.

    각 Runner는 현재 Context dict를 입력받고 해당 Stage Result를
    반환해야 합니다. 실패 시 이후 Runner는 호출하지 않습니다.
    """

    policy = (
        orchestrator_policy
        if orchestrator_policy is not None
        else ManualPaperRunOrchestratorPolicy()
    )
    policy_valid, policy_errors = (
        validate_orchestrator_policy(policy)
    )
    input_valid, input_errors = (
        validate_manual_input(
            manual_actor,
            manual_note,
            manual_text,
            policy,
        )
    )

    runner_errors: list[str] = []
    if not isinstance(stage_runners, dict):
        runner_errors.append(
            "Stage Runners는 dict여야 합니다."
        )
        working_runners: dict[str, Any] = {}
    else:
        working_runners = stage_runners

    for name in STAGE_ORDER:
        if not callable(
            working_runners.get(name)
        ):
            runner_errors.append(
                f"{name} Runner가 없습니다."
            )

    runner_valid = not runner_errors
    started_at = datetime.now()
    context = dict(initial_context or {})
    context["manual_actor"] = (
        manual_actor.strip()
        if isinstance(manual_actor, str)
        else ""
    )
    context["manual_note"] = (
        manual_note.strip()
        if isinstance(manual_note, str)
        else ""
    )
    context["manual_text"] = (
        manual_text.strip()
        if isinstance(manual_text, str)
        else ""
    )

    stage_results: dict[str, Any] = {}
    stage_records: list[
        ManualPaperRunStageRecord
    ] = []
    warnings = [
        *policy_errors,
        *input_errors,
        *runner_errors,
    ]
    failed_stage_name: str | None = None

    preflight_valid = bool(
        policy_valid
        and input_valid
        and runner_valid
    )

    if preflight_valid:
        for index, stage_name in enumerate(
            STAGE_ORDER,
            start=1,
        ):
            stage_started_at = datetime.now()
            result: Any = None
            error_message: str | None = None

            try:
                result = working_runners[
                    stage_name
                ](dict(context))
                (
                    type_valid,
                    status_valid,
                    safety_valid,
                    stage_warnings,
                ) = validate_stage_result(
                    stage_name,
                    result,
                )
            except Exception as error:
                type_valid = False
                status_valid = False
                safety_valid = True
                stage_warnings = [
                    f"{stage_name} Runner 실행 실패: {error}"
                ]
                error_message = str(error)

            stage_completed_at = datetime.now()
            stage_all_valid = bool(
                type_valid
                and status_valid
                and safety_valid
            )

            status_field = (
                stage_specifications()[
                    stage_name
                ][2]
            )
            record = ManualPaperRunStageRecord(
                stage_name=stage_name,
                stage_order=index,
                expected_version=(
                    stage_specifications()[
                        stage_name
                    ][1]
                ),
                started_at=(
                    stage_started_at.isoformat()
                ),
                completed_at=(
                    stage_completed_at.isoformat()
                ),
                duration_seconds=round(
                    (
                        stage_completed_at
                        - stage_started_at
                    ).total_seconds(),
                    6,
                ),
                called=True,
                completed=stage_all_valid,
                result_type=(
                    type(result).__name__
                    if result is not None
                    else None
                ),
                result_version=getattr(
                    result,
                    "version",
                    None,
                ),
                result_status=getattr(
                    result,
                    status_field,
                    None,
                ),
                type_checks_passed=type_valid,
                status_checks_passed=status_valid,
                safety_checks_passed=safety_valid,
                all_checks_passed=(
                    stage_all_valid
                ),
                execution_blocked=getattr(
                    result,
                    "execution_blocked",
                    True,
                ),
                broker_api_called=getattr(
                    result,
                    "broker_api_called",
                    False,
                ),
                broker_order_created=getattr(
                    result,
                    "broker_order_created",
                    False,
                ),
                live_order_created=getattr(
                    result,
                    "live_order_created",
                    False,
                ),
                live_execution_authorized=(
                    getattr(
                        result,
                        "live_execution_authorized",
                        False,
                    )
                ),
                error_message=error_message,
                warnings=tuple(stage_warnings),
            )
            stage_records.append(record)
            warnings.extend(stage_warnings)

            if result is not None:
                stage_results[
                    stage_name
                ] = result
                context[
                    f"{stage_name.lower()}_result"
                ] = result

            if not stage_all_valid:
                failed_stage_name = stage_name

                for skipped_index, skipped_name in enumerate(
                    STAGE_ORDER[index:],
                    start=index + 1,
                ):
                    stage_records.append(
                        create_skipped_stage_record(
                            skipped_name,
                            skipped_index,
                            (
                                f"{stage_name} 실패로 "
                                f"{skipped_name} 호출을 건너뛰었습니다."
                            ),
                        )
                    )
                break
    else:
        failed_stage_name = "PREFLIGHT"
        for index, stage_name in enumerate(
            STAGE_ORDER,
            start=1,
        ):
            stage_records.append(
                create_skipped_stage_record(
                    stage_name,
                    index,
                    "Orchestrator 사전검사 실패로 호출하지 않았습니다.",
                )
            )

    completed_at = datetime.now()
    called_stage_count = sum(
        record.called
        for record in stage_records
    )
    completed_stage_count = sum(
        record.completed
        for record in stage_records
    )
    stage_checks_passed = bool(
        completed_stage_count == len(STAGE_ORDER)
    )
    sequence_checks_passed = bool(
        [
            record.stage_name
            for record in stage_records
        ]
        == list(STAGE_ORDER)
        and [
            record.stage_order
            for record in stage_records
        ]
        == list(
            range(1, len(STAGE_ORDER) + 1)
        )
    )
    safety_checks_passed = all(
        record.execution_blocked
        and not any(
            (
                record.broker_api_called,
                record.broker_order_created,
                record.live_order_created,
                record.live_execution_authorized,
            )
        )
        for record in stage_records
    )

    all_checks_passed = bool(
        preflight_valid
        and stage_checks_passed
        and sequence_checks_passed
        and safety_checks_passed
    )

    if all_checks_passed:
        status = "COMPLETED"
        status_label = (
            "End-to-End Manual Paper Run 완료"
        )
        reasons = [
            "V11.0부터 V11.5까지 모든 Stage가 순서대로 완료되었습니다.",
            "각 Stage의 상태와 실거래 안전 조건이 검증되었습니다.",
        ]
        next_actions = [
            "Final Report의 Risk Status와 Action을 확인합니다.",
            "다음 실행에는 새로운 Schedule과 수동 승인을 사용합니다.",
        ]
    elif not preflight_valid:
        status = "FAILED"
        status_label = (
            "Orchestrator 사전검사 실패"
        )
        reasons = [
            "수동 입력, Policy 또는 Stage Runner 구성에 실패했습니다."
        ]
        next_actions = [
            "Warnings에서 사전검사 실패 원인을 확인합니다.",
            "Runner 구성을 수정한 후 수동으로 다시 시작합니다.",
        ]
    else:
        status = "BLOCKED"
        status_label = (
            "Stage 실패로 End-to-End 실행 중단"
        )
        reasons = [
            (
                f"{failed_stage_name} Stage 실패 후 "
                "나머지 Stage를 호출하지 않았습니다."
            )
        ]
        next_actions = [
            "실패한 Stage Result와 Warnings를 확인합니다.",
            "실패를 우회해 이후 Stage만 따로 실행하지 않습니다.",
        ]

    warnings.extend(
        [
            "V11.6은 사용자가 시작하는 Paper 전용 Orchestrator입니다.",
            "Broker API, 실제 주문 및 Live Execution은 허용하지 않습니다.",
        ]
    )

    result = ManualPaperRunOrchestratorResult(
        version="V11.6",
        created_at=datetime.now().isoformat(),
        orchestration_id=str(uuid.uuid4()),
        orchestrator_status=status,
        orchestrator_status_label=status_label,
        manual_actor=context["manual_actor"],
        manual_note=context["manual_note"],
        manual_text=context["manual_text"],
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        total_duration_seconds=round(
            (
                completed_at - started_at
            ).total_seconds(),
            6,
        ),
        total_stage_count=len(STAGE_ORDER),
        called_stage_count=called_stage_count,
        completed_stage_count=(
            completed_stage_count
        ),
        failed_stage_name=failed_stage_name,
        policy_checks_passed=policy_valid,
        input_checks_passed=input_valid,
        runner_checks_passed=runner_valid,
        stage_checks_passed=stage_checks_passed,
        sequence_checks_passed=(
            sequence_checks_passed
        ),
        safety_checks_passed=(
            safety_checks_passed
        ),
        all_checks_passed=all_checks_passed,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        orchestrator_policy=policy,
        stage_records=tuple(stage_records),
        stage_results=stage_results,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_manual_paper_run_orchestrator(
        result
    )
    return result


def save_manual_paper_run_orchestrator(
    result: ManualPaperRunOrchestratorResult,
) -> tuple[Path, Path]:
    directory = (
        MANUAL_PAPER_RUN_ORCHESTRATOR_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"manual_paper_run_orchestrator_{timestamp}.json"
    )
    latest_path = directory / (
        "manual_paper_run_orchestrator_latest.json"
    )
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_manual_paper_run_orchestrator() -> (
    dict[str, Any]
):
    path = (
        MANUAL_PAPER_RUN_ORCHESTRATOR_OUTPUT_DIRECTORY
        / "manual_paper_run_orchestrator_latest.json"
    )
    return read_json_file(path)


def print_manual_paper_run_orchestrator(
    result: ManualPaperRunOrchestratorResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V11.6 END-TO-END MANUAL PAPER RUN ORCHESTRATOR")
    print("=" * line_length)
    print(
        f"Orchestrator status           : "
        f"{result.orchestrator_status}"
    )
    print(
        f"Orchestrator status label     : "
        f"{result.orchestrator_status_label}"
    )
    print(
        f"Manual actor                  : "
        f"{result.manual_actor}"
    )
    print(
        f"Called stages                 : "
        f"{result.called_stage_count}/{result.total_stage_count}"
    )
    print(
        f"Completed stages              : "
        f"{result.completed_stage_count}/{result.total_stage_count}"
    )
    print(
        f"Failed stage                  : "
        f"{result.failed_stage_name}"
    )
    print()
    print("STAGES")
    print("-" * line_length)
    for record in result.stage_records:
        print(
            f"{record.stage_order}. "
            f"{record.stage_name:<28} "
            f"Called={str(record.called):<5} "
            f"Completed={str(record.completed):<5} "
            f"Status={record.result_status}"
        )
    print()
    print("VALIDATION")
    print("-" * line_length)
    print(
        f"Policy checks passed          : "
        f"{result.policy_checks_passed}"
    )
    print(
        f"Input checks passed           : "
        f"{result.input_checks_passed}"
    )
    print(
        f"Runner checks passed          : "
        f"{result.runner_checks_passed}"
    )
    print(
        f"Stage checks passed           : "
        f"{result.stage_checks_passed}"
    )
    print(
        f"Sequence checks passed        : "
        f"{result.sequence_checks_passed}"
    )
    print(
        f"Safety checks passed          : "
        f"{result.safety_checks_passed}"
    )
    print(
        f"All checks passed             : "
        f"{result.all_checks_passed}"
    )
    print()
    print("EXECUTION SAFETY")
    print("-" * line_length)
    print(
        f"Automatic execution authorized: "
        f"{result.automatic_execution_authorized}"
    )
    print(
        f"Execution blocked             : "
        f"{result.execution_blocked}"
    )
    print(
        f"Broker API called             : "
        f"{result.broker_api_called}"
    )
    print(
        f"Broker order created          : "
        f"{result.broker_order_created}"
    )
    print(
        f"Live order created            : "
        f"{result.live_order_created}"
    )
    print(
        f"Live execution authorized     : "
        f"{result.live_execution_authorized}"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * line_length)
        for reason in result.reasons:
            print(f"- {reason}")

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * line_length)
        for warning in result.warnings:
            print(f"- {warning}")

    print()
    print("FILES")
    print("-" * line_length)
    print(
        f"Report file                   : "
        f"{result.report_path or 'Not saved yet'}"
    )
    print(
        f"Latest file                   : "
        f"{result.latest_path or 'Not saved yet'}"
    )
    print("=" * line_length)
    print(
        "주의: V11.6은 수동 Paper 흐름만 조정하며 "
        "Broker 주문을 허용하지 않습니다."
    )
