from __future__ import annotations
from dataclasses import dataclass, replace
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from broker.broker_state_checkpoint_v77_5 import BrokerStateCheckpoint, BrokerStateCheckpointManager
from broker.contracts_v77_1 import BrokerOrderRequest, OrderSide, OrderType, TimeInForce
from broker.execution_event_reconciliation_v77_4 import ExecutionEventReconciler
from broker.order_lifecycle_simulator_v77_3 import SandboxFill
from broker.restart_recovery_replay_v77_6 import RestartRecoveryReplay

class FailureInjectionError(ValueError):
    pass

@dataclass(frozen=True)
class FailureInjectionReport:
    status: str
    checks: MappingProxyType
    blocked_failure_count: int
    detected_corruption_count: int
    recovered_state_sha256: str
    source_state_sha256: str
    def as_dict(self)->dict[str,Any]:
        return {"status":self.status,"checks":dict(self.checks),
        "blocked_failure_count":self.blocked_failure_count,
        "detected_corruption_count":self.detected_corruption_count,
        "recovered_state_sha256":self.recovered_state_sha256,
        "source_state_sha256":self.source_state_sha256}

class FailureInjectionRecovery:
    def __init__(self, manager=None, recovery=None, reconciler=None):
        self.manager=manager or BrokerStateCheckpointManager()
        self.recovery=recovery or RestartRecoveryReplay(checkpoint_manager=self.manager)
        self.reconciler=reconciler or ExecutionEventReconciler()

    def run(self, checkpoint: BrokerStateCheckpoint):
        checks={}
        blocked=0
        sim=self.recovery.restore(checkpoint)
        order_id=str(checkpoint.orders[0]["broker_order_id"])

        for name, fn in (
            ("zero_fill_quantity_blocked",lambda:sim.apply_fill(order_id,quantity=Decimal("0"),price=Decimal("1"))),
            ("overfill_blocked",lambda:sim.apply_fill(order_id,quantity=Decimal("999999"),price=Decimal("1"))),
            ("unknown_order_blocked",lambda:sim.apply_fill("UNKNOWN",quantity=Decimal("1"),price=Decimal("1"))),
        ):
            try: fn(); checks[name]=False
            except Exception: checks[name]=True; blocked+=1

        def corrupted(mutator):
            s=self.recovery.restore(checkpoint); mutator(s)
            return not self.reconciler.reconcile(s).passed

        checks["cash_corruption_detected"]=corrupted(
            lambda s:setattr(s,"_cash",s._cash+Decimal("1")))
        checks["position_corruption_detected"]=corrupted(
            lambda s:setattr(next(iter(s._positions.values())),"quantity",
                             next(iter(s._positions.values())).quantity+Decimal("1")))
        def corrupt_event_sequence(s):
            s._events[-1] = replace(s._events[-1], sequence=999999)
        checks["event_sequence_corruption_detected"]=corrupted(
            corrupt_event_sequence)
        def duplicate_fill(s):
            last=s._fills[-1]
            s._fills.append(SandboxFill(last.fill_id,last.broker_order_id,last.quantity,
                last.price,last.cumulative_quantity,last.cumulative_average_price,last.occurred_at_utc))
        checks["duplicate_fill_id_detected"]=corrupted(duplicate_fill)
        detected=sum(bool(checks[k]) for k in (
            "cash_corruption_detected","position_corruption_detected",
            "event_sequence_corruption_detected","duplicate_fill_id_detected"))

        damaged=replace(checkpoint,cash=str(Decimal(checkpoint.cash)+Decimal("1")))
        checks["damaged_checkpoint_rejected"]=not self.manager.verify(damaged)
        try:
            self.recovery.restore(damaged); checks["damaged_restore_blocked"]=False
        except Exception:
            checks["damaged_restore_blocked"]=True; blocked+=1

        recovered=self.recovery.restore(checkpoint)
        replay=self.recovery.verify_replay(checkpoint,recovered)
        checks["last_good_checkpoint_recovered"]=replay["status"]=="PASS"
        checks["recovered_hash_matches_source"]=(
            replay["replayed_state_sha256"]==checkpoint.state_sha256)
        checks["recovered_reconciliation_pass"]=self.reconciler.reconcile(recovered).passed
        checks["network_unused"]=recovered.health().network_used is False
        checks["broker_disconnected"]=recovered.health().connected is False
        checks["actual_orders_zero"]=recovered.actual_orders_submitted==0

        status="PASS" if all(checks.values()) else "FAIL"
        report=FailureInjectionReport(status,MappingProxyType(checks),blocked,detected,
            replay["replayed_state_sha256"],checkpoint.state_sha256)
        if status!="PASS":
            raise FailureInjectionError(", ".join(k for k,v in checks.items() if not v))
        return recovered,report
