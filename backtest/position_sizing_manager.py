import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.position_state_manager import (
    CurrentPosition,
)
from backtest.risk_decision_manager import (
    RiskDecisionResult,
    RiskLimits,
    run_risk_decision_manager,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

POSITION_SIZING_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "position_sizing"
)


VALID_SIZING_STATUSES = {
    "READY",
    "LIMITED",
    "NO_ACTION",
    "BLOCKED",
    "FAILED",
}


VALID_SIZING_ACTIONS = {
    "PREPARE_ENTRY",
    "MAINTAIN_POSITION",
    "PREPARE_EXIT",
    "NO_ACTION",
    "BLOCKED",
}


VALID_RISK_DECISIONS = {
    "ALLOW",
    "REDUCE_SIZE",
    "REVIEW_REQUIRED",
    "BLOCK",
    "NO_ACTION",
}


@dataclass(frozen=True)
class PositionSizingLimits:
    """
    포지션 수량 계산에 사용하는 안전 한도입니다.

    실제 주문 한도가 아니라 연구 및 검증용 설정입니다.
    """

    minimum_account_cash: float = 100.0
    maximum_account_cash: float = 100_000_000.0

    minimum_trade_value: float = 25.0
    maximum_trade_value: float = 1_000_000.0

    minimum_shares: int = 1
    maximum_shares: int = 100_000

    cash_reserve_percent: float = 5.0
    allow_fractional_shares: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PositionSizingResult:
    """
    V9.4 Position Sizing Manager 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    source_risk_decision_file: str | None

    sizing_status: str
    sizing_action: str
    sizing_action_label: str

    position_state: str
    position_action: str
    signal: str

    risk_status: str
    risk_decision: str
    risk_level: str
    risk_score: float

    account_cash: float
    cash_reserve_percent: float
    reserved_cash: float
    available_cash: float

    requested_position_percent: float
    approved_position_percent: float

    latest_close: float
    estimated_entry_price: float

    target_position_value: float
    affordable_position_value: float
    proposed_position_value: float

    raw_share_quantity: float
    proposed_shares: int
    current_shares: int
    share_difference: int

    estimated_cash_after_entry: float
    estimated_position_percent: float

    maximum_shares: int
    minimum_trade_value: float

    sizing_required: bool
    sizing_generated: bool
    sufficient_cash: bool
    minimum_trade_value_passed: bool
    share_limit_passed: bool
    position_percent_passed: bool

    source_loaded: bool
    source_valid: bool
    account_checks_passed: bool
    price_checks_passed: bool
    risk_checks_passed: bool
    sizing_checks_passed: bool
    all_checks_passed: bool

    order_generated: bool
    paper_order_generated: bool
    live_order_generated: bool
    execution_blocked: bool
    manual_approval_required: bool

    sizing_limits: PositionSizingLimits

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["sizing_limits"] = (
            self.sizing_limits.to_dict()
        )

        return payload


def normalize_symbol(
    symbol: str,
) -> str:
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
    JSON 파일을 안전하게 저장합니다.
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


def is_valid_number(
    value: Any,
) -> bool:
    """
    값이 유효한 유한 숫자인지 검사합니다.
    """

    if isinstance(
        value,
        bool,
    ):
        return False

    try:
        numeric_value = float(
            value
        )

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
    숫자를 지정된 범위 안으로 제한합니다.
    """

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def validate_sizing_limits(
    limits: PositionSizingLimits,
) -> tuple[
    bool,
    list[str],
]:
    """
    PositionSizingLimits의 유효성을 검사합니다.
    """

    errors: list[str] = []

    if not (
        0.0
        < limits.minimum_account_cash
        < limits.maximum_account_cash
    ):
        errors.append(
            "계좌 현금 최소·최대 한도가 올바르지 않습니다."
        )

    if not (
        0.0
        < limits.minimum_trade_value
        <= limits.maximum_trade_value
    ):
        errors.append(
            "거래금액 최소·최대 한도가 올바르지 않습니다."
        )

    if not (
        1
        <= limits.minimum_shares
        <= limits.maximum_shares
    ):
        errors.append(
            "주식 수량 최소·최대 한도가 올바르지 않습니다."
        )

    if not (
        0.0
        <= limits.cash_reserve_percent
        < 100.0
    ):
        errors.append(
            "Cash Reserve Percent가 허용 범위를 벗어났습니다."
        )

    if not isinstance(
        limits.allow_fractional_shares,
        bool,
    ):
        errors.append(
            "Allow Fractional Shares가 bool 형식이 아닙니다."
        )

    return (
        not errors,
        errors,
    )


def validate_risk_result(
    risk_result: RiskDecisionResult,
) -> tuple[
    bool,
    list[str],
]:
    """
    V9.3 Risk Decision 결과를 검사합니다.
    """

    errors: list[str] = []

    if risk_result.version != "V9.3":
        errors.append(
            "Risk Decision Result 버전이 V9.3이 아닙니다."
        )

    if (
        risk_result.risk_decision
        not in VALID_RISK_DECISIONS
    ):
        errors.append(
            "올바르지 않은 Risk Decision입니다: "
            f"{risk_result.risk_decision}"
        )

    if not risk_result.source_loaded:
        errors.append(
            "V9.3 Source Loaded가 False입니다."
        )

    if not risk_result.source_valid:
        errors.append(
            "V9.3 Source Valid가 False입니다."
        )

    if not risk_result.decision_generated:
        errors.append(
            "V9.3 Decision Generated가 False입니다."
        )

    if not risk_result.all_checks_passed:
        errors.append(
            "V9.3 검사가 모두 통과되지 않았습니다."
        )

    if not risk_result.execution_blocked:
        errors.append(
            "V9.3에서 Execution이 차단되지 않았습니다."
        )

    if risk_result.latest_close <= 0:
        errors.append(
            "Latest Close가 0 이하입니다."
        )

    if not (
        0.0
        <= risk_result.approved_position_percent
        <= 100.0
    ):
        errors.append(
            "Approved Position Percent가 유효하지 않습니다."
        )

    return (
        not errors,
        errors,
    )


def validate_account_cash(
    account_cash: float,
    limits: PositionSizingLimits,
) -> tuple[
    bool,
    list[str],
]:
    """
    계산에 사용하는 가상 계좌 현금을 검사합니다.
    """

    errors: list[str] = []

    if not is_valid_number(
        account_cash
    ):
        errors.append(
            "Account Cash가 유효한 숫자가 아닙니다."
        )

        return (
            False,
            errors,
        )

    normalized_cash = float(
        account_cash
    )

    if normalized_cash < (
        limits.minimum_account_cash
    ):
        errors.append(
            "Account Cash가 최소 현금 기준보다 낮습니다."
        )

    if normalized_cash > (
        limits.maximum_account_cash
    ):
        errors.append(
            "Account Cash가 최대 안전 기준보다 높습니다."
        )

    return (
        not errors,
        errors,
    )


def calculate_available_cash(
    account_cash: float,
    reserve_percent: float,
) -> tuple[
    float,
    float,
]:
    """
    현금 준비금과 사용 가능한 현금을 계산합니다.
    """

    reserved_cash = (
        float(account_cash)
        * float(reserve_percent)
        / 100.0
    )

    available_cash = max(
        0.0,
        float(account_cash)
        - reserved_cash,
    )

    return (
        reserved_cash,
        available_cash,
    )


def calculate_entry_position_size(
    account_cash: float,
    available_cash: float,
    approved_position_percent: float,
    latest_close: float,
    limits: PositionSizingLimits,
) -> dict[str, float | int | bool]:
    """
    신규 진입에 필요한 목표 투자금액과 주식 수량을 계산합니다.
    """

    target_position_value = (
        float(account_cash)
        * float(approved_position_percent)
        / 100.0
    )

    affordable_position_value = min(
        target_position_value,
        available_cash,
        limits.maximum_trade_value,
    )

    if latest_close <= 0:
        raw_share_quantity = 0.0

    else:
        raw_share_quantity = (
            affordable_position_value
            / float(latest_close)
        )

    if limits.allow_fractional_shares:
        proposed_shares = int(
            raw_share_quantity
        )

    else:
        proposed_shares = math.floor(
            raw_share_quantity
        )

    proposed_shares = int(
        clamp(
            float(proposed_shares),
            0.0,
            float(limits.maximum_shares),
        )
    )

    proposed_position_value = (
        float(proposed_shares)
        * float(latest_close)
    )

    sufficient_cash = (
        proposed_position_value
        <= available_cash + 0.0001
    )

    minimum_trade_value_passed = (
        proposed_position_value
        >= limits.minimum_trade_value
    )

    share_limit_passed = (
        proposed_shares
        <= limits.maximum_shares
    )

    estimated_cash_after_entry = max(
        0.0,
        float(account_cash)
        - proposed_position_value,
    )

    if account_cash <= 0:
        estimated_position_percent = 0.0

    else:
        estimated_position_percent = (
            proposed_position_value
            / float(account_cash)
            * 100.0
        )

    position_percent_passed = (
        estimated_position_percent
        <= approved_position_percent + 0.0001
    )

    return {
        "target_position_value": float(
            target_position_value
        ),
        "affordable_position_value": float(
            affordable_position_value
        ),
        "raw_share_quantity": float(
            raw_share_quantity
        ),
        "proposed_shares": int(
            proposed_shares
        ),
        "proposed_position_value": float(
            proposed_position_value
        ),
        "sufficient_cash": bool(
            sufficient_cash
        ),
        "minimum_trade_value_passed": bool(
            minimum_trade_value_passed
        ),
        "share_limit_passed": bool(
            share_limit_passed
        ),
        "estimated_cash_after_entry": float(
            estimated_cash_after_entry
        ),
        "estimated_position_percent": float(
            estimated_position_percent
        ),
        "position_percent_passed": bool(
            position_percent_passed
        ),
    }


def determine_sizing_action(
    risk_decision: str,
    position_action: str,
) -> tuple[
    str,
    str,
    bool,
    list[str],
]:
    """
    V9.3 Risk Decision과 V9.2 Position Action을 바탕으로
    V9.4 수량 계산 행동을 결정합니다.
    """

    if risk_decision == "BLOCK":
        return (
            "BLOCKED",
            "위험 판단으로 수량 계산 차단",
            False,
            [
                "V9.3 Risk Decision이 BLOCK입니다.",
                "신규 수량을 계산 단계로 전달하지 않습니다.",
            ],
        )

    if risk_decision == "REVIEW_REQUIRED":
        return (
            "BLOCKED",
            "수동 검토 전 수량 계산 차단",
            False,
            [
                "V9.3에서 수동 검토가 요구되었습니다.",
                "승인 전까지 실행용 수량을 생성하지 않습니다.",
            ],
        )

    if (
        risk_decision == "NO_ACTION"
        or position_action == "NO_ACTION"
    ):
        return (
            "NO_ACTION",
            "추가 수량 계산 없음",
            False,
            [
                "현재 실행할 포지션 행동이 없습니다."
            ],
        )

    if (
        position_action == "ENTER_LONG"
        and risk_decision
        in {
            "ALLOW",
            "REDUCE_SIZE",
        }
    ):
        return (
            "PREPARE_ENTRY",
            "신규 진입 수량 계산",
            True,
            [
                "신규 Long 진입 검토 조건입니다.",
                "승인된 포지션 비율로 예상 수량을 계산합니다.",
            ],
        )

    if position_action == "HOLD_POSITION":
        return (
            "MAINTAIN_POSITION",
            "기존 보유 수량 유지",
            False,
            [
                "기존 Long 포지션 유지 조건입니다.",
                "추가 매수 수량을 생성하지 않습니다.",
            ],
        )

    if position_action == "EXIT_LONG":
        return (
            "PREPARE_EXIT",
            "기존 보유 수량 종료 계산",
            True,
            [
                "기존 Long 포지션 종료 검토 조건입니다.",
                "현재 보유 수량을 종료 검토 수량으로 사용합니다.",
            ],
        )

    return (
        "BLOCKED",
        "지원하지 않는 조합 차단",
        False,
        [
            "지원하지 않는 Risk Decision과 Position Action "
            "조합입니다."
        ],
    )


def determine_sizing_status(
    sizing_action: str,
    sizing_generated: bool,
    core_checks_passed: bool,
) -> str:
    """
    Position Sizing Manager 상태를 결정합니다.
    """

    if not core_checks_passed:
        return "FAILED"

    if sizing_action == "BLOCKED":
        return "BLOCKED"

    if sizing_action == "NO_ACTION":
        return "NO_ACTION"

    if sizing_action == "MAINTAIN_POSITION":
        return "READY"

    if sizing_generated:
        return "READY"

    return "LIMITED"


def build_sizing_notes(
    sizing_action: str,
    proposed_shares: int,
    approved_position_percent: float,
    source_errors: list[str],
    account_errors: list[str],
    limit_errors: list[str],
) -> tuple[
    list[str],
    list[str],
]:
    """
    경고와 다음 단계 설명을 생성합니다.
    """

    warnings: list[str] = []

    warnings.extend(
        source_errors
    )

    warnings.extend(
        account_errors
    )

    warnings.extend(
        limit_errors
    )

    warnings.extend(
        [
            (
                "계좌 현금은 사용자가 전달한 연구용 값이며 "
                "실제 증권 계좌 잔고가 아닙니다."
            ),
            (
                "계산된 주식 수량은 주문이 아니라 "
                "검토용 예상 수량입니다."
            ),
            (
                "V9.4는 Broker, 계좌 또는 주문 API를 "
                "호출하지 않습니다."
            ),
            (
                "Paper Order와 Live Order는 계속 차단됩니다."
            ),
        ]
    )

    if sizing_action == "PREPARE_ENTRY":
        next_actions = [
            (
                f"승인 비율 {approved_position_percent:.2f}%에 "
                f"따라 {proposed_shares}주의 진입 요청 초안을 "
                "V9.5에 전달합니다."
            ),
            (
                "실제 주문 생성 전 가격과 계좌 현금을 "
                "다시 확인합니다."
            ),
            (
                "수동 승인 없이는 주문 단계로 진행하지 않습니다."
            ),
        ]

    elif sizing_action == "PREPARE_EXIT":
        next_actions = [
            (
                f"현재 보유 수량 {proposed_shares}주를 "
                "종료 요청 초안으로 전달합니다."
            ),
            (
                "실제 계좌 보유 수량과 일치하는지 "
                "별도로 확인합니다."
            ),
            (
                "수동 승인 없이는 매도 주문을 생성하지 않습니다."
            ),
        ]

    elif sizing_action == "MAINTAIN_POSITION":
        next_actions = [
            (
                "현재 보유 수량을 그대로 유지합니다."
            ),
            (
                "추가 매수 또는 매도 수량을 생성하지 않습니다."
            ),
            (
                "새로운 시장 데이터에서 신호를 다시 계산합니다."
            ),
        ]

    elif sizing_action == "NO_ACTION":
        next_actions = [
            (
                "추가 수량 계산 없이 현재 상태를 유지합니다."
            ),
            (
                "새로운 Position Action이 생성되면 다시 계산합니다."
            ),
            (
                "주문 요청 단계로 전달하지 않습니다."
            ),
        ]

    else:
        next_actions = [
            (
                "수량 계산을 중단합니다."
            ),
            (
                "위험 판단 또는 입력값을 다시 확인합니다."
            ),
            (
                "문제가 해결되기 전 주문 요청 단계로 "
                "전달하지 않습니다."
            ),
        ]

    return (
        warnings,
        next_actions,
    )


def run_position_sizing_manager(
    symbol: str = "AAPL",
    risk_result: RiskDecisionResult | None = None,
    current_position: CurrentPosition | None = None,
    account_cash: float = 10_000.0,
    risk_limits: RiskLimits | None = None,
    sizing_limits: PositionSizingLimits | None = None,
    period: str = "5y",
    interval: str = "1d",
) -> PositionSizingResult:
    """
    V9.3 위험 판단 결과를 이용해 검토용 포지션 수량을 계산합니다.

    실제 주문은 생성하거나 전송하지 않습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    limits = (
        sizing_limits
        if sizing_limits is not None
        else PositionSizingLimits()
    )

    (
        limits_valid,
        limit_errors,
    ) = validate_sizing_limits(
        limits
    )

    if risk_result is None:
        risk_result = run_risk_decision_manager(
            symbol=normalized_symbol,
            current_position=current_position,
            risk_limits=risk_limits,
            period=period,
            interval=interval,
        )

    if risk_result.symbol != normalized_symbol:
        raise ValueError(
            "Risk Result Symbol과 요청 Symbol이 "
            "일치하지 않습니다."
        )

    (
        source_valid,
        source_errors,
    ) = validate_risk_result(
        risk_result
    )

    (
        account_checks_passed,
        account_errors,
    ) = validate_account_cash(
        account_cash=float(
            account_cash
        ),
        limits=limits,
    )

    price_checks_passed = (
        is_valid_number(
            risk_result.latest_close
        )
        and float(
            risk_result.latest_close
        ) > 0.0
    )

    risk_checks_passed = (
        risk_result.risk_decision
        in VALID_RISK_DECISIONS
        and is_valid_number(
            risk_result.risk_score
        )
        and 0.0
        <= float(risk_result.risk_score)
        <= 100.0
    )

    (
        sizing_action,
        sizing_action_label,
        sizing_required,
        action_reasons,
    ) = determine_sizing_action(
        risk_decision=(
            risk_result.risk_decision
        ),
        position_action=(
            risk_result.position_action
        ),
    )

    (
        reserved_cash,
        available_cash,
    ) = calculate_available_cash(
        account_cash=float(
            account_cash
        ),
        reserve_percent=(
            limits.cash_reserve_percent
        ),
    )

    target_position_value = 0.0
    affordable_position_value = 0.0
    proposed_position_value = 0.0

    raw_share_quantity = 0.0
    proposed_shares = 0

    estimated_cash_after_entry = float(
        account_cash
    )

    estimated_position_percent = 0.0

    sufficient_cash = True
    minimum_trade_value_passed = True
    share_limit_passed = True
    position_percent_passed = True

    current_shares = int(
        risk_result.current_shares
    )

    if sizing_action == "PREPARE_ENTRY":
        entry_metrics = (
            calculate_entry_position_size(
                account_cash=float(
                    account_cash
                ),
                available_cash=available_cash,
                approved_position_percent=float(
                    risk_result
                    .approved_position_percent
                ),
                latest_close=float(
                    risk_result.latest_close
                ),
                limits=limits,
            )
        )

        target_position_value = float(
            entry_metrics[
                "target_position_value"
            ]
        )

        affordable_position_value = float(
            entry_metrics[
                "affordable_position_value"
            ]
        )

        proposed_position_value = float(
            entry_metrics[
                "proposed_position_value"
            ]
        )

        raw_share_quantity = float(
            entry_metrics[
                "raw_share_quantity"
            ]
        )

        proposed_shares = int(
            entry_metrics[
                "proposed_shares"
            ]
        )

        sufficient_cash = bool(
            entry_metrics[
                "sufficient_cash"
            ]
        )

        minimum_trade_value_passed = bool(
            entry_metrics[
                "minimum_trade_value_passed"
            ]
        )

        share_limit_passed = bool(
            entry_metrics[
                "share_limit_passed"
            ]
        )

        estimated_cash_after_entry = float(
            entry_metrics[
                "estimated_cash_after_entry"
            ]
        )

        estimated_position_percent = float(
            entry_metrics[
                "estimated_position_percent"
            ]
        )

        position_percent_passed = bool(
            entry_metrics[
                "position_percent_passed"
            ]
        )

    elif sizing_action == "PREPARE_EXIT":
        proposed_shares = current_shares

        raw_share_quantity = float(
            proposed_shares
        )

        proposed_position_value = (
            float(proposed_shares)
            * float(risk_result.latest_close)
        )

        target_position_value = (
            proposed_position_value
        )

        affordable_position_value = (
            proposed_position_value
        )

        minimum_trade_value_passed = (
            proposed_position_value
            >= limits.minimum_trade_value
            or proposed_shares == 0
        )

        share_limit_passed = (
            proposed_shares
            <= limits.maximum_shares
        )

        sufficient_cash = True
        position_percent_passed = True

        estimated_cash_after_entry = (
            float(account_cash)
            + proposed_position_value
        )

        if account_cash <= 0:
            estimated_position_percent = 0.0

        else:
            estimated_position_percent = (
                proposed_position_value
                / float(account_cash)
                * 100.0
            )

    elif sizing_action == "MAINTAIN_POSITION":
        proposed_shares = current_shares

        raw_share_quantity = float(
            proposed_shares
        )

        proposed_position_value = (
            float(proposed_shares)
            * float(risk_result.latest_close)
        )

        target_position_value = (
            proposed_position_value
        )

        affordable_position_value = (
            proposed_position_value
        )

        estimated_cash_after_entry = float(
            account_cash
        )

        if account_cash <= 0:
            estimated_position_percent = 0.0

        else:
            estimated_position_percent = (
                proposed_position_value
                / float(account_cash)
                * 100.0
            )

    share_difference = (
        proposed_shares
        - current_shares
    )

    sizing_generated = (
        sizing_action
        in VALID_SIZING_ACTIONS
        and sizing_action != "BLOCKED"
    )

    sizing_checks_passed = (
        sufficient_cash
        and minimum_trade_value_passed
        and share_limit_passed
        and position_percent_passed
    )

    core_checks_passed = (
        source_valid
        and account_checks_passed
        and price_checks_passed
        and risk_checks_passed
        and limits_valid
    )

    all_checks_passed = (
        core_checks_passed
        and sizing_checks_passed
        and sizing_generated
    )

    sizing_status = determine_sizing_status(
        sizing_action=sizing_action,
        sizing_generated=sizing_generated,
        core_checks_passed=(
            core_checks_passed
        ),
    )

    reasons: list[str] = []

    reasons.extend(
        action_reasons
    )

    if sizing_action == "PREPARE_ENTRY":
        reasons.extend(
            [
                (
                    f"가상 계좌 현금은 "
                    f"${float(account_cash):,.2f}입니다."
                ),
                (
                    f"현금 준비금 "
                    f"{limits.cash_reserve_percent:.2f}%를 "
                    "제외했습니다."
                ),
                (
                    f"승인 포지션 비율은 "
                    f"{risk_result.approved_position_percent:.2f}%입니다."
                ),
                (
                    f"최근 종가는 "
                    f"${risk_result.latest_close:,.2f}입니다."
                ),
                (
                    f"예상 진입 수량은 "
                    f"{proposed_shares}주입니다."
                ),
            ]
        )

    elif sizing_action == "PREPARE_EXIT":
        reasons.append(
            f"현재 보유 수량 {current_shares}주를 "
            "종료 검토 수량으로 사용했습니다."
        )

    elif sizing_action == "MAINTAIN_POSITION":
        reasons.append(
            f"현재 보유 수량 {current_shares}주를 "
            "그대로 유지합니다."
        )

    (
        warnings,
        next_actions,
    ) = build_sizing_notes(
        sizing_action=sizing_action,
        proposed_shares=proposed_shares,
        approved_position_percent=float(
            risk_result.approved_position_percent
        ),
        source_errors=source_errors,
        account_errors=account_errors,
        limit_errors=limit_errors,
    )

    result = PositionSizingResult(
        version="V9.4",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        source_risk_decision_file=(
            risk_result.latest_path
            or risk_result.report_path
            or risk_result.source_position_state_file
        ),

        sizing_status=sizing_status,
        sizing_action=sizing_action,
        sizing_action_label=(
            sizing_action_label
        ),

        position_state=(
            risk_result.position_state
        ),
        position_action=(
            risk_result.position_action
        ),
        signal=risk_result.signal,

        risk_status=risk_result.risk_status,
        risk_decision=(
            risk_result.risk_decision
        ),
        risk_level=risk_result.risk_level,
        risk_score=float(
            risk_result.risk_score
        ),

        account_cash=float(
            account_cash
        ),
        cash_reserve_percent=float(
            limits.cash_reserve_percent
        ),
        reserved_cash=float(
            reserved_cash
        ),
        available_cash=float(
            available_cash
        ),

        requested_position_percent=float(
            risk_result.requested_position_percent
        ),
        approved_position_percent=float(
            risk_result.approved_position_percent
        ),

        latest_close=float(
            risk_result.latest_close
        ),
        estimated_entry_price=float(
            risk_result.latest_close
        ),

        target_position_value=float(
            target_position_value
        ),
        affordable_position_value=float(
            affordable_position_value
        ),
        proposed_position_value=float(
            proposed_position_value
        ),

        raw_share_quantity=float(
            raw_share_quantity
        ),
        proposed_shares=int(
            proposed_shares
        ),
        current_shares=int(
            current_shares
        ),
        share_difference=int(
            share_difference
        ),

        estimated_cash_after_entry=float(
            estimated_cash_after_entry
        ),
        estimated_position_percent=float(
            estimated_position_percent
        ),

        maximum_shares=int(
            limits.maximum_shares
        ),
        minimum_trade_value=float(
            limits.minimum_trade_value
        ),

        sizing_required=bool(
            sizing_required
        ),
        sizing_generated=bool(
            sizing_generated
        ),
        sufficient_cash=bool(
            sufficient_cash
        ),
        minimum_trade_value_passed=bool(
            minimum_trade_value_passed
        ),
        share_limit_passed=bool(
            share_limit_passed
        ),
        position_percent_passed=bool(
            position_percent_passed
        ),

        source_loaded=True,
        source_valid=bool(
            source_valid
        ),
        account_checks_passed=bool(
            account_checks_passed
        ),
        price_checks_passed=bool(
            price_checks_passed
        ),
        risk_checks_passed=bool(
            risk_checks_passed
        ),
        sizing_checks_passed=bool(
            sizing_checks_passed
        ),
        all_checks_passed=bool(
            all_checks_passed
        ),

        order_generated=False,
        paper_order_generated=False,
        live_order_generated=False,
        execution_blocked=True,
        manual_approval_required=True,

        sizing_limits=limits,

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_position_sizing_manager(
        result
    )

    return result


def save_position_sizing_manager(
    result: PositionSizingResult,
) -> tuple[
    Path,
    Path,
]:
    """
    V9.4 결과를 JSON으로 저장합니다.
    """

    POSITION_SIZING_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        POSITION_SIZING_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "position_sizing_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        POSITION_SIZING_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "position_sizing_latest.json"
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


def print_position_sizing_manager(
    result: PositionSizingResult,
) -> None:
    """
    V9.4 Position Sizing 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V9.4 "
        "POSITION SIZING MANAGER"
    )
    print("=" * 140)

    print(
        f"Sizing status                  : "
        f"{result.sizing_status}"
    )

    print(
        f"Sizing action                  : "
        f"{result.sizing_action}"
    )

    print(
        f"Sizing action label            : "
        f"{result.sizing_action_label}"
    )

    print()
    print("SOURCE DECISION")
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
        f"Risk decision                  : "
        f"{result.risk_decision}"
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
    print("ACCOUNT")
    print("-" * 140)

    print(
        f"Account cash                   : "
        f"${result.account_cash:,.2f}"
    )

    print(
        f"Cash reserve percent           : "
        f"{result.cash_reserve_percent:.2f}%"
    )

    print(
        f"Reserved cash                  : "
        f"${result.reserved_cash:,.2f}"
    )

    print(
        f"Available cash                 : "
        f"${result.available_cash:,.2f}"
    )

    print()
    print("POSITION SIZE")
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
        f"Latest close                   : "
        f"${result.latest_close:,.2f}"
    )

    print(
        f"Target position value          : "
        f"${result.target_position_value:,.2f}"
    )

    print(
        f"Affordable position value      : "
        f"${result.affordable_position_value:,.2f}"
    )

    print(
        f"Proposed position value        : "
        f"${result.proposed_position_value:,.2f}"
    )

    print(
        f"Raw share quantity             : "
        f"{result.raw_share_quantity:.4f}"
    )

    print(
        f"Proposed shares                : "
        f"{result.proposed_shares}"
    )

    print(
        f"Current shares                 : "
        f"{result.current_shares}"
    )

    print(
        f"Share difference               : "
        f"{result.share_difference:+d}"
    )

    print(
        f"Estimated position percent     : "
        f"{result.estimated_position_percent:.2f}%"
    )

    print(
        f"Estimated cash after entry     : "
        f"${result.estimated_cash_after_entry:,.2f}"
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
        f"Account checks passed          : "
        f"{result.account_checks_passed}"
    )

    print(
        f"Price checks passed            : "
        f"{result.price_checks_passed}"
    )

    print(
        f"Risk checks passed             : "
        f"{result.risk_checks_passed}"
    )

    print(
        f"Sizing generated               : "
        f"{result.sizing_generated}"
    )

    print(
        f"Sufficient cash                : "
        f"{result.sufficient_cash}"
    )

    print(
        f"Minimum trade value passed     : "
        f"{result.minimum_trade_value_passed}"
    )

    print(
        f"Share limit passed             : "
        f"{result.share_limit_passed}"
    )

    print(
        f"Position percent passed        : "
        f"{result.position_percent_passed}"
    )

    print(
        f"Sizing checks passed           : "
        f"{result.sizing_checks_passed}"
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
        f"Source Risk Decision file      : "
        f"{result.source_risk_decision_file}"
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
        "주의: 이 모듈은 검토용 포지션 수량만 계산하며 "
        "실제 주문, 모의 주문 또는 실거래 주문을 "
        "생성하거나 전송하지 않습니다."
    )