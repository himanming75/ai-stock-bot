from __future__ import annotations

from decimal import Decimal

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


class HistoricalBootstrapLiveContinuationV218:
    def __init__(
        self,
        symbols,
        bars_per_symbol=3,
        bootstrap_client=None,
        live_collector_factory=None,
    ):
        self.symbols=sorted({str(x).upper().strip() for x in symbols if str(x).strip()})
        self.bars_per_symbol=int(bars_per_symbol)
        self.bootstrap_client=bootstrap_client or AlpacaReadOnlyHistoricalBootstrapV218()
        self.live_collector_factory=live_collector_factory or AlpacaReadOnlyCurrentBarCollectorV217

    def bootstrap_signal(self,quantity=Decimal("1")):
        bar_map=self.bootstrap_client.fetch_recent_completed_bars(
            self.symbols,
            bars_per_symbol=self.bars_per_symbol,
        )
        bars=flatten_bootstrap_map(bar_map)
        signal_result=CurrentMarketDataSignalBridgeV217(
            min_bars_per_symbol=self.bars_per_symbol
        ).build_from_bars(
            bars,
            quantity=quantity,
            max_signals=3,
        )
        return {
            "status":"PASS_HISTORICAL_BOOTSTRAP_SIGNAL",
            "bar_counts":{k:len(v) for k,v in sorted(bar_map.items())},
            "signal_result":signal_result,
            "live_continuation_required":True,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }

    def live_continuation_once(self,timeout_seconds=900,quantity=Decimal("1")):
        collector=self.live_collector_factory(
            self.symbols,
            bars_per_symbol=self.bars_per_symbol,
        )
        bars,counts=collector.collect(timeout_seconds=timeout_seconds)
        signal_result=CurrentMarketDataSignalBridgeV217(
            min_bars_per_symbol=self.bars_per_symbol
        ).build_from_bars(
            bars,
            quantity=quantity,
            max_signals=3,
        )
        return {
            "status":"PASS_LIVE_CONTINUATION_SIGNAL",
            "bar_counts":counts,
            "signal_result":signal_result,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }
