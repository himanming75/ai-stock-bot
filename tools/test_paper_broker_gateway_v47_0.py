import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.paper_broker_gateway_v47_0 import (
    ChildOrderInput,
    PaperBrokerGateway,
    RoutePlanInput,
    canonical_hash,
    load_route,
)


def make_child(sequence=1, child_order_id="v46-child-1", **updates):
    core = {
        "sequence": sequence,
        "child_order_id": child_order_id,
        "parent_client_order_id": "v43-parent-1",
        "symbol": "AAPL",
        "side": "buy",
        "quantity": "50",
        "order_type": "market",
        "time_in_force": "day",
        "limit_price": None,
        "venue": "PAPER_PRIMARY",
        "status": "ROUTED_PAPER",
        "network_used": False,
    }
    core.update(updates)
    return {**core, "child_sha256": canonical_hash(core)}


def make_route(children=None, **updates):
    children = children or [make_child()]
    core = {
        "schema_version": "v46.0.route_plan.1",
        "version": "46.0",
        "status": "PASS",
        "route_decision": "route",
        "parent_client_order_id": "v43-parent-1",
        "symbol": "AAPL",
        "side": "buy",
        "requested_quantity": "50",
        "routed_quantity": "50",
        "child_order_count": len(children),
        "order_type": "market",
        "time_in_force": "day",
        "limit_price": None,
        "checks": [{"check_id": "demo", "status": "PASS", "message": "ok"}],
        "rejection_reasons": [],
        "children": children,
        "network_used": False,
    }
    core.update(updates)
    return RoutePlanInput(**core, route_sha256=canonical_hash(core))


class PaperBrokerGatewayV470Tests(unittest.TestCase):
    def gateway(self):
        return PaperBrokerGateway(
            mode="paper",
            reference_time="2026-07-29T18:00:00Z",
        )

    def test_accept_single_child(self):
        result = self.gateway().accept_route(make_route())
        self.assertEqual("PASS", result.status)
        self.assertEqual(1, result.accepted_count)
        self.assertEqual("ACCEPTED", result.orders[0]["status"])

    def test_accept_multiple_children(self):
        children = [
            make_child(1, "v46-child-1", quantity="500"),
            make_child(2, "v46-child-2", quantity="100"),
            make_child(3, "v46-child-3", quantity="400", venue="PAPER_SECONDARY"),
        ]
        result = self.gateway().accept_route(
            make_route(
                children,
                requested_quantity="1000",
                routed_quantity="1000",
            )
        )
        self.assertEqual(3, result.accepted_count)
        self.assertEqual(3, len(result.ledger))

    def test_deterministic_broker_order_id(self):
        first = self.gateway().accept_route(make_route())
        second = self.gateway().accept_route(make_route())
        self.assertEqual(
            first.orders[0]["broker_order_id"],
            second.orders[0]["broker_order_id"],
        )

    def test_deterministic_gateway_hash(self):
        first = self.gateway().accept_route(make_route())
        second = self.gateway().accept_route(make_route())
        self.assertEqual(first.gateway_sha256, second.gateway_sha256)

    def test_route_status_rejected(self):
        result = self.gateway().accept_route(make_route(status="FAIL"))
        self.assertEqual("FAIL", result.status)

    def test_route_decision_rejected(self):
        result = self.gateway().accept_route(make_route(route_decision="reject"))
        self.assertEqual("FAIL", result.status)

    def test_route_network_rejected(self):
        result = self.gateway().accept_route(make_route(network_used=True))
        self.assertEqual("FAIL", result.status)

    def test_route_rejection_reasons_rejected(self):
        result = self.gateway().accept_route(
            make_route(rejection_reasons=["blocked"])
        )
        self.assertEqual("FAIL", result.status)

    def test_route_child_count_mismatch(self):
        result = self.gateway().accept_route(make_route(child_order_count=2))
        self.assertEqual("FAIL", result.status)

    def test_route_hash_tamper_rejected(self):
        route = make_route()
        tampered = RoutePlanInput(**{**asdict(route), "symbol": "MSFT"})
        result = self.gateway().accept_route(tampered)
        self.assertIn(
            "V46 route-plan SHA-256 verification failed.",
            result.rejection_reasons,
        )

    def test_child_hash_tamper_rejected(self):
        child = make_child()
        child["quantity"] = "51"
        result = self.gateway().accept_route(make_route([child]))
        self.assertEqual("FAIL", result.status)

    def test_child_network_rejected(self):
        result = self.gateway().accept_route(
            make_route([make_child(network_used=True)])
        )
        self.assertEqual("FAIL", result.status)

    def test_child_status_rejected(self):
        result = self.gateway().accept_route(
            make_route([make_child(status="FILLED")])
        )
        self.assertEqual("FAIL", result.status)

    def test_duplicate_rejected(self):
        gateway = self.gateway()
        first = gateway.accept_route(make_route())
        second = gateway.accept_route(make_route())
        self.assertEqual("PASS", first.status)
        self.assertEqual("FAIL", second.status)
        self.assertEqual(1, second.duplicate_count)

    def test_transition_to_working(self):
        gateway = self.gateway()
        result = gateway.accept_route(make_route())
        broker_id = result.orders[0]["broker_order_id"]
        updated = gateway.transition_order(broker_id, "WORKING")
        self.assertEqual("WORKING", updated.status)

    def test_working_to_partial_fill(self):
        gateway = self.gateway()
        result = gateway.accept_route(make_route())
        broker_id = result.orders[0]["broker_order_id"]
        gateway.transition_order(broker_id, "WORKING")
        updated = gateway.transition_order(broker_id, "PARTIAL_FILL")
        self.assertEqual("PARTIAL_FILL", updated.status)

    def test_working_to_filled(self):
        gateway = self.gateway()
        result = gateway.accept_route(make_route())
        broker_id = result.orders[0]["broker_order_id"]
        gateway.transition_order(broker_id, "WORKING")
        updated = gateway.transition_order(broker_id, "FILLED")
        self.assertEqual("FILLED", updated.status)

    def test_cancel_accepted(self):
        gateway = self.gateway()
        result = gateway.accept_route(make_route())
        broker_id = result.orders[0]["broker_order_id"]
        cancelled = gateway.cancel_order(broker_id)
        self.assertEqual("CANCELLED", cancelled.status)

    def test_cancel_working(self):
        gateway = self.gateway()
        result = gateway.accept_route(make_route())
        broker_id = result.orders[0]["broker_order_id"]
        gateway.transition_order(broker_id, "WORKING")
        cancelled = gateway.cancel_order(broker_id)
        self.assertEqual("CANCELLED", cancelled.status)

    def test_cancel_filled_rejected(self):
        gateway = self.gateway()
        result = gateway.accept_route(make_route())
        broker_id = result.orders[0]["broker_order_id"]
        gateway.transition_order(broker_id, "WORKING")
        gateway.transition_order(broker_id, "FILLED")
        with self.assertRaises(ValueError):
            gateway.cancel_order(broker_id)

    def test_invalid_transition_rejected(self):
        gateway = self.gateway()
        result = gateway.accept_route(make_route())
        broker_id = result.orders[0]["broker_order_id"]
        with self.assertRaises(ValueError):
            gateway.transition_order(broker_id, "FILLED")

    def test_unknown_order_rejected(self):
        with self.assertRaises(KeyError):
            self.gateway().cancel_order("missing")

    def test_ledger_hash_chain(self):
        gateway = self.gateway()
        result = gateway.accept_route(make_route())
        broker_id = result.orders[0]["broker_order_id"]
        gateway.transition_order(broker_id, "WORKING")
        self.assertEqual("GENESIS", gateway.ledger[0].previous_entry_sha256)
        self.assertEqual(
            gateway.ledger[0].entry_sha256,
            gateway.ledger[1].previous_entry_sha256,
        )

    def test_order_hash_present(self):
        result = self.gateway().accept_route(make_route())
        self.assertEqual(64, len(result.orders[0]["broker_order_sha256"]))

    def test_gateway_hash_present(self):
        result = self.gateway().accept_route(make_route())
        self.assertEqual(64, len(result.gateway_sha256))

    def test_no_network(self):
        result = self.gateway().accept_route(make_route())
        self.assertFalse(result.network_used)
        self.assertFalse(result.orders[0]["network_used"])

    def test_export(self):
        gateway = self.gateway()
        result = gateway.accept_route(make_route())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gateway.json"
            gateway.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("PASS", payload["result"]["status"])
            self.assertFalse(payload["network_used"])

    def test_load_route_export_shape(self):
        route = make_route()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "route.json"
            path.write_text(
                json.dumps({"result": asdict(route)}),
                encoding="utf-8",
            )
            loaded = load_route(path)
            self.assertEqual(route, loaded)

    def test_live_gate(self):
        gateway = PaperBrokerGateway(mode="live")
        with self.assertRaises(PermissionError):
            gateway.accept_route(make_route())

    def test_live_transport_not_implemented(self):
        gateway = PaperBrokerGateway(mode="live", enable_live=True)
        with self.assertRaises(NotImplementedError):
            gateway.accept_route(make_route())

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            PaperBrokerGateway(mode="bad")


if __name__ == "__main__":
    unittest.main()
