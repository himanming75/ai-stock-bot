import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.signal_engine_runtime_adapter import (
    SignalEngineRuntimeResult,
    run_signal_engine_runtime_adapter,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

POSITION_STATE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "position_state"
)


VALID_POSITION_STATES = {
    "FLAT",
    "LONG",
}


VALID_POSITION_ACTIONS = {
    "ENTER_LONG",
    "HOLD_POSITION",
    "EXIT_LONG",
    "NO_ACTION",
    "BLOCKED",
}


VALID_MANAGER_STATUSES = {
    "READY",
    "LIMITED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class CurrentPosition:
    """
    현재 포지션 상태입니다.

    V9.2에서는 실제 증권 계좌를 조회하지 않습니다.
    테스트 또는 연구 목적으로 전달된 상태만 사용합니다.
    """

    state: str = "FLAT"
    shares: int = 0
    average_price: float = 0.0
    entry_date: str | None = None
    holding_days: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PositionStateResult:
    """
    V9.2 Position State Manager 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    source_signal_file: str | None

    manager_status: str
    position_state: str
    signal: str

    recommended_action: str
    action_label: str
    action_required: bool

    current_position: CurrentPosition

    current_score: float
    entry_score: float
    exit_score: float
    latest_close: float
    latest_date: str

    strategy_source: str
    strategy_status: str
    strategy_name: str | None
    strategy_type: str | None

    maximum_holding_days: int
    position_percent: float
    holding_limit_reached: bool

    signal_result_loaded: bool
    position_loaded: bool
    position_valid: bool
    signal_valid: bool
    transition_valid: bool
    action_generated: bool

    order_generated: bool
    paper_order_generated: bool
    live_order_generated: bool
    execution_blocked: bool
    manual_approval_required: bool

    all_checks_passed: bool

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["current_position"] = (
            self.current_position.to_dict()
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


def normalize_position(
    position: CurrentPosition | None,
) -> CurrentPosition:
    """
    포지션이 전달되지 않은 경우 FLAT 상태를 생성합니다.
    """

    if position is None:
        return CurrentPosition(
            state="FLAT",
            shares=0,
            average_price=0.0,
            entry_date=None,
            holding_days=0,
        )

    normalized_state = (
        position.state
        .strip()
        .upper()
    )

    return CurrentPosition(
        state=normalized_state,
        shares=int(position.shares),
        average_price=float(position.average_price),
        entry_date=position.entry_date,
        holding_days=int(position.holding_days),
    )


def validate_position(
    position: CurrentPosition,
) -> tuple[
    bool,
    list[str],
]:
    """
    현재 포지션 데이터의 일관성을 검사합니다.
    """

    errors: list[str] = []

    if position.state not in VALID_POSITION_STATES:
        errors.append(
            f"올바르지 않은 Position State입니다: "
            f"{position.state}"
        )

        return (
            False,
            errors,
        )

    if position.shares < 0:
        errors.append(
            "Shares는 음수가 될 수 없습니다."
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

        if position.holding_days != 0:
            errors.append(
                "FLAT 상태에서는 Holding Days가 "
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


def validate_signal_result(
    signal_result: SignalEngineRuntimeResult,
) -> tuple[
    bool,
    list[str],
]:
    """
    V9.1 Signal Engine 결과를 검사합니다.
    """

    errors: list[str] = []

    if signal_result.version != "V9.1":
        errors.append(
            "Signal Result 버전이 V9.1이 아닙니다."
        )

    if signal_result.signal not in {
        "BUY",
        "HOLD",
        "SELL",
    }:
        errors.append(
            f"올바르지 않은 Signal입니다: "
            f"{signal_result.signal}"
        )

    if not signal_result.signal_generated:
        errors.append(
            "Signal Generated가 False입니다."
        )

    if not signal_result.all_checks_passed:
        errors.append(
            "V9.1 Signal Engine 검사가 통과되지 않았습니다."
        )

    if not signal_result.execution_blocked:
        errors.append(
            "V9.1에서 Execution이 차단되지 않았습니다."
        )

    return (
        not errors,
        errors,
    )


def determine_position_action(
    position_state: str,
    signal: str,
    holding_limit_reached: bool = False,
) -> tuple[
    str,
    str,
    bool,
    list[str],
]:
    """
    현재 포지션과 Signal을 조합하여 행동을 결정합니다.

    FLAT + BUY:
        ENTER_LONG

    FLAT + HOLD:
        NO_ACTION

    FLAT + SELL:
        NO_ACTION

    LONG + BUY:
        HOLD_POSITION

    LONG + HOLD:
        HOLD_POSITION

    LONG + SELL:
        EXIT_LONG

    최대 보유기간 도달:
        LONG 상태라면 EXIT_LONG
    """

    normalized_position = (
        position_state
        .strip()
        .upper()
    )

    normalized_signal = (
        signal
        .strip()
        .upper()
    )

    if normalized_position not in VALID_POSITION_STATES:
        return (
            "BLOCKED",
            "판단 차단",
            False,
            [
                "올바르지 않은 Position State입니다."
            ],
        )

    if normalized_signal not in {
        "BUY",
        "HOLD",
        "SELL",
    }:
        return (
            "BLOCKED",
            "판단 차단",
            False,
            [
                "올바르지 않은 Signal입니다."
            ],
        )

    if (
        normalized_position == "LONG"
        and holding_limit_reached
    ):
        return (
            "EXIT_LONG",
            "보유기간 종료 검토",
            True,
            [
                "최대 보유기간에 도달했습니다.",
                "Signal과 관계없이 포지션 종료 검토가 필요합니다.",
            ],
        )

    if normalized_position == "FLAT":
        if normalized_signal == "BUY":
            return (
                "ENTER_LONG",
                "신규 매수 검토",
                True,
                [
                    "현재 포지션은 FLAT입니다.",
                    "Signal Engine에서 BUY 신호가 생성되었습니다.",
                    "신규 Long 포지션 진입 조건입니다.",
                ],
            )

        if normalized_signal == "HOLD":
            return (
                "NO_ACTION",
                "관망 유지",
                False,
                [
                    "현재 보유 포지션이 없습니다.",
                    "Signal이 HOLD이므로 신규 진입하지 않습니다.",
                ],
            )

        return (
            "NO_ACTION",
            "미보유 상태 유지",
            False,
            [
                "현재 보유 포지션이 없습니다.",
                "SELL 신호이지만 청산할 포지션이 없습니다.",
            ],
        )

    if normalized_signal == "SELL":
        return (
            "EXIT_LONG",
            "보유 포지션 종료 검토",
            True,
            [
                "현재 Long 포지션을 보유하고 있습니다.",
                "Signal Engine에서 SELL 신호가 생성되었습니다.",
                "Long 포지션 종료 조건입니다.",
            ],
        )

    if normalized_signal == "BUY":
        return (
            "HOLD_POSITION",
            "기존 포지션 유지",
            False,
            [
                "현재 Long 포지션을 보유하고 있습니다.",
                "BUY 신호가 유지되고 있습니다.",
                "V9.2에서는 추가 매수나 피라미딩을 허용하지 않습니다.",
            ],
        )

    return (
        "HOLD_POSITION",
        "기존 포지션 유지",
        False,
        [
            "현재 Long 포지션을 보유하고 있습니다.",
            "Signal이 HOLD이므로 기존 포지션을 유지합니다.",
        ],
    )


def validate_transition(
    position_state: str,
    action: str,
) -> tuple[
    bool,
    list[str],
]:
    """
    포지션 상태와 추천 행동의 조합이 유효한지 검사합니다.
    """

    errors: list[str] = []

    allowed_transitions = {
        "FLAT": {
            "ENTER_LONG",
            "NO_ACTION",
            "BLOCKED",
        },
        "LONG": {
            "HOLD_POSITION",
            "EXIT_LONG",
            "BLOCKED",
        },
    }

    allowed_actions = allowed_transitions.get(
        position_state,
        set(),
    )

    if action not in allowed_actions:
        errors.append(
            f"{position_state} 상태에서 {action} 행동은 "
            "허용되지 않습니다."
        )

    return (
        not errors,
        errors,
    )


def determine_manager_status(
    signal_valid: bool,
    position_valid: bool,
    transition_valid: bool,
    action_generated: bool,
) -> str:
    """
    Position State Manager 상태를 결정합니다.
    """

    if not (
        signal_valid
        and position_valid
        and transition_valid
    ):
        return "FAILED"

    if not action_generated:
        return "BLOCKED"

    return "READY"


def build_position_notes(
    action: str,
    action_required: bool,
    holding_limit_reached: bool,
    position_errors: list[str],
    signal_errors: list[str],
    transition_errors: list[str],
) -> tuple[
    list[str],
    list[str],
]:
    """
    경고와 다음 작업을 생성합니다.
    """

    warnings: list[str] = []

    warnings.extend(
        position_errors
    )

    warnings.extend(
        signal_errors
    )

    warnings.extend(
        transition_errors
    )

    warnings.extend(
        [
            (
                "추천 행동은 포지션 상태 분석 결과이며 "
                "증권 주문이 아닙니다."
            ),
            (
                "V9.2는 Broker, 계좌 또는 주문 API를 "
                "호출하지 않습니다."
            ),
            (
                "모든 Paper Order와 Live Order는 "
                "계속 차단됩니다."
            ),
        ]
    )

    if holding_limit_reached:
        warnings.append(
            "최대 보유기간에 도달했습니다."
        )

    if action_required:
        next_actions = [
            (
                f"추천 행동 {action}을 V9.3 Risk Decision "
                "Manager에 전달합니다."
            ),
            (
                "포지션 크기와 예상 위험을 별도로 계산합니다."
            ),
            (
                "실행 전 수동 승인 여부를 확인합니다."
            ),
        ]

    else:
        next_actions = [
            (
                f"현재 추천 행동 {action} 상태를 유지합니다."
            ),
            (
                "새로운 시장 데이터가 추가되면 Signal을 "
                "다시 계산합니다."
            ),
            (
                "실제 주문 모듈에는 전달하지 않습니다."
            ),
        ]

    return (
        warnings,
        next_actions,
    )


def run_position_state_manager(
    symbol: str = "AAPL",
    current_position: CurrentPosition | None = None,
    signal_result: SignalEngineRuntimeResult | None = None,
    period: str = "5y",
    interval: str = "1d",
) -> PositionStateResult:
    """
    V9.1 Signal과 현재 포지션을 비교하여
    Position Action을 생성합니다.

    실제 주문은 생성하지 않습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if signal_result is None:
        signal_result = (
            run_signal_engine_runtime_adapter(
                symbol=normalized_symbol,
                period=period,
                interval=interval,
            )
        )

    if signal_result.symbol != normalized_symbol:
        raise ValueError(
            "Signal Result Symbol과 요청 Symbol이 "
            "일치하지 않습니다."
        )

    position = normalize_position(
        current_position
    )

    (
        position_valid,
        position_errors,
    ) = validate_position(
        position
    )

    (
        signal_valid,
        signal_errors,
    ) = validate_signal_result(
        signal_result
    )

    holding_limit_reached = (
        position.state == "LONG"
        and position.holding_days
        >= signal_result.parameters.maximum_holding_days
    )

    (
        recommended_action,
        action_label,
        action_required,
        reasons,
    ) = determine_position_action(
        position_state=position.state,
        signal=signal_result.signal,
        holding_limit_reached=(
            holding_limit_reached
        ),
    )

    (
        transition_valid,
        transition_errors,
    ) = validate_transition(
        position_state=position.state,
        action=recommended_action,
    )

    action_generated = (
        recommended_action
        in VALID_POSITION_ACTIONS
        and recommended_action != "BLOCKED"
        and position_valid
        and signal_valid
        and transition_valid
    )

    manager_status = determine_manager_status(
        signal_valid=signal_valid,
        position_valid=position_valid,
        transition_valid=transition_valid,
        action_generated=action_generated,
    )

    (
        warnings,
        next_actions,
    ) = build_position_notes(
        action=recommended_action,
        action_required=action_required,
        holding_limit_reached=(
            holding_limit_reached
        ),
        position_errors=position_errors,
        signal_errors=signal_errors,
        transition_errors=transition_errors,
    )

    all_checks_passed = (
        signal_result.all_checks_passed
        and signal_valid
        and position_valid
        and transition_valid
        and action_generated
    )

    result = PositionStateResult(
        version="V9.2",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        source_signal_file=(
            signal_result.latest_path
            or signal_result.report_path
            or signal_result.source_trading_engine_file
        ),

        manager_status=manager_status,
        position_state=position.state,
        signal=signal_result.signal,

        recommended_action=recommended_action,
        action_label=action_label,
        action_required=action_required,

        current_position=position,

        current_score=float(
            signal_result.current_score
        ),
        entry_score=float(
            signal_result.entry_score
        ),
        exit_score=float(
            signal_result.exit_score
        ),
        latest_close=float(
            signal_result.latest_close
        ),
        latest_date=signal_result.latest_date,

        strategy_source=(
            signal_result.strategy_source
        ),
        strategy_status=(
            signal_result.strategy_status
        ),
        strategy_name=(
            signal_result.strategy_name
        ),
        strategy_type=(
            signal_result.strategy_type
        ),

        maximum_holding_days=int(
            signal_result
            .parameters
            .maximum_holding_days
        ),
        position_percent=float(
            signal_result
            .parameters
            .position_percent
        ),
        holding_limit_reached=(
            holding_limit_reached
        ),

        signal_result_loaded=True,
        position_loaded=True,
        position_valid=position_valid,
        signal_valid=signal_valid,
        transition_valid=transition_valid,
        action_generated=action_generated,

        order_generated=False,
        paper_order_generated=False,
        live_order_generated=False,
        execution_blocked=True,
        manual_approval_required=True,

        all_checks_passed=(
            all_checks_passed
        ),

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_position_state_manager(
        result
    )

    return result


def save_position_state_manager(
    result: PositionStateResult,
) -> tuple[
    Path,
    Path,
]:
    """
    V9.2 Position State 결과를 JSON으로 저장합니다.
    """

    POSITION_STATE_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        POSITION_STATE_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "position_state_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        POSITION_STATE_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "position_state_latest.json"
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


def print_position_state_manager(
    result: PositionStateResult,
) -> None:
    """
    V9.2 Position State Manager 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V9.2 "
        "POSITION STATE MANAGER"
    )
    print("=" * 140)

    print(
        f"Manager status                 : "
        f"{result.manager_status}"
    )

    print(
        f"Position state                 : "
        f"{result.position_state}"
    )

    print(
        f"Signal                         : "
        f"{result.signal}"
    )

    print(
        f"Recommended action             : "
        f"{result.recommended_action}"
    )

    print(
        f"Action label                   : "
        f"{result.action_label}"
    )

    print(
        f"Action required                : "
        f"{result.action_required}"
    )

    print()
    print("CURRENT POSITION")
    print("-" * 140)

    print(
        f"State                          : "
        f"{result.current_position.state}"
    )

    print(
        f"Shares                         : "
        f"{result.current_position.shares}"
    )

    print(
        f"Average price                  : "
        f"${result.current_position.average_price:,.2f}"
    )

    print(
        f"Entry date                     : "
        f"{result.current_position.entry_date}"
    )

    print(
        f"Holding days                   : "
        f"{result.current_position.holding_days}"
    )

    print(
        f"Maximum holding days           : "
        f"{result.maximum_holding_days}"
    )

    print(
        f"Holding limit reached          : "
        f"{result.holding_limit_reached}"
    )

    print()
    print("MARKET AND SIGNAL")
    print("-" * 140)

    print(
        f"Latest date                    : "
        f"{result.latest_date}"
    )

    print(
        f"Latest close                   : "
        f"${result.latest_close:,.2f}"
    )

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
        f"Position percent               : "
        f"{result.position_percent:.2f}%"
    )

    print()
    print("VALIDATION")
    print("-" * 140)

    print(
        f"Signal result loaded           : "
        f"{result.signal_result_loaded}"
    )

    print(
        f"Position loaded                : "
        f"{result.position_loaded}"
    )

    print(
        f"Position valid                 : "
        f"{result.position_valid}"
    )

    print(
        f"Signal valid                   : "
        f"{result.signal_valid}"
    )

    print(
        f"Transition valid               : "
        f"{result.transition_valid}"
    )

    print(
        f"Action generated               : "
        f"{result.action_generated}"
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
        f"Source Signal file             : "
        f"{result.source_signal_file}"
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
        "주의: 이 모듈은 포지션 상태와 추천 행동만 "
        "판단하며 실제 주문을 생성하거나 전송하지 않습니다."
    )