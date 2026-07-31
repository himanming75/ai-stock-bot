from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "76.0"
SCHEMA = "v76.0.stable_release_transition_functional_capability_baseline.1"


class CapabilityBaselineError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_of(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CapabilityBaselineError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CapabilityBaselineError(f"invalid JSON: {path}") from exc

    if not isinstance(value, dict):
        raise CapabilityBaselineError("top-level JSON must be an object")
    return value


def validate_config(config: Dict[str, Any]) -> None:
    if config.get("transition_scope") != (
        "STABLE_RELEASE_TRANSITION_AND_FUNCTIONAL_CAPABILITY_BASELINE"
    ):
        raise CapabilityBaselineError("transition_scope invalid")

    required_true = (
        "freeze_audit_evidence_layer",
        "preserve_existing_capabilities",
        "require_deterministic_baseline_id",
        "require_capability_inventory",
        "require_acceptance_gates",
        "require_gap_plan",
        "require_zero_trading_side_effects",
        "require_offline_only",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise CapabilityBaselineError(f"{key} must be true")

    required_false = (
        "network_allowed",
        "broker_connection_allowed",
        "external_order_submission_allowed",
        "paper_order_submission_allowed",
        "live_order_submission_allowed",
        "settlement_mutation_allowed",
        "cash_mutation_allowed",
        "position_mutation_allowed",
        "portfolio_mutation_allowed",
    )
    for key in required_false:
        if config.get(key) is not False:
            raise CapabilityBaselineError(f"{key} must be false")

    required_capabilities = config.get("required_capabilities")
    if not isinstance(required_capabilities, list) or not required_capabilities:
        raise CapabilityBaselineError("required_capabilities must be non-empty")

    seen = set()
    for item in required_capabilities:
        if not isinstance(item, dict):
            raise CapabilityBaselineError("capability definition must be object")
        capability_id = item.get("capability_id")
        if not isinstance(capability_id, str) or not capability_id:
            raise CapabilityBaselineError("capability_id required")
        if capability_id in seen:
            raise CapabilityBaselineError("duplicate capability_id")
        seen.add(capability_id)
        if item.get("required_for_stable_release") is not True:
            raise CapabilityBaselineError(
                "every configured capability must be required"
            )


def validate_inventory(
    inventory: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    if inventory.get("inventory_scope") != "AI_STOCK_BOT_FUNCTIONAL_INVENTORY":
        raise CapabilityBaselineError("inventory_scope invalid")

    capabilities = inventory.get("capabilities")
    if not isinstance(capabilities, list):
        raise CapabilityBaselineError("capabilities must be a list")

    allowed_states = {"COMPLETE", "PARTIAL", "MISSING", "BLOCKED"}
    indexed: Dict[str, Dict[str, Any]] = {}

    for item in capabilities:
        if not isinstance(item, dict):
            raise CapabilityBaselineError("inventory capability must be object")
        capability_id = item.get("capability_id")
        if not isinstance(capability_id, str) or not capability_id:
            raise CapabilityBaselineError("inventory capability_id required")
        if capability_id in indexed:
            raise CapabilityBaselineError(
                f"duplicate inventory capability: {capability_id}"
            )
        state = item.get("state")
        if state not in allowed_states:
            raise CapabilityBaselineError(
                f"invalid state for {capability_id}: {state}"
            )
        evidence = item.get("evidence")
        if not isinstance(evidence, list):
            raise CapabilityBaselineError(
                f"evidence must be a list for {capability_id}"
            )
        indexed[capability_id] = copy.deepcopy(item)

    configured_ids = {
        item["capability_id"] for item in config["required_capabilities"]
    }
    unknown = sorted(set(indexed) - configured_ids)
    if unknown:
        raise CapabilityBaselineError(
            "unknown inventory capabilities: " + ", ".join(unknown)
        )

    return indexed


def build_baseline(
    inventory: Dict[str, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    validate_config(config)
    indexed = validate_inventory(inventory, config)

    normalized: List[Dict[str, Any]] = []
    complete_count = 0
    gap_count = 0

    for sequence, definition in enumerate(
        config["required_capabilities"], 1
    ):
        capability_id = definition["capability_id"]
        observed = indexed.get(
            capability_id,
            {
                "capability_id": capability_id,
                "state": "MISSING",
                "evidence": [],
                "notes": "Not present in submitted inventory.",
            },
        )
        state = observed["state"]
        accepted = state == "COMPLETE"
        if accepted:
            complete_count += 1
        else:
            gap_count += 1

        normalized.append({
            "sequence": sequence,
            "capability_id": capability_id,
            "name": definition["name"],
            "category": definition["category"],
            "required_for_stable_release": True,
            "state": state,
            "accepted": accepted,
            "evidence": copy.deepcopy(observed.get("evidence", [])),
            "notes": observed.get("notes", ""),
            "next_action": (
                "PRESERVE_AND_REGRESSION_TEST"
                if accepted
                else definition["default_next_action"]
            ),
        })

    inventory_hash = sha256_of(normalized)
    audit_anchor = config["audit_evidence_anchor"]
    baseline_id = "SRFCB-" + hashlib.sha256(
        f"{audit_anchor}|{inventory_hash}|{VERSION}".encode("utf-8")
    ).hexdigest()[:16].upper()

    readiness_state = (
        "STABLE_RELEASE_READY"
        if gap_count == 0
        else "FUNCTIONAL_GAPS_REMAIN"
    )

    priority_order = {"BLOCKED": 0, "MISSING": 1, "PARTIAL": 2}
    gap_plan = [
        {
            "priority": 0,
            "capability_id": item["capability_id"],
            "name": item["name"],
            "state": item["state"],
            "recommended_action": item["next_action"],
        }
        for item in normalized
        if not item["accepted"]
    ]
    gap_plan.sort(
        key=lambda item: (
            priority_order.get(item["state"], 9),
            next(
                row["sequence"]
                for row in normalized
                if row["capability_id"] == item["capability_id"]
            ),
        )
    )
    for priority, item in enumerate(gap_plan, 1):
        item["priority"] = priority

    acceptance_gates = [
        {
            "gate_id": "AUDIT_EVIDENCE_LAYER_FROZEN",
            "state": "PASS",
            "details": audit_anchor,
        },
        {
            "gate_id": "EXISTING_CAPABILITIES_PRESERVED",
            "state": "PASS",
            "details": "No source capability is deleted or mutated.",
        },
        {
            "gate_id": "CAPABILITY_INVENTORY_NORMALIZED",
            "state": "PASS",
            "details": f"{len(normalized)} required capabilities evaluated.",
        },
        {
            "gate_id": "ALL_REQUIRED_CAPABILITIES_COMPLETE",
            "state": "PASS" if gap_count == 0 else "PENDING",
            "details": f"{complete_count} complete, {gap_count} gaps.",
        },
        {
            "gate_id": "TRADING_SIDE_EFFECTS_ABSENT",
            "state": "PASS",
            "details": "No orders, settlements, cash, positions, or portfolio mutations.",
        },
        {
            "gate_id": "NETWORK_AND_BROKER_DISABLED",
            "state": "PASS",
            "details": "Offline analysis only.",
        },
    ]

    output = {
        "status": "PASS",
        "decision": (
            "stable_release_transition_functional_capability_baseline_built"
        ),
        "baseline_id": baseline_id,
        "baseline_state": readiness_state,
        "audit_evidence_layer": {
            "state": "FROZEN_AS_BASELINE",
            "anchor_version": audit_anchor,
            "preserved": True,
            "removal_allowed": False,
        },
        "required_capability_count": len(normalized),
        "complete_capability_count": complete_count,
        "functional_gap_count": gap_count,
        "stable_release_ready": gap_count == 0,
        "capability_inventory": normalized,
        "capability_inventory_sha256": inventory_hash,
        "functional_gap_plan": gap_plan,
        "functional_gap_plan_sha256": sha256_of(gap_plan),
        "acceptance_gates": acceptance_gates,
        "acceptance_gates_sha256": sha256_of(acceptance_gates),
        "next_phase": (
            "CREATE_STABLE_RELEASE_CANDIDATE"
            if gap_count == 0
            else "IMPLEMENT_HIGHEST_PRIORITY_FUNCTIONAL_GAP"
        ),
        "next_recommended_capability": (
            None if not gap_plan else gap_plan[0]["capability_id"]
        ),
        "orders_submitted": 0,
        "settlements_created": 0,
        "cash_mutations": 0,
        "position_mutations": 0,
        "portfolio_mutations": 0,
        "network_used": False,
        "broker_connected": False,
        "approved_for_live": False,
        "schema_version": SCHEMA,
        "version": VERSION,
    }
    output["baseline_sha256"] = sha256_of(output)
    return output


def write_outputs(output: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "stable_release_functional_capability_baseline_v76_0.json": output,
        "functional_capability_inventory_v76_0.json": {
            "baseline_id": output["baseline_id"],
            "capability_inventory": output["capability_inventory"],
            "capability_inventory_sha256":
                output["capability_inventory_sha256"],
        },
        "functional_gap_plan_v76_0.json": {
            "baseline_id": output["baseline_id"],
            "functional_gap_plan": output["functional_gap_plan"],
            "functional_gap_plan_sha256":
                output["functional_gap_plan_sha256"],
        },
        "stable_release_acceptance_gates_v76_0.json": {
            "baseline_id": output["baseline_id"],
            "acceptance_gates": output["acceptance_gates"],
            "acceptance_gates_sha256":
                output["acceptance_gates_sha256"],
        },
    }
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        output = build_baseline(
            read_json(Path(args.inventory)),
            read_json(Path(args.config)),
        )
        write_outputs(output, Path(args.output_dir))
        summary_keys = (
            "status",
            "decision",
            "baseline_id",
            "baseline_state",
            "required_capability_count",
            "complete_capability_count",
            "functional_gap_count",
            "stable_release_ready",
            "next_phase",
            "next_recommended_capability",
            "orders_submitted",
            "network_used",
            "approved_for_live",
            "baseline_sha256",
        )
        print(json.dumps(
            {key: output[key] for key in summary_keys},
            indent=2,
            sort_keys=True,
        ))
        return 0
    except (
        CapabilityBaselineError,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(json.dumps({
            "status": "FAIL",
            "decision": "functional_capability_baseline_build_failed",
            "error": str(exc),
            "orders_submitted": 0,
            "settlements_created": 0,
            "cash_mutations": 0,
            "position_mutations": 0,
            "portfolio_mutations": 0,
            "network_used": False,
            "broker_connected": False,
            "approved_for_live": False,
            "version": VERSION,
        }, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
