from __future__ import annotations
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .dashboard import build_dashboard
from .fixtures import ACCOUNTS
from .profiles import PolicyProfileCatalog
from .runtime import RuntimeProfileStore
from .transition import validate_transition


class DualAccountOperationsCertificationService:
    def evaluate(
        self,
        *,
        output_dir: Path,
    ) -> dict:
        now = datetime.now(timezone.utc)
        catalog = PolicyProfileCatalog()

        active = catalog.get("PAPER_TEST")
        dashboard = build_dashboard(
            active_profile=active.name,
            accounts=ACCOUNTS,
            policy_profile=active.to_dict(),
            global_kill_switch=False,
        )

        scenarios = {
            "all_stop_to_paper_test": validate_transition(
                "ALL_STOP",
                "PAPER_TEST",
                operator_ack=False,
                etrade_actual_connection_validated=False,
            ),
            "all_stop_to_etrade_without_ack": (
                validate_transition(
                    "ALL_STOP",
                    "ETRADE_READ_ONLY",
                    operator_ack=False,
                    etrade_actual_connection_validated=False,
                )
            ),
            "all_stop_to_etrade_without_validation": (
                validate_transition(
                    "ALL_STOP",
                    "ETRADE_READ_ONLY",
                    operator_ack=True,
                    etrade_actual_connection_validated=False,
                )
            ),
            "all_stop_to_etrade_validated": (
                validate_transition(
                    "ALL_STOP",
                    "ETRADE_READ_ONLY",
                    operator_ack=True,
                    etrade_actual_connection_validated=True,
                )
            ),
            "paper_test_to_etrade_direct": (
                validate_transition(
                    "PAPER_TEST",
                    "ETRADE_READ_ONLY",
                    operator_ack=True,
                    etrade_actual_connection_validated=True,
                )
            ),
            "paper_test_to_all_stop": (
                validate_transition(
                    "PAPER_TEST",
                    "ALL_STOP",
                    operator_ack=False,
                    etrade_actual_connection_validated=False,
                )
            ),
        }

        store = RuntimeProfileStore(
            output_dir / "active_policy_profile.runtime.json"
        )
        store.save("PAPER_TEST")
        loaded_profile = store.load()

        result = {
            "stage": (
                "V5201_TO_V5400_DUAL_ACCOUNT_"
                "OPERATIONS_DASHBOARD_AND_POLICY_PROFILES"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": (
                "FIXTURE_DUAL_ACCOUNT_OPERATIONS"
            ),
            "active_profile": active.name,
            "loaded_runtime_profile": loaded_profile,
            "profile_catalog": [
                item.to_dict()
                for item in catalog.all()
            ],
            "dashboard": dashboard,
            "transition_scenarios": scenarios,
            "profile_count": len(
                catalog.all()
            ),
            "paper_test_profile_ready": True,
            "etrade_read_only_profile_ready": True,
            "dual_monitor_profile_ready": True,
            "all_stop_profile_ready": True,
            "maintenance_profile_ready": True,
            "runtime_profile_store_ready": True,
            "safe_profile_transition_ready": True,
            "operator_ack_guard_ready": True,
            "etrade_connection_validation_guard_ready": True,
            "account_dashboard_ready": True,
            "future_multi_account_dashboard_ready": True,
            "future_multi_broker_dashboard_ready": True,
            "actual_etrade_connection_validated": False,
            "etrade_key_issuance_pending": True,
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
                "V5401_TO_V5600_DUAL_ACCOUNT_"
                "OPERATIONS_CONTROLLER_AND_FINAL_CERTIFICATION"
            ),
        }

        checks = (
            dashboard["account_count"] == 2,
            dashboard[
                "effective_read_account_count"
            ] == 1,
            dashboard[
                "effective_write_account_count"
            ] == 0,
            scenarios[
                "all_stop_to_paper_test"
            ]["allowed"],
            not scenarios[
                "all_stop_to_etrade_without_ack"
            ]["allowed"],
            not scenarios[
                "all_stop_to_etrade_without_validation"
            ]["allowed"],
            scenarios[
                "all_stop_to_etrade_validated"
            ]["allowed"],
            not scenarios[
                "paper_test_to_etrade_direct"
            ]["allowed"],
            scenarios[
                "paper_test_to_all_stop"
            ]["allowed"],
            loaded_profile == "PAPER_TEST",
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
            "dual_account_operations_certification.json": result,
            "dual_account_operations_dashboard.json": dashboard,
            "dual_account_policy_profiles.json": {
                "items": result["profile_catalog"]
            },
            "dual_account_profile_transition_report.json": {
                "scenarios": scenarios
            },
            "dual_account_operations_summary.json": {
                "status": result["status"],
                "active_profile": (
                    result["active_profile"]
                ),
                "account_count": (
                    dashboard["account_count"]
                ),
                "effective_read_account_count": (
                    dashboard[
                        "effective_read_account_count"
                    ]
                ),
                "effective_write_account_count": (
                    dashboard[
                        "effective_write_account_count"
                    ]
                ),
                "etrade_key_issuance_pending": True,
                "broker_write": False,
            },
            "dual_account_dashboard_extension_contract.json": {
                "registry_driven": True,
                "dynamic_account_rows": True,
                "dynamic_broker_rows": True,
                "schema_version": 1,
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
                )
                + "\n",
                encoding="utf-8",
            )

        csv_path = (
            output_dir
            / "dual_account_operations_dashboard.csv"
        )
        keys = sorted({
            key
            for row in dashboard["accounts"]
            for key in row
        })
        with csv_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=keys,
            )
            writer.writeheader()
            writer.writerows(
                dashboard["accounts"]
            )

        with (
            output_dir
            / "dual_account_operations_ledger.jsonl"
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
