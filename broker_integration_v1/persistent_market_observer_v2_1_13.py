from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal

from .canonically_aligned_end_to_end_runtime_v2_1_12 import (
    CanonicallyAlignedEndToEndRuntimeV2112,
)


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _signal_to_dict(sig):
    return {
        "symbol":sig.symbol,
        "side":sig.side,
        "quantity":str(sig.quantity),
        "strategy_id":sig.strategy_id,
        "source_confidence":str(
            getattr(sig,"source_confidence","")
        ),
    }


def canonical_plan_snapshot(plan):
    signals=[
        _signal_to_dict(sig)
        for sig in plan.get("eligible_signals",[])
    ]
    signals.sort(
        key=lambda x:(
            x["symbol"],
            x["side"],
            x["strategy_id"],
        )
    )

    return {
        "bootstrap_status":plan.get("bootstrap_status"),
        "bootstrap_counts":plan.get("bootstrap_counts"),
        "canonical_gate_aligned":
            bool(plan.get("canonical_gate_aligned")),
        "eligible_signal_count":
            int(plan.get("eligible_signal_count",0)),
        "eligible_signals":signals,
        "hold_only":bool(plan.get("hold_only")),
        "sandbox_only":True,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }


def snapshot_fingerprint(snapshot):
    payload=json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",",":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class ObservationPolicyV2113:
    max_iterations:int=30
    interval_seconds:int=60
    stop_after_unchanged:int=10

    def validate(self):
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")
        if self.max_iterations > 500:
            raise ValueError("max_iterations must be <= 500")
        if self.interval_seconds < 1:
            raise ValueError("interval_seconds must be >= 1")
        if self.interval_seconds > 3600:
            raise ValueError("interval_seconds must be <= 3600")
        if self.stop_after_unchanged < 1:
            raise ValueError("stop_after_unchanged must be >= 1")
        return self


class PersistentMarketObserverV2113:
    """
    Repeatedly evaluates the existing V2.1.12 end-to-end plan and
    writes observation snapshots to JSONL.

    This stage NEVER starts E*TRADE OAuth and NEVER submits orders.
    """

    def __init__(
        self,
        runtime,
        root,
        policy=None,
        sleep_fn=time.sleep,
    ):
        self.runtime=runtime
        self.root=Path(root)
        self.policy=(policy or ObservationPolicyV2113()).validate()
        self.sleep_fn=sleep_fn

        self.runtime_dir=(
            self.root
            /"runtime"
            /"persistent_market_observer_v2_1_13"
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
                )
                +"\n"
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

    def run(self,quantity=Decimal("1")):
        previous_fingerprint=None
        unchanged_streak=0
        eligible_seen=0
        observations=0
        changed_observations=0
        stop_reason="MAX_ITERATIONS"

        for index in range(1,self.policy.max_iterations+1):
            plan=self.runtime.build_runtime_plan(
                quantity=Decimal(str(quantity))
            )

            snapshot=canonical_plan_snapshot(plan)
            fingerprint=snapshot_fingerprint(snapshot)

            changed=(
                previous_fingerprint is None
                or fingerprint != previous_fingerprint
            )

            if changed:
                unchanged_streak=0
                changed_observations+=1
            else:
                unchanged_streak+=1

            if snapshot["eligible_signal_count"] > 0:
                eligible_seen+=1

            row={
                "stage":
                    "BROKER_INTEGRATION_V2_1_13_PERSISTENT_MARKET_OBSERVER",
                "observed_at_utc":utc_now_iso(),
                "iteration":index,
                "changed_since_previous":changed,
                "unchanged_streak":unchanged_streak,
                "snapshot_fingerprint":fingerprint,
                "snapshot":snapshot,
                "eligible_signal_captured":
                    snapshot["eligible_signal_count"]>0,
                "etrade_oauth_started":False,
                "sandbox_preview_sent":False,
                "sandbox_place_sent":False,
                "broker_orders_submitted":0,
                "production_order_submission":False,
                "live_trading":False,
            }
            self._append(row)

            observations+=1

            print(
                f"OBSERVATION {index}/{self.policy.max_iterations} | "
                f"eligible={snapshot['eligible_signal_count']} | "
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
            "status":"PASS_PERSISTENT_MARKET_OBSERVATION",
            "observation_count":observations,
            "changed_observation_count":changed_observations,
            "eligible_observation_count":eligible_seen,
            "stopped_reason":stop_reason,
            "ledger_path":str(self.ledger_path),
            "latest_snapshot_path":str(self.latest_path),
            "etrade_oauth_started":False,
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
            "profitability_validated":False,
        }
