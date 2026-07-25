import math
from dataclasses import asdict, dataclass

from config import (
    ACCOUNT_SIZE,
    MAX_POSITION_PERCENT,
    MIN_ACCEPTABLE_RISK_REWARD,
    RISK_PER_TRADE,
)
from forecast.predictor import TradePlan


@dataclass
class PositionPlan:
    """
    한 종목의 포지션 크기와 예상 손익 계획입니다.
    """

    symbol: str

    account_size: float
    risk_per_trade_percent: float
    maximum_risk_amount: float

    reference_entry: float
    stop_loss: float
    target_1: float
    target_2: float

    risk_per_share: float

    shares_by_risk: int
    shares_by_position_limit: int
    recommended_shares: int

    investment_amount: float
    position_percent: float

    expected_loss_amount: float
    expected_profit_1: float
    expected_profit_2: float

    actual_account_risk_percent: float

    risk_reward_1: float
    risk_reward_2: float

    position_status: str
    warning: str

    def to_dict(self) -> dict:
        """
        JSON 저장용 딕셔너리로 변환합니다.
        """

        return asdict(self)


def validate_positive_number(
    name: str,
    value: float,
) -> float:
    """
    값이 0보다 큰 정상적인 숫자인지 검사합니다.
    """

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(
            f"{name} 값이 정상적인 숫자가 아닙니다: {value}"
        )

    if number <= 0:
        raise ValueError(
            f"{name} 값은 0보다 커야 합니다: {value}"
        )

    return number


def determine_position_status(
    trade_plan: TradePlan,
    recommended_shares: int,
    risk_reward_2: float,
) -> tuple[str, str]:
    """
    매매계획과 포지션 크기를 바탕으로
    포지션 사용 가능 여부를 판단합니다.
    """

    if trade_plan.plan_status == "AVOID":
        return (
            "DO_NOT_ENTER",
            "기술적 매매계획이 AVOID 상태입니다.",
        )

    if recommended_shares <= 0:
        return (
            "NO_POSITION",
            "현재 계좌 크기와 위험 제한으로는 매수 가능한 수량이 없습니다.",
        )

    if risk_reward_2 < MIN_ACCEPTABLE_RISK_REWARD:
        return (
            "LOW_REWARD",
            (
                "2차 목표가 기준 Risk/Reward가 "
                f"{MIN_ACCEPTABLE_RISK_REWARD:.2f}보다 낮습니다."
            ),
        )

    if trade_plan.plan_status == "ATTRACTIVE":
        return (
            "READY",
            "위험 한도와 Risk/Reward 기준을 충족합니다.",
        )

    if trade_plan.plan_status == "WATCH":
        return (
            "WATCH",
            "진입 전 추가 확인이 필요한 매매계획입니다.",
        )

    return (
        "CAUTION",
        "매매계획의 신뢰도가 낮아 보수적인 접근이 필요합니다.",
    )


def create_position_plan(
    trade_plan: TradePlan,
    account_size: float = ACCOUNT_SIZE,
    risk_per_trade: float = RISK_PER_TRADE,
    max_position_percent: float = MAX_POSITION_PERCENT,
) -> PositionPlan:
    """
    TradePlan을 이용해 적정 매수 수량과 예상 손익을 계산합니다.

    포지션 크기 제한:

    1. 손절 시 최대 허용 손실 기준
    2. 한 종목 최대 투자 비중 기준

    두 기준 중 더 작은 수량을 사용합니다.
    """

    account_size = validate_positive_number(
        "account_size",
        account_size,
    )

    risk_per_trade = validate_positive_number(
        "risk_per_trade",
        risk_per_trade,
    )

    max_position_percent = validate_positive_number(
        "max_position_percent",
        max_position_percent,
    )

    if risk_per_trade > 1:
        raise ValueError(
            "risk_per_trade는 0과 1 사이의 비율이어야 합니다."
        )

    if max_position_percent > 1:
        raise ValueError(
            "max_position_percent는 0과 1 사이의 비율이어야 합니다."
        )

    reference_entry = (
        float(trade_plan.entry_low)
        + float(trade_plan.entry_high)
    ) / 2

    stop_loss = float(
        trade_plan.stop_loss
    )

    target_1 = float(
        trade_plan.target_1
    )

    target_2 = float(
        trade_plan.target_2
    )

    if stop_loss >= reference_entry:
        raise ValueError(
            "Stop Loss는 진입 기준가보다 낮아야 합니다."
        )

    risk_per_share = (
        reference_entry - stop_loss
    )

    maximum_risk_amount = (
        account_size * risk_per_trade
    )

    maximum_position_amount = (
        account_size * max_position_percent
    )

    shares_by_risk = int(
        maximum_risk_amount
        // risk_per_share
    )

    shares_by_position_limit = int(
        maximum_position_amount
        // reference_entry
    )

    recommended_shares = min(
        shares_by_risk,
        shares_by_position_limit,
    )

    recommended_shares = max(
        0,
        recommended_shares,
    )

    investment_amount = (
        recommended_shares
        * reference_entry
    )

    expected_loss_amount = (
        recommended_shares
        * risk_per_share
    )

    expected_profit_1 = (
        recommended_shares
        * max(
            0.0,
            target_1 - reference_entry,
        )
    )

    expected_profit_2 = (
        recommended_shares
        * max(
            0.0,
            target_2 - reference_entry,
        )
    )

    position_percent = (
        investment_amount
        / account_size
        * 100
        if account_size > 0
        else 0.0
    )

    actual_account_risk_percent = (
        expected_loss_amount
        / account_size
        * 100
        if account_size > 0
        else 0.0
    )

    risk_reward_1 = (
        expected_profit_1
        / expected_loss_amount
        if expected_loss_amount > 0
        else 0.0
    )

    risk_reward_2 = (
        expected_profit_2
        / expected_loss_amount
        if expected_loss_amount > 0
        else 0.0
    )

    position_status, warning = determine_position_status(
        trade_plan=trade_plan,
        recommended_shares=recommended_shares,
        risk_reward_2=risk_reward_2,
    )

    return PositionPlan(
        symbol=trade_plan.symbol,

        account_size=round(
            account_size,
            2,
        ),

        risk_per_trade_percent=round(
            risk_per_trade * 100,
            2,
        ),

        maximum_risk_amount=round(
            maximum_risk_amount,
            2,
        ),

        reference_entry=round(
            reference_entry,
            2,
        ),

        stop_loss=round(
            stop_loss,
            2,
        ),

        target_1=round(
            target_1,
            2,
        ),

        target_2=round(
            target_2,
            2,
        ),

        risk_per_share=round(
            risk_per_share,
            2,
        ),

        shares_by_risk=shares_by_risk,

        shares_by_position_limit=(
            shares_by_position_limit
        ),

        recommended_shares=(
            recommended_shares
        ),

        investment_amount=round(
            investment_amount,
            2,
        ),

        position_percent=round(
            position_percent,
            2,
        ),

        expected_loss_amount=round(
            expected_loss_amount,
            2,
        ),

        expected_profit_1=round(
            expected_profit_1,
            2,
        ),

        expected_profit_2=round(
            expected_profit_2,
            2,
        ),

        actual_account_risk_percent=round(
            actual_account_risk_percent,
            2,
        ),

        risk_reward_1=round(
            risk_reward_1,
            2,
        ),

        risk_reward_2=round(
            risk_reward_2,
            2,
        ),

        position_status=position_status,
        warning=warning,
    )


def print_position_plan(
    position_plan: PositionPlan,
) -> None:
    """
    포지션 계획을 터미널에 출력합니다.
    """

    print()
    print("=" * 60)
    print(
        f"{position_plan.symbol} POSITION PLAN"
    )
    print("=" * 60)

    print(
        f"Position status    : "
        f"{position_plan.position_status}"
    )

    print(
        f"Account size       : "
        f"${position_plan.account_size:,.2f}"
    )

    print(
        f"Risk per trade     : "
        f"{position_plan.risk_per_trade_percent:.2f}%"
    )

    print(
        f"Maximum risk       : "
        f"${position_plan.maximum_risk_amount:,.2f}"
    )

    print("-" * 60)

    print(
        f"Reference entry    : "
        f"${position_plan.reference_entry:,.2f}"
    )

    print(
        f"Stop loss          : "
        f"${position_plan.stop_loss:,.2f}"
    )

    print(
        f"Risk per share     : "
        f"${position_plan.risk_per_share:,.2f}"
    )

    print("-" * 60)

    print(
        f"Shares by risk     : "
        f"{position_plan.shares_by_risk}"
    )

    print(
        f"Shares by max size : "
        f"{position_plan.shares_by_position_limit}"
    )

    print(
        f"Recommended shares : "
        f"{position_plan.recommended_shares}"
    )

    print(
        f"Investment amount  : "
        f"${position_plan.investment_amount:,.2f}"
    )

    print(
        f"Position percent   : "
        f"{position_plan.position_percent:.2f}%"
    )

    print("-" * 60)

    print(
        f"Expected loss      : "
        f"${position_plan.expected_loss_amount:,.2f}"
    )

    print(
        f"Account risk       : "
        f"{position_plan.actual_account_risk_percent:.2f}%"
    )

    print(
        f"Expected profit 1  : "
        f"${position_plan.expected_profit_1:,.2f}"
    )

    print(
        f"Expected profit 2  : "
        f"${position_plan.expected_profit_2:,.2f}"
    )

    print(
        f"Risk/Reward 1      : "
        f"{position_plan.risk_reward_1:.2f}"
    )

    print(
        f"Risk/Reward 2      : "
        f"{position_plan.risk_reward_2:.2f}"
    )

    print("-" * 60)
    print(
        f"Note                : "
        f"{position_plan.warning}"
    )

    print()
    print(
        "This position size is a risk-management calculation, "
        "not an instruction to trade."
    )