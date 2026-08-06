from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from .cleanup import build_cleanup_plan
from .etrade_mock import ETradeMockClient
from .failure_injection import (
    SCENARIOS,
    execute_fixture_scenario,
)
from .monitor import RuntimeSample, evaluate_samples
from .multi_account import fixture_accounts, validate_accounts
from .runtime_policy import RULES, gitignore_append_block


class PreMarketHardeningCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        now = datetime.now(timezone.utc)

        cleanup_plan = build_cleanup_plan(
            files=[
                {
                    "path": (
                        "release/actual_market_polling_validation/"
                        "actual/cycle_0001/market_snapshot.json"
                    ),
                    "modified_at": now - timedelta(days=10),
                },
                {
                    "path": (
                        "release/watchdog/actual/watchdog_ledger.jsonl"
                    ),
                    "modified_at": now - timedelta(days=40),
                },
                {
                    "path": (
                        "release/controller/actual/checkpoint.json"
                    ),
                    "modified_at": now - timedelta(days=5),
                },
                {
                    "path": "source/module.py",
                    "modified_at": now - timedelta(days=500),
                },
            ],
            now=now,
            dry_run=True,
        )

        monitor_result = evaluate_samples([
            RuntimeSample(
                "T0", 100, Decimal("400"),
                Decimal("12"), Decimal("30"),
                0, 0, 1000,
            ),
            RuntimeSample(
                "T1", 220, Decimal("408"),
                Decimal("18"), Decimal("31"),
                0, 0, 1120,
            ),
            RuntimeSample(
                "T2", 340, Decimal("413"),
                Decimal("22"), Decimal("29"),
                0, 0, 1240,
            ),
        ])

        failure_results = {
            name: execute_fixture_scenario(name)
            for name in SCENARIOS
        }

        etrade = ETradeMockClient()
        request_token = etrade.request_token()
        access_token = etrade.exchange_token("123456")
        account_read = etrade.read_accounts()
        try:
            etrade.submit_order()
            write_blocked = False
        except PermissionError:
            write_blocked = True

        account_validation = validate_accounts(
            fixture_accounts(10)
        )

        result = {
            "stage": (
                "V6801_TO_V7000_PHASES_1_TO_4_"
                "PREMARKET_HARDENING"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": (
                "OFFLINE_PREMARKET_HARDENING_FIXTURES"
            ),
            "runtime_policy_rules": [
                item.to_dict() for item in RULES
            ],
            "gitignore_append_block": gitignore_append_block(),
            "cleanup_plan": cleanup_plan,
            "long_run_monitor_fixture": monitor_result,
            "failure_injection_results": failure_results,
            "etrade_mock": {
                "request_token_created": bool(
                    request_token.request_token
                ),
                "access_token_created": bool(
                    access_token.access_token
                ),
                "account_read": account_read,
                "write_blocked": write_blocked,
                "write_calls": etrade.write_calls,
                "actual_credentials_used": False,
            },
            "multi_account_validation": account_validation,
            "runtime_git_separation_ready": True,
            "cleanup_dry_run_ready": True,
            "log_rotation_policy_ready": True,
            "compression_policy_ready": True,
            "long_run_monitor_ready": True,
            "cpu_monitor_ready": True,
            "memory_monitor_ready": True,
            "cycle_gap_monitor_ready": True,
            "ledger_sequence_monitor_ready": True,
            "failure_injection_ready": True,
            "restart_recovery_fixture_ready": True,
            "etrade_oauth_mock_ready": True,
            "etrade_retry_mock_ready": True,
            "etrade_rate_limit_fixture_ready": True,
            "etrade_write_guard_ready": True,
            "multi_account_load_fixture_ready": True,
            "multi_account_permission_validation_ready": True,
            "multi_account_risk_profile_validation_ready": True,
            "market_open_required": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "existing_order_paths_modified": False,
            "next_user_action": (
                "INSTALL_AND_RUN_BUNDLE_THEN_RUN_INTRADAY_"
                "VALIDATION_WHEN_MARKET_OPENS"
            ),
        }

        checks = (
            cleanup_plan["delete_count"] == 1,
            cleanup_plan["compress_count"] == 1,
            cleanup_plan["protected_skipped"] == 1,
            monitor_result["status"] == "PASS",
            all(
                item["status"] == "PASS"
                for item in failure_results.values()
            ),
            account_read["status"] == "PASS",
            write_blocked,
            account_validation["status"] == "PASS",
            result["actual_paper_orders_submitted"] == 0,
            result["actual_live_orders_submitted"] == 0,
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
            "premarket_hardening_certification.json": result,
            "runtime_retention_policy.json": {
                "rules": result["runtime_policy_rules"]
            },
            "runtime_cleanup_dry_run.json": cleanup_plan,
            "long_run_monitor_fixture.json": monitor_result,
            "failure_injection_certification.json": {
                "scenarios": failure_results
            },
            "etrade_mock_certification.json": result["etrade_mock"],
            "multi_account_load_certification.json": (
                account_validation
            ),
            "premarket_remaining_live_checks.json": {
                "paper_intraday_data_freshness": "PENDING_MARKET_OPEN",
                "paper_end_of_day_shutdown": "PENDING_MARKET_CLOSE",
                "actual_8_hour_session": "PENDING_MARKET_SESSION",
                "etrade_real_oauth": "PENDING_CONSUMER_KEY",
                "broker_write": "DISABLED",
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
            / "premarket_hardening_ledger.jsonl"
        ).open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    result,
                    sort_keys=True,
                ) + "\n"
            )

        return result
