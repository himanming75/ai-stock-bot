from backtest.engine import run_backtest
from charts.backtest_chart import plot_backtest
from data.market import get_history
from strategy.score import calculate_score
from strategy.signal import add_signals


symbol = "AAPL"

# 데이터 다운로드 및 지표 계산
data = get_history(symbol, period="5y")

# 모든 날짜에 매매 신호 추가
data = add_signals(data)

# 가장 최근 완성 데이터
latest = data.iloc[-1]

# 기술적 점수 계산
score_result = calculate_score(latest)
score = score_result["score"]
reasons = score_result["reasons"]

print("=" * 60)
print(f"{symbol} MARKET ANALYSIS")
print("=" * 60)

print(f"Close        : ${latest['Close']:.2f}")
print(f"MA5          : {latest['MA5']:.2f}")
print(f"MA20         : {latest['MA20']:.2f}")
print(f"RSI          : {latest['RSI']:.2f}")
print(f"MACD         : {latest['MACD']:.2f}")
print(f"MACD Signal  : {latest['MACD_SIGNAL']:.2f}")
print(f"BB Upper     : {latest['BB_UPPER']:.2f}")
print(f"BB Middle    : {latest['BB_MIDDLE']:.2f}")
print(f"BB Lower     : {latest['BB_LOWER']:.2f}")
print(f"Score        : {score}/100")
print(f"Signal       : {latest['Signal']}")

print("-" * 60)
print("Score reasons:")

for reason in reasons:
    print(f"- {reason}")

print()

# 백테스트
result = run_backtest(
    data,
    starting_cash=10000,
    fee_rate=0.001,
)

print("=" * 60)
print(f"{symbol} BACKTEST RESULT")
print("=" * 60)

print(f"Starting cash    : ${result['starting_cash']:,.2f}")
print(f"Final value      : ${result['final_value']:,.2f}")
print(f"Total return     : {result['total_return']:.2f}%")
print(f"Trade count      : {len(result['trades'])}")
print(f"Completed trades : {result['completed_trades']}")
print(f"Winning trades   : {result['winning_trades']}")
print(f"Losing trades    : {result['losing_trades']}")
print(f"Win rate         : {result['win_rate']:.2f}%")
print(f"Max drawdown     : {result['max_drawdown']:.2f}%")
print("=" * 60)

for trade in result["trades"]:
    print(
        f"{trade['date'].date()} "
        f"{trade['action']:<4} "
        f"${trade['price']:.2f}"
    )

plot_backtest(
    data,
    result["trades"],
    symbol,
)