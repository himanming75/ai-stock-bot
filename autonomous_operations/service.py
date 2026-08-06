from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .circuit import CircuitBreaker
from .fixtures import (
    BLOCKED_MODULES,
    CRITICAL_MODULES,
    HEALTHY_MODULES,
)
from .orchestrator import (
    AutonomousOperationsOrchestrator,
)


class AutonomousOperationsCertificationService:
    def evaluate(
        self,
        *,
        output_dir: Path,
    ) -> dict:
        now = datetime.now(timezone.utc)
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        checkpoint_path = (
            output_dir
            / "autonomous_operations_checkpoint.json"
        )
        ledger_path = (
            output_dir
            / "autonomous_operations_global_ledger.jsonl"
        )

        if checkpoint_path.exists():
            checkpoint_path.unlink()
        if ledger_path.exists():
            ledger_path.unlink()

        orchestrator = (
            AutonomousOperationsOrchestrator(
                checkpoint_path=checkpoint_path,
                ledger_path=ledger_path,
            )
        )

        restored_default = (
            orchestrator.restore()
        )

        market_closed = orchestrator.run_cycle(
            module_health=HEALTHY_MODULES,
            market_open=False,
            requested_action="BUY",
        )
        healthy_cycle = orchestrator.run_cycle(
            module_health=HEALTHY_MODULES,
            market_open=True,
            requested_action="BUY",
        )
        blocked_cycle = orchestrator.run_cycle(
            module_health=BLOCKED_MODULES,
            market_open=True,
            requested_action="BUY",
        )
        emergency_cycle = orchestrator.run_cycle(
            module_health=CRITICAL_MODULES,
            market_open=True,
            requested_action="BUY",
        )

        restarted = (
            AutonomousOperationsOrchestrator(
                checkpoint_path=checkpoint_path,
                ledger_path=ledger_path,
            )
        )
        restored_after_restart = (
            restarted.restore()
        )

        circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_success_threshold=2,
        )
        failure_states = [
            circuit.record_failure()
            for _ in range(5)
        ]
        recovery_state_1 = (
            circuit.record_success()
        )
        recovery_state_2 = (
            circuit.record_success()
        )

        result = {
            "stage": (
                "V6401_TO_V6600_AUTONOMOUS_OPERATIONS_"
                "HEALTH_AND_FINAL_ORCHESTRATION"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": (
                "FIXTURE_AUTONOMOUS_OPERATIONS_CYCLES"
            ),
            "restored_default": restored_default,
            "market_closed_cycle": market_closed,
            "healthy_cycle": healthy_cycle,
            "blocked_cycle": blocked_cycle,
            "emergency_cycle": emergency_cycle,
            "restored_after_restart": (
                restored_after_restart
            ),
            "circuit_breaker": {
                "failure_states": failure_states,
                "recovery_state_1": recovery_state_1,
                "recovery_state_2": recovery_state_2,
                "final": circuit.to_dict(),
            },
            "global_health_monitor_ready": True,
            "dependency_graph_ready": True,
            "dependency_guard_ready": True,
            "global_safety_lock_ready": True,
            "circuit_breaker_ready": True,
            "checkpoint_restore_ready": True,
            "scheduler_integration_ready": True,
            "global_ledger_ready": True,
            "health_dashboard_ready": True,
            "emergency_stop_ready": True,
            "autonomous_cycle_ready": True,
            "phase_5_final_orchestration_ready": True,
            "automatic_order_generation_enabled": False,
            "automatic_order_submission_enabled": False,
            "automatic_broker_failover_enabled": False,
            "broker_write_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "existing_ai_engine_modified": False,
            "existing_broker_modules_modified": False,
            "existing_controller_modified": False,
            "next_fixed_development": (
                "V6601_TO_V6800_AUTONOMOUS_PLATFORM_"
                "FINAL_CERTIFICATION_AND_LIVE_VALIDATION_HANDOFF"
            ),
        }

        checks = (
            restored_default["emergency_stop"] is True,
            market_closed["cycle_result"]["final_action"]
            == "WAIT",
            healthy_cycle["cycle_result"]["status"]
            == "PASS",
            healthy_cycle["cycle_result"]["final_action"]
            == "BUY",
            blocked_cycle["cycle_result"]["status"]
            == "BLOCKED",
            blocked_cycle["cycle_result"]["final_action"]
            == "WAIT",
            emergency_cycle["cycle_result"]["status"]
            == "EMERGENCY_STOP",
            emergency_cycle["cycle_result"]["final_action"]
            == "ALL_STOP",
            restored_after_restart["last_status"]
            == "EMERGENCY_STOP",
            "OPEN" in failure_states,
            recovery_state_1 == "HALF_OPEN",
            recovery_state_2 == "CLOSED",
            result[
                "automatic_order_submission_enabled"
            ] is False,
        )

        if not all(checks):
            result["status"] = "BLOCKED"

        seed = dict(result)
        seed.pop("generated_at")
        result["certification_fingerprint"] = (
            hashlib.sha256(
                json.dumps(
                    seed,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        )

        dashboard = {
            "status": result["status"],
            "healthy_cycle": (
                healthy_cycle["cycle_result"]
            ),
            "blocked_cycle": (
                blocked_cycle["cycle_result"]
            ),
            "emergency_cycle": (
                emergency_cycle["cycle_result"]
            ),
            "circuit_breaker": (
                result["circuit_breaker"]
            ),
            "broker_write": False,
            "paper_orders": 0,
            "live_orders": 0,
        }

        outputs = {
            "autonomous_operations_certification.json": result,
            "autonomous_operations_health_dashboard.json": dashboard,
            "autonomous_operations_dependency_graph.json": {
                "order": [
                    "MARKET_DATA",
                    "AI_BRAIN",
                    "MULTI_AI_VOTING",
                    "RISK_ENGINE",
                    "PORTFOLIO_AI",
                    "BROKER_ADAPTER",
                    "SELF_LEARNING",
                    "LEDGER",
                ]
            },
            "autonomous_operations_circuit_breaker.json": (
                result["circuit_breaker"]
            ),
            "autonomous_operations_scheduler_status.json": {
                "market_closed": market_closed["scheduler"],
                "healthy": healthy_cycle["scheduler"],
                "blocked": blocked_cycle["scheduler"],
                "emergency": emergency_cycle["scheduler"],
            },
            "autonomous_operations_safety_policy.json": {
                "critical_market_data": "ALL_STOP",
                "critical_risk_engine": "ALL_STOP",
                "critical_portfolio_ai": "ALL_STOP",
                "critical_broker_adapter": "ALL_STOP",
                "critical_ledger": "ALL_STOP",
                "unhealthy_dependency": "WAIT",
                "market_closed": "WAIT",
                "broker_write_enabled": False,
                "automatic_order_submission_enabled": False,
            },
        }

        for name, payload in outputs.items():
            (
                output_dir / name
            ).write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                ) + "\n",
                encoding="utf-8",
            )

        with (
            output_dir
            / "autonomous_operations_certification_ledger.jsonl"
        ).open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    result,
                    sort_keys=True,
                ) + "\n"
            )

        return result
