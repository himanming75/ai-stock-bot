import pandas as pd
import yfinance as yf


def get_history(
    symbol: str,
    period: str = "5y",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Yahoo Finance에서 주가 데이터를 다운로드하고
    기술지표를 계산하여 반환합니다.

    포함 지표:
    - MA5
    - MA20
    - RSI
    - MACD
    - MACD Signal
    - MACD Histogram
    - Bollinger Band
    """

    if not symbol:
        raise ValueError("symbol이 비어 있습니다.")

    symbol = symbol.upper().strip()

    data = yf.download(
        tickers=symbol,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )

    if data is None or data.empty:
        raise ValueError(
            f"{symbol}의 시장 데이터를 가져오지 못했습니다."
        )

    data = normalize_columns(data)

    required_columns = {
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    }

    missing_columns = required_columns - set(data.columns)

    if missing_columns:
        raise ValueError(
            "다운로드 데이터에 필요한 컬럼이 없습니다: "
            + ", ".join(sorted(missing_columns))
        )

    data = data.copy()

    # 숫자형 변환
    for column in required_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce",
        )

    # 이동평균
    data["MA5"] = data["Close"].rolling(
        window=5
    ).mean()

    data["MA20"] = data["Close"].rolling(
        window=20
    ).mean()

    # RSI
    data["RSI"] = calculate_rsi(
        close=data["Close"],
        period=14,
    )

    # MACD
    ema12 = data["Close"].ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = data["Close"].ewm(
        span=26,
        adjust=False,
    ).mean()

    data["MACD"] = ema12 - ema26

    data["MACD_SIGNAL"] = data["MACD"].ewm(
        span=9,
        adjust=False,
    ).mean()

    data["MACD_HIST"] = (
        data["MACD"]
        - data["MACD_SIGNAL"]
    )

    # Bollinger Bands
    data["BB_MIDDLE"] = data["Close"].rolling(
        window=20
    ).mean()

    rolling_std = data["Close"].rolling(
        window=20
    ).std()

    data["BB_UPPER"] = (
        data["BB_MIDDLE"]
        + 2 * rolling_std
    )

    data["BB_LOWER"] = (
        data["BB_MIDDLE"]
        - 2 * rolling_std
    )

    # 무한대 제거
    data = data.replace(
        [float("inf"), float("-inf")],
        pd.NA,
    )

    # 기술지표 계산이 완료되지 않은 초기 행 제거
    indicator_columns = [
        "MA5",
        "MA20",
        "RSI",
        "MACD",
        "MACD_SIGNAL",
        "MACD_HIST",
        "BB_UPPER",
        "BB_MIDDLE",
        "BB_LOWER",
    ]

    data = data.dropna(
        subset=indicator_columns
    )

    if data.empty:
        raise ValueError(
            "기술지표 계산 후 사용할 데이터가 없습니다."
        )

    data.index = pd.to_datetime(data.index)
    data.index.name = "Date"

    data = data.sort_index()
    data = data[~data.index.duplicated(keep="last")]

    return data


def calculate_rsi(
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """
    Wilder 방식에 가까운 RSI를 계산합니다.
    """

    if period <= 0:
        raise ValueError(
            "RSI period는 0보다 커야 합니다."
        )

    price_change = close.diff()

    gain = price_change.clip(lower=0)
    loss = -price_change.clip(upper=0)

    average_gain = gain.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    average_loss = loss.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    relative_strength = (
        average_gain / average_loss
    )

    rsi = 100 - (
        100 / (1 + relative_strength)
    )

    # 하락이 전혀 없는 경우 RSI 100
    rsi = rsi.where(
        average_loss != 0,
        100,
    )

    # 상승과 하락이 모두 없는 경우 RSI 50
    no_movement = (
        (average_gain == 0)
        & (average_loss == 0)
    )

    rsi = rsi.where(
        ~no_movement,
        50,
    )

    return rsi


def normalize_columns(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    yfinance가 MultiIndex 컬럼을 반환하는 경우
    일반 컬럼 형태로 변환합니다.
    """

    normalized = data.copy()

    if isinstance(
        normalized.columns,
        pd.MultiIndex,
    ):
        first_level = normalized.columns.get_level_values(
            0
        )

        second_level = normalized.columns.get_level_values(
            1
        )

        price_columns = {
            "Open",
            "High",
            "Low",
            "Close",
            "Adj Close",
            "Volume",
        }

        if any(
            column in price_columns
            for column in first_level
        ):
            normalized.columns = first_level

        elif any(
            column in price_columns
            for column in second_level
        ):
            normalized.columns = second_level

        else:
            normalized.columns = [
                "_".join(
                    str(part)
                    for part in column
                    if part
                )
                for column in normalized.columns
            ]

    normalized.columns = [
        str(column).strip()
        for column in normalized.columns
    ]

    return normalized


def get_latest_price(
    symbol: str,
) -> float:
    """
    가장 최근 종가만 간단히 반환합니다.
    """

    data = get_history(
        symbol=symbol,
        period="3mo",
        interval="1d",
    )

    return float(
        data.iloc[-1]["Close"]
    )