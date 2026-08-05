from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .io import append_jsonl, read_json, write_json
from .registry import normalize_account, validate_account


class MultiAccountFrameworkService:
    def evaluate(
        self,
        *,
        registry_path: Path,
        policy_path: Path,
        output_dir: Path,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        registry = read_json(registry_path)
        policy = read_json(policy_path)
        accounts = list(registry.get("accounts", []))

        aliases = [str(item.get("alias", "")) for item in accounts]
        duplicate_aliases = sorted(
            {
                alias for alias in aliases
                if aliases.count(alias) > 1
            }
        )

        account_results = []
        for raw in accounts:
            blockers = validate_account(raw)
            normalized = normalize_account(raw)
            if normalized["alias"] in duplicate_aliases:
                blockers.append("DUPLICATE_ACCOUNT_ALIAS")
            account_results.append(
                {
                    "alias": normalized["alias"],
                    "status": "VALID" if not blockers else "BLOCKED",
                    "blockers": sorted(set(blockers)),
                    "account": normalized,
                }
            )

        global_blockers = []
        if len(accounts) > int(policy.get("maximum_accounts", 10)):
            global_blockers.append("MAXIMUM_ACCOUNT_COUNT_EXCEEDED")
        if not accounts:
            global_blockers.append("ACCOUNT_REGISTRY_EMPTY")
        if policy.get("global_broker_network_enabled") is True:
            global_blockers.append("GLOBAL_BROKER_NETWORK_MUST_BE_OFF")
        if policy.get("global_order_submission_enabled") is True:
            global_blockers.append("GLOBAL_ORDER_SUBMISSION_MUST_BE_OFF")

        valid_count = sum(
            1 for item in account_results
            if item["status"] == "VALID"
        )
        blocked_count = len(account_results) - valid_count

        broker_summary = {}
        for item in account_results:
            broker = item["account"]["broker"]
            broker_summary.setdefault(
                broker,
                {
                    "account_count": 0,
                    "valid_count": 0,
                    "network_enabled_count": 0,
                    "submission_enabled_count": 0,
                },
            )
            broker_summary[broker]["account_count"] += 1
            if item["status"] == "VALID":
                broker_summary[broker]["valid_count"] += 1
            if item["account"]["broker_network_enabled"]:
                broker_summary[broker][
                    "network_enabled_count"
                ] += 1
            if item["account"]["order_submission_enabled"]:
                broker_summary[broker][
                    "submission_enabled_count"
                ] += 1

        registry_seed = {
            "accounts": [
                item["account"] for item in account_results
            ],
            "policy_version": policy.get("policy_version"),
        }
        registry_fingerprint = hashlib.sha256(
            json.dumps(
                registry_seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V431_TO_V460_MULTI_ACCOUNT_FRAMEWORK",
            "status": (
                "PASS"
                if not global_blockers and blocked_count == 0
                else "PASS_WITH_BLOCKED_ACCOUNTS"
            ),
            "generated_at": now.isoformat(),
            "registry_fingerprint": registry_fingerprint,
            "account_count": len(account_results),
            "valid_account_count": valid_count,
            "blocked_account_count": blocked_count,
            "duplicate_aliases": duplicate_aliases,
            "global_blockers": global_blockers,
            "accounts": account_results,
            "broker_summary": broker_summary,
            "credential_values_stored": False,
            "credential_aliases_only": True,
            "global_broker_network_enabled": False,
            "global_order_submission_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V461_TO_V490_STRATEGY_FRAMEWORK"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            output_dir / "multi_account_registry_latest.json",
            result,
        )
        write_json(
            output_dir / "multi_account_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "status": result["status"],
                "registry_fingerprint": registry_fingerprint,
                "account_count": len(account_results),
                "valid_account_count": valid_count,
                "blocked_account_count": blocked_count,
                "broker_summary": broker_summary,
                "global_broker_network_enabled": False,
                "global_order_submission_enabled": False,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )

        for item in account_results:
            alias = item["alias"] or "invalid"
            account_dir = output_dir / "accounts" / alias
            write_json(
                account_dir / "account_profile.json",
                item,
            )
            write_json(
                account_dir / "risk_policy.json",
                item["account"]["risk_policy"],
            )
            write_json(
                account_dir / "controller_profile.json",
                item["account"]["controller_profile"],
            )
            write_json(
                account_dir / "health_status.json",
                {
                    "alias": alias,
                    "status": "NOT_CONNECTED",
                    "broker_network_enabled": False,
                    "order_submission_enabled": False,
                    "actual_broker_read_performed": False,
                    "actual_broker_write_performed": False,
                },
            )
            append_jsonl(
                account_dir / "account_event_ledger.jsonl",
                {
                    "generated_at": now.isoformat(),
                    "event": "ACCOUNT_PROFILE_EVALUATED",
                    "status": item["status"],
                    "blockers": item["blockers"],
                    "broker_network_enabled": False,
                    "order_submission_enabled": False,
                },
            )

        append_jsonl(
            output_dir / "multi_account_registry_ledger.jsonl",
            result,
        )
        return result
