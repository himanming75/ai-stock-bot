"""Order intent, position sizing, and paper execution foundations."""

from .models import OrderIntent, OrderSide, OrderType, TimeInForce
from .sizing import PositionSizer, PositionSizingConfig, SizingResult
from .factory import OrderIntentFactory
from .dedup import DuplicateIntentGuard
from .expiry import IntentExpiryPolicy
from .engine import OrderIntentEngine, OrderIntentEngineStats

from .adapter_models import (
    CancelRequest,
    CancelResult,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    FillRecord,
    ReconciliationRecord,
)
from .client_order_id import ClientOrderIdGenerator
from .payloads import AlpacaPaperPayloadBuilder
from .idempotency import ExecutionIdempotencyGuard
from .transport import ExecutionTransport, MockPaperTransport
from .paper_adapter import PaperExecutionAdapter
from .execution_engine import PaperExecutionEngine, PaperExecutionEngineStats

__all__ = [
    "OrderIntent",
    "OrderSide",
    "OrderType",
    "TimeInForce",
    "PositionSizer",
    "PositionSizingConfig",
    "SizingResult",
    "OrderIntentFactory",
    "DuplicateIntentGuard",
    "IntentExpiryPolicy",
    "OrderIntentEngine",
    "OrderIntentEngineStats",
    "CancelRequest",
    "CancelResult",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStatus",
    "FillRecord",
    "ReconciliationRecord",
    "ClientOrderIdGenerator",
    "AlpacaPaperPayloadBuilder",
    "ExecutionIdempotencyGuard",
    "ExecutionTransport",
    "MockPaperTransport",
    "PaperExecutionAdapter",
    "PaperExecutionEngine",
    "PaperExecutionEngineStats",
]
