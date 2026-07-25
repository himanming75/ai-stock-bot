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
# PORTFOLIO SETTINGS
# ============================================================

# 실제 투자에 사용할 가상 계좌 금액
ACCOUNT_SIZE = 10_000.0

# 한 거래에서 계좌의 최대 1%만 위험에 노출
RISK_PER_TRADE = 0.01

# 한 종목에 계좌의 최대 20%까지만 투자
MAX_POSITION_PERCENT = 0.20

# 최소 Risk/Reward 기준
MIN_ACCEPTABLE_RISK_REWARD = 1.5

# ============================================================
# PORTFOLIO ALLOCATION SETTINGS
# ============================================================

# 동시에 보유할 최대 종목 수
MAX_PORTFOLIO_POSITIONS = 5

# 전체 계좌에서 최소한 현금으로 남겨둘 비율
MIN_CASH_RESERVE_PERCENT = 0.20

# 포트폴리오에 편입하기 위한 최소 최종점수
MIN_ALLOCATION_SCORE = 60.0

# AI 신뢰도 최소 기준
MIN_AI_CONFIDENCE = 60

# 개별 종목 최대 투자 비율
MAX_ALLOCATION_PER_STOCK = 0.20

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