from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal

from .persistent_market_observer_v2_1_13 import (
    ObservationPolicyV2113,
    canonical_plan_snapshot,
    snapshot_fingerprint,
)
from .market_session_freshness_guard_v2_1_14 import (
    regular_session_window,
)


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class FreshnessGuardedPersistentObserverV2115:
    """
    Integrates V2.1.13 observation behavior with V2.1.14
    session/freshness protection.

    Key optimization:
    outside the regular clock window, the guarded runtime is NOT called,
    therefore no Alpaca REST bootstrap request is made by this observer.

    This stage never starts E*TRADE OAuth and never submits orders.
    """

    def __init__(
        self,
        guarded_runtime,
        root,
        policy=None,
        sleep_fn=time.sleep,
        now_fn=None,
    ):
        self.guarded_runtime=guarded_runtime
        self.root=Path(root)
        self.policy=(policy or ObservationPolicyV2113()).validate()
        self.sleep_fn=sleep_fn
        self.now_fn=now_fn or (lambda: datetime.now(timezone.utc))

        self.runtime_dir=(
            self.root
            /"runtime"
            /"freshness_guarded_persistent_observer_v2_1_15"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)

        self.ledger_path=self.runtime_dir/"observation_ledger.jsonl"
        self.latest_path=self.runtime_dir/"latest_snapshot.json"

    def _append(self,row):
        with self.ledger_path.open("a",encoding="utf-8") as f:
            f.write(
                json.dumps(
                    row,
                    sort_keys=True,
                    ensure_ascii=False,
                )+"\n"
            )
        self.latest_path.write_text(
            json.dumps(
                row,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def _waiting_row(self,index,now_utc,session):
        snapshot={
            "observer_state":"WAITING_SESSION",
            "session_status":session["status"],
            "inside_regular_clock_window":False,
            "market_data_fetch_skipped":True,
            "freshness_status":"NOT_EVALUATED",
            "signal_capture_allowed":False,
            "eligible_signal_count":0,
            "eligible_signals":[],
            "hold_only":True,
            "sandbox_only":True,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }
        fingerprint=snapshot_fingerprint(snapshot)
        return {
            "stage":
                "BROKER_INTEGRATION_V2_1_15_FRESHNESS_GUARDED_PERSISTENT_OBSERVER",
            "observed_at_utc":now_utc.isoformat(),
            "iteration":index,
            "observer_state":"WAITING_SESSION",
            "session":session,
            "market_data_runtime_called":False,
            "market_data_fetch_skipped":True,
            "snapshot_fingerprint":fingerprint,
            "snapshot":snapshot,
            "eligible_signal_captured":False,
            "etrade_oauth_started":False,
            "sandbox_preview_sent":False,
            "sandbox_place_sent":False,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }

    def _runtime_row(self,index,now_utc,plan):
        gate=plan.get("session_freshness_gate") or {}
        freshness=gate.get("freshness") or {}
        allowed=bool(
            plan.get("signal_capture_allowed_by_v2_1_14")
        )

        if allowed:
            state="OBSERVED_FRESH"
        else:
            state="STALE_BLOCK"

        snapshot=canonical_plan_snapshot(plan)
        snapshot.update({
            "observer_state":state,
            "session_status":(
                (gate.get("session") or {}).get("status")
            ),
            "freshness_status":gate.get("status"),
            "all_fresh":bool(freshness.get("all_fresh")),
            "signal_capture_allowed":allowed,
            "market_data_fetch_skipped":False,
        })

        fingerprint=snapshot_fingerprint(snapshot)

        return {
            "stage":
                "BROKER_INTEGRATION_V2_1_15_FRESHNESS_GUARDED_PERSISTENT_OBSERVER",
            "observed_at_utc":now_utc.isoformat(),
            "iteration":index,
            "observer_state":state,
            "session_freshness_gate":gate,
            "market_data_runtime_called":True,
            "market_data_fetch_skipped":False,
            "snapshot_fingerprint":fingerprint,
            "snapshot":snapshot,
            "eligible_signal_captured":(
                allowed
                and int(snapshot.get("eligible_signal_count",0))>0
            ),
            "etrade_oauth_started":False,
            "sandbox_preview_sent":False,
            "sandbox_place_sent":False,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }

    def run(self,quantity=Decimal("1")):
        previous_fingerprint=None
        unchanged_streak=0
        observations=0
        waiting_count=0
        stale_block_count=0
        fresh_observation_count=0
        eligible_capture_count=0
        runtime_call_count=0
        skipped_market_data_count=0
        changed_observation_count=0
        stop_reason="MAX_ITERATIONS"

        for index in range(1,self.policy.max_iterations+1):
            now_utc=self.now_fn()
            if now_utc.tzinfo is None:
                raise ValueError("now_fn must return timezone-aware datetime")
            now_utc=now_utc.astimezone(timezone.utc)

            session=regular_session_window(now_utc)

            if not session["inside_regular_clock_window"]:
                row=self._waiting_row(index,now_utc,session)
                waiting_count+=1
                skipped_market_data_count+=1
            else:
                plan=self.guarded_runtime.build_runtime_plan(
                    quantity=Decimal(str(quantity)),
                    now_utc=now_utc,
                )
                row=self._runtime_row(index,now_utc,plan)
                runtime_call_count+=1

                if row["observer_state"]=="STALE_BLOCK":
                    stale_block_count+=1
                else:
                    fresh_observation_count+=1

                if row["eligible_signal_captured"]:
                    eligible_capture_count+=1

            fingerprint=row["snapshot_fingerprint"]
            changed=(
                previous_fingerprint is None
                or fingerprint != previous_fingerprint
            )

            if changed:
                unchanged_streak=0
                changed_observation_count+=1
            else:
                unchanged_streak+=1

            row["changed_since_previous"]=changed
            row["unchanged_streak"]=unchanged_streak
            self._append(row)
            observations+=1

            print(
                f"OBSERVATION {index}/{self.policy.max_iterations} | "
                f"state={row['observer_state']} | "
                f"eligible={int(row['eligible_signal_captured'])} | "
                f"runtime_called={row['market_data_runtime_called']} | "
                f"changed={changed} | "
                f"unchanged_streak={unchanged_streak}"
            )

            if unchanged_streak >= self.policy.stop_after_unchanged:
                stop_reason="UNCHANGED_LIMIT"
                break

            previous_fingerprint=fingerprint

            if index < self.policy.max_iterations:
                self.sleep_fn(self.policy.interval_seconds)

        return {
            "status":"PASS_FRESHNESS_GUARDED_PERSISTENT_OBSERVATION",
            "observation_count":observations,
            "changed_observation_count":changed_observation_count,
            "waiting_session_count":waiting_count,
            "stale_block_count":stale_block_count,
            "fresh_observation_count":fresh_observation_count,
            "eligible_capture_count":eligible_capture_count,
            "market_data_runtime_call_count":runtime_call_count,
            "market_data_fetch_skipped_count":skipped_market_data_count,
            "stopped_reason":stop_reason,
            "ledger_path":str(self.ledger_path),
            "latest_snapshot_path":str(self.latest_path),
            "etrade_oauth_started":False,
            "sandbox_preview_sent":False,
            "sandbox_place_sent":False,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
            "profitability_validated":False,
        }
