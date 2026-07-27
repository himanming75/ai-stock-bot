import json
import math
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_portfolio_performance_tracker import (
    PaperPerformanceSnapshot,
    PaperPortfolioPerformanceResult,
    load_latest_performance_result,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_RISK_MONITOR_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_risk_monitor"
)


VALID_RISK_STATUSES = {
    "SAFE",
    "WARNING",
    "PAUSED",
    "BLOCKED",
    "FAILED",
}


VALID_RISK_ACTIONS = {
    "ALLOW",
    "WARNING",
    "PAUSE",
    "BLOCK",
}


RISK_LEVEL_SCORES = {
    "ALLOW": 0,
    "WARNING": 1,
    "PAUSE": 2,
    "BLOCK": 3,
}


@dataclass(frozen=True)
class PaperTradingRiskMonitorPolicy:
    """
    V10.4 Paper Trading Risk Monitor 정책입니다.

    Paper Portfolio 성과를 이용해 새 Paper Trading의
    허용, 경고, 일시정지 또는 차단을 판정합니다.
    """

    drawdown_warning_percent: float = 5.0
    drawdown_pause_percent: float = 10.0
    drawdown_block_percent: float = 20.0

    period_loss_warning_percent: float = 2.0
    period_loss_pause_percent: float = 5.0
    period_loss_block_percent: float = 10.0

    cumulative_loss_warning_percent: float = 5.0
    cumulative_loss_pause_percent: float = 10.0
    cumulative_loss_block_percent: float = 20.0

    consecutive_loss_warning_count: int = 2
    consecutive_loss_pause_count: int = 3
    consecutive_loss_block_count: int = 5

    minimum_cash_balance: float = 100.0
    minimum_total_equity: float = 1_000.0
    maximum_commission_to_equity_percent: float = 2.0

    minimum_performance_periods: int = 1
    allow_warning_trades: bool = True
    require_valid_performance: bool = True

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperRiskRuleResult:
    """
    한 가지 Risk Rule의 검사 결과입니다.
    """

    rule_name: str
    rule_label: str

    observed_value: float
    observed_unit: str

    warning_threshold: float | None
    pause_threshold: float | None
    block_threshold: float | None

    risk_action: str
    risk_action_label: str

    triggered: bool
    checks_passed: bool

    reason: str
    warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperTradingRiskMonitorResult:
    """
    V10.4 Paper Trading Risk Monitor 전체 결과입니다.
    """

    version: str
    created_at: str

    monitor_id: str
    portfolio_id: str
    source_performance_id: str
    source_performance_file: str | None

    risk_status: str
    risk_status_label: str

    risk_action: str
    risk_action_label: str

    current_equity: float
    cash_balance: float
    total_market_value: float

    period_profit_loss: float
    period_return_percent: float

    cumulative_profit_loss: float
    cumulative_return_percent: float

    current_drawdown_amount: float
    current_drawdown_percent: float
    maximum_drawdown_percent: float

    consecutive_loss_count: int
    performance_period_count: int

    total_commission: float
    commission_to_equity_percent: float

    triggered_rule_count: int
    warning_rule_count: int
    pause_rule_count: int
    block_rule_count: int

    source_loaded: bool
    source_valid: bool
    policy_checks_passed: bool
    history_checks_passed: bool
    rule_checks_passed: bool
    all_checks_passed: bool

    paper_trading_allowed: bool
    paper_trading_warning: bool
    paper_trading_paused: bool
    paper_trading_blocked: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    monitor_policy: PaperTradingRiskMonitorPolicy
    rule_results: dict[str, PaperRiskRuleResult]

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["monitor_policy"] = (
            self.monitor_policy.to_dict()
        )

        payload["rule_results"] = {
            name: result.to_dict()
            for name, result
            in self.rule_results.items()
        }

        return payload


def is_valid_number(value: Any) -> bool:
    """
    bool을 제외한 유한 숫자인지 검사합니다.
    """

    if isinstance(value, bool):
        return False

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return False

    return math.isfinite(numeric_value)


def round_money(value: float) -> float:
    return round(float(value), 2)


def round_percent(value: float) -> float:
    return round(float(value), 4)


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    임시 파일을 이용해 JSON을 안전하게 저장합니다.
    """

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
    """
    JSON 파일을 읽습니다.
    """

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
    """
    Warning < Pause < Block 순서인지 검사합니다.
    """

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
        errors.append(
            f"{field_label} 기준에 유효하지 않은 숫자가 있습니다."
        )
        return errors

    if any(float(value) < 0 for value in values):
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


def validate_risk_monitor_policy(
    policy: PaperTradingRiskMonitorPolicy,
) -> tuple[bool, list[str]]:
    """
    V10.4 Risk Monitor Policy를 검사합니다.
    """

    if not isinstance(
        policy,
        PaperTradingRiskMonitorPolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "PaperTradingRiskMonitorPolicy "
                    "형식이 아닙니다."
                )
            ],
        )

    errors: list[str] = []

    errors.extend(
        validate_ascending_thresholds(
            policy.drawdown_warning_percent,
            policy.drawdown_pause_percent,
            policy.drawdown_block_percent,
            "Drawdown Percent",
        )
    )

    errors.extend(
        validate_ascending_thresholds(
            policy.period_loss_warning_percent,
            policy.period_loss_pause_percent,
            policy.period_loss_block_percent,
            "Period Loss Percent",
        )
    )

    errors.extend(
        validate_ascending_thresholds(
            policy.cumulative_loss_warning_percent,
            policy.cumulative_loss_pause_percent,
            policy.cumulative_loss_block_percent,
            "Cumulative Loss Percent",
        )
    )

    loss_counts = (
        policy.consecutive_loss_warning_count,
        policy.consecutive_loss_pause_count,
        policy.consecutive_loss_block_count,
    )

    if not all(
        isinstance(value, int)
        for value in loss_counts
    ):
        errors.append(
            "Consecutive Loss Count 기준은 int여야 합니다."
        )
    elif not all(
        value > 0
        for value in loss_counts
    ):
        errors.append(
            "Consecutive Loss Count 기준은 0보다 커야 합니다."
        )
    elif not (
        policy.consecutive_loss_warning_count
        < policy.consecutive_loss_pause_count
        < policy.consecutive_loss_block_count
    ):
        errors.append(
            "Consecutive Loss 기준은 Warning < Pause < Block "
            "순서여야 합니다."
        )

    numeric_minimums = {
        "minimum_cash_balance": (
            policy.minimum_cash_balance
        ),
        "minimum_total_equity": (
            policy.minimum_total_equity
        ),
        "maximum_commission_to_equity_percent": (
            policy.maximum_commission_to_equity_percent
        ),
    }

    for field_name, value in numeric_minimums.items():
        if not is_valid_number(value):
            errors.append(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )
        elif float(value) < 0:
            errors.append(
                f"{field_name}는 음수일 수 없습니다."
            )

    if (
        not isinstance(
            policy.minimum_performance_periods,
            int,
        )
        or policy.minimum_performance_periods < 0
    ):
        errors.append(
            "Minimum Performance Periods는 0 이상의 int여야 합니다."
        )

    boolean_fields = {
        "allow_warning_trades": (
            policy.allow_warning_trades
        ),
        "require_valid_performance": (
            policy.require_valid_performance
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(value, bool):
            errors.append(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    if not policy.paper_only:
        errors.append(
            "V10.4에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V10.4에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (not errors, errors)


def performance_result_to_dict(
    performance_result: (
        PaperPortfolioPerformanceResult
        | dict[str, Any]
    ),
) -> dict[str, Any]:
    """
    V10.1 Performance Result를 Dictionary로 정규화합니다.
    """

    if isinstance(
        performance_result,
        PaperPortfolioPerformanceResult,
    ):
        return performance_result.to_dict()

    if isinstance(performance_result, dict):
        return dict(performance_result)

    raise TypeError(
        "Performance Result는 "
        "PaperPortfolioPerformanceResult 또는 "
        "Dictionary 형식이어야 합니다."
    )


def validate_performance_payload(
    payload: dict[str, Any],
    policy: PaperTradingRiskMonitorPolicy,
) -> tuple[bool, list[str]]:
    """
    V10.1 Performance Payload를 검사합니다.
    """

    errors: list[str] = []

    if payload.get("version") != "V10.1":
        errors.append(
            "Performance 버전이 V10.1이 아닙니다."
        )

    text_fields = {
        "performance_id": payload.get(
            "performance_id"
        ),
        "portfolio_id": payload.get(
            "portfolio_id"
        ),
        "source_valuation_id": payload.get(
            "source_valuation_id"
        ),
        "performance_status": payload.get(
            "performance_status"
        ),
    }

    for field_name, value in text_fields.items():
        if not isinstance(value, str) or not value.strip():
            errors.append(
                f"{field_name}가 비어 있습니다."
            )

    numeric_fields = {
        "current_equity": payload.get(
            "current_equity"
        ),
        "period_profit_loss": payload.get(
            "period_profit_loss"
        ),
        "period_return_percent": payload.get(
            "period_return_percent"
        ),
        "cumulative_profit_loss": payload.get(
            "cumulative_profit_loss"
        ),
        "cumulative_return_percent": payload.get(
            "cumulative_return_percent"
        ),
        "current_drawdown_amount": payload.get(
            "current_drawdown_amount"
        ),
        "current_drawdown_percent": payload.get(
            "current_drawdown_percent"
        ),
        "maximum_drawdown_percent": payload.get(
            "maximum_drawdown_percent"
        ),
        "total_commission": payload.get(
            "total_commission"
        ),
    }

    for field_name, value in numeric_fields.items():
        if not is_valid_number(value):
            errors.append(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )

    if not isinstance(
        payload.get("performance_period_count"),
        int,
    ):
        errors.append(
            "performance_period_count가 int가 아닙니다."
        )

    history = payload.get(
        "performance_history"
    )

    if not isinstance(history, list):
        errors.append(
            "performance_history가 List가 아닙니다."
        )

    if policy.require_valid_performance:
        if payload.get("performance_status") not in {
            "TRACKED",
            "FIRST_SNAPSHOT",
            "NO_CHANGE",
        }:
            errors.append(
                "Risk Monitor가 사용할 수 없는 Performance Status입니다."
            )

        if not bool(payload.get("all_checks_passed")):
            errors.append(
                "V10.1 Performance All Checks가 실패했습니다."
            )

    return (not errors, errors)


def extract_latest_portfolio_values(
    payload: dict[str, Any],
) -> tuple[float, float]:
    """
    최신 Snapshot에서 Cash Balance와 Market Value를 가져옵니다.
    """

    latest_snapshot = payload.get(
        "latest_snapshot"
    )

    if not isinstance(latest_snapshot, dict):
        history = payload.get(
            "performance_history",
            [],
        )

        if isinstance(history, list) and history:
            latest_snapshot = history[-1]

    if not isinstance(latest_snapshot, dict):
        return (0.0, 0.0)

    cash_balance = latest_snapshot.get(
        "cash_balance",
        0.0,
    )
    market_value = latest_snapshot.get(
        "total_market_value",
        0.0,
    )

    return (
        round_money(
            cash_balance
            if is_valid_number(cash_balance)
            else 0.0
        ),
        round_money(
            market_value
            if is_valid_number(market_value)
            else 0.0
        ),
    )


def calculate_consecutive_loss_count(
    history: list[dict[str, Any]]
    | list[PaperPerformanceSnapshot],
) -> tuple[int, list[str]]:
    """
    History 끝에서부터 연속 손실 기간 수를 계산합니다.
    """

    errors: list[str] = []

    if not isinstance(history, list):
        return (
            0,
            ["Performance History가 List가 아닙니다."],
        )

    consecutive_loss_count = 0

    for item in reversed(history):
        if isinstance(
            item,
            PaperPerformanceSnapshot,
        ):
            period_profit_loss = (
                item.period_profit_loss
            )
        elif isinstance(item, dict):
            period_profit_loss = item.get(
                "period_profit_loss"
            )
        else:
            errors.append(
                "History Item 형식이 올바르지 않습니다."
            )
            break

        if not is_valid_number(period_profit_loss):
            errors.append(
                "History Period Profit/Loss가 유효하지 않습니다."
            )
            break

        if float(period_profit_loss) < 0:
            consecutive_loss_count += 1
        else:
            break

    return (
        consecutive_loss_count,
        errors,
    )


def determine_upper_limit_action(
    observed_value: float,
    warning_threshold: float,
    pause_threshold: float,
    block_threshold: float,
) -> str:
    """
    값이 클수록 위험한 Rule의 Action을 결정합니다.
    """

    if observed_value >= block_threshold:
        return "BLOCK"

    if observed_value >= pause_threshold:
        return "PAUSE"

    if observed_value >= warning_threshold:
        return "WARNING"

    return "ALLOW"


def action_label(action: str) -> str:
    labels = {
        "ALLOW": "정상 범위",
        "WARNING": "위험 경고",
        "PAUSE": "신규 Paper Trading 일시정지",
        "BLOCK": "신규 Paper Trading 차단",
    }

    return labels[action]


def create_upper_limit_rule(
    rule_name: str,
    rule_label: str,
    observed_value: float,
    observed_unit: str,
    warning_threshold: float,
    pause_threshold: float,
    block_threshold: float,
) -> PaperRiskRuleResult:
    """
    값이 커질수록 위험한 Rule 결과를 생성합니다.
    """

    action = determine_upper_limit_action(
        observed_value=observed_value,
        warning_threshold=warning_threshold,
        pause_threshold=pause_threshold,
        block_threshold=block_threshold,
    )

    triggered = action != "ALLOW"

    reason = (
        f"{rule_label} 관측값은 "
        f"{observed_value:.4f}{observed_unit}입니다."
    )

    warning = (
        (
            f"{rule_label}이 {action} 기준에 "
            "도달했습니다."
        )
        if triggered
        else None
    )

    return PaperRiskRuleResult(
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
        risk_action=action,
        risk_action_label=action_label(action),
        triggered=triggered,
        checks_passed=True,
        reason=reason,
        warning=warning,
    )


def create_lower_limit_rule(
    rule_name: str,
    rule_label: str,
    observed_value: float,
    observed_unit: str,
    block_threshold: float,
) -> PaperRiskRuleResult:
    """
    값이 기준보다 낮으면 차단하는 Rule을 생성합니다.
    """

    action = (
        "BLOCK"
        if observed_value < block_threshold
        else "ALLOW"
    )

    triggered = action == "BLOCK"

    reason = (
        f"{rule_label} 관측값은 "
        f"{observed_value:.2f}{observed_unit}입니다."
    )

    warning = (
        (
            f"{rule_label}이 최소 기준 "
            f"{block_threshold:.2f}{observed_unit}보다 낮습니다."
        )
        if triggered
        else None
    )

    return PaperRiskRuleResult(
        rule_name=rule_name,
        rule_label=rule_label,
        observed_value=round_money(
            observed_value
        ),
        observed_unit=observed_unit,
        warning_threshold=None,
        pause_threshold=None,
        block_threshold=round_money(
            block_threshold
        ),
        risk_action=action,
        risk_action_label=action_label(action),
        triggered=triggered,
        checks_passed=True,
        reason=reason,
        warning=warning,
    )


def select_strongest_action(
    rule_results: dict[str, PaperRiskRuleResult],
) -> str:
    """
    모든 Rule 중 가장 강한 Action을 선택합니다.
    """

    if not rule_results:
        return "BLOCK"

    return max(
        (
            result.risk_action
            for result in rule_results.values()
        ),
        key=lambda action: RISK_LEVEL_SCORES[
            action
        ],
    )


def run_paper_trading_risk_monitor(
    performance_result: (
        PaperPortfolioPerformanceResult
        | dict[str, Any]
        | None
    ) = None,
    monitor_policy: (
        PaperTradingRiskMonitorPolicy
        | None
    ) = None,
) -> PaperTradingRiskMonitorResult:
    """
    V10.1 Performance를 이용해 V10.4 Risk Monitor를 실행합니다.

    실제 Broker API 또는 실제 주문은 수행하지 않습니다.
    """

    policy = (
        monitor_policy
        if monitor_policy is not None
        else PaperTradingRiskMonitorPolicy()
    )

    policy_valid, policy_errors = (
        validate_risk_monitor_policy(policy)
    )

    source_performance_file: str | None = None
    source_loaded = False
    source_load_errors: list[str] = []

    if performance_result is None:
        source_performance_file = str(
            PROJECT_ROOT
            / "output"
            / "trading_engine"
            / "paper_portfolio_performance"
            / "paper_portfolio_performance_latest.json"
        )

        try:
            performance_result = (
                load_latest_performance_result()
            )
            source_loaded = True
        except Exception as error:
            source_load_errors.append(
                f"최신 Performance 로드 실패: {error}"
            )
            performance_result = {}
    else:
        source_loaded = True

        if isinstance(
            performance_result,
            PaperPortfolioPerformanceResult,
        ):
            source_performance_file = (
                performance_result.latest_path
                or performance_result.report_path
            )

    performance_payload = (
        performance_result_to_dict(
            performance_result
        )
    )

    source_valid, source_errors = (
        validate_performance_payload(
            payload=performance_payload,
            policy=policy,
        )
    )

    source_errors.extend(
        source_load_errors
    )

    history = performance_payload.get(
        "performance_history",
        [],
    )

    (
        consecutive_loss_count,
        history_errors,
    ) = calculate_consecutive_loss_count(
        history
        if isinstance(history, list)
        else []
    )

    history_checks_passed = not history_errors

    current_equity = float(
        performance_payload.get(
            "current_equity",
            0.0,
        )
        if is_valid_number(
            performance_payload.get(
                "current_equity"
            )
        )
        else 0.0
    )

    (
        cash_balance,
        total_market_value,
    ) = extract_latest_portfolio_values(
        performance_payload
    )

    period_profit_loss = float(
        performance_payload.get(
            "period_profit_loss",
            0.0,
        )
        if is_valid_number(
            performance_payload.get(
                "period_profit_loss"
            )
        )
        else 0.0
    )

    period_return_percent = float(
        performance_payload.get(
            "period_return_percent",
            0.0,
        )
        if is_valid_number(
            performance_payload.get(
                "period_return_percent"
            )
        )
        else 0.0
    )

    cumulative_profit_loss = float(
        performance_payload.get(
            "cumulative_profit_loss",
            0.0,
        )
        if is_valid_number(
            performance_payload.get(
                "cumulative_profit_loss"
            )
        )
        else 0.0
    )

    cumulative_return_percent = float(
        performance_payload.get(
            "cumulative_return_percent",
            0.0,
        )
        if is_valid_number(
            performance_payload.get(
                "cumulative_return_percent"
            )
        )
        else 0.0
    )

    current_drawdown_amount = float(
        performance_payload.get(
            "current_drawdown_amount",
            0.0,
        )
        if is_valid_number(
            performance_payload.get(
                "current_drawdown_amount"
            )
        )
        else 0.0
    )

    current_drawdown_percent = float(
        performance_payload.get(
            "current_drawdown_percent",
            0.0,
        )
        if is_valid_number(
            performance_payload.get(
                "current_drawdown_percent"
            )
        )
        else 0.0
    )

    maximum_drawdown_percent = float(
        performance_payload.get(
            "maximum_drawdown_percent",
            0.0,
        )
        if is_valid_number(
            performance_payload.get(
                "maximum_drawdown_percent"
            )
        )
        else 0.0
    )

    total_commission = float(
        performance_payload.get(
            "total_commission",
            0.0,
        )
        if is_valid_number(
            performance_payload.get(
                "total_commission"
            )
        )
        else 0.0
    )

    performance_period_count = int(
        performance_payload.get(
            "performance_period_count",
            0,
        )
        if isinstance(
            performance_payload.get(
                "performance_period_count"
            ),
            int,
        )
        else 0
    )

    if current_equity > 0:
        commission_to_equity_percent = (
            round_percent(
                total_commission
                / current_equity
                * 100.0
            )
        )
    else:
        commission_to_equity_percent = 0.0

    rule_results: dict[
        str,
        PaperRiskRuleResult,
    ] = {}

    if source_valid and policy_valid:
        rule_results["CURRENT_DRAWDOWN"] = (
            create_upper_limit_rule(
                rule_name="CURRENT_DRAWDOWN",
                rule_label="현재 Drawdown",
                observed_value=max(
                    current_drawdown_percent,
                    0.0,
                ),
                observed_unit="%",
                warning_threshold=(
                    policy.drawdown_warning_percent
                ),
                pause_threshold=(
                    policy.drawdown_pause_percent
                ),
                block_threshold=(
                    policy.drawdown_block_percent
                ),
            )
        )

        rule_results["PERIOD_LOSS"] = (
            create_upper_limit_rule(
                rule_name="PERIOD_LOSS",
                rule_label="현재 기간 손실률",
                observed_value=max(
                    -period_return_percent,
                    0.0,
                ),
                observed_unit="%",
                warning_threshold=(
                    policy.period_loss_warning_percent
                ),
                pause_threshold=(
                    policy.period_loss_pause_percent
                ),
                block_threshold=(
                    policy.period_loss_block_percent
                ),
            )
        )

        rule_results["CUMULATIVE_LOSS"] = (
            create_upper_limit_rule(
                rule_name="CUMULATIVE_LOSS",
                rule_label="누적 손실률",
                observed_value=max(
                    -cumulative_return_percent,
                    0.0,
                ),
                observed_unit="%",
                warning_threshold=(
                    policy.cumulative_loss_warning_percent
                ),
                pause_threshold=(
                    policy.cumulative_loss_pause_percent
                ),
                block_threshold=(
                    policy.cumulative_loss_block_percent
                ),
            )
        )

        rule_results["CONSECUTIVE_LOSSES"] = (
            create_upper_limit_rule(
                rule_name="CONSECUTIVE_LOSSES",
                rule_label="연속 손실 기간",
                observed_value=float(
                    consecutive_loss_count
                ),
                observed_unit="회",
                warning_threshold=float(
                    policy
                    .consecutive_loss_warning_count
                ),
                pause_threshold=float(
                    policy
                    .consecutive_loss_pause_count
                ),
                block_threshold=float(
                    policy
                    .consecutive_loss_block_count
                ),
            )
        )

        rule_results["MINIMUM_CASH"] = (
            create_lower_limit_rule(
                rule_name="MINIMUM_CASH",
                rule_label="현금 잔액",
                observed_value=cash_balance,
                observed_unit="$",
                block_threshold=(
                    policy.minimum_cash_balance
                ),
            )
        )

        rule_results["MINIMUM_EQUITY"] = (
            create_lower_limit_rule(
                rule_name="MINIMUM_EQUITY",
                rule_label="총 계좌가치",
                observed_value=current_equity,
                observed_unit="$",
                block_threshold=(
                    policy.minimum_total_equity
                ),
            )
        )

        rule_results["COMMISSION_RATIO"] = (
            create_upper_limit_rule(
                rule_name="COMMISSION_RATIO",
                rule_label="수수료/Equity 비율",
                observed_value=(
                    commission_to_equity_percent
                ),
                observed_unit="%",
                warning_threshold=(
                    policy
                    .maximum_commission_to_equity_percent
                ),
                pause_threshold=(
                    policy
                    .maximum_commission_to_equity_percent
                    * 1.5
                ),
                block_threshold=(
                    policy
                    .maximum_commission_to_equity_percent
                    * 2.0
                ),
            )
        )

        if (
            performance_period_count
            < policy.minimum_performance_periods
        ):
            rule_results[
                "MINIMUM_HISTORY"
            ] = PaperRiskRuleResult(
                rule_name="MINIMUM_HISTORY",
                rule_label="최소 성과 기간",
                observed_value=float(
                    performance_period_count
                ),
                observed_unit="개",
                warning_threshold=float(
                    policy.minimum_performance_periods
                ),
                pause_threshold=None,
                block_threshold=None,
                risk_action="WARNING",
                risk_action_label=(
                    "성과 History 부족 경고"
                ),
                triggered=True,
                checks_passed=True,
                reason=(
                    "성과 기간이 설정된 최소 기간보다 적습니다."
                ),
                warning=(
                    "위험 통계가 충분히 안정적이지 않을 수 있습니다."
                ),
            )

    rule_checks_passed = (
        bool(rule_results)
        and all(
            result.checks_passed
            for result in rule_results.values()
        )
    )

    if (
        not source_loaded
        or not source_valid
        or not policy_valid
        or not history_checks_passed
        or not rule_checks_passed
    ):
        risk_action = "BLOCK"
    else:
        risk_action = select_strongest_action(
            rule_results
        )

    if (
        risk_action == "WARNING"
        and not policy.allow_warning_trades
    ):
        risk_action = "PAUSE"

    if risk_action == "ALLOW":
        risk_status = "SAFE"
        risk_status_label = (
            "Paper Trading 위험 기준 정상"
        )
    elif risk_action == "WARNING":
        risk_status = "WARNING"
        risk_status_label = (
            "Paper Trading 위험 경고"
        )
    elif risk_action == "PAUSE":
        risk_status = "PAUSED"
        risk_status_label = (
            "신규 Paper Trading 일시정지"
        )
    else:
        risk_status = (
            "FAILED"
            if not (
                source_valid
                and policy_valid
                and history_checks_passed
                and rule_checks_passed
            )
            else "BLOCKED"
        )
        risk_status_label = (
            "Risk Monitor 검사 실패"
            if risk_status == "FAILED"
            else "신규 Paper Trading 차단"
        )

    paper_trading_allowed = (
        risk_action == "ALLOW"
        or (
            risk_action == "WARNING"
            and policy.allow_warning_trades
        )
    )

    paper_trading_warning = (
        risk_action == "WARNING"
    )
    paper_trading_paused = (
        risk_action == "PAUSE"
    )
    paper_trading_blocked = (
        risk_action == "BLOCK"
    )

    triggered_rule_count = sum(
        result.triggered
        for result in rule_results.values()
    )
    warning_rule_count = sum(
        result.risk_action == "WARNING"
        for result in rule_results.values()
    )
    pause_rule_count = sum(
        result.risk_action == "PAUSE"
        for result in rule_results.values()
    )
    block_rule_count = sum(
        result.risk_action == "BLOCK"
        for result in rule_results.values()
    )

    reasons = [
        (
            f"최종 Risk Action은 {risk_action}입니다."
        ),
        (
            f"현재 Equity는 ${current_equity:,.2f}입니다."
        ),
        (
            f"현재 Drawdown은 "
            f"{current_drawdown_percent:.4f}%입니다."
        ),
        (
            f"연속 손실 기간은 "
            f"{consecutive_loss_count}회입니다."
        ),
    ]

    warnings: list[str] = []
    warnings.extend(policy_errors)
    warnings.extend(source_errors)
    warnings.extend(history_errors)

    warnings.extend(
        [
            result.warning
            for result in rule_results.values()
            if result.warning
        ]
    )

    warnings.extend(
        [
            (
                "V10.4는 연구용 Paper Trading "
                "Risk Monitor입니다."
            ),
            (
                "Risk Monitor 결과는 미래 손실을 완전히 "
                "방지하지 못합니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 "
                "Live Execution은 모두 차단됩니다."
            ),
        ]
    )

    if risk_action == "ALLOW":
        next_actions = [
            "현재 Risk 기준 내에서 Paper Pipeline을 실행할 수 있습니다.",
            "다음 Performance Snapshot 후 Risk를 다시 평가합니다.",
        ]
    elif risk_action == "WARNING":
        next_actions = [
            "경고 Rule을 확인하고 Position Size 축소를 검토합니다.",
            "다음 Paper 거래 전에 Risk Monitor를 다시 실행합니다.",
        ]
    elif risk_action == "PAUSE":
        next_actions = [
            "신규 Paper Trading을 일시정지합니다.",
            "손실 원인과 Strategy 상태를 검토합니다.",
            "Risk 기준이 회복될 때까지 신규 거래를 만들지 않습니다.",
        ]
    else:
        next_actions = [
            "신규 Paper Trading을 차단합니다.",
            "차단 Rule과 Performance 데이터 유효성을 확인합니다.",
            "수동 검토 후에만 Risk Policy 변경을 검토합니다.",
        ]

    all_checks_passed = (
        source_loaded
        and source_valid
        and policy_valid
        and history_checks_passed
        and rule_checks_passed
        and risk_status
        in {
            "SAFE",
            "WARNING",
            "PAUSED",
            "BLOCKED",
        }
    )

    result = PaperTradingRiskMonitorResult(
        version="V10.4",
        created_at=datetime.now().isoformat(),
        monitor_id=str(uuid.uuid4()),
        portfolio_id=str(
            performance_payload.get(
                "portfolio_id",
                "",
            )
        ),
        source_performance_id=str(
            performance_payload.get(
                "performance_id",
                "",
            )
        ),
        source_performance_file=(
            source_performance_file
        ),
        risk_status=risk_status,
        risk_status_label=risk_status_label,
        risk_action=risk_action,
        risk_action_label=action_label(
            risk_action
        ),
        current_equity=round_money(
            current_equity
        ),
        cash_balance=round_money(
            cash_balance
        ),
        total_market_value=round_money(
            total_market_value
        ),
        period_profit_loss=round_money(
            period_profit_loss
        ),
        period_return_percent=round_percent(
            period_return_percent
        ),
        cumulative_profit_loss=round_money(
            cumulative_profit_loss
        ),
        cumulative_return_percent=(
            round_percent(
                cumulative_return_percent
            )
        ),
        current_drawdown_amount=round_money(
            current_drawdown_amount
        ),
        current_drawdown_percent=round_percent(
            current_drawdown_percent
        ),
        maximum_drawdown_percent=round_percent(
            maximum_drawdown_percent
        ),
        consecutive_loss_count=(
            consecutive_loss_count
        ),
        performance_period_count=(
            performance_period_count
        ),
        total_commission=round_money(
            total_commission
        ),
        commission_to_equity_percent=(
            commission_to_equity_percent
        ),
        triggered_rule_count=(
            triggered_rule_count
        ),
        warning_rule_count=warning_rule_count,
        pause_rule_count=pause_rule_count,
        block_rule_count=block_rule_count,
        source_loaded=source_loaded,
        source_valid=source_valid,
        policy_checks_passed=policy_valid,
        history_checks_passed=(
            history_checks_passed
        ),
        rule_checks_passed=(
            rule_checks_passed
        ),
        all_checks_passed=all_checks_passed,
        paper_trading_allowed=(
            paper_trading_allowed
        ),
        paper_trading_warning=(
            paper_trading_warning
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
        monitor_policy=policy,
        rule_results=rule_results,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_trading_risk_monitor(result)

    return result


def save_paper_trading_risk_monitor(
    result: PaperTradingRiskMonitorResult,
) -> tuple[Path, Path]:
    """
    V10.4 Risk Monitor Report와 Latest JSON을 저장합니다.
    """

    PAPER_RISK_MONITOR_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PAPER_RISK_MONITOR_OUTPUT_DIRECTORY
        / (
            "paper_trading_risk_monitor_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        PAPER_RISK_MONITOR_OUTPUT_DIRECTORY
        / "paper_trading_risk_monitor_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)

    payload = result.to_dict()

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)

    return (report_path, latest_path)


def load_latest_paper_trading_risk_monitor() -> (
    dict[str, Any]
):
    """
    저장된 최신 V10.4 Risk Monitor 결과를 읽습니다.
    """

    latest_path = (
        PAPER_RISK_MONITOR_OUTPUT_DIRECTORY
        / "paper_trading_risk_monitor_latest.json"
    )

    return read_json_file(latest_path)


def print_paper_trading_risk_monitor(
    result: PaperTradingRiskMonitorResult,
) -> None:
    """
    V10.4 Risk Monitor 결과를 출력합니다.
    """

    line_length = 140

    print()
    print("=" * line_length)
    print(
        "V10.4 PAPER TRADING RISK MONITOR"
    )
    print("=" * line_length)

    print(
        f"Risk status                    : "
        f"{result.risk_status}"
    )
    print(
        f"Risk status label              : "
        f"{result.risk_status_label}"
    )
    print(
        f"Risk action                    : "
        f"{result.risk_action}"
    )
    print(
        f"Risk action label              : "
        f"{result.risk_action_label}"
    )
    print(
        f"Monitor ID                     : "
        f"{result.monitor_id}"
    )
    print(
        f"Portfolio ID                   : "
        f"{result.portfolio_id}"
    )

    print()
    print("PORTFOLIO RISK")
    print("-" * line_length)

    print(
        f"Current equity                 : "
        f"${result.current_equity:,.2f}"
    )
    print(
        f"Cash balance                   : "
        f"${result.cash_balance:,.2f}"
    )
    print(
        f"Total market value             : "
        f"${result.total_market_value:,.2f}"
    )
    print(
        f"Period profit/loss             : "
        f"${result.period_profit_loss:,.2f}"
    )
    print(
        f"Period return                  : "
        f"{result.period_return_percent:.4f}%"
    )
    print(
        f"Cumulative profit/loss         : "
        f"${result.cumulative_profit_loss:,.2f}"
    )
    print(
        f"Cumulative return              : "
        f"{result.cumulative_return_percent:.4f}%"
    )
    print(
        f"Current drawdown               : "
        f"{result.current_drawdown_percent:.4f}%"
    )
    print(
        f"Maximum drawdown               : "
        f"{result.maximum_drawdown_percent:.4f}%"
    )
    print(
        f"Consecutive losses             : "
        f"{result.consecutive_loss_count}"
    )
    print(
        f"Commission/Equity              : "
        f"{result.commission_to_equity_percent:.4f}%"
    )

    print()
    print("RULE RESULTS")
    print("-" * line_length)

    for rule in result.rule_results.values():
        print(
            f"{rule.rule_name:<28}: "
            f"{rule.risk_action:<8} "
            f"| Value={rule.observed_value:.4f}"
            f"{rule.observed_unit}"
        )

    print()
    print("RULE COUNTS")
    print("-" * line_length)

    print(
        f"Triggered rules                : "
        f"{result.triggered_rule_count}"
    )
    print(
        f"Warning rules                  : "
        f"{result.warning_rule_count}"
    )
    print(
        f"Pause rules                    : "
        f"{result.pause_rule_count}"
    )
    print(
        f"Block rules                    : "
        f"{result.block_rule_count}"
    )

    print()
    print("PAPER TRADING DECISION")
    print("-" * line_length)

    print(
        f"Paper trading allowed          : "
        f"{result.paper_trading_allowed}"
    )
    print(
        f"Paper trading warning          : "
        f"{result.paper_trading_warning}"
    )
    print(
        f"Paper trading paused           : "
        f"{result.paper_trading_paused}"
    )
    print(
        f"Paper trading blocked          : "
        f"{result.paper_trading_blocked}"
    )

    print()
    print("VALIDATION")
    print("-" * line_length)

    print(
        f"Source loaded                  : "
        f"{result.source_loaded}"
    )
    print(
        f"Source valid                   : "
        f"{result.source_valid}"
    )
    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )
    print(
        f"History checks passed          : "
        f"{result.history_checks_passed}"
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
        f"Source performance file        : "
        f"{result.source_performance_file}"
    )
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
        "주의: V10.4는 연구용 Paper Trading Risk Monitor이며 "
        "실제 Broker 주문을 수행하지 않습니다."
    )


if __name__ == "__main__":
    monitor_result = (
        run_paper_trading_risk_monitor()
    )

    save_paper_trading_risk_monitor(
        monitor_result
    )
