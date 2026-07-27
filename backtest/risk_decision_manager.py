import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.position_state_manager import (
    CurrentPosition,
    PositionStateResult,
    run_position_state_manager,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

RISK_DECISION_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "risk_decision"
)


VALID_RISK_DECISIONS = {
    "ALLOW",
    "REDUCE_SIZE",
    "REVIEW_REQUIRED",
    "BLOCK",
    "NO_ACTION",
}


VALID_RISK_STATUSES = {
    "READY",
    "LIMITED",
    "BLOCKED",
    "FAILED",
}


VALID_RISK_LEVELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}


VALID_POSITION_ACTIONS = {
    "ENTER_LONG",
    "HOLD_POSITION",
    "EXIT_LONG",
    "NO_ACTION",
    "BLOCKED",
}


@dataclass(frozen=True)
class RiskLimits:
    """
    V9.3 Risk Decision Manager에서 사용하는 위험 한도입니다.

    모든 값은 연구 및 검증 목적의 설정이며,
    실제 증권 계좌나 주문 시스템과 연결되지 않습니다.
    """

    maximum_position_percent: float = 20.0
    reduced_position_percent: float = 10.0

    maximum_stop_atr: float = 2.0
    maximum_target_atr: float = 4.0
    maximum_holding_days: int = 30

    minimum_entry_score: float = 60.0
    minimum_score_margin: float = 5.0

    maximum_price_distance_percent: float = 15.0
    manual_review_position_percent: float = 15.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RiskDecisionResult:
    """
    V9.3 Risk Decision Manager 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    source_position_state_file: str | None

    risk_status: str
    risk_decision: str
    risk_decision_label: str
    risk_level: str
    risk_score: float

    position_action: str
    position_state: str
    signal: str
    action_required: bool

    current_score: float
    entry_score: float
    exit_score: float
    score_margin: float

    latest_close: float
    latest_date: str

    stop_atr_multiple: float
    target_atr_multiple: float
    maximum_holding_days: int
    holding_days: int
    holding_limit_reached: bool

    requested_position_percent: float
    approved_position_percent: float
    position_reduction_percent: float

    current_shares: int
    average_price: float
    estimated_position_value: float
    unrealized_return_percent: float | None

    strategy_source: str
    strategy_status: str
    strategy_name: str | None
    strategy_type: str | None

    risk_limits: RiskLimits

    source_loaded: bool
    source_valid: bool
    action_valid: bool
    parameter_checks_passed: bool
    position_checks_passed: bool
    score_checks_passed: bool
    risk_checks_passed: bool
    decision_generated: bool
    all_checks_passed: bool

    order_generated: bool
    paper_order_generated: bool
    live_order_generated: bool
    execution_blocked: bool
    manual_approval_required: bool

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["risk_limits"] = (
            self.risk_limits.to_dict()
        )

        return payload


def normalize_symbol(symbol: str) -> str:
    """
    종목 코드를 대문자로 정규화합니다.
    """

    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    return normalized


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    JSON 파일을 임시 파일을 이용해 안전하게 저장합니다.
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

    temporary_path.replace(
        file_path
    )


def is_valid_number(value: Any) -> bool:
    """
    값이 유효한 숫자인지 검사합니다.
    """

    if isinstance(value, bool):
        return False

    try:
        numeric_value = float(value)

    except (
        TypeError,
        ValueError,
    ):
        return False

    return math.isfinite(
        numeric_value
    )


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    """
    값을 지정된 범위 안으로 제한합니다.
    """

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def validate_risk_limits(
    limits: RiskLimits,
) -> tuple[
    bool,
    list[str],
]:
    """
    RiskLimits 값의 유효성을 검사합니다.
    """

    errors: list[str] = []

    if not (
        0.0
        < limits.maximum_position_percent
        <= 100.0
    ):
        errors.append(
            "Maximum Position Percent가 "
            "허용 범위를 벗어났습니다."
        )

    if not (
        0.0
        < limits.reduced_position_percent
        <= limits.maximum_position_percent
    ):
        errors.append(
            "Reduced Position Percent가 "
            "허용 범위를 벗어났습니다."
        )

    if not (
        0.50
        <= limits.maximum_stop_atr
        <= 10.0
    ):
        errors.append(
            "Maximum Stop ATR이 허용 범위를 "
            "벗어났습니다."
        )

    if not (
        0.50
        <= limits.maximum_target_atr
        <= 20.0
    ):
        errors.append(
            "Maximum Target ATR이 허용 범위를 "
            "벗어났습니다."
        )

    if not (
        1
        <= limits.maximum_holding_days
        <= 365
    ):
        errors.append(
            "Maximum Holding Days가 허용 범위를 "
            "벗어났습니다."
        )

    if not (
        0.0
        <= limits.minimum_entry_score
        <= 100.0
    ):
        errors.append(
            "Minimum Entry Score가 허용 범위를 "
            "벗어났습니다."
        )

    if not (
        0.0
        <= limits.minimum_score_margin
        <= 100.0
    ):
        errors.append(
            "Minimum Score Margin이 허용 범위를 "
            "벗어났습니다."
        )

    if not (
        0.0
        <= limits.maximum_price_distance_percent
        <= 100.0
    ):
        errors.append(
            "Maximum Price Distance Percent가 "
            "허용 범위를 벗어났습니다."
        )

    if not (
        0.0
        < limits.manual_review_position_percent
        <= limits.maximum_position_percent
    ):
        errors.append(
            "Manual Review Position Percent가 "
            "허용 범위를 벗어났습니다."
        )

    return (
        not errors,
        errors,
    )


def validate_position_state_result(
    position_result: PositionStateResult,
) -> tuple[
    bool,
    list[str],
]:
    """
    V9.2 Position State Manager 결과를 검사합니다.
    """

    errors: list[str] = []

    if position_result.version != "V9.2":
        errors.append(
            "Position State Result 버전이 V9.2가 아닙니다."
        )

    if position_result.position_state not in {
        "FLAT",
        "LONG",
    }:
        errors.append(
            "올바르지 않은 Position State입니다: "
            f"{position_result.position_state}"
        )

    if (
        position_result.recommended_action
        not in VALID_POSITION_ACTIONS
    ):
        errors.append(
            "올바르지 않은 Position Action입니다: "
            f"{position_result.recommended_action}"
        )

    if position_result.signal not in {
        "BUY",
        "HOLD",
        "SELL",
    }:
        errors.append(
            "올바르지 않은 Signal입니다: "
            f"{position_result.signal}"
        )

    if not position_result.signal_result_loaded:
        errors.append(
            "Signal Result Loaded가 False입니다."
        )

    if not position_result.position_loaded:
        errors.append(
            "Position Loaded가 False입니다."
        )

    if not position_result.position_valid:
        errors.append(
            "Position Valid가 False입니다."
        )

    if not position_result.signal_valid:
        errors.append(
            "Signal Valid가 False입니다."
        )

    if not position_result.transition_valid:
        errors.append(
            "Transition Valid가 False입니다."
        )

    if not position_result.action_generated:
        errors.append(
            "Action Generated가 False입니다."
        )

    if not position_result.all_checks_passed:
        errors.append(
            "V9.2 검사가 모두 통과되지 않았습니다."
        )

    if not position_result.execution_blocked:
        errors.append(
            "V9.2에서 Execution이 차단되지 않았습니다."
        )

    return (
        not errors,
        errors,
    )


def validate_risk_parameters(
    position_result: PositionStateResult,
    limits: RiskLimits,
) -> tuple[
    bool,
    list[str],
]:
    """
    V9.2에서 전달된 전략 및 위험 파라미터를 검사합니다.
    """

    errors: list[str] = []

    if not (
        0.0
        <= position_result.current_score
        <= 100.0
    ):
        errors.append(
            "Current Score가 0~100 범위를 벗어났습니다."
        )

    if not (
        0.0
        <= position_result.entry_score
        <= 100.0
    ):
        errors.append(
            "Entry Score가 0~100 범위를 벗어났습니다."
        )

    if not (
        0.0
        <= position_result.exit_score
        <= 100.0
    ):
        errors.append(
            "Exit Score가 0~100 범위를 벗어났습니다."
        )

    if (
        position_result.entry_score
        <= position_result.exit_score
    ):
        errors.append(
            "Entry Score는 Exit Score보다 높아야 합니다."
        )

    if not (
        0.0
        < position_result.position_percent
        <= 100.0
    ):
        errors.append(
            "Position Percent가 허용 범위를 벗어났습니다."
        )

    if (
        position_result.position_percent
        > limits.maximum_position_percent
    ):
        errors.append(
            "요청 Position Percent가 Risk Limit을 "
            "초과했습니다."
        )

    if position_result.maximum_holding_days <= 0:
        errors.append(
            "Maximum Holding Days가 0 이하입니다."
        )

    if position_result.latest_close <= 0:
        errors.append(
            "Latest Close가 0 이하입니다."
        )

    return (
        not errors,
        errors,
    )


def validate_current_position(
    position: CurrentPosition,
) -> tuple[
    bool,
    list[str],
]:
    """
    현재 포지션의 위험 관련 값을 검사합니다.
    """

    errors: list[str] = []

    if position.state not in {
        "FLAT",
        "LONG",
    }:
        errors.append(
            "Current Position State가 올바르지 않습니다."
        )

    if position.shares < 0:
        errors.append(
            "Current Shares는 음수가 될 수 없습니다."
        )

    if position.average_price < 0:
        errors.append(
            "Average Price는 음수가 될 수 없습니다."
        )

    if position.holding_days < 0:
        errors.append(
            "Holding Days는 음수가 될 수 없습니다."
        )

    if position.state == "FLAT":
        if position.shares != 0:
            errors.append(
                "FLAT 상태에서는 Shares가 0이어야 합니다."
            )

        if position.average_price != 0.0:
            errors.append(
                "FLAT 상태에서는 Average Price가 "
                "0이어야 합니다."
            )

    if position.state == "LONG":
        if position.shares <= 0:
            errors.append(
                "LONG 상태에서는 Shares가 1 이상이어야 합니다."
            )

        if position.average_price <= 0:
            errors.append(
                "LONG 상태에서는 Average Price가 "
                "0보다 커야 합니다."
            )

    return (
        not errors,
        errors,
    )


def calculate_position_metrics(
    position: CurrentPosition,
    latest_close: float,
) -> tuple[
    float,
    float | None,
]:
    """
    현재 포지션 가치와 평가 수익률을 계산합니다.
    """

    if (
        position.state == "FLAT"
        or position.shares <= 0
    ):
        return (
            0.0,
            None,
        )

    estimated_position_value = (
        float(position.shares)
        * float(latest_close)
    )

    if position.average_price <= 0:
        unrealized_return_percent = None

    else:
        unrealized_return_percent = (
            (
                float(latest_close)
                / float(position.average_price)
            )
            - 1.0
        ) * 100.0

    return (
        estimated_position_value,
        unrealized_return_percent,
    )


def calculate_risk_score(
    position_result: PositionStateResult,
    limits: RiskLimits,
) -> tuple[
    float,
    list[str],
]:
    """
    위험 점수를 0~100 사이로 계산합니다.

    점수가 높을수록 위험이 높습니다.
    """

    risk_score = 0.0
    reasons: list[str] = []

    requested_position = (
        float(position_result.position_percent)
    )

    if requested_position > (
        limits.manual_review_position_percent
    ):
        risk_score += 20.0
        reasons.append(
            "요청 포지션 비율이 수동 검토 기준보다 높습니다."
        )

    elif requested_position == (
        limits.manual_review_position_percent
    ):
        risk_score += 10.0
        reasons.append(
            "요청 포지션 비율이 수동 검토 기준과 같습니다."
        )

    score_margin = (
        float(position_result.current_score)
        - float(position_result.entry_score)
    )

    if (
        position_result.recommended_action
        == "ENTER_LONG"
    ):
        if score_margin < 0:
            risk_score += 40.0
            reasons.append(
                "현재 점수가 진입 기준보다 낮습니다."
            )

        elif score_margin < (
            limits.minimum_score_margin
        ):
            risk_score += 20.0
            reasons.append(
                "현재 점수와 진입 기준의 여유가 작습니다."
            )

        else:
            reasons.append(
                "현재 점수가 진입 기준보다 충분히 높습니다."
            )

    if (
        position_result.current_score
        < limits.minimum_entry_score
        and position_result.recommended_action
        == "ENTER_LONG"
    ):
        risk_score += 30.0
        reasons.append(
            "현재 점수가 최소 진입 점수보다 낮습니다."
        )

    if position_result.holding_limit_reached:
        risk_score += 20.0
        reasons.append(
            "최대 보유기간에 도달했습니다."
        )

    if (
        position_result.current_position.state
        == "LONG"
        and position_result.current_position.holding_days
        >= limits.maximum_holding_days
    ):
        risk_score += 20.0
        reasons.append(
            "Risk Limit의 최대 보유기간에 도달했습니다."
        )

    if (
        position_result.recommended_action
        == "BLOCKED"
    ):
        risk_score += 100.0
        reasons.append(
            "V9.2 추천 행동이 BLOCKED입니다."
        )

    if (
        position_result.recommended_action
        == "EXIT_LONG"
    ):
        reasons.append(
            "기존 포지션 종료 행동은 신규 위험 노출을 "
            "증가시키지 않습니다."
        )

        risk_score -= 10.0

    if (
        position_result.recommended_action
        in {
            "NO_ACTION",
            "HOLD_POSITION",
        }
    ):
        reasons.append(
            "신규 포지션 진입이 아니므로 추가 위험 노출이 "
            "제한적입니다."
        )

        risk_score -= 5.0

    risk_score = clamp(
        risk_score,
        0.0,
        100.0,
    )

    return (
        risk_score,
        reasons,
    )


def determine_risk_level(
    risk_score: float,
) -> str:
    """
    위험 점수를 위험 등급으로 변환합니다.
    """

    if risk_score >= 80.0:
        return "CRITICAL"

    if risk_score >= 60.0:
        return "HIGH"

    if risk_score >= 30.0:
        return "MEDIUM"

    return "LOW"


def determine_risk_decision(
    position_action: str,
    risk_score: float,
    requested_position_percent: float,
    limits: RiskLimits,
    source_valid: bool,
    parameter_checks_passed: bool,
    position_checks_passed: bool,
) -> tuple[
    str,
    str,
    float,
    bool,
    list[str],
]:
    """
    위험 조건에 따라 최종 Risk Decision을 결정합니다.
    """

    if not (
        source_valid
        and parameter_checks_passed
        and position_checks_passed
    ):
        return (
            "BLOCK",
            "위험 검사 실패로 차단",
            0.0,
            True,
            [
                "필수 위험 검사가 통과되지 않았습니다.",
                "추천 행동을 실행 단계로 전달할 수 없습니다.",
            ],
        )

    if position_action == "BLOCKED":
        return (
            "BLOCK",
            "상위 단계 행동 차단",
            0.0,
            True,
            [
                "V9.2 Position State Manager에서 "
                "행동이 차단되었습니다."
            ],
        )

    if position_action == "NO_ACTION":
        return (
            "NO_ACTION",
            "추가 행동 없음",
            0.0,
            False,
            [
                "V9.2에서 실행할 포지션 행동이 없습니다."
            ],
        )

    if position_action == "HOLD_POSITION":
        return (
            "ALLOW",
            "기존 포지션 유지 허용",
            requested_position_percent,
            False,
            [
                "기존 포지션 유지 행동입니다.",
                "신규 주문 생성 없이 상태 유지가 허용됩니다.",
            ],
        )

    if position_action == "EXIT_LONG":
        if risk_score >= 80.0:
            return (
                "REVIEW_REQUIRED",
                "포지션 종료 수동 검토",
                requested_position_percent,
                True,
                [
                    "포지션 종료 행동이지만 위험 점수가 "
                    "매우 높습니다.",
                    "수동 검토 후 종료 판단이 필요합니다.",
                ],
            )

        return (
            "ALLOW",
            "포지션 종료 검토 허용",
            requested_position_percent,
            True,
            [
                "기존 Long 포지션 종료 조건입니다.",
                "신규 위험 노출을 증가시키지 않습니다.",
            ],
        )

    if position_action == "ENTER_LONG":
        if risk_score >= 80.0:
            return (
                "BLOCK",
                "신규 진입 위험 차단",
                0.0,
                True,
                [
                    "신규 진입 위험 점수가 매우 높습니다.",
                    "포지션 진입을 차단합니다.",
                ],
            )

        if risk_score >= 60.0:
            return (
                "REVIEW_REQUIRED",
                "신규 진입 수동 검토",
                0.0,
                True,
                [
                    "신규 진입 위험 점수가 높습니다.",
                    "수동 검토 전까지 포지션을 허용하지 않습니다.",
                ],
            )

        if (
            risk_score >= 30.0
            or requested_position_percent
            > limits.manual_review_position_percent
        ):
            approved_position_percent = min(
                requested_position_percent,
                limits.reduced_position_percent,
            )

            return (
                "REDUCE_SIZE",
                "축소 포지션 검토",
                approved_position_percent,
                True,
                [
                    "신규 진입은 가능하지만 위험이 중간 수준입니다.",
                    "포지션 크기를 축소해 검토합니다.",
                ],
            )

        approved_position_percent = min(
            requested_position_percent,
            limits.maximum_position_percent,
        )

        return (
            "ALLOW",
            "신규 진입 검토 허용",
            approved_position_percent,
            True,
            [
                "주요 위험 조건이 허용 범위입니다.",
                "요청 포지션 비율이 위험 한도 이내입니다.",
            ],
        )

    return (
        "BLOCK",
        "알 수 없는 행동 차단",
        0.0,
        True,
        [
            "지원하지 않는 Position Action입니다."
        ],
    )


def determine_risk_status(
    risk_decision: str,
    decision_generated: bool,
    all_core_checks_passed: bool,
) -> str:
    """
    Risk Decision Manager 상태를 결정합니다.
    """

    if not all_core_checks_passed:
        return "FAILED"

    if not decision_generated:
        return "FAILED"

    if risk_decision == "BLOCK":
        return "BLOCKED"

    if risk_decision in {
        "REDUCE_SIZE",
        "REVIEW_REQUIRED",
    }:
        return "LIMITED"

    return "READY"


def build_risk_notes(
    risk_decision: str,
    position_action: str,
    approved_position_percent: float,
    requested_position_percent: float,
    source_errors: list[str],
    parameter_errors: list[str],
    position_errors: list[str],
    limit_errors: list[str],
) -> tuple[
    list[str],
    list[str],
]:
    """
    경고와 다음 작업 목록을 생성합니다.
    """

    warnings: list[str] = []

    warnings.extend(
        source_errors
    )

    warnings.extend(
        parameter_errors
    )

    warnings.extend(
        position_errors
    )

    warnings.extend(
        limit_errors
    )

    warnings.extend(
        [
            (
                "Risk Decision은 연구 및 검토용 판단이며 "
                "증권 주문이 아닙니다."
            ),
            (
                "V9.3은 Broker, 계좌 또는 주문 API를 "
                "호출하지 않습니다."
            ),
            (
                "Paper Order와 Live Order는 모두 "
                "계속 차단됩니다."
            ),
            (
                "실행 관련 모든 행동에는 수동 승인이 "
                "필요합니다."
            ),
        ]
    )

    if risk_decision == "ALLOW":
        next_actions = [
            (
                f"{position_action} 판단을 V9.4 Position "
                "Sizing Manager에 전달합니다."
            ),
            (
                f"승인 포지션 비율 "
                f"{approved_position_percent:.2f}%를 "
                "기준으로 예상 수량을 계산합니다."
            ),
            (
                "계산된 수량은 주문으로 전송하지 않습니다."
            ),
        ]

    elif risk_decision == "REDUCE_SIZE":
        next_actions = [
            (
                f"요청 포지션 비율 "
                f"{requested_position_percent:.2f}%를 "
                f"{approved_position_percent:.2f}%로 "
                "축소해 검토합니다."
            ),
            (
                "V9.4 Position Sizing Manager에서 "
                "축소 수량을 계산합니다."
            ),
            (
                "실행 전 수동 승인이 필요합니다."
            ),
        ]

    elif risk_decision == "REVIEW_REQUIRED":
        next_actions = [
            (
                "위험 조건을 사람이 다시 검토합니다."
            ),
            (
                "승인 전까지 Position Sizing 단계로 "
                "전달하지 않습니다."
            ),
            (
                "시장 데이터와 포지션 상태를 다시 확인합니다."
            ),
        ]

    elif risk_decision == "BLOCK":
        next_actions = [
            (
                "현재 Position Action을 중단합니다."
            ),
            (
                "위험 검사 실패 원인을 수정합니다."
            ),
            (
                "새로운 시장 데이터로 다시 평가합니다."
            ),
        ]

    else:
        next_actions = [
            (
                "추가 행동 없이 현재 상태를 유지합니다."
            ),
            (
                "새로운 신호가 생성되면 다시 위험을 평가합니다."
            ),
            (
                "주문 실행 단계에는 전달하지 않습니다."
            ),
        ]

    return (
        warnings,
        next_actions,
    )


def run_risk_decision_manager(
    symbol: str = "AAPL",
    position_result: PositionStateResult | None = None,
    current_position: CurrentPosition | None = None,
    risk_limits: RiskLimits | None = None,
    period: str = "5y",
    interval: str = "1d",
) -> RiskDecisionResult:
    """
    V9.2 Position Action과 위험 한도를 비교하여
    V9.3 Risk Decision을 생성합니다.

    실제 주문은 생성하지 않습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    limits = (
        risk_limits
        if risk_limits is not None
        else RiskLimits()
    )

    (
        limit_checks_passed,
        limit_errors,
    ) = validate_risk_limits(
        limits
    )

    if position_result is None:
        position_result = run_position_state_manager(
            symbol=normalized_symbol,
            current_position=current_position,
            period=period,
            interval=interval,
        )

    if position_result.symbol != normalized_symbol:
        raise ValueError(
            "Position Result Symbol과 요청 Symbol이 "
            "일치하지 않습니다."
        )

    (
        source_valid,
        source_errors,
    ) = validate_position_state_result(
        position_result
    )

    (
        parameter_checks_passed,
        parameter_errors,
    ) = validate_risk_parameters(
        position_result=position_result,
        limits=limits,
    )

    (
        position_checks_passed,
        position_errors,
    ) = validate_current_position(
        position_result.current_position
    )

    action_valid = (
        position_result.recommended_action
        in VALID_POSITION_ACTIONS
    )

    score_checks_passed = (
        is_valid_number(
            position_result.current_score
        )
        and is_valid_number(
            position_result.entry_score
        )
        and is_valid_number(
            position_result.exit_score
        )
        and 0.0
        <= float(position_result.current_score)
        <= 100.0
        and 0.0
        <= float(position_result.entry_score)
        <= 100.0
        and 0.0
        <= float(position_result.exit_score)
        <= 100.0
    )

    score_margin = (
        float(position_result.current_score)
        - float(position_result.entry_score)
    )

    (
        estimated_position_value,
        unrealized_return_percent,
    ) = calculate_position_metrics(
        position=position_result.current_position,
        latest_close=float(
            position_result.latest_close
        ),
    )

    (
        risk_score,
        risk_reasons,
    ) = calculate_risk_score(
        position_result=position_result,
        limits=limits,
    )

    risk_level = determine_risk_level(
        risk_score
    )

    (
        risk_decision,
        risk_decision_label,
        approved_position_percent,
        manual_approval_required,
        decision_reasons,
    ) = determine_risk_decision(
        position_action=(
            position_result.recommended_action
        ),
        risk_score=risk_score,
        requested_position_percent=float(
            position_result.position_percent
        ),
        limits=limits,
        source_valid=source_valid,
        parameter_checks_passed=(
            parameter_checks_passed
            and limit_checks_passed
        ),
        position_checks_passed=(
            position_checks_passed
        ),
    )

    position_reduction_percent = max(
        0.0,
        float(position_result.position_percent)
        - float(approved_position_percent),
    )

    decision_generated = (
        risk_decision
        in VALID_RISK_DECISIONS
    )

    risk_checks_passed = (
        is_valid_number(
            risk_score
        )
        and 0.0
        <= risk_score
        <= 100.0
        and risk_level
        in VALID_RISK_LEVELS
        and decision_generated
    )

    all_core_checks_passed = (
        source_valid
        and action_valid
        and parameter_checks_passed
        and position_checks_passed
        and score_checks_passed
        and risk_checks_passed
        and limit_checks_passed
    )

    risk_status = determine_risk_status(
        risk_decision=risk_decision,
        decision_generated=decision_generated,
        all_core_checks_passed=(
            all_core_checks_passed
        ),
    )

    reasons = []

    reasons.extend(
        risk_reasons
    )

    reasons.extend(
        decision_reasons
    )

    (
        warnings,
        next_actions,
    ) = build_risk_notes(
        risk_decision=risk_decision,
        position_action=(
            position_result.recommended_action
        ),
        approved_position_percent=(
            approved_position_percent
        ),
        requested_position_percent=float(
            position_result.position_percent
        ),
        source_errors=source_errors,
        parameter_errors=parameter_errors,
        position_errors=position_errors,
        limit_errors=limit_errors,
    )

    all_checks_passed = (
        all_core_checks_passed
        and decision_generated
    )

    result = RiskDecisionResult(
        version="V9.3",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        source_position_state_file=(
            position_result.latest_path
            or position_result.report_path
            or position_result.source_signal_file
        ),

        risk_status=risk_status,
        risk_decision=risk_decision,
        risk_decision_label=(
            risk_decision_label
        ),
        risk_level=risk_level,
        risk_score=float(
            risk_score
        ),

        position_action=(
            position_result.recommended_action
        ),
        position_state=(
            position_result.position_state
        ),
        signal=position_result.signal,
        action_required=(
            position_result.action_required
        ),

        current_score=float(
            position_result.current_score
        ),
        entry_score=float(
            position_result.entry_score
        ),
        exit_score=float(
            position_result.exit_score
        ),
        score_margin=float(
            score_margin
        ),

        latest_close=float(
            position_result.latest_close
        ),
        latest_date=(
            position_result.latest_date
        ),

        stop_atr_multiple=1.50,
        target_atr_multiple=2.25,
        maximum_holding_days=int(
            position_result.maximum_holding_days
        ),
        holding_days=int(
            position_result
            .current_position
            .holding_days
        ),
        holding_limit_reached=(
            position_result.holding_limit_reached
        ),

        requested_position_percent=float(
            position_result.position_percent
        ),
        approved_position_percent=float(
            approved_position_percent
        ),
        position_reduction_percent=float(
            position_reduction_percent
        ),

        current_shares=int(
            position_result
            .current_position
            .shares
        ),
        average_price=float(
            position_result
            .current_position
            .average_price
        ),
        estimated_position_value=float(
            estimated_position_value
        ),
        unrealized_return_percent=(
            float(unrealized_return_percent)
            if unrealized_return_percent is not None
            else None
        ),

        strategy_source=(
            position_result.strategy_source
        ),
        strategy_status=(
            position_result.strategy_status
        ),
        strategy_name=(
            position_result.strategy_name
        ),
        strategy_type=(
            position_result.strategy_type
        ),

        risk_limits=limits,

        source_loaded=True,
        source_valid=source_valid,
        action_valid=action_valid,
        parameter_checks_passed=(
            parameter_checks_passed
            and limit_checks_passed
        ),
        position_checks_passed=(
            position_checks_passed
        ),
        score_checks_passed=(
            score_checks_passed
        ),
        risk_checks_passed=(
            risk_checks_passed
        ),
        decision_generated=(
            decision_generated
        ),
        all_checks_passed=(
            all_checks_passed
        ),

        order_generated=False,
        paper_order_generated=False,
        live_order_generated=False,
        execution_blocked=True,
        manual_approval_required=(
            manual_approval_required
        ),

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_risk_decision_manager(
        result
    )

    return result


def save_risk_decision_manager(
    result: RiskDecisionResult,
) -> tuple[
    Path,
    Path,
]:
    """
    V9.3 Risk Decision 결과를 JSON으로 저장합니다.
    """

    RISK_DECISION_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        RISK_DECISION_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "risk_decision_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        RISK_DECISION_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "risk_decision_latest.json"
        )
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    payload = result.to_dict()

    write_json_file(
        report_path,
        payload,
    )

    write_json_file(
        latest_path,
        payload,
    )

    return (
        report_path,
        latest_path,
    )


def print_risk_decision_manager(
    result: RiskDecisionResult,
) -> None:
    """
    V9.3 Risk Decision Manager 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V9.3 "
        "RISK DECISION MANAGER"
    )
    print("=" * 140)

    print(
        f"Risk status                    : "
        f"{result.risk_status}"
    )

    print(
        f"Risk decision                  : "
        f"{result.risk_decision}"
    )

    print(
        f"Risk decision label            : "
        f"{result.risk_decision_label}"
    )

    print(
        f"Risk level                     : "
        f"{result.risk_level}"
    )

    print(
        f"Risk score                     : "
        f"{result.risk_score:.2f}/100"
    )

    print()
    print("POSITION ACTION")
    print("-" * 140)

    print(
        f"Position state                 : "
        f"{result.position_state}"
    )

    print(
        f"Signal                         : "
        f"{result.signal}"
    )

    print(
        f"Position action                : "
        f"{result.position_action}"
    )

    print(
        f"Action required                : "
        f"{result.action_required}"
    )

    print()
    print("SCORE")
    print("-" * 140)

    print(
        f"Current score                  : "
        f"{result.current_score:.2f}"
    )

    print(
        f"Entry score                    : "
        f"{result.entry_score:.2f}"
    )

    print(
        f"Exit score                     : "
        f"{result.exit_score:.2f}"
    )

    print(
        f"Score margin                   : "
        f"{result.score_margin:+.2f}"
    )

    print()
    print("POSITION RISK")
    print("-" * 140)

    print(
        f"Requested position percent     : "
        f"{result.requested_position_percent:.2f}%"
    )

    print(
        f"Approved position percent      : "
        f"{result.approved_position_percent:.2f}%"
    )

    print(
        f"Position reduction             : "
        f"{result.position_reduction_percent:.2f}%p"
    )

    print(
        f"Current shares                 : "
        f"{result.current_shares}"
    )

    print(
        f"Average price                  : "
        f"${result.average_price:,.2f}"
    )

    print(
        f"Estimated position value       : "
        f"${result.estimated_position_value:,.2f}"
    )

    if result.unrealized_return_percent is None:
        unrealized_text = "N/A"

    else:
        unrealized_text = (
            f"{result.unrealized_return_percent:+.2f}%"
        )

    print(
        f"Unrealized return              : "
        f"{unrealized_text}"
    )

    print()
    print("HOLDING RISK")
    print("-" * 140)

    print(
        f"Holding days                   : "
        f"{result.holding_days}"
    )

    print(
        f"Maximum holding days           : "
        f"{result.maximum_holding_days}"
    )

    print(
        f"Holding limit reached          : "
        f"{result.holding_limit_reached}"
    )

    print(
        f"Stop ATR                       : "
        f"{result.stop_atr_multiple:.2f}"
    )

    print(
        f"Target ATR                     : "
        f"{result.target_atr_multiple:.2f}"
    )

    print()
    print("VALIDATION")
    print("-" * 140)

    print(
        f"Source loaded                  : "
        f"{result.source_loaded}"
    )

    print(
        f"Source valid                   : "
        f"{result.source_valid}"
    )

    print(
        f"Action valid                   : "
        f"{result.action_valid}"
    )

    print(
        f"Parameter checks passed        : "
        f"{result.parameter_checks_passed}"
    )

    print(
        f"Position checks passed         : "
        f"{result.position_checks_passed}"
    )

    print(
        f"Score checks passed            : "
        f"{result.score_checks_passed}"
    )

    print(
        f"Risk checks passed             : "
        f"{result.risk_checks_passed}"
    )

    print(
        f"Decision generated             : "
        f"{result.decision_generated}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 140)

    print(
        f"Order generated                : "
        f"{result.order_generated}"
    )

    print(
        f"Paper order generated          : "
        f"{result.paper_order_generated}"
    )

    print(
        f"Live order generated           : "
        f"{result.live_order_generated}"
    )

    print(
        f"Execution blocked              : "
        f"{result.execution_blocked}"
    )

    print(
        f"Manual approval required       : "
        f"{result.manual_approval_required}"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * 140)

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * 140)

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * 140)

        for action in result.next_actions:
            print(
                f"- {action}"
            )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Source Position State file     : "
        f"{result.source_position_state_file}"
    )

    print(
        f"Report file                    : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                    : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 140)

    print(
        "주의: 이 모듈은 위험 판단만 수행하며 실제 주문, "
        "모의 주문 또는 실거래 주문을 생성하거나 "
        "전송하지 않습니다."
    )