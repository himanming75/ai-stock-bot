from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from market_data_engine.models import Bar
from alpaca_market_data.historical_indicator_library_v79_66_70 import (
    IndicatorConfig,
    build_indicator_registry,
    build_indicators,
    validate_indicator_rows,
)
from .etrade_canonical_signal_source_bridge_v2_1_6 import (
    CanonicalSignalSourceBridgeV216,
)


def bar_to_feature_row(bar: Bar, timeframe: str="1Min") -> dict:
    return {
        "symbol":bar.symbol,
        "timeframe":timeframe,
        "timestamp":bar.timestamp.isoformat(),
        "source_close":float(bar.close),
        "features":{
            "open":float(bar.open),
            "high":float(bar.high),
            "low":float(bar.low),
            "close":float(bar.close),
            "volume":int(bar.volume),
            "trade_count":bar.trade_count,
            "vwap":None if bar.vwap is None else float(bar.vwap),
        },
    }


class CurrentBarWindow:
    def __init__(self, max_bars_per_symbol=50):
        if int(max_bars_per_symbol) < 3:
            raise ValueError("max_bars_per_symbol must be >= 3")
        self.max_bars_per_symbol=int(max_bars_per_symbol)
        self._bars=defaultdict(list)

    def add(self, bar: Bar):
        rows=self._bars[bar.symbol]
        rows.append(bar)
        rows.sort(key=lambda x:x.timestamp)
        if len(rows)>self.max_bars_per_symbol:
            del rows[:-self.max_bars_per_symbol]

    def counts(self):
        return {k:len(v) for k,v in sorted(self._bars.items())}

    def bars(self):
        out=[]
        for symbol in sorted(self._bars):
            out.extend(self._bars[symbol])
        return list(out)

    def feature_rows(self, timeframe="1Min"):
        return [bar_to_feature_row(bar,timeframe=timeframe) for bar in self.bars()]


class CurrentMarketDataSignalBridgeV217:
    """
    Read-only bridge:
    existing market_data_engine.Bar
      -> existing V79.66-V79.70 indicators
      -> existing V79.71-V79.75 signals
      -> V2.1.6/V2.1.5 decision queue.

    No broker order submission occurs here.
    """

    def __init__(
        self,
        indicator_config=None,
        signal_source=None,
        min_bars_per_symbol=3,
    ):
        self.indicator_config=indicator_config or IndicatorConfig()
        self.signal_source=signal_source or CanonicalSignalSourceBridgeV216()
        self.min_bars_per_symbol=int(min_bars_per_symbol)
        if self.min_bars_per_symbol < 3:
            raise ValueError("min_bars_per_symbol must be >= 3")

    def build_from_bars(self, bars, quantity=Decimal("1"), max_signals=3):
        bars=list(bars)
        if not bars:
            raise ValueError("No current market bars supplied.")

        by_symbol=defaultdict(list)
        for bar in bars:
            if not isinstance(bar,Bar):
                raise TypeError("All current market rows must be market_data_engine.Bar.")
            by_symbol[bar.symbol].append(bar)

        insufficient={
            symbol:len(rows)
            for symbol,rows in by_symbol.items()
            if len(rows)<self.min_bars_per_symbol
        }
        if insufficient:
            raise ValueError(f"Insufficient bars for indicator generation: {insufficient}")

        feature_rows=[]
        for symbol in sorted(by_symbol):
            for bar in sorted(by_symbol[symbol],key=lambda x:x.timestamp):
                feature_rows.append(bar_to_feature_row(bar))

        registry=build_indicator_registry(self.indicator_config)
        indicator_rows=build_indicators(feature_rows,self.indicator_config)
        indicator_stats=validate_indicator_rows(indicator_rows,registry)

        signal_result=self.signal_source.from_indicator_rows(
            indicator_rows,
            quantity=quantity,
            max_signals=max_signals,
        )

        return {
            "stage":"BROKER_INTEGRATION_V2_1_7_CURRENT_MARKET_DATA_SIGNAL_BRIDGE",
            "status":"PASS_CURRENT_MARKET_DATA_TO_SIGNAL",
            "symbols":sorted(by_symbol),
            "bar_counts":{k:len(v) for k,v in sorted(by_symbol.items())},
            "indicator_row_count":indicator_stats["indicator_row_count"],
            "recommendations":signal_result["recommendations"],
            "decision_queue":signal_result["decision_queue"],
            "network_used_by_bridge":False,
            "broker_orders_submitted":0,
            "profitability_validated":False,
        }
