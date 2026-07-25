from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# STOCK SCANNER SETTINGS
# ============================================================

SYMBOLS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
]

MARKET_PERIOD = "5y"
MARKET_INTERVAL = "1d"


# ============================================================
# STRATEGY SETTINGS
# ============================================================

BUY_SCORE_THRESHOLD = 75
SELL_SCORE_THRESHOLD = 40

RSI_OVERBOUGHT = 75
RSI_BUY_LIMIT = 70


# ============================================================
# BACKTEST SETTINGS
# ============================================================

STARTING_CASH = 10_000.0

# 0.10% 매수/매도 수수료
COMMISSION_RATE = 0.001

# 실제 주문 가격이 불리하게 체결되는 비율
# 0.05% 슬리피지
SLIPPAGE_RATE = 0.0005


# ============================================================
# OPENAI SETTINGS
# ============================================================

OPENAI_MODEL = "gpt-5-mini"

# 응답 길이를 짧게 유지해 비용과 잘림을 줄입니다.
OPENAI_MAX_OUTPUT_TOKENS = 2_000


# ============================================================
# REPORT SETTINGS
# ============================================================

SAVE_JSON_REPORT = True
SAVE_CHARTS = True
SHOW_CHARTS = False

TOP_RESULT_COUNT = 5