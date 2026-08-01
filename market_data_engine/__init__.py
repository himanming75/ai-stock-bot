"""Real-time market-data foundation for the AI Stock Bot."""

from .models import Bar, MarketDataMessage, Quote, Trade
from .parser import AlpacaMessageParser, MessageParseError
from .subscriptions import SubscriptionRegistry
from .sequence import SequenceDecision, SequenceGuard
from .freshness import FreshnessMonitor, FreshnessStatus
from .connection import ConnectionState, ConnectionStateMachine
from .reconnect import ExponentialBackoff
from .router import MarketDataRouter, RoutingStats
from .fixture_stream import FixtureMarketDataStream

__all__ = [
    "Bar",
    "MarketDataMessage",
    "Quote",
    "Trade",
    "AlpacaMessageParser",
    "MessageParseError",
    "SubscriptionRegistry",
    "SequenceDecision",
    "SequenceGuard",
    "FreshnessMonitor",
    "FreshnessStatus",
    "ConnectionState",
    "ConnectionStateMachine",
    "ExponentialBackoff",
    "MarketDataRouter",
    "RoutingStats",
    "FixtureMarketDataStream",
]
