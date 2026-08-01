from __future__ import annotations

import unittest

from runtime_certification import (
    CertificationStatus,
    ContinuousRuntimeFinalCertifier,
    RuntimeIntegrityValidator,
    RuntimeStressRunner,
)


class FakeRuntime:
    def __init__(self):
        self.state = "CREATED"
        self.cycles = 0
        self.recovery_saves = 0

    def start(self):
        self.state = "RUNNING"

    def run_cycle(self):
        if self.state != "RUNNING":
            raise RuntimeError("not running")
        self.cycles += 1

    def save_recovery(self):
        self.recovery_saves += 1

    def recover(self):
        self.state = "RECOVERED"

    def close_session(self):
        self.state = "CLOSED"

    def stop(self):
        self.state = "STOPPED"


def valid_components():
    return (
        "continuous_paper_runtime",
        "paper_runtime_stability",
        "paper_runtime_scheduler",
        "paper_scheduler",
        "paper_runtime",
        "risk_engine",
        "portfolio_engine",
        "execution_engine",
        "strategy_engine",
        "runtime_engine",
        "alpaca_broker",
    )


class ContinuousRuntimeFinalCertificationTests(unittest.TestCase):
    def setUp(self):
        self.validator = RuntimeIntegrityValidator()

    def test_component_integrity_pass(self):
        self.assertTrue(
            self.validator.validate_components(valid_components()).passed
        )

    def test_component_integrity_fail(self):
        self.assertFalse(
            self.validator.validate_components(["continuous_paper_runtime"]).passed
        )

    def test_event_order_pass(self):
        events = ["PREPARE", "START_SESSION", "RUN_CYCLE", "CLOSE_SESSION", "STOPPED"]
        self.assertTrue(self.validator.validate_event_order(events).passed)

    def test_event_order_fail(self):
        self.assertFalse(self.validator.validate_event_order(["RUN_CYCLE"]).passed)

    def test_state_consistency_pass(self):
        state = {
            "runtime_state": "STOPPED",
            "session_active": False,
            "session_closed": True,
            "circuit_open": False,
        }
        self.assertTrue(self.validator.validate_state_consistency(state).passed)

    def test_recovery_pass(self):
        snapshot = {"exists": True, "valid": True, "generation": 10}
        self.assertTrue(self.validator.validate_recovery(snapshot).passed)

    def test_portfolio_pass(self):
        portfolio = {
            "cash_nonnegative": True,
            "positions_nonnegative": True,
            "equity_consistent": True,
        }
        self.assertTrue(self.validator.validate_portfolio(portfolio).passed)

    def test_safety_pass(self):
        counters = {
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
        }
        self.assertTrue(self.validator.validate_safety(counters).passed)

    def test_safety_fail(self):
        counters = {
            "network_requests_executed": 1,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
        }
        self.assertFalse(self.validator.validate_safety(counters).passed)

    def test_stress_1000_cycles(self):
        result = RuntimeStressRunner(FakeRuntime).run(
            cycles=1000,
            restart_every=100,
        )
        self.assertEqual(result.cycles_completed, 1000)
        self.assertEqual(result.restart_count, 9)
        self.assertEqual(result.recovery_count, 9)
        self.assertEqual(result.final_state, "STOPPED")

    def test_stress_validation(self):
        runner = RuntimeStressRunner(FakeRuntime)
        with self.assertRaises(ValueError):
            runner.run(cycles=0, restart_every=10)

    def test_final_certificate_pass(self):
        stress = RuntimeStressRunner(FakeRuntime).run(
            cycles=1000,
            restart_every=100,
        )
        certificate = ContinuousRuntimeFinalCertifier(
            validator=self.validator
        ).certify(
            available_components=valid_components(),
            events=["PREPARE", "START_SESSION", "RUN_CYCLE", "CLOSE_SESSION", "STOPPED"],
            runtime_state={
                "runtime_state": "STOPPED",
                "session_active": False,
                "session_closed": True,
                "circuit_open": False,
            },
            recovery_snapshot={"exists": True, "valid": True, "generation": 10},
            portfolio_state={
                "cash_nonnegative": True,
                "positions_nonnegative": True,
                "equity_consistent": True,
            },
            safety_counters={
                "network_requests_executed": 0,
                "write_requests_executed": 0,
                "actual_paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
            stress=stress,
        )
        self.assertEqual(certificate.certification_status, CertificationStatus.PASS)
        self.assertEqual(len(certificate.certificate_sha256), 64)
        self.assertTrue(certificate.certificate_id.startswith("continuous-paper-final-"))

    def test_certificate_json_serialization(self):
        stress = RuntimeStressRunner(FakeRuntime).run(
            cycles=10,
            restart_every=5,
        )
        certificate = ContinuousRuntimeFinalCertifier(
            validator=self.validator
        ).certify(
            available_components=valid_components(),
            events=["PREPARE", "START_SESSION", "RUN_CYCLE", "CLOSE_SESSION", "STOPPED"],
            runtime_state={
                "runtime_state": "STOPPED",
                "session_active": False,
                "session_closed": True,
                "circuit_open": False,
            },
            recovery_snapshot={"exists": True, "valid": True, "generation": 1},
            portfolio_state={
                "cash_nonnegative": True,
                "positions_nonnegative": True,
                "equity_consistent": True,
            },
            safety_counters={
                "network_requests_executed": 0,
                "write_requests_executed": 0,
                "actual_paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
            stress=stress,
        )
        raw = certificate.to_json_dict()
        self.assertEqual(raw["certification_status"], "PASS")
        self.assertEqual(raw["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
