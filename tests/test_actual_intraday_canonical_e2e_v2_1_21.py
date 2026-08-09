from pathlib import Path
from datetime import datetime,timezone
import tempfile,sys,unittest,json

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.actual_intraday_canonical_e2e_validation_v2_1_21 import (
    ActualIntradayCanonicalEndToEndValidatorV2121,
)
from broker_integration_v1.actual_intraday_canonical_e2e_validation_status_v2_1_21 import (
    build_v2_1_21_status,
)


FIXTURE_EVIDENCE_KEY="fixture-current-evidence-key"


class FakeRuntime:
    def __init__(self,eligible=True,fresh=True):
        self.eligible=eligible
        self.fresh=fresh

    def build_runtime_plan(self,quantity=1,now_utc=None):
        return {
            "signal_capture_allowed_by_v2_1_14":self.fresh,
            "session_freshness_gate":{
                "status":(
                    "PASS_REGULAR_WINDOW_FRESH_BARS"
                    if self.fresh
                    else "BLOCK_STALE_OR_INVALID_BAR"
                ),
            },
            "eligible_signal_count":1 if self.eligible else 0,
        }


class FakeObserver:
    def __init__(self,*args):
        self.root=Path(args[1])
        self.runtime=args[0]

    def run(self,quantity=1):
        self.runtime.build_runtime_plan(
            quantity=quantity,
            now_utc=datetime(
                2026,8,10,14,0,
                tzinfo=timezone.utc,
            ),
        )

        # V2.1.21 binds qualification to the CURRENT V2.1.15 observation.
        p=(
            self.root
            /"runtime"
            /"freshness_guarded_persistent_observer_v2_1_15"
        )
        p.mkdir(parents=True,exist_ok=True)
        (p/"latest_snapshot.json").write_text(
            json.dumps({
                "snapshot_fingerprint":FIXTURE_EVIDENCE_KEY,
                "observer_state":"OBSERVED_FRESH",
                "eligible_signal_captured":True,
            }),
            encoding="utf-8",
        )

        return {
            "eligible_capture_count":1,
            "broker_orders_submitted":0,
        }


class FakeEvidence:
    def __init__(self,root):
        self.root=Path(root)

    def capture(self):
        return {
            "status":
                "PASS_FRESH_ELIGIBLE_SIGNAL_EVIDENCE_CAPTURE",
            "new_evidence_rows":1,
            "latest_evidence":"fixture",
        }


class FakeProv:
    def __init__(self,root):
        pass

    def build(self):
        return {
            "status":
                "PASS_CANONICAL_REWARD_RISK_PROVENANCE_BRIDGE",
            "broker_orders_submitted":0,
        }


class FakeQual:
    def __init__(self,root):
        self.root=Path(root)

    def evaluate(self):
        p=(
            self.root
            /"runtime"
            /"sandbox_readiness_gate_v2_1_17"
        )
        p.mkdir(parents=True,exist_ok=True)

        latest={
            "evidence_key":FIXTURE_EVIDENCE_KEY,
            "ready":True,
            "qualification_status":
                "READY_FOR_MANUAL_SANDBOX_REVIEW",
            "canonical_paper_gate_semantics":
                "CORRECTED_V2_1_19_1",
        }

        (p/"latest_qualification.json").write_text(
            json.dumps(latest),
            encoding="utf-8",
        )

        return {
            "status":
                "PASS_EVIDENCE_QUALIFICATION_SANDBOX_READINESS",
            "ready_rows":1,
            "broker_orders_submitted":0,
        }


def observer_factory(recording,root,policy,now):
    return FakeObserver(recording,root)


class T(unittest.TestCase):
    def test_sunday_waits_without_runtime(self):
        called={"runtime":0}

        def rf(symbols):
            called["runtime"]+=1
            return FakeRuntime()

        with tempfile.TemporaryDirectory() as td:
            v=ActualIntradayCanonicalEndToEndValidatorV2121(
                td,
                now_fn=lambda:datetime(
                    2026,8,9,17,0,
                    tzinfo=timezone.utc,
                ),
                runtime_factory=rf,
            )
            r=v.run_once()

            self.assertEqual(
                r["status"],
                "WAITING_FOR_MARKET_SESSION",
            )
            self.assertEqual(called["runtime"],0)
            self.assertEqual(
                r["broker_orders_submitted"],
                0,
            )

    def test_intraday_ready_path_current_evidence_binding(self):
        with tempfile.TemporaryDirectory() as td:
            v=ActualIntradayCanonicalEndToEndValidatorV2121(
                td,
                now_fn=lambda:datetime(
                    2026,8,10,14,0,
                    tzinfo=timezone.utc,
                ),
                runtime_factory=lambda s:FakeRuntime(),
                observer_factory=observer_factory,
                evidence_factory=FakeEvidence,
                canonical_snapshot_fn=lambda r:{
                    "status":"PASS",
                    "generated_at_utc":"fixture",
                    "thresholds":{
                        "min_confidence":0.75,
                        "min_reward_risk":1.0,
                    },
                    "analyses":[{}],
                },
                provenance_factory=FakeProv,
                qualification_factory=FakeQual,
            )

            r=v.run_once()

            self.assertEqual(
                r["status"],
                "PASS_ACTUAL_INTRADAY_CANONICAL_READY",
            )
            self.assertTrue(
                r["ready_for_manual_sandbox_review"]
            )
            self.assertEqual(
                r["latest_qualification"]["evidence_key"],
                FIXTURE_EVIDENCE_KEY,
            )
            self.assertEqual(
                r["broker_orders_submitted"],
                0,
            )
            self.assertFalse(
                r["automatic_sandbox_execution_allowed"]
            )

    def test_status_locks(self):
        s=build_v2_1_21_status()

        self.assertEqual(
            s["canonical_min_confidence"],
            "0.75",
        )
        self.assertEqual(
            s["canonical_min_reward_risk"],
            "1.0",
        )
        self.assertFalse(
            s["etrade_oauth_from_stage"]
        )
        self.assertFalse(
            s["broker_order_submission_from_stage"]
        )
        self.assertFalse(
            s["production_order_post_allowed"]
        )
        self.assertFalse(
            s["live_trading_enabled"]
        )


if __name__=="__main__":
    unittest.main()
