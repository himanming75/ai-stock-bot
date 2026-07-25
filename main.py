from data.market import get_history
from strategy.signal import add_signals
from strategy.score import calculate_score
from backtest.engine import run_backtest
from charts.backtest_chart import plot_backtest


symbol = "AAPL"

# -----------------------------
# 데이터 다운로드
# -----------------------------
data = get_history(symbol, period="5y")

# -----------------------------
# 기술적 지표 계산
# -----------------------------
data = add_signals(data)

# -----------------------------
# 최신 데이터
# -----------------------------
latest = data.iloc[-1]

score = calculate_score(latest)

print("=" * 50)
print(f"{symbol} MARKET ANALYSIS")
print("=" * 50)

print(f"Close  : ${latest['Close']:.2f}")
print(f"MA5    : {latest['MA5']:.2f}")
print(f"MA20   : {latest['MA20']:.2f}")
print(f"RSI    : {latest['RSI']:.2f}")
print(f"Score  : {score}/100")
print(f"Signal : {latest['Signal']}")

print()

# -----------------------------
# 백테스트
# -----------------------------
result = run_backtest(
    data,
    starting_cash=10000,
    fee_rate=0.001
)

print("=" * 50)
print(f"{symbol} BACKTEST RESULT")
print("=" * 50)

print(f"Starting cash   : ${result['starting_cash']:,.2f}")
print(f"Final value     : ${result['final_value']:,.2f}")
print(f"Total return    : {result['total_return']:.2f}%")
print(f"Trade count     : {len(result['trades'])}")

print(f"Completed trades : {result['completed_trades']}")
print(f"Winning trades   : {result['winning_trades']}")
print(f"Losing trades    : {result['losing_trades']}")
print(f"Win rate         : {result['win_rate']:.2f}%")
print(f"Max drawdown     : {result['max_drawdown']:.2f}%")

print("=" * 50)

# -----------------------------
# 거래내역 출력
# -----------------------------
for trade in result["trades"]:
    print(
        f"{trade['date'].date()} "
        f"{trade['action']:<4} "
        f"${trade['price']:.2f}"
    )

# -----------------------------
# 차트 출력
# -----------------------------
plot_backtest(
    data,
    result["trades"],
    symbol
)