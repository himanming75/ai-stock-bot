from __future__ import annotations
from pathlib import Path

COMPONENTS = [
    {
        "name": "MARKET_INTELLIGENCE_FEATURE_STORE",
        "path": "release/v1001_1200_ai_market_intelligence/actual/ai_market_intelligence_latest.json",
        "allowed": {"PASS", "BLOCKED"},
        "fixture_capable": False,
        "live_required": True,
        "weight": 14,
    },
    {
        "name": "MULTI_STRATEGY_ENSEMBLE",
        "path": "release/v1201_1400_multi_strategy_ensemble/actual/multi_strategy_ensemble_latest.json",
        "allowed": {"PASS", "BLOCKED"},
        "fixture_capable": False,
        "live_required": True,
        "weight": 14,
    },
    {
        "name": "NEWS_EARNINGS_MACRO",
        "path": "release/v1401_1600_news_earnings_macro/actual/news_earnings_macro_latest.json",
        "allowed": {"PASS"},
        "fixture_capable": True,
        "live_required": False,
        "weight": 12,
    },
    {
        "name": "FUNDAMENTAL_SECTOR_OPTIONS",
        "path": "release/v1601_1800_fundamental_sector_options/actual/fundamental_sector_options_latest.json",
        "allowed": {"PASS"},
        "fixture_capable": True,
        "live_required": False,
        "weight": 14,
    },
    {
        "name": "UNIFIED_AI_DECISION",
        "path": "release/v1801_2000_unified_ai_decision/actual/unified_ai_decision_latest.json",
        "allowed": {"PASS", "PARTIAL_INPUT"},
        "fixture_capable": True,
        "live_required": True,
        "weight": 16,
    },
    {
        "name": "MODEL_VALIDATION",
        "path": "release/v2001_2200_model_validation/actual/model_validation_latest.json",
        "allowed": {"PASS"},
        "fixture_capable": True,
        "live_required": False,
        "weight": 14,
    },
    {
        "name": "MODEL_GOVERNANCE",
        "path": "release/v2201_2400_model_governance/actual/model_governance_latest.json",
        "allowed": {"PASS"},
        "fixture_capable": True,
        "live_required": False,
        "weight": 16,
    },
]

def classify_component(root: Path, spec: dict, payload: dict) -> dict:
    path = root / spec["path"]
    blockers = []
    warnings = []

    if not path.exists():
        blockers.append("FILE_MISSING")
    if not payload:
        blockers.append("PAYLOAD_MISSING_OR_INVALID")

    status = payload.get("status")
    if payload and status not in spec["allowed"]:
        blockers.append(f"STATUS_NOT_ALLOWED:{status}")

    zero_fields = (
        "actual_paper_orders_submitted",
        "actual_live_orders_submitted",
    )
    false_fields = (
        "actual_broker_write_performed",
        "actual_order_submission_performed",
    )
    for field in zero_fields:
        if field in payload and payload.get(field) != 0:
            blockers.append(f"ZERO_ORDER_CONTRACT_FAILED:{field}")
    for field in false_fields:
        if field in payload and payload.get(field) is not False:
            blockers.append(f"SAFETY_CONTRACT_FAILED:{field}")

    input_mode = str(payload.get("input_mode", ""))
    fixture_evidence = (
        "FIXTURE" in input_mode
        or bool(payload.get("fixture_only"))
        or spec["fixture_capable"]
    )

    if spec["live_required"] and status in {"BLOCKED", "PARTIAL_INPUT"}:
        warnings.append("LIVE_OR_COMPLETE_INPUT_VALIDATION_PENDING")

    if spec["fixture_capable"] and fixture_evidence:
        evidence_class = "FIXTURE_VALIDATED"
    elif status == "PASS":
        evidence_class = "IMPLEMENTATION_VALIDATED"
    else:
        evidence_class = "LIVE_VALIDATION_PENDING"

    if blockers:
        readiness = 0.0
    elif status == "PASS":
        readiness = 1.0
    elif status == "PARTIAL_INPUT":
        readiness = 0.72
    elif status == "BLOCKED" and spec["live_required"]:
        readiness = 0.55
    else:
        readiness = 0.25

    return {
        "component": spec["name"],
        "path": str(path),
        "status": status,
        "weight": spec["weight"],
        "live_required": spec["live_required"],
        "fixture_capable": spec["fixture_capable"],
        "evidence_class": evidence_class,
        "readiness_fraction": readiness,
        "passed_contract_checks": not blockers,
        "blockers": blockers,
        "warnings": warnings,
    }
