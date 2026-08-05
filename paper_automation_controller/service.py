from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .checkpoint import CheckpointStore
from .lock import InstanceLock
from .models import AutomationProfile


class PaperAutomationController:
    def __init__(self, root: Path, clock_provider=None) -> None:
        self.root = root
        self.clock_provider = clock_provider

    def _load_profile(self, path: Path) -> AutomationProfile:
        return AutomationProfile.from_mapping(
            json.loads(path.read_text(encoding="utf-8-sig"))
        )

    def _clock(self) -> dict:
        if self.clock_provider is not None:
            return self.clock_provider()
        from actual_market_polling.service import ReadOnlyAlpaca
        return ReadOnlyAlpaca().clock()

    def _run_market_pipeline(self, symbols: list[str], cycle_number: int) -> dict:
        from actual_market_polling.service import ActualMarketPollingValidationService
        service = ActualMarketPollingValidationService(self.root)
        return service.run_cycle(symbols, cycle_number)

    def _run_execution_pipeline(self) -> dict:
        from ai_execution_plan_bridge.service import ExecutionPlanBridgeService
        from order_ticket_generator.service import OrderTicketGeneratorService

        bridge_path = (
            self.root
            / "release/ai_decision_strategy_risk_portfolio_bridge/actual/bridge_snapshot.json"
        )
        execution_config = (
            self.root
            / "release/ai_execution_plan_bridge/config/execution_bridge_config.json"
        )
        execution_output = (
            self.root
            / "release/paper_automation_controller/actual/execution_plan_snapshot.json"
        )
        execution = ExecutionPlanBridgeService().run_file(
            bridge_path, execution_config, execution_output
        )

        ticket_policy = (
            self.root
            / "release/order_ticket_generator/config/ticket_policy.json"
        )
        ticket_output = (
            self.root
            / "release/paper_automation_controller/actual/order_ticket_snapshot.json"
        )
        tickets = OrderTicketGeneratorService().run_file(
            execution_output, ticket_policy, ticket_output
        )
        return {
            "execution_status": execution.get("status"),
            "ready_symbols": execution.get("ready_symbols", []),
            "ticket_status": tickets.get("status"),
            "ready_ticket_count": tickets.get("ready_ticket_count", 0),
        }

    def run(self, profile_path: Path) -> dict:
        profile = self._load_profile(profile_path)
        if profile.enable_actual_submission:
            raise RuntimeError(
                "ACTUAL_SUBMISSION_DISABLED_IN_CONTROLLER_V1:"
                "USE_SEPARATE_APPROVAL_TOKEN_WORKFLOW"
            )

        actual_dir = self.root / "release/paper_automation_controller/actual"
        actual_dir.mkdir(parents=True, exist_ok=True)
        lock_path = actual_dir / "controller.lock"
        checkpoint = CheckpointStore(actual_dir / "checkpoint.json")
        previous = checkpoint.load()
        start_cycle = int(previous.get("last_completed_cycle", 0)) + 1
        cycle_ledger = actual_dir / "controller_cycle_ledger.jsonl"
        cycles = []
        stopped_reason = None

        with InstanceLock(lock_path):
            for cycle_number in range(start_cycle, start_cycle + profile.max_cycles):
                clock = self._clock()
                market_open = bool(clock.get("is_open", False))

                if profile.stop_when_market_closed and not market_open:
                    stopped_reason = "MARKET_CLOSED"
                    break

                started_at = datetime.now(timezone.utc).isoformat()
                canonical = f"{profile.name}|{cycle_number}|{started_at}"
                cycle_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

                market_result = None
                execution_result = None
                errors = []

                try:
                    if profile.enable_market_pipeline:
                        market_result = self._run_market_pipeline(
                            list(profile.symbols), cycle_number
                        )
                except Exception as exc:
                    errors.append(f"MARKET_PIPELINE:{type(exc).__name__}:{exc}")

                try:
                    if (
                        profile.enable_execution_planning
                        and profile.enable_order_ticket_generation
                        and market_result is not None
                    ):
                        execution_result = self._run_execution_pipeline()
                except Exception as exc:
                    errors.append(f"EXECUTION_PIPELINE:{type(exc).__name__}:{exc}")

                cycle = {
                    "cycle_number": cycle_number,
                    "cycle_id": cycle_id,
                    "profile": profile.name,
                    "started_at": started_at,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "market_is_open": market_open,
                    "market_result": market_result,
                    "execution_result": execution_result,
                    "errors": errors,
                    "actual_external_network_used": bool(profile.enable_market_pipeline),
                    "actual_broker_read_performed": bool(profile.enable_market_pipeline),
                    "actual_broker_write_performed": False,
                    "actual_order_submission_performed": False,
                    "actual_paper_orders_submitted": 0,
                    "actual_live_orders_submitted": 0,
                }
                cycles.append(cycle)
                with cycle_ledger.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(cycle, sort_keys=True) + "\n")

                checkpoint.save(
                    cycle_number=cycle_number,
                    cycle_id=cycle_id,
                    state="ERROR" if errors else "COMPLETED",
                    summary=cycle,
                )

                print(json.dumps(cycle, indent=2, sort_keys=True), flush=True)

                if errors:
                    stopped_reason = "CYCLE_ERROR"
                    break
                if len(cycles) < profile.max_cycles:
                    time.sleep(profile.interval_seconds)

        summary = {
            "stage": "PAPER_AUTOMATION_CONTROLLER_AND_SCHEDULER",
            "status": "PASS" if cycles and not any(x["errors"] for x in cycles) else (
                "IDLE" if stopped_reason == "MARKET_CLOSED" else "BLOCKED"
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "profile": profile.as_json(),
            "resumed_from_cycle": start_cycle,
            "completed_cycles": len(cycles),
            "stopped_reason": stopped_reason,
            "last_cycle": cycles[-1] if cycles else None,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "submission_mode": "SEPARATE_APPROVAL_TOKEN_ONLY",
            "next_fixed_development": "AUTOMATION_WATCHDOG_RESTART_RECOVERY",
            "next_market_validation": "FULL_SESSION_READ_ONLY_AUTOMATION_RUN",
        }
        (actual_dir / "controller_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return summary
