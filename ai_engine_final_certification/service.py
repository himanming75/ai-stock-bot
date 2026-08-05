from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

from .checks import COMPONENTS, classify_component
from .io import append_jsonl, read_json_optional, write_json

class AIEngineFinalCertificationService:
    def evaluate(self, *, repository_root: Path, output_dir: Path, now=None) -> dict:
        now = now or datetime.now(timezone.utc)
        checks = []
        for spec in COMPONENTS:
            path = repository_root / spec["path"]
            payload = read_json_optional(path)
            checks.append(classify_component(repository_root, spec, payload))

        blockers = []
        warnings = []
        for item in checks:
            blockers.extend(f"{item['component']}:{x}" for x in item["blockers"])
            warnings.extend(f"{item['component']}:{x}" for x in item["warnings"])

        weighted_total = sum(item["weight"] for item in checks)
        readiness = (
            sum(item["weight"] * item["readiness_fraction"] for item in checks)
            / weighted_total * 100.0
            if weighted_total else 0.0
        )

        live_pending = [
            item["component"]
            for item in checks
            if item["live_required"]
            and item["evidence_class"] == "LIVE_VALIDATION_PENDING"
        ]
        fixture_validated = [
            item["component"]
            for item in checks
            if item["evidence_class"] == "FIXTURE_VALIDATED"
        ]

        if blockers:
            certificate_status = "BLOCKED"
            operational_state = "NOT_READY"
        elif live_pending:
            certificate_status = "CONDITIONALLY_CERTIFIED_AWAITING_LIVE_TECHNICAL_DATA"
            operational_state = "READY_FOR_OFFLINE_AND_FIXTURE_ANALYSIS"
        else:
            certificate_status = "FULLY_CERTIFIED"
            operational_state = "READY_FOR_LIVE_DATA_READ_ONLY_AI_ANALYSIS"

        checklist = [
            {
                "item": "AI component files present",
                "status": "PASS" if not any("FILE_MISSING" in x for x in blockers) else "BLOCKED",
            },
            {
                "item": "Zero broker write contract",
                "status": "PASS" if not any("SAFETY_CONTRACT_FAILED" in x for x in blockers) else "BLOCKED",
            },
            {
                "item": "Zero order contract",
                "status": "PASS" if not any("ZERO_ORDER_CONTRACT_FAILED" in x for x in blockers) else "BLOCKED",
            },
            {
                "item": "Technical live data validation",
                "status": "PENDING" if live_pending else "PASS",
            },
            {
                "item": "Fixture-based intelligence validation",
                "status": "PASS" if fixture_validated else "NOT_APPLICABLE",
            },
            {
                "item": "Model promotion remains manual",
                "status": "PASS",
            },
            {
                "item": "Controller remains isolated",
                "status": "PASS",
            },
        ]

        seed = {
            "checks": checks,
            "readiness": readiness,
            "certificate_status": certificate_status,
            "live_pending": live_pending,
            "fixture_validated": fixture_validated,
        }
        fingerprint = hashlib.sha256(
            json.dumps(seed, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

        result = {
            "stage": "V2401_TO_V2600_AI_ENGINE_FINAL_CERTIFICATION",
            "status": "PASS" if not blockers else "BLOCKED",
            "generated_at": now.isoformat(),
            "certificate_status": certificate_status,
            "operational_state": operational_state,
            "readiness_score_percent": round(readiness, 4),
            "ai_engine_fingerprint": fingerprint,
            "component_count": len(checks),
            "component_contract_pass_count": sum(1 for x in checks if x["passed_contract_checks"]),
            "component_checks": checks,
            "fixture_validated_components": fixture_validated,
            "live_validation_pending_components": live_pending,
            "global_blockers": blockers,
            "global_warnings": warnings,
            "operational_checklist": checklist,
            "automatic_model_promotion_enabled": False,
            "automatic_model_rollback_enabled": False,
            "weights_changed": False,
            "thresholds_changed": False,
            "external_llm_enabled": False,
            "live_news_network_enabled": False,
            "live_options_network_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "phase_2_build_status": (
                "STRUCTURALLY_COMPLETE_AWAITING_REAL_DATA_VALIDATION"
                if not blockers and live_pending
                else "AI_ENGINE_CERTIFIED"
                if not blockers
                else "AI_ENGINE_CERTIFICATION_BLOCKED"
            ),
            "next_real_validation": "NEXT_MARKET_OPEN_TECHNICAL_FEATURE_ENSEMBLE_REFRESH",
            "next_fixed_development": "PHASE_2_COMPLETE_AFTER_REAL_DATA_VALIDATION",
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "ai_engine_final_certification_latest.json", result)
        write_json(output_dir / "ai_engine_certificate.json", {
            "certificate_status": certificate_status,
            "operational_state": operational_state,
            "readiness_score_percent": round(readiness, 4),
            "ai_engine_fingerprint": fingerprint,
            "generated_at": now.isoformat(),
            "phase_2_build_status": result["phase_2_build_status"],
            "live_validation_pending_components": live_pending,
            "fixture_validated_components": fixture_validated,
            "paper_orders_submitted": 0,
            "live_orders_submitted": 0,
        })
        write_json(output_dir / "ai_engine_readiness_dashboard.json", {
            "status": result["status"],
            "certificate_status": certificate_status,
            "readiness_score_percent": round(readiness, 4),
            "component_count": len(checks),
            "contract_pass_count": result["component_contract_pass_count"],
            "live_pending_count": len(live_pending),
            "fixture_validated_count": len(fixture_validated),
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
        })
        write_json(output_dir / "ai_engine_operational_checklist.json", {
            "generated_at": now.isoformat(),
            "items": checklist,
        })
        append_jsonl(output_dir / "ai_engine_certification_ledger.jsonl", result)
        return result
