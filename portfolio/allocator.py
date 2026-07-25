import math
from dataclasses import asdict, dataclass
from typing import Any

from config import (
    ACCOUNT_SIZE,
    MAX_ALLOCATION_PER_STOCK,
    MAX_PORTFOLIO_POSITIONS,
    MIN_AI_CONFIDENCE,
    MIN_ALLOCATION_SCORE,
    MIN_CASH_RESERVE_PERCENT,
)
from portfolio.manager import PositionPlan


@dataclass
class AllocationCandidate:
    """
    포트폴리오 배분을 위한 한 종목의 입력 데이터입니다.
    """

    symbol: str

    final_score: float
    ai_confidence: int
    risk_level: str

    technical_signal: str
    ai_signal: str
    plan_status: str

    position_plan: PositionPlan


@dataclass
class StockAllocation:
    """
    한 종목에 최종적으로 배정된 투자 계획입니다.
    """

    rank: int
    symbol: str

    allocation_status: str
    allocation_score: float

    allocated_amount: float
    allocation_percent: float
    shares: int

    reference_entry: float
    stop_loss: float
    target_1: float
    target_2: float

    expected_loss_amount: float
    expected_profit_1: float
    expected_profit_2: float

    actual_account_risk_percent: float

    final_score: float
    ai_confidence: int
    risk_level: str
    plan_status: str

    note: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PortfolioAllocation:
    """
    계좌 전체의 최종 자금 배분 결과입니다.
    """

    account_size: float

    maximum_investable_amount: float
    total_allocated_amount: float

    cash_reserve_amount: float
    cash_reserve_percent: float

    total_expected_loss: float
    total_expected_profit_1: float
    total_expected_profit_2: float

    total_account_risk_percent: float

    selected_count: int
    rejected_count: int

    allocations: list[StockAllocation]
    rejected_symbols: list[dict[str, str]]

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_text(
    value: Any,
) -> str:
    """
    문자열 값을 대문자로 정리합니다.
    """

    return (
        str(value)
        .upper()
        .strip()
    )


def validate_ratio(
    name: str,
    value: float,
) -> float:
    """
    0부터 1 사이의 비율인지 검사합니다.
    """

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(
            f"{name} 값이 정상적인 숫자가 아닙니다."
        )

    if number < 0 or number > 1:
        raise ValueError(
            f"{name} 값은 0부터 1 사이여야 합니다."
        )

    return number


def calculate_risk_multiplier(
    risk_level: str,
) -> float:
    """
    AI 위험도에 따라 배분 점수를 조절합니다.
    """

    normalized = normalize_text(
        risk_level
    )

    mapping = {
        "LOW": 1.00,
        "MEDIUM": 0.85,
        "HIGH": 0.55,
    }

    return mapping.get(
        normalized,
        0.55,
    )


def calculate_plan_multiplier(
    plan_status: str,
) -> float:
    """
    기술적 매매계획 상태에 따라 배분 점수를 조절합니다.
    """

    normalized = normalize_text(
        plan_status
    )

    mapping = {
        "ATTRACTIVE": 1.00,
        "WATCH": 0.75,
        "WEAK": 0.45,
        "AVOID": 0.00,
    }

    return mapping.get(
        normalized,
        0.40,
    )


def calculate_signal_multiplier(
    technical_signal: str,
    ai_signal: str,
) -> float:
    """
    기술 신호와 AI 신호의 일치 여부를 평가합니다.
    """

    technical = normalize_text(
        technical_signal
    )

    ai = normalize_text(
        ai_signal
    )

    if technical == "BUY" and ai == "BUY":
        return 1.00

    if (
        technical in {"BUY", "HOLD"}
        and ai in {"BUY", "HOLD"}
    ):
        return 0.75

    if technical == "SELL" or ai == "SELL":
        return 0.00

    return 0.50


def calculate_allocation_score(
    candidate: AllocationCandidate,
) -> float:
    """
    포트폴리오 배분용 종합점수를 계산합니다.

    구성:
    - 기존 최종점수: 70%
    - AI 신뢰도: 30%

    그 후:
    - 위험도
    - 매매계획 상태
    - 기술/AI 신호 일치도

    를 곱해서 보정합니다.
    """

    base_score = (
        float(candidate.final_score) * 0.70
        + float(candidate.ai_confidence) * 0.30
    )

    risk_multiplier = calculate_risk_multiplier(
        candidate.risk_level
    )

    plan_multiplier = calculate_plan_multiplier(
        candidate.plan_status
    )

    signal_multiplier = calculate_signal_multiplier(
        candidate.technical_signal,
        candidate.ai_signal,
    )

    adjusted_score = (
        base_score
        * risk_multiplier
        * plan_multiplier
        * signal_multiplier
    )

    return round(
        max(
            0.0,
            min(
                100.0,
                adjusted_score,
            ),
        ),
        2,
    )


def check_candidate_eligibility(
    candidate: AllocationCandidate,
) -> tuple[bool, str]:
    """
    포트폴리오 편입 가능 여부를 검사합니다.
    """

    if candidate.final_score < MIN_ALLOCATION_SCORE:
        return (
            False,
            (
                "최종점수가 최소 기준보다 낮습니다. "
                f"현재 {candidate.final_score:.2f}, "
                f"기준 {MIN_ALLOCATION_SCORE:.2f}"
            ),
        )

    if candidate.ai_confidence < MIN_AI_CONFIDENCE:
        return (
            False,
            (
                "AI 신뢰도가 최소 기준보다 낮습니다. "
                f"현재 {candidate.ai_confidence}%, "
                f"기준 {MIN_AI_CONFIDENCE}%"
            ),
        )

    if normalize_text(
        candidate.technical_signal
    ) == "SELL":
        return (
            False,
            "기술 신호가 SELL입니다.",
        )

    if normalize_text(
        candidate.ai_signal
    ) == "SELL":
        return (
            False,
            "AI 신호가 SELL입니다.",
        )

    if normalize_text(
        candidate.plan_status
    ) == "AVOID":
        return (
            False,
            "매매계획 상태가 AVOID입니다.",
        )

    if candidate.position_plan.recommended_shares <= 0:
        return (
            False,
            "추천 가능한 주식 수가 없습니다.",
        )

    return (
        True,
        "포트폴리오 편입 조건을 충족합니다.",
    )


def build_allocation_candidate(
    result: Any,
    position_plan: PositionPlan,
) -> AllocationCandidate:
    """
    StockScanResult와 PositionPlan을
    AllocationCandidate로 변환합니다.
    """

    return AllocationCandidate(
        symbol=normalize_text(
            result.symbol
        ),
        final_score=float(
            result.final_score
        ),
        ai_confidence=int(
            result.ai_confidence
        ),
        risk_level=normalize_text(
            result.risk_level
        ),
        technical_signal=normalize_text(
            result.technical_signal
        ),
        ai_signal=normalize_text(
            result.ai_signal
        ),
        plan_status=normalize_text(
            result.plan_status
        ),
        position_plan=position_plan,
    )


def create_portfolio_allocation(
    candidates: list[AllocationCandidate],
    account_size: float = ACCOUNT_SIZE,
    minimum_cash_reserve: float = (
        MIN_CASH_RESERVE_PERCENT
    ),
    max_allocation_per_stock: float = (
        MAX_ALLOCATION_PER_STOCK
    ),
    max_positions: int = (
        MAX_PORTFOLIO_POSITIONS
    ),
) -> PortfolioAllocation:
    """
    여러 종목에 계좌 자금을 자동 배분합니다.

    핵심 원칙:
    1. 최소 현금 보유 비율 유지
    2. 종목별 최대 투자 비율 제한
    3. PositionPlan의 추천 수량 초과 금지
    4. 배분점수가 높은 종목 우선
    5. 매수 가능한 정수 주식 수만 사용
    """

    account_size = float(
        account_size
    )

    if (
        not math.isfinite(account_size)
        or account_size <= 0
    ):
        raise ValueError(
            "account_size는 0보다 큰 숫자여야 합니다."
        )

    minimum_cash_reserve = validate_ratio(
        "minimum_cash_reserve",
        minimum_cash_reserve,
    )

    max_allocation_per_stock = validate_ratio(
        "max_allocation_per_stock",
        max_allocation_per_stock,
    )

    if max_positions <= 0:
        raise ValueError(
            "max_positions는 1 이상이어야 합니다."
        )

    maximum_investable_amount = (
        account_size
        * (1 - minimum_cash_reserve)
    )

    eligible_candidates = []
    rejected_symbols = []

    for candidate in candidates:
        eligible, reason = (
            check_candidate_eligibility(
                candidate
            )
        )

        if not eligible:
            rejected_symbols.append(
                {
                    "symbol": candidate.symbol,
                    "reason": reason,
                }
            )
            continue

        allocation_score = (
            calculate_allocation_score(
                candidate
            )
        )

        if allocation_score <= 0:
            rejected_symbols.append(
                {
                    "symbol": candidate.symbol,
                    "reason": (
                        "위험·신호 보정 후 "
                        "배분점수가 0입니다."
                    ),
                }
            )
            continue

        eligible_candidates.append(
            (
                candidate,
                allocation_score,
            )
        )

    eligible_candidates.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    selected_candidates = (
        eligible_candidates[
            :max_positions
        ]
    )

    total_score = sum(
        allocation_score
        for _, allocation_score
        in selected_candidates
    )

    remaining_cash = float(
        maximum_investable_amount
    )

    allocations = []

    for rank, (
        candidate,
        allocation_score,
    ) in enumerate(
        selected_candidates,
        start=1,
    ):
        position_plan = (
            candidate.position_plan
        )

        reference_entry = float(
            position_plan.reference_entry
        )

        if reference_entry <= 0:
            rejected_symbols.append(
                {
                    "symbol": candidate.symbol,
                    "reason": (
                        "진입 기준가가 "
                        "올바르지 않습니다."
                    ),
                }
            )
            continue

        if total_score > 0:
            weighted_amount = (
                maximum_investable_amount
                * allocation_score
                / total_score
            )
        else:
            weighted_amount = 0.0

        maximum_stock_amount = (
            account_size
            * max_allocation_per_stock
        )

        position_plan_limit = float(
            position_plan.investment_amount
        )

        allowed_amount = min(
            weighted_amount,
            maximum_stock_amount,
            position_plan_limit,
            remaining_cash,
        )

        shares = int(
            allowed_amount
            // reference_entry
        )

        shares = min(
            shares,
            int(
                position_plan.recommended_shares
            ),
        )

        if shares <= 0:
            rejected_symbols.append(
                {
                    "symbol": candidate.symbol,
                    "reason": (
                        "배분 가능한 자금으로 "
                        "1주 이상 매수할 수 없습니다."
                    ),
                }
            )
            continue

        allocated_amount = (
            shares
            * reference_entry
        )

        risk_per_share = (
            reference_entry
            - float(
                position_plan.stop_loss
            )
        )

        reward_1_per_share = max(
            0.0,
            float(
                position_plan.target_1
            )
            - reference_entry,
        )

        reward_2_per_share = max(
            0.0,
            float(
                position_plan.target_2
            )
            - reference_entry,
        )

        expected_loss_amount = (
            shares
            * risk_per_share
        )

        expected_profit_1 = (
            shares
            * reward_1_per_share
        )

        expected_profit_2 = (
            shares
            * reward_2_per_share
        )

        allocation_percent = (
            allocated_amount
            / account_size
            * 100
        )

        actual_account_risk_percent = (
            expected_loss_amount
            / account_size
            * 100
        )

        if allocation_score >= 80:
            allocation_status = (
                "STRONG_ALLOCATION"
            )
        elif allocation_score >= 60:
            allocation_status = (
                "NORMAL_ALLOCATION"
            )
        else:
            allocation_status = (
                "SMALL_ALLOCATION"
            )

        note = (
            "포트폴리오 점수와 위험 제한을 "
            "반영한 자동 배분입니다."
        )

        allocation = StockAllocation(
            rank=rank,
            symbol=candidate.symbol,

            allocation_status=(
                allocation_status
            ),

            allocation_score=round(
                allocation_score,
                2,
            ),

            allocated_amount=round(
                allocated_amount,
                2,
            ),

            allocation_percent=round(
                allocation_percent,
                2,
            ),

            shares=shares,

            reference_entry=round(
                reference_entry,
                2,
            ),

            stop_loss=round(
                float(
                    position_plan.stop_loss
                ),
                2,
            ),

            target_1=round(
                float(
                    position_plan.target_1
                ),
                2,
            ),

            target_2=round(
                float(
                    position_plan.target_2
                ),
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

            final_score=round(
                candidate.final_score,
                2,
            ),

            ai_confidence=(
                candidate.ai_confidence
            ),

            risk_level=(
                candidate.risk_level
            ),

            plan_status=(
                candidate.plan_status
            ),

            note=note,
        )

        allocations.append(
            allocation
        )

        remaining_cash -= (
            allocated_amount
        )

    total_allocated_amount = sum(
        allocation.allocated_amount
        for allocation in allocations
    )

    cash_reserve_amount = (
        account_size
        - total_allocated_amount
    )

    cash_reserve_percent = (
        cash_reserve_amount
        / account_size
        * 100
    )

    total_expected_loss = sum(
        allocation.expected_loss_amount
        for allocation in allocations
    )

    total_expected_profit_1 = sum(
        allocation.expected_profit_1
        for allocation in allocations
    )

    total_expected_profit_2 = sum(
        allocation.expected_profit_2
        for allocation in allocations
    )

    total_account_risk_percent = (
        total_expected_loss
        / account_size
        * 100
    )

    return PortfolioAllocation(
        account_size=round(
            account_size,
            2,
        ),

        maximum_investable_amount=round(
            maximum_investable_amount,
            2,
        ),

        total_allocated_amount=round(
            total_allocated_amount,
            2,
        ),

        cash_reserve_amount=round(
            cash_reserve_amount,
            2,
        ),

        cash_reserve_percent=round(
            cash_reserve_percent,
            2,
        ),

        total_expected_loss=round(
            total_expected_loss,
            2,
        ),

        total_expected_profit_1=round(
            total_expected_profit_1,
            2,
        ),

        total_expected_profit_2=round(
            total_expected_profit_2,
            2,
        ),

        total_account_risk_percent=round(
            total_account_risk_percent,
            2,
        ),

        selected_count=len(
            allocations
        ),

        rejected_count=len(
            rejected_symbols
        ),

        allocations=allocations,
        rejected_symbols=(
            rejected_symbols
        ),
    )


def print_portfolio_allocation(
    portfolio: PortfolioAllocation,
) -> None:
    """
    최종 포트폴리오 배분 결과를 출력합니다.
    """

    print()
    print("=" * 90)
    print("V3.2 PORTFOLIO ALLOCATION")
    print("=" * 90)

    print(
        f"Account size          : "
        f"${portfolio.account_size:,.2f}"
    )

    print(
        f"Maximum investable    : "
        f"${portfolio.maximum_investable_amount:,.2f}"
    )

    print(
        f"Total allocated       : "
        f"${portfolio.total_allocated_amount:,.2f}"
    )

    print(
        f"Cash reserve          : "
        f"${portfolio.cash_reserve_amount:,.2f} "
        f"({portfolio.cash_reserve_percent:.2f}%)"
    )

    print(
        f"Total expected loss   : "
        f"${portfolio.total_expected_loss:,.2f}"
    )

    print(
        f"Total account risk    : "
        f"{portfolio.total_account_risk_percent:.2f}%"
    )

    print(
        f"Expected profit T1    : "
        f"${portfolio.total_expected_profit_1:,.2f}"
    )

    print(
        f"Expected profit T2    : "
        f"${portfolio.total_expected_profit_2:,.2f}"
    )

    print()
    print("-" * 90)

    header = (
        f"{'Rank':<6}"
        f"{'Symbol':<9}"
        f"{'Score':>9}"
        f"{'Shares':>9}"
        f"{'Amount':>13}"
        f"{'Weight':>10}"
        f"{'Risk $':>11}"
        f"{'Profit T2':>13}"
        f"{'Status':>20}"
    )

    print(header)
    print("-" * 90)

    for allocation in portfolio.allocations:
        print(
            f"{allocation.rank:<6}"
            f"{allocation.symbol:<9}"
            f"{allocation.allocation_score:>9.2f}"
            f"{allocation.shares:>9}"
            f"${allocation.allocated_amount:>12,.2f}"
            f"{allocation.allocation_percent:>9.2f}%"
            f"${allocation.expected_loss_amount:>10,.2f}"
            f"${allocation.expected_profit_2:>12,.2f}"
            f"{allocation.allocation_status:>20}"
        )

    print("=" * 90)

    if portfolio.rejected_symbols:
        print()
        print("REJECTED SYMBOLS")
        print("-" * 90)

        for rejected in (
            portfolio.rejected_symbols
        ):
            print(
                f"{rejected['symbol']}: "
                f"{rejected['reason']}"
            )

    print()
    print(
        "This allocation is a mathematical "
        "risk-management model, not investment advice."
    )