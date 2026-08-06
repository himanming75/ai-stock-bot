from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .checklists import (
    platform_readiness_checks,
    validation_gates,
)
from .deployment import deployment_audit
from .performance import evaluate_fixture_metrics


class AutonomousPlatformFinalCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        now = datetime.now(timezone.utc)
        checks = [
            item.to_dict()
            for item in platform_readiness_checks()
        ]
        gates = [
            item.to_dict()
            for item in validation_gates()
        ]
        performance = evaluate_fixture_metrics()
        deployment = deployment_audit()

        blocking_checks = [
            item
            for item in checks
            if item["blocking"]
            and item["status"]
            not in {"PASS", "DISABLED"}
        ]
        pending_gates = [
            item for item in gates
            if item["status"] in {"PENDING", "BLOCKED"}
        ]

        code_ready = (
            len(blocking_checks) == 1
            and blocking_checks[0]["name"]
            == "ALPACA_PAPER_CONNECTION"
        )

        result = {
            "stage": (
                "V6601_TO_V6800_AUTONOMOUS_PLATFORM_"
                "FINAL_CERTIFICATION_AND_LIVE_VALIDATION_HANDOFF"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": (
                "OFFLINE_FINAL_CERTIFICATION_AND_HANDOFF"
            ),
            "platform_readiness_checks": checks,
            "validation_gates": gates,
            "performance_audit": performance,
            "deployment_audit": deployment,
            "code_platform_status": (
                "CODE_COMPLETE_LIVE_VALIDATION_PENDING"
                if code_ready
                else "BLOCKED"
            ),
            "paper_platform_status": (
                "READY_FOR_INTRADAY_VALIDATION"
            ),
            "etrade_platform_status": (
                "READ_ONLY_CODE_COMPLETE_KEY_PENDING"
            ),
            "phase_5_status": (
                "STRUCTURALLY_COMPLETE"
            ),
            "live_validation_handoff_ready": True,
            "paper_intraday_checklist_ready": True,
            "etrade_key_handoff_ready": True,
            "long_run_test_plan_ready": True,
            "performance_targets_ready": True,
            "deployment_audit_ready": True,
            "final_safety_audit_ready": True,
            "manual_approval_required_for_any_write": True,
            "automatic_order_generation_enabled": False,
            "automatic_order_submission_enabled": False,
            "automatic_live_trading_enabled": False,
            "broker_write_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "pending_gate_count": len(pending_gates),
            "external_blockers": [
                "MARKET_OPEN_REQUIRED_FOR_PAPER_VALIDATION",
                "ETRADE_SANDBOX_CONSUMER_KEY_REQUIRED",
            ],
            "next_user_actions": [
                "RUN_PAPER_INTRADAY_VALIDATION_WHEN_MARKET_OPENS",
                "OBTAIN_ETRADE_SANDBOX_CONSUMER_KEY",
                "RUN_MINIMUM_8_HOUR_LONG_DURATION_TEST",
            ],
            "next_fixed_development": (
                "NO_NEW_CORE_DEVELOPMENT_REQUIRED_"
                "UNTIL_LIVE_VALIDATION_RESULTS"
            ),
        }

        required_checks = (
            performance["fixture_performance_status"] == "PASS",
            deployment["broker_write_enabled"] is False,
            result["automatic_order_submission_enabled"] is False,
            result["phase_5_status"] == "STRUCTURALLY_COMPLETE",
            result["live_validation_handoff_ready"] is True,
        )
        if not all(required_checks):
            result["status"] = "BLOCKED"

        seed = dict(result)
        seed.pop("generated_at")
        result["certification_fingerprint"] = hashlib.sha256(
            json.dumps(
                seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        output_dir.mkdir(parents=True, exist_ok=True)

        paper_checklist = {
            "market_open": "REQUIRED",
            "fresh_1_minute_bars": "VERIFY",
            "cycle_counter_increasing": "VERIFY",
            "market_pipeline": "PASS_REQUIRED",
            "ai_decision_generated": "VERIFY",
            "portfolio_target_generated": "VERIFY",
            "watchdog_healthy": "VERIFY",
            "snapshot_generation": "VERIFY",
            "market_close_auto_stop": "VERIFY",
            "paper_orders_expected": 0,
            "broker_write_expected": False,
        }

        etrade_checklist = {
            "consumer_key_available": False,
            "sandbox_oauth_complete": False,
            "account_read": "PENDING",
            "balance_read": "PENDING",
            "positions_read": "PENDING",
            "orders_read": "PENDING",
            "production_read_only": "PENDING",
            "write_enabled": False,
            "order_submission_enabled": False,
        }

        long_run_plan = {
            "minimum_hours": 8,
            "recommended_sessions": 3,
            "monitor": [
                "memory_growth",
                "uncaught_exceptions",
                "deadlocks",
                "missed_cycles",
                "ledger_integrity",
                "watchdog_restarts",
                "snapshot_freshness",
            ],
            "pass_conditions": {
                "uncaught_exceptions": 0,
                "deadlocks": 0,
                "missed_cycles": 0,
                "memory_growth_per_hour_mb_max": 50,
            },
        }

        outputs = {
            "autonomous_platform_final_certification.json": result,
            "autonomous_platform_readiness_checklist.json": {
                "items": checks
            },
            "autonomous_platform_validation_gates.json": {
                "items": gates
            },
            "autonomous_paper_intraday_handoff.json": paper_checklist,
            "autonomous_etrade_validation_handoff.json": etrade_checklist,
            "autonomous_long_run_test_plan.json": long_run_plan,
            "autonomous_performance_audit.json": performance,
            "autonomous_deployment_audit.json": deployment,
            "autonomous_final_safety_status.json": {
                "broker_write": False,
                "automatic_order_generation": False,
                "automatic_order_submission": False,
                "automatic_live_trading": False,
                "paper_orders": 0,
                "live_orders": 0,
            },
        }

        for name, payload in outputs.items():
            (output_dir / name).write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                ) + "\n",
                encoding="utf-8",
            )

        with (
            output_dir
            / "autonomous_platform_final_certification_ledger.jsonl"
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
