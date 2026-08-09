from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import time


@dataclass(frozen=True)
class BoundedCyclePolicy:
    max_cycles: int = 3
    cooldown_seconds: int = 30
    stop_on_error: bool = True
    duplicate_signal_guard: bool = True

    def validate(self):
        if not (1 <= int(self.max_cycles) <= 3):
            raise ValueError("V2.1.4 max_cycles must be between 1 and 3.")
        if int(self.cooldown_seconds) < 0:
            raise ValueError("cooldown_seconds cannot be negative.")
        if int(self.cooldown_seconds) > 300:
            raise ValueError("cooldown_seconds cannot exceed 300 seconds.")
        return self


def signal_key(signal):
    return (
        str(signal.symbol).upper(),
        str(signal.side).upper(),
        str(signal.quantity),
        str(signal.order_type).upper(),
        str(signal.strategy_id),
    )


class ETradeSandboxBoundedMultiCycleController:
    def __init__(self, cycle_engine, root, policy=None, sleep_fn=time.sleep):
        self.cycle_engine=cycle_engine
        self.root=Path(root)
        self.policy=(policy or BoundedCyclePolicy()).validate()
        self.sleep_fn=sleep_fn
        self.kill_switch_path=(
            self.root/
            "runtime"/
            "etrade_sandbox_multi_cycle_v2_1_4"/
            "KILL_SWITCH"
        )

    def kill_switch_active(self):
        return self.kill_switch_path.exists()

    def _client_order_id(self,index):
        stamp=datetime.now(timezone.utc).strftime("%H%M%S")
        return f"A14{stamp}{index:02d}"[:20]

    def run(self, account_id_key, signals):
        signals=list(signals)
        started=datetime.now(timezone.utc).isoformat()
        results=[]
        seen=set()
        blocked_duplicates=0
        stopped_reason=None

        for index,signal in enumerate(signals,1):
            if len(results) >= self.policy.max_cycles:
                stopped_reason="MAX_CYCLES_REACHED"
                break

            if self.kill_switch_active():
                stopped_reason="KILL_SWITCH_ACTIVE"
                break

            key=signal_key(signal)
            if self.policy.duplicate_signal_guard and key in seen:
                blocked_duplicates+=1
                continue
            seen.add(key)

            try:
                result=self.cycle_engine.run_once(
                    account_id_key,
                    signal,
                    self._client_order_id(index),
                )
                results.append(result)
            except Exception as exc:
                results.append({
                    "status":"CYCLE_ERROR",
                    "error_type":type(exc).__name__,
                    "real_money_moved":False,
                    "production_order_submission":False,
                })
                stopped_reason="CYCLE_ERROR"
                if self.policy.stop_on_error:
                    break

            if (
                len(results) < self.policy.max_cycles
                and index < len(signals)
                and self.policy.cooldown_seconds > 0
            ):
                self.sleep_fn(self.policy.cooldown_seconds)

        if stopped_reason is None:
            if len(results) >= self.policy.max_cycles:
                stopped_reason="MAX_CYCLES_REACHED"
            else:
                stopped_reason="SIGNAL_QUEUE_EXHAUSTED"

        pass_count=sum(
            1 for r in results
            if r.get("status")=="PASS_SANDBOX_AUTONOMOUS_CYCLE"
        )

        return {
            "stage":"BROKER_INTEGRATION_V2_1_4_BOUNDED_MULTI_CYCLE_CONTROLLER",
            "status":"PASS_BOUNDED_MULTI_CYCLE_CONTROLLER",
            "started_at_utc":started,
            "completed_at_utc":datetime.now(timezone.utc).isoformat(),
            "policy":{
                "max_cycles":self.policy.max_cycles,
                "cooldown_seconds":self.policy.cooldown_seconds,
                "stop_on_error":self.policy.stop_on_error,
                "duplicate_signal_guard":self.policy.duplicate_signal_guard,
            },
            "submitted_cycle_count":len(results),
            "successful_cycle_count":pass_count,
            "duplicate_signal_block_count":blocked_duplicates,
            "stopped_reason":stopped_reason,
            "kill_switch_active":self.kill_switch_active(),
            "cycles":results,
            "sandbox_only":True,
            "real_money_moved":False,
            "production_order_submission":False,
            "live_trading":False,
        }
