import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_trading_run_ledger import (
    PaperTradingRunLedgerEntry,
    PaperTradingRunLedgerState,
    load_latest_ledger_state,
    validate_ledger_state,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_TRADING_SESSION_SUMMARY_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_trading_session_summary"
)


VALID_SESSION_STATUSES = {
    "READY",
    "WARNING",
    "NOT_READY",
    "FAILED",
}


VALID_SESSION_ACTIONS = {
    "CONTINUE",
    "REVIEW",
    "PAUSE",
    "BLOCK",
}


SESSION_ACTION_SCORES = {
    "CONTINUE": 0,
    "REVIEW": 1,
    "PAUSE": 2,
    "BLOCK": 3,
}


@dataclass(frozen=True)
class PaperTradingSessionSummaryPolicy:
    """
    V10.8 Paper Trading Session Summary 정책입니다.

    누적 Ledger의 실행 품질과 안정성을 평가합니다.
    """

    minimum_run_count: int = 5
    minimum_completed_run_rate_percent: float = 60.0
    minimum_completed_symbol_rate_percent: float = 60.0

    warning_failed_run_rate_percent: float = 10.0
    pause_failed_run_rate_percent: float = 25.0
    block_failed_run_rate_percent: float = 50.0

    warning_blocked_run_rate_percent: float = 20.0
    pause_blocked_run_rate_percent: float = 40.0
    block_blocked_run_rate_percent: float = 70.0

    warning_consecutive_failed_runs: int = 1
    pause_consecutive_failed_runs: int = 2
    block_consecutive_failed_runs: int = 3

    warning_cumulative_equity_loss: float = 100.0
    pause_cumulative_equity_loss: float = 500.0
    block_cumulative_equity_loss: float = 1_000.0

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperTradingSessionRuleResult:
    """
    한 가지 Session 운영 규칙의 검사 결과입니다.
    """

    rule_name: str
    rule_label: str

    observed_value: float
    observed_unit: str

    warning_threshold: float | None
    pause_threshold: float | None
    block_threshold: float | None

    session_action: str
    session_action_label: str

    triggered: bool
    checks_passed: bool

    reason: str
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperTradingSessionSummaryResult:
    """
    V10.8 Paper Trading Session Summary 전체 결과입니다.
    """

    version: str
    created_at: str

    session_summary_id: str
    source_ledger_id: str

    session_status: str
    session_status_label: str
    session_action: str
    session_action_label: str

    first_run_at: str | None
    latest_run_at: str | None

    total_run_count: int
    daily_run_count: int
    batch_run_count: int

    completed_run_count: int
    partial_run_count: int
    blocked_run_count: int
    failed_run_count: int

    completed_run_rate_percent: float
    partial_run_rate_percent: float
    blocked_run_rate_percent: float
    failed_run_rate_percent: float

    requested_symbol_count: int
    completed_symbol_count: int
    blocked_symbol_count: int
    failed_symbol_count: int
    skipped_symbol_count: int
    completed_symbol_rate_percent: float

    consecutive_failed_run_count: int
    consecutive_blocked_run_count: int

    cumulative_equity_change: float
    profitable_run_count: int
    losing_run_count: int
    unchanged_run_count: int

    triggered_rule_count: int
    review_rule_count: int
    pause_rule_count: int
    block_rule_count: int

    minimum_history_met: bool
    source_checks_passed: bool
    policy_checks_passed: bool
    rule_checks_passed: bool
    all_checks_passed: bool

    paper_trading_continue_allowed: bool
    manual_review_required: bool
    paper_trading_paused: bool
    paper_trading_blocked: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    summary_policy: (
        PaperTradingSessionSummaryPolicy
    )
    rule_results: dict[
        str,
        PaperTradingSessionRuleResult,
    ]

    reasons: list[str] = field(
        default_factory=list
    )
    warnings: list[str] = field(
        default_factory=list
    )
    next_actions: list[str] = field(
        default_factory=list
    )

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["summary_policy"] = (
            self.summary_policy.to_dict()
        )
        payload["rule_results"] = {
            name: result.to_dict()
            for name, result
            in self.rule_results.items()
        }
        return payload


def is_valid_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False

    try:
        number = float(value)
    except (TypeError, ValueError):
        return False

    return (
        number == number
        and number
        not in {
            float("inf"),
            float("-inf"),
        }
    )


def round_money(value: float) -> float:
    return round(float(value), 2)


def round_percent(value: float) -> float:
    return round(float(value), 4)


def safe_rate(
    numerator: int | float,
    denominator: int | float,
) -> float:
    """
    0으로 나누지 않고 비율을 계산합니다.
    """

    if denominator <= 0:
        return 0.0

    return round_percent(
        float(numerator)
        / float(denominator)
        * 100.0
    )


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    with temporary_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    temporary_path.replace(file_path)


def read_json_file(
    file_path: Path,
) -> dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON 파일이 없습니다: {file_path}"
        )

    if file_path.stat().st_size <= 0:
        raise RuntimeError(
            f"JSON 파일이 비어 있습니다: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise RuntimeError(
            "JSON 최상위 데이터가 Dictionary가 아닙니다."
        )

    return payload


def validate_ascending_thresholds(
    warning_value: float,
    pause_value: float,
    block_value: float,
    field_label: str,
) -> list[str]:
    errors: list[str] = []
    values = (
        warning_value,
        pause_value,
        block_value,
    )

    if not all(
        is_valid_number(value)
        for value in values
    ):
        return [
            f"{field_label} 기준에 유효하지 않은 숫자가 있습니다."
        ]

    if any(
        float(value) < 0
        for value in values
    ):
        errors.append(
            f"{field_label} 기준은 음수일 수 없습니다."
        )

    if not (
        warning_value
        < pause_value
        < block_value
    ):
        errors.append(
            (
                f"{field_label} 기준은 "
                "Warning < Pause < Block 순서여야 합니다."
            )
        )

    return errors


def validate_session_summary_policy(
    policy: PaperTradingSessionSummaryPolicy,
) -> tuple[bool, list[str]]:
    """
    V10.8 Summary Policy를 검사합니다.
    """

    if not isinstance(
        policy,
        PaperTradingSessionSummaryPolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "PaperTradingSessionSummaryPolicy "
                    "형식이 아닙니다."
                )
            ],
        )

    errors: list[str] = []

    if (
        not isinstance(
            policy.minimum_run_count,
            int,
        )
        or policy.minimum_run_count <= 0
    ):
        errors.append(
            "Minimum Run Count는 0보다 큰 int여야 합니다."
        )

    rate_fields = {
        "minimum_completed_run_rate_percent": (
            policy.minimum_completed_run_rate_percent
        ),
        "minimum_completed_symbol_rate_percent": (
            policy.minimum_completed_symbol_rate_percent
        ),
    }

    for field_name, value in rate_fields.items():
        if not is_valid_number(value):
            errors.append(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )
        elif not 0 <= float(value) <= 100:
            errors.append(
                f"{field_name}는 0~100 범위여야 합니다."
            )

    errors.extend(
        validate_ascending_thresholds(
            policy.warning_failed_run_rate_percent,
            policy.pause_failed_run_rate_percent,
            policy.block_failed_run_rate_percent,
            "Failed Run Rate",
        )
    )
    errors.extend(
        validate_ascending_thresholds(
            policy.warning_blocked_run_rate_percent,
            policy.pause_blocked_run_rate_percent,
            policy.block_blocked_run_rate_percent,
            "Blocked Run Rate",
        )
    )
    errors.extend(
        validate_ascending_thresholds(
            policy.warning_consecutive_failed_runs,
            policy.pause_consecutive_failed_runs,
            policy.block_consecutive_failed_runs,
            "Consecutive Failed Runs",
        )
    )
    errors.extend(
        validate_ascending_thresholds(
            policy.warning_cumulative_equity_loss,
            policy.pause_cumulative_equity_loss,
            policy.block_cumulative_equity_loss,
            "Cumulative Equity Loss",
        )
    )

    count_fields = (
        policy.warning_consecutive_failed_runs,
        policy.pause_consecutive_failed_runs,
        policy.block_consecutive_failed_runs,
    )

    if not all(
        isinstance(value, int)
        for value in count_fields
    ):
        errors.append(
            "Consecutive Failed Runs 기준은 int여야 합니다."
        )

    if not isinstance(
        policy.paper_only,
        bool,
    ):
        errors.append(
            "paper_only가 bool 형식이 아닙니다."
        )

    if not isinstance(
        policy.live_execution_disabled,
        bool,
    ):
        errors.append(
            "live_execution_disabled가 bool 형식이 아닙니다."
        )

    if not policy.paper_only:
        errors.append(
            "V10.8에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V10.8에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (not errors, errors)


def session_action_label(
    action: str,
) -> str:
    labels = {
        "CONTINUE": "Paper Trading 계속",
        "REVIEW": "수동 검토 필요",
        "PAUSE": "Paper Trading 일시정지",
        "BLOCK": "Paper Trading 차단",
    }
    return labels[action]


def determine_upper_limit_action(
    observed_value: float,
    warning_threshold: float,
    pause_threshold: float,
    block_threshold: float,
) -> str:
    if observed_value >= block_threshold:
        return "BLOCK"

    if observed_value >= pause_threshold:
        return "PAUSE"

    if observed_value >= warning_threshold:
        return "REVIEW"

    return "CONTINUE"


def create_upper_limit_rule(
    rule_name: str,
    rule_label: str,
    observed_value: float,
    observed_unit: str,
    warning_threshold: float,
    pause_threshold: float,
    block_threshold: float,
) -> PaperTradingSessionRuleResult:
    action = determine_upper_limit_action(
        observed_value=observed_value,
        warning_threshold=warning_threshold,
        pause_threshold=pause_threshold,
        block_threshold=block_threshold,
    )

    triggered = action != "CONTINUE"

    return PaperTradingSessionRuleResult(
        rule_name=rule_name,
        rule_label=rule_label,
        observed_value=round_percent(
            observed_value
        ),
        observed_unit=observed_unit,
        warning_threshold=round_percent(
            warning_threshold
        ),
        pause_threshold=round_percent(
            pause_threshold
        ),
        block_threshold=round_percent(
            block_threshold
        ),
        session_action=action,
        session_action_label=(
            session_action_label(action)
        ),
        triggered=triggered,
        checks_passed=True,
        reason=(
            f"{rule_label} 관측값은 "
            f"{observed_value:.4f}{observed_unit}입니다."
        ),
        warning=(
            f"{rule_label}이 {action} 기준에 도달했습니다."
            if triggered
            else None
        ),
    )


def create_minimum_rule(
    rule_name: str,
    rule_label: str,
    observed_value: float,
    observed_unit: str,
    minimum_threshold: float,
    insufficient_action: str,
) -> PaperTradingSessionRuleResult:
    triggered = (
        observed_value < minimum_threshold
    )
    action = (
        insufficient_action
        if triggered
        else "CONTINUE"
    )

    return PaperTradingSessionRuleResult(
        rule_name=rule_name,
        rule_label=rule_label,
        observed_value=round_percent(
            observed_value
        ),
        observed_unit=observed_unit,
        warning_threshold=round_percent(
            minimum_threshold
        ),
        pause_threshold=None,
        block_threshold=None,
        session_action=action,
        session_action_label=(
            session_action_label(action)
        ),
        triggered=triggered,
        checks_passed=True,
        reason=(
            f"{rule_label} 관측값은 "
            f"{observed_value:.4f}{observed_unit}입니다."
        ),
        warning=(
            (
                f"{rule_label}이 최소 기준 "
                f"{minimum_threshold:.4f}{observed_unit}보다 낮습니다."
            )
            if triggered
            else None
        ),
    )


def select_strongest_action(
    rules: dict[
        str,
        PaperTradingSessionRuleResult,
    ],
) -> str:
    if not rules:
        return "BLOCK"

    return max(
        (
            rule.session_action
            for rule in rules.values()
        ),
        key=lambda action: (
            SESSION_ACTION_SCORES[action]
        ),
    )


def calculate_consecutive_status_count(
    entries: tuple[
        PaperTradingRunLedgerEntry,
        ...,
    ],
    target_status: str,
) -> int:
    """
    최신 Entry부터 동일 상태가 연속된 횟수를 계산합니다.
    """

    count = 0

    for entry in reversed(entries):
        if entry.run_status == target_status:
            count += 1
        else:
            break

    return count


def run_paper_trading_session_summary(
    ledger_state: (
        PaperTradingRunLedgerState
        | None
    ) = None,
    summary_policy: (
        PaperTradingSessionSummaryPolicy
        | None
    ) = None,
) -> PaperTradingSessionSummaryResult:
    """
    V10.7 Ledger를 분석해 Paper Trading Session 상태를 요약합니다.

    실제 Broker API 또는 주문은 수행하지 않습니다.
    """

    policy = (
        summary_policy
        if summary_policy is not None
        else PaperTradingSessionSummaryPolicy()
    )

    policy_valid, policy_errors = (
        validate_session_summary_policy(
            policy
        )
    )

    source_load_errors: list[str] = []

    if ledger_state is None:
        try:
            working_state = (
                load_latest_ledger_state()
            )
        except Exception as error:
            source_load_errors.append(
                f"최신 Ledger 로드 실패: {error}"
            )
            working_state = None
    else:
        working_state = ledger_state

    if working_state is not None:
        source_valid, source_errors = (
            validate_ledger_state(
                working_state
            )
        )
    else:
        source_valid = False
        source_errors = [
            "Ledger State가 없습니다."
        ]

    source_errors.extend(
        source_load_errors
    )

    entries = (
        working_state.entries
        if working_state is not None
        else ()
    )

    total_run_count = len(entries)
    daily_run_count = sum(
        entry.run_type == "DAILY_GATED"
        for entry in entries
    )
    batch_run_count = sum(
        entry.run_type == "BATCH_GATED"
        for entry in entries
    )

    completed_run_count = sum(
        entry.run_status == "COMPLETED"
        for entry in entries
    )
    partial_run_count = sum(
        entry.run_status == "PARTIAL"
        for entry in entries
    )
    blocked_run_count = sum(
        entry.run_status == "BLOCKED"
        for entry in entries
    )
    failed_run_count = sum(
        entry.run_status == "FAILED"
        for entry in entries
    )

    completed_run_rate_percent = safe_rate(
        completed_run_count,
        total_run_count,
    )
    partial_run_rate_percent = safe_rate(
        partial_run_count,
        total_run_count,
    )
    blocked_run_rate_percent = safe_rate(
        blocked_run_count,
        total_run_count,
    )
    failed_run_rate_percent = safe_rate(
        failed_run_count,
        total_run_count,
    )

    requested_symbol_count = sum(
        entry.requested_symbol_count
        for entry in entries
    )
    completed_symbol_count = sum(
        entry.completed_symbol_count
        for entry in entries
    )
    blocked_symbol_count = sum(
        entry.blocked_symbol_count
        for entry in entries
    )
    failed_symbol_count = sum(
        entry.failed_symbol_count
        for entry in entries
    )
    skipped_symbol_count = sum(
        entry.skipped_symbol_count
        for entry in entries
    )
    completed_symbol_rate_percent = (
        safe_rate(
            completed_symbol_count,
            requested_symbol_count,
        )
    )

    consecutive_failed_run_count = (
        calculate_consecutive_status_count(
            entries,
            "FAILED",
        )
    )
    consecutive_blocked_run_count = (
        calculate_consecutive_status_count(
            entries,
            "BLOCKED",
        )
    )

    cumulative_equity_change = round_money(
        sum(
            entry.equity_change
            for entry in entries
        )
    )

    profitable_run_count = sum(
        entry.equity_change > 0
        for entry in entries
    )
    losing_run_count = sum(
        entry.equity_change < 0
        for entry in entries
    )
    unchanged_run_count = sum(
        entry.equity_change == 0
        for entry in entries
    )

    first_run_at = (
        entries[0].source_created_at
        if entries
        else None
    )
    latest_run_at = (
        entries[-1].source_created_at
        if entries
        else None
    )

    minimum_history_met = (
        total_run_count
        >= policy.minimum_run_count
    )

    rules: dict[
        str,
        PaperTradingSessionRuleResult,
    ] = {}

    if policy_valid and source_valid:
        rules["MINIMUM_HISTORY"] = (
            create_minimum_rule(
                rule_name="MINIMUM_HISTORY",
                rule_label="최소 실행 이력",
                observed_value=float(
                    total_run_count
                ),
                observed_unit="회",
                minimum_threshold=float(
                    policy.minimum_run_count
                ),
                insufficient_action="REVIEW",
            )
        )
        rules["COMPLETED_RUN_RATE"] = (
            create_minimum_rule(
                rule_name="COMPLETED_RUN_RATE",
                rule_label="완료 Run 비율",
                observed_value=(
                    completed_run_rate_percent
                ),
                observed_unit="%",
                minimum_threshold=(
                    policy
                    .minimum_completed_run_rate_percent
                ),
                insufficient_action="REVIEW",
            )
        )
        rules["COMPLETED_SYMBOL_RATE"] = (
            create_minimum_rule(
                rule_name="COMPLETED_SYMBOL_RATE",
                rule_label="완료 종목 비율",
                observed_value=(
                    completed_symbol_rate_percent
                ),
                observed_unit="%",
                minimum_threshold=(
                    policy
                    .minimum_completed_symbol_rate_percent
                ),
                insufficient_action="REVIEW",
            )
        )
        rules["FAILED_RUN_RATE"] = (
            create_upper_limit_rule(
                rule_name="FAILED_RUN_RATE",
                rule_label="실패 Run 비율",
                observed_value=(
                    failed_run_rate_percent
                ),
                observed_unit="%",
                warning_threshold=(
                    policy
                    .warning_failed_run_rate_percent
                ),
                pause_threshold=(
                    policy
                    .pause_failed_run_rate_percent
                ),
                block_threshold=(
                    policy
                    .block_failed_run_rate_percent
                ),
            )
        )
        rules["BLOCKED_RUN_RATE"] = (
            create_upper_limit_rule(
                rule_name="BLOCKED_RUN_RATE",
                rule_label="차단 Run 비율",
                observed_value=(
                    blocked_run_rate_percent
                ),
                observed_unit="%",
                warning_threshold=(
                    policy
                    .warning_blocked_run_rate_percent
                ),
                pause_threshold=(
                    policy
                    .pause_blocked_run_rate_percent
                ),
                block_threshold=(
                    policy
                    .block_blocked_run_rate_percent
                ),
            )
        )
        rules["CONSECUTIVE_FAILED_RUNS"] = (
            create_upper_limit_rule(
                rule_name=(
                    "CONSECUTIVE_FAILED_RUNS"
                ),
                rule_label="연속 실패 Run",
                observed_value=float(
                    consecutive_failed_run_count
                ),
                observed_unit="회",
                warning_threshold=float(
                    policy
                    .warning_consecutive_failed_runs
                ),
                pause_threshold=float(
                    policy
                    .pause_consecutive_failed_runs
                ),
                block_threshold=float(
                    policy
                    .block_consecutive_failed_runs
                ),
            )
        )
        rules["CUMULATIVE_EQUITY_LOSS"] = (
            create_upper_limit_rule(
                rule_name=(
                    "CUMULATIVE_EQUITY_LOSS"
                ),
                rule_label="누적 Equity 손실",
                observed_value=max(
                    -cumulative_equity_change,
                    0.0,
                ),
                observed_unit="$",
                warning_threshold=(
                    policy
                    .warning_cumulative_equity_loss
                ),
                pause_threshold=(
                    policy
                    .pause_cumulative_equity_loss
                ),
                block_threshold=(
                    policy
                    .block_cumulative_equity_loss
                ),
            )
        )

    rule_checks_passed = bool(
        rules
        and all(
            rule.checks_passed
            for rule in rules.values()
        )
    )

    if (
        not policy_valid
        or not source_valid
        or not rule_checks_passed
    ):
        session_action = "BLOCK"
        session_status = "FAILED"
        session_status_label = (
            "Session Summary 검사 실패"
        )
    else:
        session_action = (
            select_strongest_action(
                rules
            )
        )

        if session_action == "CONTINUE":
            session_status = "READY"
            session_status_label = (
                "Paper Trading Session 정상"
            )
        elif session_action == "REVIEW":
            session_status = "WARNING"
            session_status_label = (
                "Paper Trading Session 수동 검토 필요"
            )
        else:
            session_status = "NOT_READY"
            session_status_label = (
                "Paper Trading Session 계속 실행 불가"
            )

    triggered_rule_count = sum(
        rule.triggered
        for rule in rules.values()
    )
    review_rule_count = sum(
        rule.session_action == "REVIEW"
        for rule in rules.values()
    )
    pause_rule_count = sum(
        rule.session_action == "PAUSE"
        for rule in rules.values()
    )
    block_rule_count = sum(
        rule.session_action == "BLOCK"
        for rule in rules.values()
    )

    paper_trading_continue_allowed = (
        session_action == "CONTINUE"
    )
    manual_review_required = (
        session_action == "REVIEW"
    )
    paper_trading_paused = (
        session_action == "PAUSE"
    )
    paper_trading_blocked = (
        session_action == "BLOCK"
    )

    all_checks_passed = bool(
        policy_valid
        and source_valid
        and rule_checks_passed
        and session_status
        in {
            "READY",
            "WARNING",
            "NOT_READY",
        }
    )

    reasons = [
        (
            f"총 Paper Trading Run은 "
            f"{total_run_count}회입니다."
        ),
        (
            f"완료 Run 비율은 "
            f"{completed_run_rate_percent:.4f}%입니다."
        ),
        (
            f"완료 종목 비율은 "
            f"{completed_symbol_rate_percent:.4f}%입니다."
        ),
        (
            f"누적 Equity 변화는 "
            f"${cumulative_equity_change:,.2f}입니다."
        ),
        (
            f"최종 Session Action은 "
            f"{session_action}입니다."
        ),
    ]

    warnings: list[str] = []
    warnings.extend(policy_errors)
    warnings.extend(source_errors)
    warnings.extend(
        [
            rule.warning
            for rule in rules.values()
            if rule.warning
        ]
    )
    warnings.extend(
        [
            (
                "V10.8은 연구용 Paper Trading "
                "Session Summary입니다."
            ),
            (
                "과거 Paper Trading 결과는 미래 성과를 "
                "보장하지 않습니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 "
                "Live Execution은 모두 차단됩니다."
            ),
        ]
    )

    if session_action == "CONTINUE":
        next_actions = [
            "현재 Policy 범위에서 Paper Trading을 계속합니다.",
            "새 Run Ledger Entry가 추가되면 Summary를 다시 생성합니다.",
        ]
    elif session_action == "REVIEW":
        next_actions = [
            "Triggered Rule과 부족한 실행 이력을 확인합니다.",
            "수동 검토 후 Paper Trading 계속 여부를 결정합니다.",
        ]
    elif session_action == "PAUSE":
        next_actions = [
            "신규 Paper Trading을 일시정지합니다.",
            "실패 Run과 손실 원인을 검토합니다.",
        ]
    else:
        next_actions = [
            "신규 Paper Trading을 차단합니다.",
            "Ledger 유효성과 Block Rule을 먼저 확인합니다.",
        ]

    result = PaperTradingSessionSummaryResult(
        version="V10.8",
        created_at=datetime.now().isoformat(),
        session_summary_id=str(uuid.uuid4()),
        source_ledger_id=(
            working_state.ledger_id
            if working_state is not None
            else ""
        ),
        session_status=session_status,
        session_status_label=(
            session_status_label
        ),
        session_action=session_action,
        session_action_label=(
            session_action_label(
                session_action
            )
        ),
        first_run_at=first_run_at,
        latest_run_at=latest_run_at,
        total_run_count=total_run_count,
        daily_run_count=daily_run_count,
        batch_run_count=batch_run_count,
        completed_run_count=(
            completed_run_count
        ),
        partial_run_count=partial_run_count,
        blocked_run_count=blocked_run_count,
        failed_run_count=failed_run_count,
        completed_run_rate_percent=(
            completed_run_rate_percent
        ),
        partial_run_rate_percent=(
            partial_run_rate_percent
        ),
        blocked_run_rate_percent=(
            blocked_run_rate_percent
        ),
        failed_run_rate_percent=(
            failed_run_rate_percent
        ),
        requested_symbol_count=(
            requested_symbol_count
        ),
        completed_symbol_count=(
            completed_symbol_count
        ),
        blocked_symbol_count=(
            blocked_symbol_count
        ),
        failed_symbol_count=(
            failed_symbol_count
        ),
        skipped_symbol_count=(
            skipped_symbol_count
        ),
        completed_symbol_rate_percent=(
            completed_symbol_rate_percent
        ),
        consecutive_failed_run_count=(
            consecutive_failed_run_count
        ),
        consecutive_blocked_run_count=(
            consecutive_blocked_run_count
        ),
        cumulative_equity_change=(
            cumulative_equity_change
        ),
        profitable_run_count=(
            profitable_run_count
        ),
        losing_run_count=losing_run_count,
        unchanged_run_count=(
            unchanged_run_count
        ),
        triggered_rule_count=(
            triggered_rule_count
        ),
        review_rule_count=review_rule_count,
        pause_rule_count=pause_rule_count,
        block_rule_count=block_rule_count,
        minimum_history_met=(
            minimum_history_met
        ),
        source_checks_passed=source_valid,
        policy_checks_passed=policy_valid,
        rule_checks_passed=(
            rule_checks_passed
        ),
        all_checks_passed=(
            all_checks_passed
        ),
        paper_trading_continue_allowed=(
            paper_trading_continue_allowed
        ),
        manual_review_required=(
            manual_review_required
        ),
        paper_trading_paused=(
            paper_trading_paused
        ),
        paper_trading_blocked=(
            paper_trading_blocked
        ),
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        summary_policy=policy,
        rule_results=rules,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_trading_session_summary(
        result
    )

    return result


def save_paper_trading_session_summary(
    result: PaperTradingSessionSummaryResult,
) -> tuple[Path, Path]:
    """
    V10.8 Report와 Latest JSON을 저장합니다.
    """

    PAPER_TRADING_SESSION_SUMMARY_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    report_path = (
        PAPER_TRADING_SESSION_SUMMARY_OUTPUT_DIRECTORY
        / (
            "paper_trading_session_summary_"
            f"{timestamp}.json"
        )
    )
    latest_path = (
        PAPER_TRADING_SESSION_SUMMARY_OUTPUT_DIRECTORY
        / (
            "paper_trading_session_summary_"
            "latest.json"
        )
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)

    payload = result.to_dict()

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)

    return (report_path, latest_path)


def load_latest_paper_trading_session_summary() -> (
    dict[str, Any]
):
    """
    최신 V10.8 Summary JSON을 읽습니다.
    """

    latest_path = (
        PAPER_TRADING_SESSION_SUMMARY_OUTPUT_DIRECTORY
        / (
            "paper_trading_session_summary_"
            "latest.json"
        )
    )

    return read_json_file(latest_path)


def print_paper_trading_session_summary(
    result: PaperTradingSessionSummaryResult,
) -> None:
    """
    V10.8 Summary를 터미널에 출력합니다.
    """

    line_length = 140

    print()
    print("=" * line_length)
    print(
        "V10.8 PAPER TRADING SESSION SUMMARY"
    )
    print("=" * line_length)

    print(
        f"Session status                 : "
        f"{result.session_status}"
    )
    print(
        f"Session status label           : "
        f"{result.session_status_label}"
    )
    print(
        f"Session action                 : "
        f"{result.session_action}"
    )
    print(
        f"Session action label           : "
        f"{result.session_action_label}"
    )
    print(
        f"Session summary ID             : "
        f"{result.session_summary_id}"
    )
    print(
        f"Source ledger ID               : "
        f"{result.source_ledger_id}"
    )

    print()
    print("RUN SUMMARY")
    print("-" * line_length)

    print(
        f"Total runs                     : "
        f"{result.total_run_count}"
    )
    print(
        f"Daily runs                     : "
        f"{result.daily_run_count}"
    )
    print(
        f"Batch runs                     : "
        f"{result.batch_run_count}"
    )
    print(
        f"Completed runs                 : "
        f"{result.completed_run_count}"
    )
    print(
        f"Partial runs                   : "
        f"{result.partial_run_count}"
    )
    print(
        f"Blocked runs                   : "
        f"{result.blocked_run_count}"
    )
    print(
        f"Failed runs                    : "
        f"{result.failed_run_count}"
    )
    print(
        f"Completed run rate             : "
        f"{result.completed_run_rate_percent:.4f}%"
    )
    print(
        f"Failed run rate                : "
        f"{result.failed_run_rate_percent:.4f}%"
    )
    print(
        f"Blocked run rate               : "
        f"{result.blocked_run_rate_percent:.4f}%"
    )

    print()
    print("SYMBOL SUMMARY")
    print("-" * line_length)

    print(
        f"Requested symbols              : "
        f"{result.requested_symbol_count}"
    )
    print(
        f"Completed symbols              : "
        f"{result.completed_symbol_count}"
    )
    print(
        f"Failed symbols                 : "
        f"{result.failed_symbol_count}"
    )
    print(
        f"Skipped symbols                : "
        f"{result.skipped_symbol_count}"
    )
    print(
        f"Completed symbol rate          : "
        f"{result.completed_symbol_rate_percent:.4f}%"
    )

    print()
    print("EQUITY AND STREAKS")
    print("-" * line_length)

    print(
        f"Cumulative equity change       : "
        f"${result.cumulative_equity_change:,.2f}"
    )
    print(
        f"Profitable runs                : "
        f"{result.profitable_run_count}"
    )
    print(
        f"Losing runs                    : "
        f"{result.losing_run_count}"
    )
    print(
        f"Consecutive failed runs        : "
        f"{result.consecutive_failed_run_count}"
    )
    print(
        f"Consecutive blocked runs       : "
        f"{result.consecutive_blocked_run_count}"
    )

    print()
    print("RULE RESULTS")
    print("-" * line_length)

    for rule in result.rule_results.values():
        print(
            f"{rule.rule_name:<32}: "
            f"{rule.session_action:<8} "
            f"| Value={rule.observed_value:.4f}"
            f"{rule.observed_unit}"
        )

    print()
    print("VALIDATION")
    print("-" * line_length)

    print(
        f"Minimum history met            : "
        f"{result.minimum_history_met}"
    )
    print(
        f"Source checks passed           : "
        f"{result.source_checks_passed}"
    )
    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )
    print(
        f"Rule checks passed             : "
        f"{result.rule_checks_passed}"
    )
    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * line_length)

    print(
        f"Execution blocked              : "
        f"{result.execution_blocked}"
    )
    print(
        f"Broker API called              : "
        f"{result.broker_api_called}"
    )
    print(
        f"Broker order created           : "
        f"{result.broker_order_created}"
    )
    print(
        f"Live order created             : "
        f"{result.live_order_created}"
    )
    print(
        f"Live execution authorized      : "
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

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * line_length)

        for action in result.next_actions:
            print(f"- {action}")

    print()
    print("FILES")
    print("-" * line_length)

    print(
        f"Report file                    : "
        f"{result.report_path or 'Not saved yet'}"
    )
    print(
        f"Latest file                    : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * line_length)
    print(
        "주의: V10.8은 연구용 Paper Trading Summary이며 "
        "실제 Broker 주문을 수행하지 않습니다."
    )
