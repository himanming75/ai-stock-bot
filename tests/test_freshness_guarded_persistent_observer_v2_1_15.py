from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.persistent_market_observer_v2_1_13 import (
    ObservationPolicyV2113,
)
from broker_integration_v1.freshness_guarded_persistent_observer_v2_1_15 import (
    FreshnessGuardedPersistentObserverV2115,
)
from broker_integration_v1.freshness_guarded_persistent_observer_status_v2_1_15 import (
    build_v2_1_15_status,
)


class NeverCalledRuntime:
    def __init__(self):
        self.calls=0
    def build_runtime_plan(self,quantity=Decimal("1"),now_utc=None):
        self.calls+=1
        raise AssertionError("runtime should not be called outside regular window")


class FreshRuntime:
    def __init__(self):
        self.calls=0
    def build_runtime_plan(self,quantity=Decimal("1"),now_utc=None):
        self.calls+=1
        return {
            "symbols":["AAPL"],
            "bootstrap_status":"PASS_BOOTSTRAP_BASELINE",
            "bootstrap_counts":{"AAPL":3},
            "canonical_gate_aligned":True,
            "eligible_signal_count":0,
            "eligible_signals":[],
            "hold_only":True,
            "session_freshness_gate":{
                "status":"PASS_REGULAR_WINDOW_FRESH_BARS",
                "session":{"status":"INSIDE_REGULAR_WINDOW"},
                "freshness":{"all_fresh":True},
            },
            "signal_capture_allowed_by_v2_1_14":True,
        }


class StaleRuntime:
    def __init__(self):
        self.calls=0
    def build_runtime_plan(self,quantity=Decimal("1"),now_utc=None):
        self.calls+=1
        return {
            "symbols":["AAPL"],
            "bootstrap_status":"PASS_BOOTSTRAP_BASELINE",
            "bootstrap_counts":{"AAPL":3},
            "canonical_gate_aligned":True,
            "eligible_signal_count":0,
            "eligible_signals":[],
            "hold_only":True,
            "session_freshness_gate":{
                "status":"BLOCK_STALE_OR_INVALID_BAR",
                "session":{"status":"INSIDE_REGULAR_WINDOW"},
                "freshness":{"all_fresh":False},
            },
            "signal_capture_allowed_by_v2_1_14":False,
        }


class TestV2115(unittest.TestCase):
    def test_outside_window_skips_runtime(self):
        runtime=NeverCalledRuntime()
        now=lambda: datetime(2026,8,9,16,0,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            r=FreshnessGuardedPersistentObserverV2115(
                runtime,
                td,
                ObservationPolicyV2113(
                    max_iterations=3,
                    interval_seconds=1,
                    stop_after_unchanged=2,
                ),
                sleep_fn=lambda _:None,
                now_fn=now,
            ).run()
        self.assertEqual(runtime.calls,0)
        self.assertEqual(r["market_data_runtime_call_count"],0)
        self.assertGreaterEqual(r["market_data_fetch_skipped_count"],1)
        self.assertEqual(r["broker_orders_submitted"],0)

    def test_inside_window_fresh_calls_runtime(self):
        runtime=FreshRuntime()
        now=lambda: datetime(2026,8,10,14,0,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            r=FreshnessGuardedPersistentObserverV2115(
                runtime,
                td,
                ObservationPolicyV2113(
                    max_iterations=1,
                    interval_seconds=1,
                    stop_after_unchanged=2,
                ),
                sleep_fn=lambda _:None,
                now_fn=now,
            ).run()
        self.assertEqual(runtime.calls,1)
        self.assertEqual(r["fresh_observation_count"],1)
        self.assertEqual(r["stale_block_count"],0)

    def test_inside_window_stale_is_blocked(self):
        runtime=StaleRuntime()
        now=lambda: datetime(2026,8,10,14,0,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as td:
            r=FreshnessGuardedPersistentObserverV2115(
                runtime,
                td,
                ObservationPolicyV2113(
                    max_iterations=1,
                    interval_seconds=1,
                    stop_after_unchanged=2,
                ),
                sleep_fn=lambda _:None,
                now_fn=now,
            ).run()
        self.assertEqual(runtime.calls,1)
        self.assertEqual(r["stale_block_count"],1)
        self.assertEqual(r["eligible_capture_count"],0)

    def test_status_locks(self):
        s=build_v2_1_15_status()
        self.assertTrue(s["outside_window_rest_skip_ready"])
        self.assertTrue(s["eligible_capture_only_when_fresh"])
        self.assertFalse(s["etrade_oauth_from_stage"])
        self.assertFalse(s["sandbox_place_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
