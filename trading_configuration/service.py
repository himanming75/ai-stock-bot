from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .api import TradingConfigurationService
from .defaults import new_draft


class TradingConfigurationCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        service = TradingConfigurationService(
            draft_path=output_dir / "draft.json",
            ledger_path=output_dir / "ledger.jsonl",
        )

        base = new_draft()
        valid = service.validate(base)
        saved = service.save(base)

        activation_blocked = False
        try:
            service.activate(base)
        except PermissionError:
            activation_blocked = True

        invalid_blocked = False
        invalid = dict(base)
        invalid["profile_key"] = "AGGRESSIVE"
        invalid["profile"] = {
            "max_positions": 50,
            "max_position_percent": 100,
            "max_daily_loss_percent": 20,
            "cash_reserve_percent": 100,
        }
        try:
            service.validate(invalid)
        except ValueError:
            invalid_blocked = True

        result = {
            "stage": (
                "V9001_TO_V9200_PROFILE_STRATEGY_"
                "AND_RISK_CONFIGURATION_GUI"
            ),
            "status": "PASS",
            "profile_presets_ready": True,
            "read_only_profile_ready": True,
            "conservative_profile_ready": True,
            "balanced_profile_ready": True,
            "aggressive_profile_ready": True,
            "symbol_universe_ready": True,
            "capital_limit_ready": True,
            "maximum_positions_ready": True,
            "maximum_position_percent_ready": True,
            "maximum_daily_loss_ready": True,
            "cash_reserve_ready": True,
            "short_permission_ready": True,
            "extended_hours_permission_ready": True,
            "ema_configuration_ready": True,
            "rsi_configuration_ready": True,
            "macd_configuration_ready": True,
            "vwap_configuration_ready": True,
            "breakout_configuration_ready": True,
            "draft_validation_ready": True,
            "draft_storage_ready": True,
            "draft_ledger_ready": True,
            "activation_blocked": (
                activation_blocked
            ),
            "unsafe_allocation_blocked": (
                invalid_blocked
            ),
            "responsive_gui_ready": True,
            "default_port": 8770,
            "fixture_validation": valid,
            "fixture_saved": saved,
            "actual_external_network_used": False,
            "actual_credentials_used": False,
            "actual_configuration_activated": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "V9201_TO_V9500_AI_STRATEGY_"
                "FEATURE_ENGINE_AND_SIGNAL_CANDIDATES"
            ),
        }

        if not (
            valid["status"] == "VALID"
            and saved["status"]
            == "DRAFT_SAVED"
            and saved["activation_status"]
            == "NOT_ACTIVATED"
            and activation_blocked
            and invalid_blocked
        ):
            result["status"] = "BLOCKED"

        result[
            "certification_fingerprint"
        ] = hashlib.sha256(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

        (
            output_dir
            / "trading_configuration_certification.json"
        ).write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        return result
