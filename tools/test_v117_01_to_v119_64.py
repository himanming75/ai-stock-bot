import tempfile,unittest
from pathlib import Path

from live_safety_system.kill_switch import evaluate_kill_switch
from live_safety_system.loss_limits import evaluate_loss_limits
from live_safety_system.exposure import evaluate_exposure
from live_safety_system.anomaly import detect_anomalies
from live_safety_system.emergency import build_emergency_action
from live_safety_system.resume import build_resume_gate
from live_safety_system.certificate import build_certificate
from live_safety_system.engine import evaluate

POLICY={
    "maximum_market_data_age_seconds":30,
    "maximum_clock_drift_seconds":5,
    "maximum_daily_loss_pct":2,
    "maximum_weekly_loss_pct":5,
    "maximum_single_order_notional":5000,
    "maximum_pending_order_notional":10000,
    "maximum_open_positions":10,
    "maximum_gross_exposure_pct":100,
    "maximum_price_gap_pct":8,
    "maximum_spread_pct":2,
    "maximum_reject_count":3,
}
TELEMETRY={
    "manual_kill_switch":False,
    "broker_health":"HEALTHY",
    "market_data_age_seconds":2,
    "market_halt_detected":False,
    "clock_drift_seconds":0.2,
    "daily_pnl":-100,
    "weekly_pnl":-200,
    "account_equity":100000,
    "open_position_count":2,
    "gross_exposure":20000,
    "price_gap_pct":1,
    "spread_pct":0.1,
    "reject_count":0,
    "duplicate_event_count":0,
    "position_mismatch_detected":False,
    "manual_resume_approval_granted":False,
}

class Tests(unittest.TestCase):
    def test_kill_switch_clear(self):
        self.assertFalse(evaluate_kill_switch(
            POLICY,TELEMETRY
        )["triggered"])

    def test_kill_switch_triggered(self):
        bad=dict(TELEMETRY)
        bad["manual_kill_switch"]=True
        self.assertTrue(evaluate_kill_switch(
            POLICY,bad
        )["triggered"])

    def test_loss_limits(self):
        self.assertTrue(evaluate_loss_limits(
            POLICY,TELEMETRY
        )["passed"])

    def test_exposure(self):
        execution={"order_intents":[
            {"estimated_notional":2000},
            {"estimated_notional":2000},
        ]}
        self.assertTrue(evaluate_exposure(
            POLICY,execution,TELEMETRY
        )["passed"])

    def test_anomaly(self):
        self.assertFalse(detect_anomalies(
            POLICY,TELEMETRY
        )["detected"])

    def test_emergency(self):
        clear={"triggered":False,"reasons":[]}
        passed={"passed":True,"failed":[]}
        anomaly={"detected":False,"events":[]}
        self.assertFalse(build_emergency_action(
            clear,passed,passed,anomaly
        )["emergency_shutdown_required"])

    def test_resume_blocked(self):
        emergency={"emergency_shutdown_required":False}
        self.assertFalse(build_resume_gate(
            emergency,TELEMETRY
        )["resume_allowed"])

    def test_certificate(self):
        value=build_certificate(
            True,{"state":"ARMED_NOT_TRIGGERED"},
            {"state":"SAFETY_CLEAR"},
            {"state":"RESUME_BLOCKED"},
        )
        self.assertEqual(len(value["certificate_sha256"]),64)

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(
                evaluate(Path(temp))["state"],
                "LIVE_SAFETY_SYSTEM_SOURCE_REQUIRED",
            )

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(
                evaluate(Path(temp))["actual_orders_submitted"],0
            )

if __name__=="__main__":
    unittest.main()
