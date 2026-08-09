from pathlib import Path
from decimal import Decimal
import tempfile,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.persistent_market_observer_v2_1_13 import (
    PersistentMarketObserverV2113,
    ObservationPolicyV2113,
    canonical_plan_snapshot,
    snapshot_fingerprint,
)
from broker_integration_v1.persistent_market_observer_status_v2_1_13 import (
    build_v2_1_13_status,
)


class HoldRuntime:
    def __init__(self):
        self.calls=0

    def build_runtime_plan(self,quantity=Decimal("1")):
        self.calls+=1
        return {
            "bootstrap_status":"PASS_BOOTSTRAP_BASELINE",
            "bootstrap_counts":{"AAPL":3},
            "canonical_gate_aligned":True,
            "eligible_signal_count":0,
            "eligible_signals":[],
            "hold_only":True,
        }


class ChangingRuntime:
    def __init__(self):
        self.calls=0

    def build_runtime_plan(self,quantity=Decimal("1")):
        self.calls+=1
        return {
            "bootstrap_status":"PASS_BOOTSTRAP_BASELINE",
            "bootstrap_counts":{"AAPL":3+self.calls},
            "canonical_gate_aligned":True,
            "eligible_signal_count":0,
            "eligible_signals":[],
            "hold_only":True,
        }


class TestV2113(unittest.TestCase):
    def test_policy_bounds(self):
        with self.assertRaises(ValueError):
            ObservationPolicyV2113(max_iterations=0).validate()

    def test_fingerprint_stable(self):
        plan={
            "bootstrap_status":"PASS",
            "bootstrap_counts":{"AAPL":3},
            "canonical_gate_aligned":True,
            "eligible_signal_count":0,
            "eligible_signals":[],
            "hold_only":True,
        }
        s=canonical_plan_snapshot(plan)
        self.assertEqual(
            snapshot_fingerprint(s),
            snapshot_fingerprint(s),
        )

    def test_unchanged_guard_stops(self):
        with tempfile.TemporaryDirectory() as td:
            o=PersistentMarketObserverV2113(
                HoldRuntime(),
                td,
                ObservationPolicyV2113(
                    max_iterations=10,
                    interval_seconds=1,
                    stop_after_unchanged=2,
                ),
                sleep_fn=lambda _:None,
            )
            r=o.run()
            self.assertEqual(r["stopped_reason"],"UNCHANGED_LIMIT")
            self.assertEqual(r["broker_orders_submitted"],0)
            self.assertTrue(Path(r["ledger_path"]).exists())

    def test_changed_runtime_reaches_max(self):
        with tempfile.TemporaryDirectory() as td:
            o=PersistentMarketObserverV2113(
                ChangingRuntime(),
                td,
                ObservationPolicyV2113(
                    max_iterations=3,
                    interval_seconds=1,
                    stop_after_unchanged=2,
                ),
                sleep_fn=lambda _:None,
            )
            r=o.run()
            self.assertEqual(r["observation_count"],3)
            self.assertEqual(r["stopped_reason"],"MAX_ITERATIONS")

    def test_status_locks(self):
        s=build_v2_1_13_status()
        self.assertFalse(s["etrade_oauth_from_stage"])
        self.assertFalse(s["sandbox_place_from_stage"])
        self.assertFalse(s["production_order_post_allowed"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
