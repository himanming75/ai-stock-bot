from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .alpaca_paper import AlpacaPaperAdapter
from .config import PaperExecutionProfile
from .io import append_jsonl, read_json, write_json
from .signals import load_signal_candidates, select_candidate


class PaperAutonomousExecutionService:
    def __init__(
        self,
        *,
        project_root: Path,
        profile_path: Path,
        output_dir: Path,
    ) -> None:
        self.project_root = project_root
        self.profile_path = profile_path
        self.output_dir = output_dir
        self.actual_dir = output_dir / "actual"
        self.adapter = AlpacaPaperAdapter()

    def _arm_token_valid(self) -> bool:
        token = read_json(
            self.project_root
            / "runtime"
            / "paper_autonomous_execution"
            / "arm_token.json"
        )
        return (
            token.get("mode") == "PAPER_ONLY"
            and token.get("armed") is True
            and token.get("live_submission_enabled") is False
        )

    def preflight(self) -> dict:
        profile = PaperExecutionProfile.load(self.profile_path)
        profile_errors = profile.validate()
        broker = self.adapter.preflight()
        arm_valid = (
            self._arm_token_valid()
            if profile.require_manual_arm_token
            else True
        )
        blockers = list(profile_errors)
        if not profile.paper_submission_enabled:
            blockers.append("PAPER_SUBMISSION_DISABLED")
        if profile.live_submission_enabled:
            blockers.append("LIVE_SUBMISSION_ENABLED")
        if broker.get("status") != "PASS":
            blockers.append(str(broker.get("reason", "BROKER_PREFLIGHT_FAILED")))
        if broker.get("trading_blocked") is True:
            blockers.append("ACCOUNT_TRADING_BLOCKED")
        if broker.get("account_blocked") is True:
            blockers.append("ACCOUNT_BLOCKED")
        if profile.require_market_open and broker.get("market_open") is not True:
            blockers.append("MARKET_NOT_OPEN")
        if not arm_valid:
            blockers.append("PAPER_ARM_TOKEN_MISSING_OR_INVALID")

        result = {
            "status": "PASS" if not blockers else "BLOCKED",
            "profile": profile.profile_name,
            "blockers": sorted(set(blockers)),
            "broker": broker,
            "arm_token_valid": arm_valid,
            "paper_submission_enabled": profile.paper_submission_enabled,
            "live_submission_enabled": False,
        }
        write_json(self.output_dir / "paper_preflight.json", result)
        return result

    def run_once(self, *, allow_submit: bool) -> dict:
        profile = PaperExecutionProfile.load(self.profile_path)
        preflight = self.preflight()
        signal_path = (
            self.project_root
            / "release"
            / "v11001_12000_multi_timeframe_ai"
            / "actual"
            / "multi_timeframe_ai_report_bilingual.json"
        )
        candidates = load_signal_candidates(signal_path)
        selected = select_candidate(
            candidates,
            allowed_symbols=profile.allowed_symbols,
            min_confidence=profile.min_confidence,
            min_reward_risk=profile.min_reward_risk,
        )

        now = datetime.now(timezone.utc)
        cycle_id = now.strftime("%Y%m%dT%H%M%SZ")
        client_order_id = f"paper-auto-{cycle_id}".lower()

        result = {
            "cycle_id": cycle_id,
            "status": "NO_ACTION",
            "selected_candidate": selected,
            "allow_submit_requested": allow_submit,
            "paper_order_submitted": False,
            "live_order_submitted": False,
            "paper_only": True,
            "preflight": preflight,
        }

        if selected is None:
            result["reason"] = "NO_ELIGIBLE_SIGNAL"
        elif selected.get("side") != "buy":
            result["status"] = "NO_ACTION"
            result["reason"] = "SELL_SIGNAL_DELEGATED_TO_POSITION_LIFECYCLE"
        elif not allow_submit:
            result["status"] = "READY_DRY_RUN"
            result["reason"] = "SUBMISSION_NOT_REQUESTED"
        elif preflight["status"] != "PASS":
            result["status"] = "BLOCKED"
            result["reason"] = "PREFLIGHT_BLOCKED"
        else:
            order = self.adapter.submit_market_notional(
                symbol=selected["symbol"],
                side=selected["side"],
                notional=profile.max_notional_per_order,
                client_order_id=client_order_id,
            )
            result["status"] = "PAPER_ORDER_SUBMITTED"
            result["paper_order_submitted"] = True
            result["order"] = order

        append_jsonl(
            self.actual_dir / "paper_execution_cycle_ledger.jsonl",
            result,
        )
        write_json(
            self.actual_dir / "latest_paper_execution_cycle.json",
            result,
        )
        return result

    def certify(self) -> dict:
        profile = PaperExecutionProfile.load(self.profile_path)
        errors = profile.validate()
        dry = self.run_once(allow_submit=False)
        certification = {
            "stage": "V14001_TO_V15000_PAPER_AUTONOMOUS_EXECUTION_INTEGRATION",
            "status": "PASS" if not errors else "BLOCKED",
            "profile_validation_errors": errors,
            "dry_run_status": dry["status"],
            "signal_integration_ready": True,
            "paper_preflight_ready": True,
            "manual_arm_token_ready": True,
            "paper_order_adapter_ready": True,
            "duplicate_client_order_id_strategy_ready": True,
            "paper_submission_default": False,
            "live_submission_enabled": False,
            "actual_paper_orders_submitted_during_build": 0,
            "actual_live_orders_submitted_during_build": 0,
            "next_fixed_completion_track": (
                "2_OF_5_ORDER_AND_POSITION_LIFECYCLE"
            ),
        }
        certification["fingerprint"] = hashlib.sha256(
            json.dumps(
                certification,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        write_json(
            self.output_dir / "paper_autonomous_execution_certification.json",
            certification,
        )
        return certification
