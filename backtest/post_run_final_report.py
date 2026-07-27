import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.approved_paper_run_launcher import (
    ApprovedPaperRunLauncherResult,
)
from backtest.approved_paper_run_ledger_integration import (
    ApprovedRunLedgerIntegrationResult,
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

POST_RUN_FINAL_REPORT_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "post_run_final_report"
)

VALID_REPORT_STATUSES = {
    "COMPLETED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PostRunFinalReportPolicy:
    """
    V11.5 Post-Run Final Report 정책입니다.

    V11.0부터 V11.4까지 결과를 변경하지 않고 최종 감사 보고서로
    묶습니다.
    """

    require_approved: bool = True
    require_completed_launch: bool = True
    require_linked_ledger: bool = True
    require_refreshed_session: bool = True
    require_refreshed_performance_risk: bool = True

    require_lineage_match: bool = True
    require_chronological_order: bool = True
    require_execution_safety: bool = True

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PostRunStageSummary:
    stage_version: str
    stage_name: str
    stage_status: str
    stage_created_at: str
    primary_id: str | None
    checks_passed: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass
class PostRunFinalReportResult:
    version: str
    created_at: str
    report_id: str

    report_status: str
    report_status_label: str

    approval_id: str | None
    plan_id: str | None
    launch_id: str | None
    integration_id: str | None
    ledger_update_id: str | None
    ledger_id: str | None
    session_refresh_id: str | None
    session_summary_id: str | None
    performance_risk_refresh_id: str | None
    performance_id: str | None
    risk_monitor_id: str | None

    session_status: str | None
    session_action: str | None
    performance_status: str | None
    current_equity: float | None
    cumulative_return_percent: float | None
    maximum_drawdown_percent: float | None
    risk_status: str | None
    risk_action: str | None

    policy_checks_passed: bool
    approval_checks_passed: bool
    launch_checks_passed: bool
    integration_checks_passed: bool
    session_checks_passed: bool
    performance_risk_checks_passed: bool
    lineage_checks_passed: bool
    chronology_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    report_policy: PostRunFinalReportPolicy
    stage_summaries: tuple[
        PostRunStageSummary,
        ...,
    ]

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["report_policy"] = (
            self.report_policy.to_dict()
        )
        payload["stage_summaries"] = [
            stage.to_dict()
            for stage in self.stage_summaries
        ]
        return payload


def parse_datetime(
    value: str | datetime,
    field_label: str,
) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise TypeError(
            f"{field_label}은 datetime 또는 ISO 문자열이어야 합니다."
        )
    try:
        return datetime.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError(
            f"{field_label} 형식이 올바르지 않습니다: {value}"
        ) from error


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


def validate_report_policy(
    policy: PostRunFinalReportPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        PostRunFinalReportPolicy,
    ):
        return (
            False,
            ["Final Report Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    for name, value in {
        "require_approved": policy.require_approved,
        "require_completed_launch": (
            policy.require_completed_launch
        ),
        "require_linked_ledger": (
            policy.require_linked_ledger
        ),
        "require_refreshed_session": (
            policy.require_refreshed_session
        ),
        "require_refreshed_performance_risk": (
            policy.require_refreshed_performance_risk
        ),
        "require_lineage_match": (
            policy.require_lineage_match
        ),
        "require_chronological_order": (
            policy.require_chronological_order
        ),
        "require_execution_safety": (
            policy.require_execution_safety
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }.items():
        if value is not True:
            errors.append(
                f"{name}는 V11.5에서 True여야 합니다."
            )
    return (not errors, errors)


def validate_stage(
    result: Any,
    expected_type: type,
    expected_version: str,
    expected_status: str,
    status_field: str,
) -> tuple[bool, list[str]]:
    if not isinstance(result, expected_type):
        return (
            False,
            [
                (
                    f"{expected_version} Result 형식이 "
                    "올바르지 않습니다."
                )
            ],
        )

    errors: list[str] = []
    if getattr(result, "version", None) != (
        expected_version
    ):
        errors.append(
            f"Version이 {expected_version}이 아닙니다."
        )
    if getattr(result, status_field, None) != (
        expected_status
    ):
        errors.append(
            (
                f"{status_field}가 "
                f"{expected_status}가 아닙니다."
            )
        )
    if getattr(
        result,
        "all_checks_passed",
        False,
    ) is not True:
        errors.append(
            "All Checks가 실패했습니다."
        )
    if getattr(
        result,
        "execution_blocked",
        None,
    ) is not True:
        errors.append(
            "Execution 차단 상태가 올바르지 않습니다."
        )
    if any(
        (
            getattr(
                result,
                "broker_api_called",
                False,
            ),
            getattr(
                result,
                "broker_order_created",
                False,
            ),
            getattr(
                result,
                "live_order_created",
                False,
            ),
            getattr(
                result,
                "live_execution_authorized",
                False,
            ),
        )
    ):
        errors.append(
            "Stage Result에 실거래 신호가 있습니다."
        )
    return (not errors, errors)


def validate_lineage(
    approval: ScheduledPaperRunApprovalResult,
    launch: ApprovedPaperRunLauncherResult,
    integration: ApprovedRunLedgerIntegrationResult,
    session: PostRunSessionRefreshResult,
    performance_risk: PostRunPerformanceRiskResult,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if approval.approval_id != launch.approval_id:
        errors.append(
            "Approval과 Launch의 Approval ID가 다릅니다."
        )
    if approval.plan_id != launch.plan_id:
        errors.append(
            "Approval과 Launch의 Plan ID가 다릅니다."
        )
    if launch.launch_id != integration.launch_id:
        errors.append(
            "Launch와 Integration의 Launch ID가 다릅니다."
        )
    if launch.approval_id != integration.approval_id:
        errors.append(
            "Launch와 Integration의 Approval ID가 다릅니다."
        )
    if launch.plan_id != integration.plan_id:
        errors.append(
            "Launch와 Integration의 Plan ID가 다릅니다."
        )
    if (
        integration.integration_id
        != session.integration_id
    ):
        errors.append(
            "Integration과 Session의 Integration ID가 다릅니다."
        )
    if integration.ledger_id != session.ledger_id:
        errors.append(
            "Integration과 Session의 Ledger ID가 다릅니다."
        )
    if (
        session.refresh_id
        != performance_risk.session_refresh_id
    ):
        errors.append(
            "Session과 Performance Risk의 Refresh ID가 다릅니다."
        )
    if (
        performance_risk.performance_result
        is not None
        and performance_risk.risk_result is not None
        and performance_risk.risk_result.source_performance_id
        != performance_risk.performance_result.performance_id
    ):
        errors.append(
            "Risk Source Performance ID가 다릅니다."
        )
    return (not errors, errors)


def validate_chronology(
    results: tuple[Any, ...],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    parsed_times: list[datetime] = []

    for result in results:
        try:
            parsed_times.append(
                parse_datetime(
                    result.created_at,
                    f"{result.version} Created At",
                )
            )
        except (TypeError, ValueError) as error:
            errors.append(str(error))

    if errors:
        return (False, errors)

    timezone_flags = {
        value.tzinfo is not None
        for value in parsed_times
    }
    if len(timezone_flags) != 1:
        return (
            False,
            ["Stage Created At의 Timezone 형식이 다릅니다."],
        )

    for previous, current in zip(
        parsed_times,
        parsed_times[1:],
    ):
        if current < previous:
            errors.append(
                "Stage 생성 순서가 시간 순서와 다릅니다."
            )
            break

    return (not errors, errors)


def build_stage_summary(
    version: str,
    name: str,
    status: str,
    result: Any,
    primary_id: str | None,
    checks_passed: bool,
    warnings: list[str],
) -> PostRunStageSummary:
    return PostRunStageSummary(
        stage_version=version,
        stage_name=name,
        stage_status=status,
        stage_created_at=result.created_at,
        primary_id=primary_id,
        checks_passed=checks_passed,
        execution_blocked=(
            result.execution_blocked
        ),
        broker_api_called=(
            result.broker_api_called
        ),
        broker_order_created=(
            result.broker_order_created
        ),
        live_order_created=(
            result.live_order_created
        ),
        live_execution_authorized=(
            result.live_execution_authorized
        ),
        warnings=tuple(warnings),
    )


def run_post_run_final_report(
    approval_result: ScheduledPaperRunApprovalResult,
    launch_result: ApprovedPaperRunLauncherResult,
    integration_result: ApprovedRunLedgerIntegrationResult,
    session_refresh_result: PostRunSessionRefreshResult,
    performance_risk_result: PostRunPerformanceRiskResult,
    report_policy: (
        PostRunFinalReportPolicy
        | None
    ) = None,
) -> PostRunFinalReportResult:
    """
    V11.0~V11.4의 결과를 최종 감사 보고서로 정리합니다.

    이전 Stage를 재실행하거나 Broker API를 호출하지 않습니다.
    """

    policy = (
        report_policy
        if report_policy is not None
        else PostRunFinalReportPolicy()
    )
    policy_valid, policy_errors = (
        validate_report_policy(policy)
    )

    approval_valid, approval_errors = (
        validate_stage(
            approval_result,
            ScheduledPaperRunApprovalResult,
            "V11.0",
            "APPROVED",
            "approval_status",
        )
    )
    launch_valid, launch_errors = (
        validate_stage(
            launch_result,
            ApprovedPaperRunLauncherResult,
            "V11.1",
            "COMPLETED",
            "launch_status",
        )
    )
    integration_valid, integration_errors = (
        validate_stage(
            integration_result,
            ApprovedRunLedgerIntegrationResult,
            "V11.2",
            "LINKED",
            "integration_status",
        )
    )
    session_valid, session_errors = (
        validate_stage(
            session_refresh_result,
            PostRunSessionRefreshResult,
            "V11.3",
            "REFRESHED",
            "refresh_status",
        )
    )
    performance_risk_valid, pr_errors = (
        validate_stage(
            performance_risk_result,
            PostRunPerformanceRiskResult,
            "V11.4",
            "REFRESHED",
            "refresh_status",
        )
    )

    lineage_valid, lineage_errors = (
        validate_lineage(
            approval_result,
            launch_result,
            integration_result,
            session_refresh_result,
            performance_risk_result,
        )
    )
    chronology_valid, chronology_errors = (
        validate_chronology(
            (
                approval_result,
                launch_result,
                integration_result,
                session_refresh_result,
                performance_risk_result,
            )
        )
    )

    stage_validities = (
        approval_valid,
        launch_valid,
        integration_valid,
        session_valid,
        performance_risk_valid,
    )
    safety_valid = all(
        getattr(
            result,
            "execution_blocked",
            False,
        )
        and not any(
            (
                result.broker_api_called,
                result.broker_order_created,
                result.live_order_created,
                result.live_execution_authorized,
            )
        )
        for result in (
            approval_result,
            launch_result,
            integration_result,
            session_refresh_result,
            performance_risk_result,
        )
    )

    warnings = [
        *policy_errors,
        *approval_errors,
        *launch_errors,
        *integration_errors,
        *session_errors,
        *pr_errors,
        *lineage_errors,
        *chronology_errors,
    ]
    if not safety_valid:
        warnings.append(
            "하나 이상의 Stage에 실거래 안전 오류가 있습니다."
        )

    complete = bool(
        policy_valid
        and all(stage_validities)
        and lineage_valid
        and chronology_valid
        and safety_valid
    )
    if complete:
        status = "COMPLETED"
        status_label = (
            "Post-Run 전체 처리 및 감사 검증 완료"
        )
        reasons = [
            "V11.0부터 V11.4까지 모든 Stage가 성공적으로 연결되었습니다.",
            "승인, 실행, Ledger, Session, Performance와 Risk가 검증되었습니다.",
        ]
        next_actions = [
            "최종 Risk Status와 Action을 사람이 확인합니다.",
            "다음 Paper Run 전에 새로운 Schedule과 Approval을 생성합니다.",
        ]
    else:
        status = (
            "FAILED"
            if not policy_valid
            else "BLOCKED"
        )
        status_label = (
            "Post-Run 최종 감사 검사 실패"
        )
        reasons = [
            "Stage 상태, ID 연결, 시간 순서 또는 안전 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings에서 실패한 Stage를 확인합니다.",
            "실패 기록을 수정하거나 우회하여 실행하지 않습니다.",
        ]

    stage_summaries = (
        build_stage_summary(
            "V11.0",
            "SCHEDULED_APPROVAL",
            approval_result.approval_status,
            approval_result,
            approval_result.approval_id,
            approval_valid,
            approval_errors,
        ),
        build_stage_summary(
            "V11.1",
            "APPROVED_LAUNCH",
            launch_result.launch_status,
            launch_result,
            launch_result.launch_id,
            launch_valid,
            launch_errors,
        ),
        build_stage_summary(
            "V11.2",
            "LEDGER_INTEGRATION",
            integration_result.integration_status,
            integration_result,
            integration_result.integration_id,
            integration_valid,
            integration_errors,
        ),
        build_stage_summary(
            "V11.3",
            "SESSION_REFRESH",
            session_refresh_result.refresh_status,
            session_refresh_result,
            session_refresh_result.refresh_id,
            session_valid,
            session_errors,
        ),
        build_stage_summary(
            "V11.4",
            "PERFORMANCE_RISK_REFRESH",
            performance_risk_result.refresh_status,
            performance_risk_result,
            performance_risk_result.refresh_id,
            performance_risk_valid,
            pr_errors,
        ),
    )

    performance = (
        performance_risk_result.performance_result
    )
    risk = performance_risk_result.risk_result
    summary = session_refresh_result.session_summary

    warnings.extend(
        [
            "V11.5는 Post-Run 최종 감사 보고서입니다.",
            "Broker API, 실제 주문 및 Live Execution은 호출하지 않습니다.",
        ]
    )

    result = PostRunFinalReportResult(
        version="V11.5",
        created_at=datetime.now().isoformat(),
        report_id=str(uuid.uuid4()),
        report_status=status,
        report_status_label=status_label,
        approval_id=approval_result.approval_id,
        plan_id=approval_result.plan_id,
        launch_id=launch_result.launch_id,
        integration_id=(
            integration_result.integration_id
        ),
        ledger_update_id=(
            integration_result.ledger_update_id
        ),
        ledger_id=integration_result.ledger_id,
        session_refresh_id=(
            session_refresh_result.refresh_id
        ),
        session_summary_id=(
            session_refresh_result.session_summary_id
        ),
        performance_risk_refresh_id=(
            performance_risk_result.refresh_id
        ),
        performance_id=(
            performance.performance_id
            if performance is not None
            else None
        ),
        risk_monitor_id=(
            risk.monitor_id
            if risk is not None
            else None
        ),
        session_status=(
            summary.session_status
            if summary is not None
            else None
        ),
        session_action=(
            summary.session_action
            if summary is not None
            else None
        ),
        performance_status=(
            performance.performance_status
            if performance is not None
            else None
        ),
        current_equity=(
            performance.current_equity
            if performance is not None
            else None
        ),
        cumulative_return_percent=(
            performance.cumulative_return_percent
            if performance is not None
            else None
        ),
        maximum_drawdown_percent=(
            performance.maximum_drawdown_percent
            if performance is not None
            else None
        ),
        risk_status=(
            risk.risk_status
            if risk is not None
            else None
        ),
        risk_action=(
            risk.risk_action
            if risk is not None
            else None
        ),
        policy_checks_passed=policy_valid,
        approval_checks_passed=approval_valid,
        launch_checks_passed=launch_valid,
        integration_checks_passed=(
            integration_valid
        ),
        session_checks_passed=session_valid,
        performance_risk_checks_passed=(
            performance_risk_valid
        ),
        lineage_checks_passed=lineage_valid,
        chronology_checks_passed=(
            chronology_valid
        ),
        safety_checks_passed=safety_valid,
        all_checks_passed=complete,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        report_policy=policy,
        stage_summaries=stage_summaries,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_post_run_final_report(result)
    return result


def save_post_run_final_report(
    result: PostRunFinalReportResult,
) -> tuple[Path, Path]:
    directory = (
        POST_RUN_FINAL_REPORT_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"post_run_final_report_{timestamp}.json"
    )
    latest_path = directory / (
        "post_run_final_report_latest.json"
    )
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_post_run_final_report() -> (
    dict[str, Any]
):
    path = (
        POST_RUN_FINAL_REPORT_OUTPUT_DIRECTORY
        / "post_run_final_report_latest.json"
    )
    return read_json_file(path)


def print_post_run_final_report(
    result: PostRunFinalReportResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V11.5 POST-RUN FINAL REPORT")
    print("=" * line_length)
    print(
        f"Report status                 : "
        f"{result.report_status}"
    )
    print(
        f"Report status label           : "
        f"{result.report_status_label}"
    )
    print(
        f"Plan ID                       : "
        f"{result.plan_id}"
    )
    print(
        f"Approval ID                   : "
        f"{result.approval_id}"
    )
    print(
        f"Launch ID                     : "
        f"{result.launch_id}"
    )
    print(
        f"Ledger ID                     : "
        f"{result.ledger_id}"
    )
    print(
        f"Session status/action         : "
        f"{result.session_status}/{result.session_action}"
    )
    print(
        f"Performance status            : "
        f"{result.performance_status}"
    )
    print(
        f"Current equity                : "
        f"{result.current_equity}"
    )
    print(
        f"Cumulative return             : "
        f"{result.cumulative_return_percent}%"
    )
    print(
        f"Maximum drawdown              : "
        f"{result.maximum_drawdown_percent}%"
    )
    print(
        f"Risk status/action            : "
        f"{result.risk_status}/{result.risk_action}"
    )
    print()
    print("STAGE SUMMARY")
    print("-" * line_length)
    for stage in result.stage_summaries:
        print(
            f"{stage.stage_version:<8} "
            f"{stage.stage_name:<28} "
            f"{stage.stage_status:<14} "
            f"Checks={stage.checks_passed}"
        )
    print()
    print("VALIDATION")
    print("-" * line_length)
    print(
        f"Lineage checks passed         : "
        f"{result.lineage_checks_passed}"
    )
    print(
        f"Chronology checks passed      : "
        f"{result.chronology_checks_passed}"
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
        "주의: V11.5는 최종 감사 보고서만 생성하며 "
        "Broker 주문을 실행하지 않습니다."
    )
