from __future__ import annotations
from pathlib import Path

from .health import aggregate_health
from .ledger import GlobalLedger
from .models import CycleResult, ModuleHealth
from .scheduler import scheduler_state
from .store import CheckpointStore


DEPENDENCY_ORDER = (
    "MARKET_DATA",
    "AI_BRAIN",
    "MULTI_AI_VOTING",
    "RISK_ENGINE",
    "PORTFOLIO_AI",
    "BROKER_ADAPTER",
    "SELF_LEARNING",
    "LEDGER",
)


class AutonomousOperationsOrchestrator:
    def __init__(
        self,
        *,
        checkpoint_path: Path,
        ledger_path: Path,
    ) -> None:
        self.store = CheckpointStore(
            checkpoint_path
        )
        self.ledger = GlobalLedger(
            ledger_path
        )
        self.state = self.store.load()

    def restore(self) -> dict:
        self.state = self.store.load()
        self.ledger.append({
            "event": "RESTORE",
            "state": self.state,
        })
        return dict(self.state)

    def run_cycle(
        self,
        *,
        module_health: list[ModuleHealth],
        market_open: bool,
        requested_action: str,
    ) -> dict:
        health = aggregate_health(
            module_health
        )
        health_by_name = {
            item.name: item
            for item in module_health
        }

        sequence = int(
            self.state.get(
                "cycle_sequence",
                0,
            )
        ) + 1
        cycle_id = f"AUTO_CYCLE_{sequence:06d}"

        if not market_open:
            result = CycleResult(
                cycle_id=cycle_id,
                status="WAITING",
                final_action="WAIT",
                completed_modules=(),
                blocked_module="MARKET_OPEN_CHECK",
                emergency_stop=False,
                reason="MARKET_CLOSED",
            )
            self._persist(
                result,
                sequence,
            )
            return {
                "cycle_result": result.to_dict(),
                "health": health,
                "scheduler": scheduler_state(
                    market_open=False,
                    current_stage="MARKET_OPEN_CHECK",
                    emergency_stop=False,
                ),
            }

        if health["emergency_stop_required"]:
            result = CycleResult(
                cycle_id=cycle_id,
                status="EMERGENCY_STOP",
                final_action="ALL_STOP",
                completed_modules=(),
                blocked_module=(
                    health["critical_modules"][0]
                    if health["critical_modules"]
                    else "UNKNOWN"
                ),
                emergency_stop=True,
                reason="CRITICAL_MODULE_HEALTH",
            )
            self._persist(
                result,
                sequence,
            )
            return {
                "cycle_result": result.to_dict(),
                "health": health,
                "scheduler": scheduler_state(
                    market_open=True,
                    current_stage=result.blocked_module or "UNKNOWN",
                    emergency_stop=True,
                ),
            }

        completed = []
        blocked_module = None
        reason = "CYCLE_COMPLETE"

        for module_name in DEPENDENCY_ORDER:
            item = health_by_name.get(module_name)
            if item is None:
                blocked_module = module_name
                reason = "MISSING_DEPENDENCY_HEALTH"
                break
            if item.status.upper() in {"UNHEALTHY", "CRITICAL"}:
                blocked_module = module_name
                reason = "DEPENDENCY_HEALTH_BLOCK"
                break
            completed.append(module_name)

        if blocked_module:
            final_action = "WAIT"
            status = "BLOCKED"
        else:
            final_action = (
                requested_action.upper()
                if requested_action.upper()
                in {"BUY", "SELL", "WAIT"}
                else "WAIT"
            )
            status = "PASS"

        result = CycleResult(
            cycle_id=cycle_id,
            status=status,
            final_action=final_action,
            completed_modules=tuple(completed),
            blocked_module=blocked_module,
            emergency_stop=False,
            reason=reason,
        )
        self._persist(
            result,
            sequence,
        )

        current_stage = (
            completed[-1]
            if completed
            else "MARKET_DATA"
        )
        return {
            "cycle_result": result.to_dict(),
            "health": health,
            "scheduler": scheduler_state(
                market_open=True,
                current_stage=current_stage,
                emergency_stop=False,
            ),
        }

    def _persist(
        self,
        result: CycleResult,
        sequence: int,
    ) -> None:
        self.state = {
            "cycle_sequence": sequence,
            "last_cycle_id": result.cycle_id,
            "last_status": result.status,
            "last_action": result.final_action,
            "emergency_stop": result.emergency_stop,
        }
        self.store.save(
            self.state
        )
        self.ledger.append({
            "event": "AUTONOMOUS_CYCLE",
            "state": self.state,
            "result": result.to_dict(),
        })
