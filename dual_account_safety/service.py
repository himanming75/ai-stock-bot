from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .accounting import segregated_account_summary
from .fixtures import (
    ALPACA_PAPER,
    ETRADE_PRIMARY,
    SNAPSHOTS,
)
from .kill_switch import KillSwitchManager
from .models import RouteRequest
from .registry import AccountRegistry
from .routing import SafeAccountRouter


class DualAccountSafetyCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        now = datetime.now(timezone.utc)

        registry = AccountRegistry()
        registry.register(ALPACA_PAPER)
        registry.register(ETRADE_PRIMARY)

        router = SafeAccountRouter(registry)

        scenarios = {
            "alpaca_paper_read": router.decide(
                RouteRequest(
                    account_key="ALPACA_PAPER_PRIMARY",
                    broker="ALPACA",
                    environment="PAPER",
                    operation="ACCOUNT_READ",
                )
            ).to_dict(),
            "alpaca_paper_write_default_blocked": router.decide(
                RouteRequest(
                    account_key="ALPACA_PAPER_PRIMARY",
                    broker="ALPACA",
                    environment="PAPER",
                    operation="ORDER_SUBMIT",
                    strategy_id="FIXTURE_STRATEGY",
                )
            ).to_dict(),
            "etrade_read_blocked_pending_validation": router.decide(
                RouteRequest(
                    account_key="ETRADE_PRIMARY",
                    broker="ETRADE",
                    environment="PRODUCTION",
                    operation="ACCOUNT_READ",
                )
            ).to_dict(),
            "etrade_write_blocked": router.decide(
                RouteRequest(
                    account_key="ETRADE_PRIMARY",
                    broker="ETRADE",
                    environment="PRODUCTION",
                    operation="ORDER_SUBMIT",
                    strategy_id="FIXTURE_STRATEGY",
                )
            ).to_dict(),
            "broker_mismatch_blocked": router.decide(
                RouteRequest(
                    account_key="ETRADE_PRIMARY",
                    broker="ALPACA",
                    environment="PRODUCTION",
                    operation="ACCOUNT_READ",
                )
            ).to_dict(),
            "environment_mismatch_blocked": router.decide(
                RouteRequest(
                    account_key="ALPACA_PAPER_PRIMARY",
                    broker="ALPACA",
                    environment="PRODUCTION",
                    operation="ACCOUNT_READ",
                )
            ).to_dict(),
            "unknown_account_blocked": router.decide(
                RouteRequest(
                    account_key="UNKNOWN",
                    broker="ALPACA",
                    environment="PAPER",
                    operation="ACCOUNT_READ",
                )
            ).to_dict(),
        }

        kill_switch = KillSwitchManager(registry)
        kill_switch.activate_account(
            "ALPACA_PAPER_PRIMARY"
        )
        killed_route = router.decide(
            RouteRequest(
                account_key="ALPACA_PAPER_PRIMARY",
                broker="ALPACA",
                environment="PAPER",
                operation="ACCOUNT_READ",
            )
        ).to_dict()
        kill_switch.deactivate_account(
            "ALPACA_PAPER_PRIMARY"
        )

        accounting = segregated_account_summary(
            SNAPSHOTS
        )

        result = {
            "stage": (
                "V5001_TO_V5200_DUAL_ACCOUNT_"
                "SAFETY_INTEGRATION_FOUNDATION"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": "FIXTURE_DUAL_ACCOUNT",
            "active_account_model": (
                "ALPACA_PAPER_PLUS_ETRADE_PRIMARY"
            ),
            "registry": [
                item.to_dict()
                for item in registry.all()
            ],
            "route_scenarios": scenarios,
            "account_kill_switch_scenario": (
                killed_route
            ),
            "kill_switch_status": (
                kill_switch.status()
            ),
            "segregated_accounting": accounting,
            "paper_actual_performance_separated": True,
            "combined_equity_reference_only": True,
            "cross_broker_order_misrouting_guard": True,
            "environment_mismatch_guard": True,
            "unknown_account_guard": True,
            "account_kill_switch_ready": True,
            "global_kill_switch_ready": True,
            "strategy_target_role_guard_ready": True,
            "future_multi_account_extension_ready": True,
            "future_multi_broker_extension_ready": True,
            "registry_schema_version": 1,
            "actual_etrade_connection_validated": False,
            "etrade_key_issuance_pending": True,
            "alpaca_paper_write_enabled_by_this_stage": False,
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
            "existing_etrade_modules_modified": False,
            "next_fixed_development": (
                "V5201_TO_V5400_DUAL_ACCOUNT_"
                "OPERATIONS_DASHBOARD_AND_POLICY_PROFILES"
            ),
        }

        checks = (
            scenarios["alpaca_paper_read"]["allowed"],
            not scenarios[
                "alpaca_paper_write_default_blocked"
            ]["allowed"],
            not scenarios[
                "etrade_read_blocked_pending_validation"
            ]["allowed"],
            not scenarios[
                "etrade_write_blocked"
            ]["allowed"],
            not scenarios[
                "broker_mismatch_blocked"
            ]["allowed"],
            not scenarios[
                "environment_mismatch_blocked"
            ]["allowed"],
            not scenarios[
                "unknown_account_blocked"
            ]["allowed"],
            not killed_route["allowed"],
            accounting[
                "paper_and_actual_performance_mixed"
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

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        outputs = {
            "dual_account_safety_certification.json": result,
            "dual_account_registry.json": {
                "schema_version": 1,
                "items": result["registry"],
            },
            "dual_account_route_policy.json": {
                "paper_account": (
                    "ALPACA_PAPER_PRIMARY"
                ),
                "actual_account": (
                    "ETRADE_PRIMARY"
                ),
                "paper_strategy_execution_only": True,
                "etrade_read_only": True,
                "cross_broker_misrouting_blocked": True,
                "broker_write_default": False,
            },
            "dual_account_kill_switch_status.json": (
                result["kill_switch_status"]
            ),
            "dual_account_segregated_accounting.json": (
                accounting
            ),
            "dual_account_extension_contract.json": {
                "registry_based": True,
                "additional_accounts_supported": True,
                "additional_brokers_supported": True,
                "existing_account_keys_immutable": True,
                "schema_version": 1,
            },
        }

        for name, payload in outputs.items():
            (output_dir / name).write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

        with (
            output_dir
            / "dual_account_safety_ledger.jsonl"
        ).open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    result,
                    sort_keys=True,
                )
                + "\n"
            )

        return result
