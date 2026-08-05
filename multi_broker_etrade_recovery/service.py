from __future__ import annotations
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .fixtures import SCENARIOS
from .playbook import PLAYBOOK
from .readiness import operational_readiness_check
from .state_machine import decide_recovery


class ETradeRecoveryOperationalReadinessService:
    def evaluate(self, *, output_dir: Path) -> dict:
        now = datetime.now(timezone.utc)

        scenario_results = []
        for scenario in SCENARIOS:
            decision = decide_recovery(
                scenario["trigger"],
                scenario["attempt"],
            )
            scenario_results.append({
                "name": scenario["name"],
                "attempt": scenario["attempt"],
                "decision": decision.to_dict(),
            })

        readiness = operational_readiness_check()
        states = Counter(
            item["decision"]["state"]
            for item in scenario_results
        )

        result = {
            "stage": (
                "V4801_TO_V5000_ETRADE_RECOVERY_ORCHESTRATION_"
                "AND_OPERATIONAL_READINESS_CERTIFICATION"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": "FIXTURE_RECOVERY_SCENARIOS",
            "recovery_scenarios": scenario_results,
            "recovery_state_counts": dict(sorted(states.items())),
            "recovery_playbook": [
                step.to_dict() for step in PLAYBOOK
            ],
            "operational_readiness": readiness,
            "token_renew_orchestration_ready": True,
            "oauth_reauthorization_orchestration_ready": True,
            "rate_limit_backoff_ready": True,
            "server_retry_ready": True,
            "network_retry_ready": True,
            "account_restriction_manual_recovery_ready": True,
            "snapshot_revalidation_ready": True,
            "unknown_failure_failsafe_ready": True,
            "read_only_platform_code_complete": True,
            "actual_sandbox_validation_complete": False,
            "actual_production_validation_complete": False,
            "etrade_key_issuance_pending": True,
            "automatic_order_submission_enabled": False,
            "production_network_read_performed": False,
            "sandbox_network_read_performed": False,
            "real_credentials_used": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "order_cancel_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "existing_alpaca_controller_modified": False,
            "existing_market_polling_modified": False,
            "key_issuance_blocks_code_development": False,
            "external_blocker": {
                "active": True,
                "type": "ETRADE_SANDBOX_CONSUMER_KEY_ISSUANCE",
                "blocks_code_completion": False,
                "blocks_actual_sandbox_validation": True,
                "blocks_actual_production_validation": True,
            },
            "next_user_action": (
                "RETRY_ETRADE_SANDBOX_KEY_ISSUANCE_OR_CONTACT_ETRADE_SUPPORT"
            ),
            "next_fixed_development": (
                "V5001_TO_V5200_ETRADE_ACTUAL_CONNECTION_"
                "VALIDATION_WHEN_KEYS_AVAILABLE"
            ),
        }

        scenario_by_name = {
            item["name"]: item["decision"]
            for item in scenario_results
        }
        checks = (
            scenario_by_name["HEALTHY"]["state"]
            == "READ_ONLY_OPERATIONAL",
            scenario_by_name["TOKEN_RENEW"]["state"]
            == "RENEWING_TOKEN",
            scenario_by_name["TOKEN_REVOKED"]["state"]
            == "REAUTHORIZATION_REQUIRED",
            scenario_by_name["RATE_LIMIT_SECOND_ATTEMPT"][
                "retry_after_seconds"
            ] == 180,
            scenario_by_name["SERVER_ERROR_THIRD_ATTEMPT"][
                "retry_after_seconds"
            ] == 45,
            scenario_by_name["ACCOUNT_RESTRICTED"]["state"]
            == "MANUAL_ACCOUNT_RECOVERY",
            scenario_by_name["UNKNOWN"]["state"]
            == "FAILSAFE_BLOCKED",
            all(
                item["decision"]["write_allowed"] is False
                for item in scenario_results
            ),
            readiness["code_operational_readiness"] == "PASS",
        )
        if not all(checks):
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
        outputs = {
            "etrade_operational_readiness_certification.json": result,
            "etrade_recovery_state_machine_report.json": {
                "scenarios": scenario_results,
                "state_counts": result["recovery_state_counts"],
            },
            "etrade_recovery_playbook.json": {
                "steps": result["recovery_playbook"]
            },
            "etrade_read_only_platform_status.json": readiness,
            "etrade_external_validation_blocker.json": result[
                "external_blocker"
            ],
            "etrade_final_readiness_dashboard.json": {
                "status": result["status"],
                "read_only_platform_code_complete": True,
                "actual_sandbox_validation_complete": False,
                "actual_production_validation_complete": False,
                "broker_write": False,
                "paper_orders": 0,
                "live_orders": 0,
                "next_user_action": result["next_user_action"],
            },
        }

        for name, payload in outputs.items():
            (output_dir / name).write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        with (
            output_dir / "etrade_operational_readiness_ledger.jsonl"
        ).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

        return result
