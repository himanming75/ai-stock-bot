from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from market_data_engine.models import Bar
from .alpaca_readonly_historical_bootstrap_v2_1_8 import (
    AlpacaReadOnlyHistoricalBootstrapV218,
    flatten_bootstrap_map,
)
from .alpaca_readonly_current_bar_collector_v2_1_7 import (
    AlpacaReadOnlyCurrentBarCollectorV217,
)
from .etrade_current_market_data_signal_bridge_v2_1_7 import (
    CurrentMarketDataSignalBridgeV217,
)


def merge_bootstrap_and_live_bars(
    bootstrap_bars,
    live_bars,
    max_bars_per_symbol=50,
):
    """
    Merge by (symbol, timestamp).
    Live bars replace bootstrap bars at an identical timestamp.
    Output is time-ordered and bounded per symbol.
    """
    max_bars_per_symbol=int(max_bars_per_symbol)
    if max_bars_per_symbol < 3:
        raise ValueError("max_bars_per_symbol must be >= 3")

    merged=defaultdict(dict)

    for bar in bootstrap_bars:
        if not isinstance(bar,Bar):
            raise TypeError("bootstrap_bars must contain market_data_engine.Bar")
        merged[bar.symbol][bar.timestamp]=bar

    for bar in live_bars:
        if not isinstance(bar,Bar):
            raise TypeError("live_bars must contain market_data_engine.Bar")
        merged[bar.symbol][bar.timestamp]=bar

    result=[]
    per_symbol_counts={}
    duplicate_free=True
    monotonic=True

    for symbol in sorted(merged):
        rows=sorted(
            merged[symbol].values(),
            key=lambda x:x.timestamp,
        )
        rows=rows[-max_bars_per_symbol:]

        timestamps=[x.timestamp for x in rows]
        if len(timestamps)!=len(set(timestamps)):
            duplicate_free=False
        if timestamps!=sorted(timestamps):
            monotonic=False

        per_symbol_counts[symbol]=len(rows)
        result.extend(rows)

    return {
        "bars":result,
        "per_symbol_counts":per_symbol_counts,
        "duplicate_free":duplicate_free,
        "monotonic":monotonic,
    }


class BootstrapLiveContinuityValidatorV219:
    def __init__(
        self,
        symbols,
        bootstrap_bars_per_symbol=3,
        retained_bars_per_symbol=50,
        bootstrap_client=None,
        live_collector_factory=None,
    ):
        self.symbols=sorted({
            str(x).upper().strip()
            for x in symbols
            if str(x).strip()
        })
        if not self.symbols:
            raise ValueError("At least one symbol is required.")

        self.bootstrap_bars_per_symbol=int(bootstrap_bars_per_symbol)
        self.retained_bars_per_symbol=int(retained_bars_per_symbol)

        self.bootstrap_client=(
            bootstrap_client
            or AlpacaReadOnlyHistoricalBootstrapV218()
        )
        self.live_collector_factory=(
            live_collector_factory
            or AlpacaReadOnlyCurrentBarCollectorV217
        )

    def bootstrap_only(self,quantity=Decimal("1")):
        bar_map=self.bootstrap_client.fetch_recent_completed_bars(
            self.symbols,
            bars_per_symbol=self.bootstrap_bars_per_symbol,
        )
        bootstrap_bars=flatten_bootstrap_map(bar_map)

        signal_result=CurrentMarketDataSignalBridgeV217(
            min_bars_per_symbol=self.bootstrap_bars_per_symbol
        ).build_from_bars(
            bootstrap_bars,
            quantity=quantity,
            max_signals=3,
        )

        return {
            "status":"PASS_BOOTSTRAP_BASELINE",
            "bootstrap_bars":bootstrap_bars,
            "bootstrap_counts":{
                k:len(v)
                for k,v in sorted(bar_map.items())
            },
            "signal_result":signal_result,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }

    def validate_with_live_bars(
        self,
        bootstrap_bars,
        live_bars,
        quantity=Decimal("1"),
    ):
        merged=merge_bootstrap_and_live_bars(
            bootstrap_bars,
            live_bars,
            max_bars_per_symbol=self.retained_bars_per_symbol,
        )

        missing={
            s:merged["per_symbol_counts"].get(s,0)
            for s in self.symbols
            if merged["per_symbol_counts"].get(s,0)
            < self.bootstrap_bars_per_symbol
        }
        if missing:
            raise ValueError(
                "Merged continuity set has insufficient bars: "
                +str(missing)
            )

        signal_result=CurrentMarketDataSignalBridgeV217(
            min_bars_per_symbol=self.bootstrap_bars_per_symbol
        ).build_from_bars(
            merged["bars"],
            quantity=quantity,
            max_signals=3,
        )

        return {
            "status":"PASS_BOOTSTRAP_LIVE_CONTINUITY",
            "merged_counts":merged["per_symbol_counts"],
            "duplicate_free":merged["duplicate_free"],
            "monotonic":merged["monotonic"],
            "signal_result":signal_result,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }

    def collect_live_and_validate(
        self,
        bootstrap_bars,
        timeout_seconds=120,
        live_bars_per_symbol=3,
        quantity=Decimal("1"),
    ):
        collector=self.live_collector_factory(
            self.symbols,
            bars_per_symbol=live_bars_per_symbol,
        )
        live_bars,live_counts=collector.collect(
            timeout_seconds=timeout_seconds
        )
        result=self.validate_with_live_bars(
            bootstrap_bars,
            live_bars,
            quantity=quantity,
        )
        result["live_counts"]=live_counts
        return result
