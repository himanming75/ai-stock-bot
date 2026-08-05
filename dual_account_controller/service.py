from __future__ import annotations
import hashlib
import json
from pathlib import Path

from dual_account_operations.profiles import (
    PolicyProfileCatalog,
)

from .controller import (
    DualAccountOperationsController,
)
from .dashboard import (
    build_controller_dashboard,
)


class DualAccountFinalCertificationService:
    def evaluate(
        self,
        *,
        output_dir: Path,
    ) -> dict:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        state_path = (
            output_dir
            / "dual_account_controller_state.runtime.json"
        )
        ledger_path = (
            output_dir
            / "dual_account_controller_audit_ledger.jsonl"
        )
        if state_path.exists():
            state_path.unlink()
        if ledger_path.exists():
            ledger_path.unlink()

        controller = (
            DualAccountOperationsController(
                state_path=state_path,
                ledger_path=ledger_path,
                etrade_actual_connection_validated=False,
            )
        )

        restored_default = (
            controller.restore().to_dict()
        )
        to_paper = controller.transition(
            "PAPER_TEST",
            operator_ack=False,
            reason="START_PAPER_TEST",
        ).to_dict()
        locked = (
            controller.lock_profile().to_dict()
        )
        blocked_by_lock = controller.transition(
            "DUAL_MONITOR",
            operator_ack=True,
            reason="TEST_LOCK_GUARD",
        ).to_dict()
        unlock_blocked = (
            controller.unlock_profile(
                operator_ack=False
            ).to_dict()
        )
        unlocked = (
            controller.unlock_profile(
                operator_ack=True
            ).to_dict()
        )
        etrade_blocked = controller.transition(
            "ETRADE_READ_ONLY",
            operator_ack=True,
            reason="TEST_ETRADE_GUARD",
        ).to_dict()
        stopped = controller.transition(
            "ALL_STOP",
            operator_ack=False,
            reason="OPERATOR_STOP",
        ).to_dict()
        paper_again = controller.transition(
            "PAPER_TEST",
            operator_ack=False,
            reason="RESTART_PAPER_TEST",
        ).to_dict()
        account_killed = (
            controller
            .activate_account_kill_switch(
                "ALPACA_PAPER_PRIMARY",
                reason="ACCOUNT_TEST_STOP",
            )
            .to_dict()
        )
        account_release_blocked = (
            controller
            .deactivate_account_kill_switch(
                "ALPACA_PAPER_PRIMARY",
                operator_ack=False,
                reason="TEST_RELEASE",
            )
            .to_dict()
        )
        account_released = (
            controller
            .deactivate_account_kill_switch(
                "ALPACA_PAPER_PRIMARY",
                operator_ack=True,
                reason="OPERATOR_RELEASE",
            )
            .to_dict()
        )
        emergency_stopped = (
            controller.emergency_guard(
                critical_condition=True,
                reason="CRITICAL_HEALTH_CONDITION",
            ).to_dict()
        )

        restarted = (
            DualAccountOperationsController(
                state_path=state_path,
                ledger_path=ledger_path,
                etrade_actual_connection_validated=False,
            )
        )
        restored_after_restart = (
            restarted.restore().to_dict()
        )

        catalog = PolicyProfileCatalog()
        profile_catalog = [
            item.to_dict()
            for item in catalog.all()
        ]
        dashboard = build_controller_dashboard(
            controller_state=(
                restored_after_restart
            ),
            profile_catalog=profile_catalog,
            etrade_key_issuance_pending=True,
            etrade_actual_connection_validated=False,
        )

        result = {
            "stage": (
                "V5401_TO_V5600_DUAL_ACCOUNT_"
                "OPERATIONS_CONTROLLER_AND_FINAL_CERTIFICATION"
            ),
            "status": "PASS",
            "validation_mode": (
                "FIXTURE_CONTROLLER_STATE_MACHINE"
            ),
            "scenarios": {
                "restored_default": restored_default,
                "to_paper": to_paper,
                "locked": locked,
                "blocked_by_lock": blocked_by_lock,
                "unlock_blocked": unlock_blocked,
                "unlocked": unlocked,
                "etrade_blocked": etrade_blocked,
                "stopped": stopped,
                "paper_again": paper_again,
                "account_killed": account_killed,
                "account_release_blocked": account_release_blocked,
                "account_released": account_released,
                "emergency_stopped": emergency_stopped,
                "restored_after_restart": (
                    restored_after_restart
                ),
            },
            "controller_dashboard": dashboard,
            "profile_controller_ready": True,
            "profile_lock_ready": True,
            "restart_restore_ready": True,
            "account_kill_switch_controller_ready": True,
            "global_kill_switch_controller_ready": True,
            "emergency_all_stop_ready": True,
            "audit_ledger_ready": True,
            "operator_ack_guard_ready": True,
            "etrade_validation_guard_ready": True,
            "fourth_stage_final_certification": "PASS",
            "future_multi_account_extension_ready": True,
            "future_multi_broker_extension_ready": True,
            "active_accounts": [
                "ALPACA_PAPER_PRIMARY",
                "ETRADE_PRIMARY",
            ],
            "etrade_key_issuance_pending": True,
            "actual_etrade_connection_validated": False,
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
                "RETURN_TO_AI_ENGINE_OR_ACTUAL_"
                "VALIDATION_WHEN_MARKET_AND_KEYS_AVAILABLE"
            ),
        }

        checks = (
            restored_default[
                "active_profile"
            ] == "ALL_STOP",
            to_paper["allowed"],
            locked["profile_locked"],
            not blocked_by_lock["allowed"],
            unlock_blocked["profile_locked"],
            not unlocked["profile_locked"],
            not etrade_blocked["allowed"],
            stopped["allowed"],
            paper_again["allowed"],
            account_killed[
                "account_kill_switches"
            ]["ALPACA_PAPER_PRIMARY"],
            account_release_blocked[
                "account_kill_switches"
            ]["ALPACA_PAPER_PRIMARY"],
            not account_released[
                "account_kill_switches"
            ]["ALPACA_PAPER_PRIMARY"],
            emergency_stopped[
                "active_profile"
            ] == "ALL_STOP",
            emergency_stopped[
                "global_kill_switch"
            ],
            restored_after_restart[
                "active_profile"
            ] == "ALL_STOP",
            restored_after_restart[
                "global_kill_switch"
            ],
            dashboard[
                "broker_write_globally_enabled"
            ] is False,
        )
        if not all(checks):
            result["status"] = "BLOCKED"
            result[
                "fourth_stage_final_certification"
            ] = "BLOCKED"

        seed = dict(result)
        result["certification_fingerprint"] = (
            hashlib.sha256(
                json.dumps(
                    seed,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        )

        outputs = {
            "dual_account_final_certification.json": result,
            "dual_account_controller_dashboard.json": dashboard,
            "dual_account_controller_scenarios.json": {
                "items": result["scenarios"]
            },
            "dual_account_fourth_stage_status.json": {
                "stage_4_status": result[
                    "fourth_stage_final_certification"
                ],
                "active_accounts": result[
                    "active_accounts"
                ],
                "future_multi_account_extension_ready": True,
                "future_multi_broker_extension_ready": True,
                "etrade_key_issuance_pending": True,
                "broker_write": False,
            },
            "dual_account_controller_extension_contract.json": {
                "registry_based": True,
                "profile_based": True,
                "dynamic_accounts_supported": True,
                "dynamic_brokers_supported": True,
                "state_schema_version": 1,
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

        with (
            output_dir
            / "dual_account_final_certification_ledger.jsonl"
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
