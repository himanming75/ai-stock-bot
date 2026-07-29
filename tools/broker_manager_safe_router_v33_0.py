#!/usr/bin/env python3
"""
V33.0 Broker Manager & Safe Order Router

Integrates:
- V31 live-trading readiness gate
- V32 broker adapter layer
- Central broker manager
- Safe order routing pipeline
- Unified health dashboard
- Final paper-trading readiness certificate

Routing pipeline:
Order Request
  -> V31 validation
  -> V31 live gate
  -> V32 adapter selection
  -> adapter capability check
  -> paper execution or external-adapter rejection
  -> immutable JSON routing receipt

No external broker network transport is enabled.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


VERSION = "33.0"
ROOT = Path(__file__).resolve().parent

V31_PATH = ROOT / "live_trading_readiness_v31_0.py"
V32_PATH = ROOT / "broker_adapter_layer_v32_0.py"


def _load_module(name: str, path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Required module is missing: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V31 = _load_module("v31_live_readiness", V31_PATH)
V32 = _load_module("v32_broker_adapter", V32_PATH)


@dataclass(frozen=True)
class RoutingReceipt:
    schema_version: str
    version: str
    route_id: str
    generated_at: str
    broker: str
    requested_mode: str
    final_status: str
    pipeline: list[dict[str, Any]]
    normalized_order: dict[str, Any] | None
    broker_result: dict[str, Any] | None
    live_transport_used: bool
    receipt_sha256: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class BrokerManager:
    def __init__(self) -> None:
        self._adapters: dict[tuple[str, str], Any] = {}

    def get_adapter(self, broker: str, mode: str):
        key = (broker, mode)
        if key not in self._adapters:
            adapter = V32.create_adapter(
                V32.BrokerName(broker),
                V32.TradingMode(mode),
            )
            self._adapters[key] = adapter
        return self._adapters[key]

    def health_dashboard(self) -> dict[str, Any]:
        brokers = {}
        for broker in V32.BrokerName:
            mode = "paper" if broker.value == "paper" else "live"
            adapter = self.get_adapter(broker.value, mode)
            brokers[broker.value] = {
                "health": asdict(adapter.health_check()),
                "capabilities": asdict(adapter.capabilities()),
            }

        ready = (
            brokers["paper"]["health"]["status"] == "PASS"
            and brokers["paper"]["capabilities"]["supports_paper"] is True
            and all(
                brokers[name]["capabilities"]["network_transport_enabled"] is False
                for name in ("ibkr", "alpaca", "tradestation")
            )
        )
        return {
            "schema_version": "v33.0.broker_health_dashboard.1",
            "version": VERSION,
            "status": "PASS" if ready else "FAIL",
            "paper_trading_ready": ready,
            "live_transport_enabled": False,
            "brokers": brokers,
            "generated_at": utc_now(),
        }

    def route_order(
        self,
        *,
        broker: str,
        mode: str,
        symbol: str,
        side: str,
        quantity: str,
        order_type: str,
        limit_price: str | None = None,
        runtime_live_flag: bool = False,
        approval_file: Path | None = None,
        client_order_id: str | None = None,
    ) -> RoutingReceipt:
        pipeline: list[dict[str, Any]] = []

        v31_order = V31.OrderRequest(
            symbol=symbol,
            side=V31.OrderSide(side),
            quantity=quantity,
            order_type=V31.OrderType(order_type),
            time_in_force=V31.TimeInForce.DAY,
            limit_price=limit_price,
            client_order_id=client_order_id,
        )
        validation = V31.validate_order(v31_order)
        pipeline.append({
            "stage": "validation",
            "status": "PASS" if validation.valid else "FAIL",
            "errors": validation.errors,
        })

        if not validation.valid:
            return self._receipt(
                broker=broker,
                mode=mode,
                final_status="REJECTED_VALIDATION",
                pipeline=pipeline,
                normalized_order=None,
                broker_result=None,
            )

        gate_open, gate_reasons = V31.evaluate_live_gate(
            V31.TradingMode(mode),
            runtime_live_flag,
            approval_file,
        )
        pipeline.append({
            "stage": "live_gate",
            "status": "PASS" if gate_open else "FAIL",
            "reasons": gate_reasons,
        })

        if not gate_open:
            return self._receipt(
                broker=broker,
                mode=mode,
                final_status="REJECTED_LIVE_GATE",
                pipeline=pipeline,
                normalized_order=validation.normalized_order,
                broker_result=None,
            )

        try:
            adapter = self.get_adapter(broker, mode)
        except Exception as exc:
            pipeline.append({
                "stage": "adapter_selection",
                "status": "FAIL",
                "error": f"{type(exc).__name__}: {exc}",
            })
            return self._receipt(
                broker=broker,
                mode=mode,
                final_status="REJECTED_ADAPTER",
                pipeline=pipeline,
                normalized_order=validation.normalized_order,
                broker_result=None,
            )

        capabilities = asdict(adapter.capabilities())
        health = asdict(adapter.health_check())
        pipeline.append({
            "stage": "adapter_selection",
            "status": "PASS",
            "adapter": adapter.name,
            "capabilities": capabilities,
            "health": health,
        })

        normalized = validation.normalized_order or {}
        broker_order = V32.BrokerOrder(
            symbol=normalized["symbol"],
            side=V32.OrderSide(normalized["side"]),
            quantity=normalized["quantity"],
            order_type=V32.OrderType(normalized["order_type"]),
            limit_price=normalized.get("limit_price"),
            client_order_id=normalized.get("client_order_id"),
        )
        broker_result = adapter.submit_order(broker_order)
        broker_payload = asdict(broker_result)

        pipeline.append({
            "stage": "broker_execution",
            "status": (
                "PASS"
                if broker_result.status != V32.OrderStatus.REJECTED.value
                else "FAIL"
            ),
            "broker_status": broker_result.status,
            "rejection_reason": broker_result.rejection_reason,
            "live_transport_used": broker_result.live_transport_used,
        })

        if broker_result.status == V32.OrderStatus.REJECTED.value:
            final_status = "REJECTED_BROKER"
        elif broker_result.status == V32.OrderStatus.FILLED.value:
            final_status = "PAPER_FILLED"
        else:
            final_status = "PAPER_ACCEPTED"

        return self._receipt(
            broker=broker,
            mode=mode,
            final_status=final_status,
            pipeline=pipeline,
            normalized_order=normalized,
            broker_result=broker_payload,
        )

    def _receipt(
        self,
        *,
        broker: str,
        mode: str,
        final_status: str,
        pipeline: list[dict[str, Any]],
        normalized_order: dict[str, Any] | None,
        broker_result: dict[str, Any] | None,
    ) -> RoutingReceipt:
        core = {
            "schema_version": "v33.0.routing_receipt.1",
            "version": VERSION,
            "route_id": f"route-{uuid.uuid4().hex}",
            "generated_at": utc_now(),
            "broker": broker,
            "requested_mode": mode,
            "final_status": final_status,
            "pipeline": pipeline,
            "normalized_order": normalized_order,
            "broker_result": broker_result,
            "live_transport_used": bool(
                broker_result and broker_result.get("live_transport_used")
            ),
        }
        return RoutingReceipt(
            **core,
            receipt_sha256=canonical_hash(core),
        )


def readiness_certificate(manager: BrokerManager) -> dict[str, Any]:
    dashboard = manager.health_dashboard()
    paper_ok = dashboard["paper_trading_ready"]
    external_disabled = all(
        dashboard["brokers"][name]["capabilities"]["network_transport_enabled"] is False
        for name in ("ibkr", "alpaca", "tradestation")
    )

    checks = {
        "paper_broker_ready": paper_ok,
        "external_transports_disabled": external_disabled,
        "live_gate_module_available": V31_PATH.is_file(),
        "broker_adapter_module_available": V32_PATH.is_file(),
    }
    passed = all(checks.values())
    payload = {
        "schema_version": "v33.0.paper_trading_certificate.1",
        "version": VERSION,
        "status": "PASS" if passed else "FAIL",
        "certification_scope": "PAPER_TRADING_ONLY",
        "live_transport_enabled": False,
        "checks": checks,
        "generated_at": utc_now(),
    }
    payload["certificate_sha256"] = canonical_hash(payload)
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="V33.0 Broker Manager & Safe Order Router"
    )
    p.add_argument(
        "--action",
        choices=["health", "certificate", "route"],
        default="health",
    )
    p.add_argument(
        "--broker",
        choices=[item.value for item in V32.BrokerName],
        default="paper",
    )
    p.add_argument(
        "--mode",
        choices=[item.value for item in V31.TradingMode],
        default="paper",
    )
    p.add_argument("--symbol", default="AAPL")
    p.add_argument(
        "--side",
        choices=[item.value for item in V31.OrderSide],
        default="buy",
    )
    p.add_argument("--quantity", default="1")
    p.add_argument(
        "--order-type",
        choices=[item.value for item in V31.OrderType],
        default="market",
    )
    p.add_argument("--limit-price", default=None)
    p.add_argument("--client-order-id", default=None)
    p.add_argument("--enable-live", action="store_true")
    p.add_argument("--approval-file", default=None)
    p.add_argument(
        "--output",
        default="release/v33/audit/broker_manager_result_v33_0.json",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    manager = BrokerManager()

    if args.action == "health":
        payload: Any = manager.health_dashboard()
        success = payload["status"] == "PASS"
    elif args.action == "certificate":
        payload = readiness_certificate(manager)
        success = payload["status"] == "PASS"
    else:
        receipt = manager.route_order(
            broker=args.broker,
            mode=args.mode,
            symbol=args.symbol,
            side=args.side,
            quantity=args.quantity,
            order_type=args.order_type,
            limit_price=args.limit_price,
            runtime_live_flag=args.enable_live,
            approval_file=Path(args.approval_file) if args.approval_file else None,
            client_order_id=args.client_order_id,
        )
        payload = asdict(receipt)
        success = receipt.final_status in {"PAPER_FILLED", "PAPER_ACCEPTED"}

    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
