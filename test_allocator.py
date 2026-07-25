from types import SimpleNamespace

from data.market import get_history
from forecast.predictor import create_trade_plan
from portfolio.allocator import (
    build_allocation_candidate,
    create_portfolio_allocation,
    print_portfolio_allocation,
)
from portfolio.manager import create_position_plan
from strategy.score import (
    calculate_score,
    determine_signal,
)


test_symbols = [
    {
        "symbol": "AAPL",
        "final_score": 88.30,
        "ai_confidence": 85,
        "risk_level": "MEDIUM",
        "ai_signal": "BUY",
    },
    {
        "symbol": "NVDA",
        "final_score": 92.00,
        "ai_confidence": 92,
        "risk_level": "MEDIUM",
        "ai_signal": "BUY",
    },
    {
        "symbol": "MSFT",
        "final_score": 80.00,
        "ai_confidence": 80,
        "risk_level": "MEDIUM",
        "ai_signal": "BUY",
    },
]


candidates = []

for item in test_symbols:
    symbol = item["symbol"]

    data = get_history(
        symbol=symbol,
        period="5y",
        interval="1d",
    )

    latest = data.iloc[-1]

    score_result = calculate_score(
        latest
    )

    technical_score = int(
        score_result["score"]
    )

    technical_signal = determine_signal(
        latest,
        technical_score,
    )

    trade_plan = create_trade_plan(
        symbol=symbol,
        data=data,
        technical_signal=technical_signal,
    )

    position_plan = create_position_plan(
        trade_plan=trade_plan,
    )

    fake_scan_result = SimpleNamespace(
        symbol=symbol,
        final_score=item["final_score"],
        ai_confidence=item["ai_confidence"],
        risk_level=item["risk_level"],
        technical_signal=technical_signal,
        ai_signal=item["ai_signal"],
        plan_status=trade_plan.plan_status,
    )

    candidate = build_allocation_candidate(
        result=fake_scan_result,
        position_plan=position_plan,
    )

    candidates.append(
        candidate
    )


portfolio = create_portfolio_allocation(
    candidates=candidates,
)

print_portfolio_allocation(
    portfolio
)