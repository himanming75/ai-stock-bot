from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal
from datetime import datetime, timezone

from broker.contracts_v77_1 import (
    BrokerOrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from .etrade_sandbox_order_pipeline_v2_1 import ETradeSandboxOrderPipeline
from .etrade_sandbox_order_ledger_v2_1_2 import SandboxOrderLedger
from .etrade_sandbox_orders_reader_v2_1_2 import ETradeSandboxOrdersReader
from .etrade_sandbox_order_reconciliation_v2_1_2 import reconcile_sandbox_place


@dataclass
class SandboxCycleSignal:
    symbol: str
    side: str
    quantity: Decimal
    order_type: str="MARKET"
    strategy_id: str="SANDBOX_AUTONOMOUS_V2_1_3"


def build_canonical_request(signal: SandboxCycleSignal):
    side=OrderSide.BUY if str(signal.side).upper()=="BUY" else OrderSide.SELL
    order_type={
        "MARKET":OrderType.MARKET,
        "LIMIT":OrderType.LIMIT,
        "STOP":OrderType.STOP,
        "STOP_LIMIT":OrderType.STOP_LIMIT,
    }[str(signal.order_type).upper()]

    return BrokerOrderRequest(
        client_order_id="sandboxv213",
        symbol=str(signal.symbol).upper(),
        side=side,
        quantity=Decimal(signal.quantity),
        order_type=order_type,
        time_in_force=TimeInForce.DAY,
        strategy_id=signal.strategy_id,
    )


class ETradeSandboxAutonomousCycle:
    def __init__(self,order_transport,readonly_transport,root):
        self.pipeline=ETradeSandboxOrderPipeline(order_transport)
        self.reader=ETradeSandboxOrdersReader(readonly_transport)
        self.ledger=SandboxOrderLedger(root)

    def run_once(self,account_id_key,signal,client_order_id):
        request=build_canonical_request(signal)

        preview=self.pipeline.preview(
            account_id_key,
            request,
            client_order_id,
        )
        self.ledger.record_preview(account_id_key,request,preview)

        place=self.pipeline.place_from_preview(
            account_id_key,
            preview,
        )
        self.ledger.record_place(account_id_key,request,place)

        read_result=self.reader.list_orders_safe(account_id_key)
        reconciliation=reconcile_sandbox_place(
            place,
            read_result["payload"],
        )
        reconciliation["orders_read_status"]=read_result["status"]
        if read_result.get("error"):
            reconciliation["orders_read_error"]=read_result["error"]

        self.ledger.record_reconciliation(
            account_id_key,
            reconciliation,
        )

        return {
            "stage":"BROKER_INTEGRATION_V2_1_3_SANDBOX_AUTONOMOUS_CYCLE",
            "status":"PASS_SANDBOX_AUTONOMOUS_CYCLE",
            "generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "signal":{
                "symbol":request.symbol,
                "side":request.side.value,
                "quantity":str(request.quantity),
                "order_type":request.order_type.value,
                "strategy_id":request.strategy_id,
            },
            "preview_status":preview["status"],
            "preview_id":preview["preview_id"],
            "place_status":place["status"],
            "sandbox_order_id":place["order_id"],
            "reconciliation_status":reconciliation["status"],
            "observed_order_count":reconciliation["observed_order_count"],
            "matched_order_count":reconciliation["matched_order_count"],
            "ledger_path":str(self.ledger.path),
            "real_money_moved":False,
            "production_order_submission":False,
            "profitability_validation":False,
        }
