from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .checks import check_component, detect_bar_sort_hotfix, runtime_evidence
from .io import append_jsonl, read_json_optional, write_json

class PaperPlatformCertificationService:
    COMPONENTS = [
        (
            "AI_DECISION_ENGINE",
            "release/v491_540_ai_decision_engine/actual/ai_decision_latest.json",
            {"PASS", "INSUFFICIENT_INPUT"},
        ),
        (
            "PORTFOLIO_RISK_INTELLIGENCE",
            "release/v541_590_portfolio_risk_intelligence/actual/portfolio_risk_latest.json",
            {"PASS", "INSUFFICIENT_PORTFOLIO_INPUT"},
        ),
        (
            "APPROVAL_EXECUTION_PLANNING",
            "release/v591_640_approval_execution_planning/actual/execution_planning_latest.json",
            {"PASS", "INSUFFICIENT_INPUT"},
        ),
        (
            "PAPER_ORDER_TICKET_BUILDER",
            "release/v641_690_paper_order_ticket_builder/actual/paper_order_ticket_bundle.json",
            {"PASS", "INSUFFICIENT_INPUT"},
        ),
        (
            "APPROVAL_SUBMISSION_SAFETY",
            "release/v691_780_approval_submission_safety/actual/submission_safety_latest.json",
            {"PASS", "INSUFFICIENT_INPUT"},
        ),
        (
            "PAPER_SUBMIT_ENGINE",
            "release/v781_860_paper_submit_engine/actual/paper_submit_engine_latest.json",
            {"PASS", "INSUFFICIENT_INPUT"},
        ),
        (
            "PAPER_RECOVERY_RETRY",
            "release/v861_940_paper_recovery_retry/actual/paper_recovery_retry_latest.json",
            {"PASS", "INSUFFICIENT_INPUT"},
        ),
    ]

    def evaluate(self, root: Path, output_dir: Path, now=None) -> dict:
        now = now or datetime.now(timezone.utc)
        checks = []
        for name, rel, statuses in self.COMPONENTS:
            path = root / rel
            payload = read_json_optional(path)
            checks.append(check_component(name, path, payload, statuses))

        hotfix = detect_bar_sort_hotfix(root / "actual_market_polling/service.py")
        runtime = runtime_evidence(root)

        blockers = []
        warnings = []
        for item in checks:
            blockers.extend(f"{item['component']}:{x}" for x in item["blockers"])
            warnings.extend(f"{item['component']}:{x}" for x in item["warnings"])

        if hotfix["status"] != "PASS":
            blockers.extend(f"MARKET_BAR_HOTFIX:{x}" for x in hotfix["blockers"])

        runtime_required = (
            runtime["controller_ledger_exists"]
            and runtime["polling_ledger_exists"]
            and runtime["watchdog_summary_exists"]
            and runtime["daily_session_summary_exists"]
        )
        if not runtime_required:
            warnings.append("RUNTIME_EVIDENCE_INCOMPLETE")

        market_validation = {
            "status": "PENDING_MARKET_VALIDATION",
            "reason": "HOTFIX_REQUIRES_NEXT_MARKET_OPEN_LIVE_BAR_FRESHNESS_CHECK",
            "required_checks": [
                "new cycle created after market open",
                "latest bar timestamp near current UTC",
                "timestamp advances across cycles",
                "zero broker writes and zero orders",
            ],
        }

        if blockers:
            certificate_status = "BLOCKED"
        elif runtime_required:
            certificate_status = "CONDITIONALLY_READY"
        else:
            certificate_status = "CONDITIONALLY_READY"

        seed = {
            "checks": checks,
            "hotfix": hotfix,
            "runtime": runtime,
            "market_validation": market_validation,
            "certificate_status": certificate_status,
        }
        fingerprint = hashlib.sha256(
            json.dumps(seed, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V941_TO_V1000_END_TO_END_PAPER_PLATFORM_CERTIFICATION",
            "status": "PASS" if not blockers else "BLOCKED",
            "certificate_status": certificate_status,
            "generated_at": now.isoformat(),
            "certification_fingerprint": fingerprint,
            "component_check_count": len(checks),
            "component_pass_count": sum(1 for x in checks if x["passed"]),
            "component_checks": checks,
            "market_bar_sort_hotfix": hotfix,
            "runtime_evidence": runtime,
            "market_open_validation": market_validation,
            "blockers": blockers,
            "warnings": warnings,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "broker_network_enabled": False,
            "broker_write_enabled": False,
            "paper_submission_enabled": False,
            "live_submission_enabled": False,
            "system_build_status": (
                "FEATURE_COMPLETE_AWAITING_MARKET_VALIDATION"
                if not blockers
                else "CERTIFICATION_BLOCKED"
            ),
            "next_market_validation": "NEXT_MARKET_OPEN_BAR_FRESHNESS_VALIDATION",
            "next_fixed_development": "SYSTEM_BUILD_COMPLETE_AFTER_MARKET_VALIDATION",
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "paper_platform_certification_latest.json", result)
        write_json(
            output_dir / "paper_platform_certificate.json",
            {
                "certificate_status": certificate_status,
                "certification_fingerprint": fingerprint,
                "generated_at": now.isoformat(),
                "system_build_status": result["system_build_status"],
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
                "market_validation_pending": True,
            },
        )
        write_json(
            output_dir / "certification_dashboard.json",
            {
                "status": result["status"],
                "certificate_status": certificate_status,
                "component_pass_count": result["component_pass_count"],
                "component_check_count": len(checks),
                "blocker_count": len(blockers),
                "warning_count": len(warnings),
                "market_validation_status": market_validation["status"],
            },
        )
        append_jsonl(output_dir / "certification_ledger.jsonl", result)
        return result
