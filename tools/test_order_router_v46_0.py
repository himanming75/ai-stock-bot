import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tools.order_router_v46_0 import (
    OrderRouter,
    RiskDecisionInput,
    RouteRequest,
    RouterConfig,
    canonical_hash,
    load_risk_decision,
)


def approved_risk(**updates):
    core = {
        "schema_version": "v45.0.risk_policy_decision.1",
        "version": "45.0",
        "status": "PASS",
        "decision": "approve",
        "symbol": "AAPL",
        "client_order_id": "v43-test-order-001",
        "side": "buy",
        "order_notional": "10000",
        "estimated_risk_amount": "100",
        "estimated_risk_pct": "0.1",
        "projected_position_weight_pct": "10",
        "projected_symbol_exposure_pct": "10",
        "projected_gross_exposure_pct": "40",
        "projected_cash_reserve_pct": "40",
        "checks": [{"check_id": "demo", "status": "PASS", "message": "ok"}],
        "rejection_reasons": [],
        "network_used": False,
    }
    core.update(updates)
    return RiskDecisionInput(**core, decision_sha256=canonical_hash(core))


class OrderRouterV460Tests(unittest.TestCase):
    def router(self, **kwargs):
        return OrderRouter(RouterConfig(**kwargs), mode="paper")

    def test_single_route(self):
        plan = self.router().route(approved_risk(), RouteRequest(quantity="50"))
        self.assertEqual("PASS", plan.status)
        self.assertEqual(1, plan.child_order_count)
        self.assertEqual("50", plan.routed_quantity)

    def test_split_route(self):
        plan = self.router(max_child_quantity="500").route(
            approved_risk(), RouteRequest(quantity="1000")
        )
        self.assertEqual("PASS", plan.status)
        self.assertEqual(3, plan.child_order_count)
        self.assertEqual("1000", plan.routed_quantity)
        self.assertEqual("PAPER_PRIMARY", plan.children[0]["venue"])
        self.assertEqual("PAPER_SECONDARY", plan.children[-1]["venue"])

    def test_child_cap_creates_multiple_children(self):
        plan = self.router(max_child_quantity="200").route(
            approved_risk(), RouteRequest(quantity="1000")
        )
        self.assertEqual(5, plan.child_order_count)
        self.assertTrue(all(int(c["quantity"]) <= 200 for c in plan.children))

    def test_limit_order(self):
        plan = self.router().route(
            approved_risk(),
            RouteRequest(quantity="25", order_type="limit", limit_price="199.50"),
        )
        self.assertEqual("199.5", plan.limit_price)
        self.assertEqual("PASS", plan.status)

    def test_limit_missing_price_rejected(self):
        plan = self.router().route(
            approved_risk(),
            RouteRequest(quantity="25", order_type="limit"),
        )
        self.assertEqual("FAIL", plan.status)

    def test_market_with_limit_rejected(self):
        plan = self.router().route(
            approved_risk(),
            RouteRequest(quantity="25", limit_price="200"),
        )
        self.assertEqual("FAIL", plan.status)

    def test_risk_status_rejected(self):
        plan = self.router().route(
            approved_risk(status="FAIL"),
            RouteRequest(quantity="25"),
        )
        self.assertEqual("FAIL", plan.status)

    def test_risk_decision_rejected(self):
        plan = self.router().route(
            approved_risk(decision="reject"),
            RouteRequest(quantity="25"),
        )
        self.assertEqual("FAIL", plan.status)

    def test_risk_hash_tamper_rejected(self):
        risk = approved_risk()
        tampered = RiskDecisionInput(**{**asdict(risk), "symbol": "MSFT"})
        plan = self.router().route(tampered, RouteRequest(quantity="25"))
        self.assertIn(
            "V45 risk-policy SHA-256 verification failed.",
            plan.rejection_reasons,
        )

    def test_network_usage_rejected(self):
        plan = self.router().route(
            approved_risk(network_used=True),
            RouteRequest(quantity="25"),
        )
        self.assertEqual("FAIL", plan.status)

    def test_existing_rejection_reasons_rejected(self):
        plan = self.router().route(
            approved_risk(rejection_reasons=["blocked"]),
            RouteRequest(quantity="25"),
        )
        self.assertEqual("FAIL", plan.status)

    def test_quantity_max_rejected(self):
        plan = self.router(max_total_quantity="100").route(
            approved_risk(), RouteRequest(quantity="101")
        )
        self.assertEqual("FAIL", plan.status)

    def test_lot_size_rejected(self):
        plan = self.router(lot_size="10").route(
            approved_risk(), RouteRequest(quantity="25")
        )
        self.assertEqual("FAIL", plan.status)

    def test_odd_lot_allowed(self):
        plan = self.router(lot_size="10", allow_odd_lot=True).route(
            approved_risk(), RouteRequest(quantity="25")
        )
        self.assertEqual("PASS", plan.status)

    def test_hashes_present(self):
        plan = self.router().route(approved_risk(), RouteRequest(quantity="1000"))
        self.assertEqual(64, len(plan.route_sha256))
        self.assertTrue(all(len(c["child_sha256"]) == 64 for c in plan.children))

    def test_deterministic_hashes(self):
        first = self.router().route(approved_risk(), RouteRequest(quantity="1000"))
        second = self.router().route(approved_risk(), RouteRequest(quantity="1000"))
        self.assertEqual(first.route_sha256, second.route_sha256)
        self.assertEqual(first.children, second.children)

    def test_no_network(self):
        plan = self.router().route(approved_risk(), RouteRequest(quantity="50"))
        self.assertFalse(plan.network_used)
        self.assertTrue(all(c["network_used"] is False for c in plan.children))

    def test_export_and_load(self):
        router = self.router()
        plan = router.route(approved_risk(), RouteRequest(quantity="50"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "route.json"
            router.export(path, plan)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(payload["network_used"])
            self.assertEqual("PASS", payload["result"]["status"])

    def test_load_v45_export_shape(self):
        risk = approved_risk()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "risk.json"
            path.write_text(
                json.dumps({"decision": asdict(risk)}),
                encoding="utf-8",
            )
            loaded = load_risk_decision(path)
            self.assertEqual(risk, loaded)

    def test_live_gate(self):
        router = OrderRouter(mode="live")
        with self.assertRaises(PermissionError):
            router.route(approved_risk(), RouteRequest(quantity="50"))

    def test_live_transport_not_implemented(self):
        router = OrderRouter(mode="live", enable_live=True)
        with self.assertRaises(NotImplementedError):
            router.route(approved_risk(), RouteRequest(quantity="50"))

    def test_invalid_same_venue(self):
        with self.assertRaises(ValueError):
            RouterConfig(primary_venue="X", secondary_venue="x").validate()


if __name__ == "__main__":
    unittest.main()
