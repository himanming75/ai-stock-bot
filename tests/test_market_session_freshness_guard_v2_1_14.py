from pathlib import Path
from datetime import datetime,timezone
import sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.market_session_freshness_guard_v2_1_14 import (
    FreshnessPolicyV2114,
    regular_session_window,
    evaluate_bar_freshness,
    build_session_freshness_gate,
)
from broker_integration_v1.session_freshness_aware_runtime_v2_1_14 import (
    SessionFreshnessAwareRuntimeV2114,
)
from broker_integration_v1.market_session_freshness_guard_status_v2_1_14 import (
    build_v2_1_14_status,
)


class FakeBootstrapClient:
    def __init__(self,last_timestamp):
        self.last_diagnostics={
            "symbol_diagnostics":{
                "AAPL":{"last_timestamp":last_timestamp},
            }
        }


class FakeValidator:
    def __init__(self,last_timestamp):
        self.bootstrap_client=FakeBootstrapClient(last_timestamp)


class FakeBaseRuntime:
    def __init__(self,last_timestamp):
        self.validator=FakeValidator(last_timestamp)

    def build_runtime_plan(self,quantity=1):
        return {
            "symbols":["AAPL"],
            "bootstrap_status":"PASS_BOOTSTRAP_BASELINE",
            "bootstrap_counts":{"AAPL":3},
            "canonical_gate_aligned":True,
            "eligible_signal_count":1,
            "eligible_signals":["synthetic"],
            "hold_only":False,
            "requires_etrade_oauth":True,
            "requires_explicit_sandbox_confirmation":True,
        }


class TestV2114(unittest.TestCase):
    def test_sunday_outside_window(self):
        now=datetime(2026,8,9,16,0,tzinfo=timezone.utc)
        s=regular_session_window(now)
        self.assertFalse(s["inside_regular_clock_window"])
        self.assertFalse(s["exchange_open_claimed"])

    def test_fresh_bar_inside_window(self):
        now=datetime(2026,8,10,14,0,tzinfo=timezone.utc)
        ts=datetime(2026,8,10,13,59,tzinfo=timezone.utc)
        r=build_session_freshness_gate(
            {"AAPL":ts},
            now_utc=now,
            policy=FreshnessPolicyV2114(max_bar_age_seconds=180),
        )
        self.assertTrue(r["signal_capture_allowed"])
        self.assertEqual(r["status"],"PASS_REGULAR_WINDOW_FRESH_BARS")

    def test_stale_bar_blocked(self):
        now=datetime(2026,8,10,14,0,tzinfo=timezone.utc)
        ts=datetime(2026,8,10,13,50,tzinfo=timezone.utc)
        r=build_session_freshness_gate(
            {"AAPL":ts},
            now_utc=now,
        )
        self.assertFalse(r["signal_capture_allowed"])
        self.assertEqual(r["status"],"BLOCK_STALE_OR_INVALID_BAR")

    def test_runtime_zeroes_eligible_when_outside(self):
        now=datetime(2026,8,9,16,0,tzinfo=timezone.utc)
        base=FakeBaseRuntime("2026-08-07T19:59:00Z")
        r=SessionFreshnessAwareRuntimeV2114(
            ["AAPL"],
            base_runtime=base,
        ).build_runtime_plan(now_utc=now)
        self.assertEqual(r["eligible_signal_count"],0)
        self.assertTrue(r["hold_only"])
        self.assertFalse(r["requires_etrade_oauth"])
        self.assertFalse(r["production_order_submission"])

    def test_status_locks(self):
        s=build_v2_1_14_status()
        self.assertTrue(s["holiday_open_claim_avoided"])
        self.assertTrue(s["stale_signal_block_ready"])
        self.assertFalse(s["broker_order_submission_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
