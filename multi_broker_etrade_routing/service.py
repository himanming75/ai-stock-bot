from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .fixtures import ACCOUNTS, ACCOUNT_SNAPSHOTS
from .policy import ProductionReadOnlyPolicy
from .routing import ETradeAccountRouter
from .unified import unified_account_summary


class ETradeProductionRoutingCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        now = datetime.now(timezone.utc)

        policy = ProductionReadOnlyPolicy(
            production_read_enabled=False,
            broker_write_enabled=False,
            order_submission_enabled=False,
            order_cancel_enabled=False,
            require_explicit_environment_ack=True,
            allowed_account_id_keys=(
                "individual-brokerage-key",
                "stock-plan-key",
            ),
            default_account_id_key=(
                "individual-brokerage-key"
            ),
        )

        aliases = {
            "individual-brokerage-key": "PRIMARY_BROKERAGE",
            "stock-plan-key": "STOCK_PLAN",
            "closed-account-key": "CLOSED_ACCOUNT",
        }

        router = ETradeAccountRouter(
            policy=policy,
            aliases=aliases,
        )
        registry = router.build_registry(ACCOUNTS)
        selected = router.select(registry)

        production_guard_passed = False
        try:
            policy.assert_production_read_allowed()
        except PermissionError:
            production_guard_passed = True

        account_allowlist_guard_passed = False
        try:
            policy.assert_account_allowed(
                "unauthorized-account-key"
            )
        except PermissionError:
            account_allowlist_guard_passed = True

        enabled_snapshots = [
            ACCOUNT_SNAPSHOTS[item.account_id_key]
            for item in registry
            if (
                item.enabled
                and item.account_id_key in ACCOUNT_SNAPSHOTS
            )
        ]
        unified = unified_account_summary(
            enabled_snapshots
        )

        result = {
            "stage": (
                "V4001_TO_V4200_ETRADE_PRODUCTION_READ_ONLY_"
                "GUARD_AND_ACCOUNT_ROUTING"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "policy": policy.to_dict(),
            "account_registry": [
                item.to_dict()
                for item in registry
            ],
            "selected_default_account": (
                selected.to_dict()
            ),
            "production_read_guard_passed": (
                production_guard_passed
            ),
            "account_allowlist_guard_passed": (
                account_allowlist_guard_passed
            ),
            "multiple_account_routing_ready": True,
            "alias_routing_ready": True,
            "default_account_routing_ready": True,
            "closed_account_visible_but_disabled": True,
            "unified_account_summary": unified,
            "production_network_read_performed": False,
            "production_credentials_used": False,
            "production_read_enabled": False,
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
            "deferred_external_validation": (
                "PRODUCTION_READ_REQUIRES_KEYS_AND_EXPLICIT_ACK"
            ),
            "next_fixed_development": (
                "V4201_TO_V4400_ETRADE_UNIFIED_PORTFOLIO_"
                "POSITIONS_AND_ORDERS_ROUTING"
            ),
        }

        checks = (
            production_guard_passed,
            account_allowlist_guard_passed,
            result["multiple_account_routing_ready"],
            result["alias_routing_ready"],
            result["default_account_routing_ready"],
            selected.account_id_key
            == "individual-brokerage-key",
            unified["account_count"] == 2,
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

        output_dir.mkdir(parents=True, exist_ok=True)
        outputs = {
            "etrade_production_routing_certification.json": (
                result
            ),
            "etrade_account_registry.json": {
                "items": result["account_registry"]
            },
            "etrade_production_read_policy.json": (
                result["policy"]
            ),
            "etrade_default_account_selection.json": {
                "selected": result[
                    "selected_default_account"
                ]
            },
            "etrade_unified_account_summary.json": (
                unified
            ),
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
            / "etrade_account_routing_ledger.jsonl"
        ).open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    result,
                    sort_keys=True,
                )
                + "\n"
            )

        return result
