from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from .adapter_models import CancelRequest, CancelResult, ExecutionRequest, ExecutionResult, ReconciliationRecord
from .client_order_id import ClientOrderIdGenerator
from .idempotency import ExecutionIdempotencyGuard
from .models import OrderIntent
from .payloads import AlpacaPaperPayloadBuilder
from .transport import ExecutionTransport


class PaperExecutionAdapter:
    """Broker-independent adapter using an injected transport."""

    def __init__(
        self,
        *,
        transport: ExecutionTransport,
        payload_builder: AlpacaPaperPayloadBuilder,
        client_order_id_generator: ClientOrderIdGenerator,
        idempotency_guard: ExecutionIdempotencyGuard,
    ) -> None:
        self.transport = transport
        self.payload_builder = payload_builder
        self.client_order_id_generator = client_order_id_generator
        self.idempotency_guard = idempotency_guard

    def build_request(self, intent: OrderIntent, now: datetime) -> ExecutionRequest:
        intent.validate()
        client_order_id = self.client_order_id_generator.next_id(now)
        if not self.idempotency_guard.register(
            intent_id=intent.intent_id,
            client_order_id=client_order_id,
        ):
            raise ValueError("duplicate execution request")
        payload = self.payload_builder.build(intent, client_order_id)
        request = ExecutionRequest(
            request_id=uuid4().hex,
            client_order_id=client_order_id,
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            side=intent.side.value,
            quantity=intent.quantity,
            order_type=intent.order_type.value,
            time_in_force=intent.time_in_force.value,
            created_at=now,
            payload=payload,
        )
        request.validate()
        return request

    def submit(self, intent: OrderIntent, now: datetime) -> tuple[ExecutionRequest, ExecutionResult]:
        request = self.build_request(intent, now)
        result = self.transport.submit(request, now)
        return request, result

    def cancel(self, client_order_id: str, now: datetime, reason: str = "USER_REQUEST") -> CancelResult:
        request = CancelRequest(client_order_id, now, reason)
        return self.transport.cancel(request, now)

    def reconcile(
        self,
        *,
        request_status,
        transport_result: ExecutionResult,
        now: datetime,
    ) -> ReconciliationRecord:
        matched = request_status == transport_result.status
        record = ReconciliationRecord(
            client_order_id=transport_result.client_order_id,
            request_status=request_status,
            transport_status=transport_result.status,
            matched=matched,
            checked_at=now,
            details={"broker_order_id": transport_result.broker_order_id},
        )
        record.validate()
        return record
