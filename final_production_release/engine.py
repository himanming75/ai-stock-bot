from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from final_production_release.config import load,validate
from final_production_release.inventory import build as build_inventory
from final_production_release.integration import evaluate as evaluate_integration
from final_production_release.integrity import build as build_integrity
from final_production_release.certificate import build as build_certificate
from final_production_release.bundle import create as create_bundle
from final_production_release.io import write_json,append_jsonl

def evaluate(root:Path,create_release_bundle:bool=True)->dict:
    policy=load(root)
    validation=validate(policy)
    inventory=build_inventory(root)
    integration=evaluate_integration(root)
    integrity=build_integrity(root)
    checks={
      "policy_valid":validation["valid"],
      "all_expected_stages_present":inventory["present_stage_count"]>=int(policy["required_stage_count"]),
      "historical_live_orders_zero":inventory["total_actual_live_orders_submitted"]==0,
      "no_unsafe_stage_flags":not inventory["unsafe_stage_flags"],
      "integration_modules_present":integration["all_modules_present"],
      "required_files_present":integration["all_required_files_present"],
      "final_integrity_present":integrity["all_present"],
      "automatic_strategy_promotion_disabled":policy["automatic_strategy_promotion_enabled"] is False,
      "automatic_order_submission_disabled":policy["automatic_order_submission_enabled"] is False,
      "broker_write_disabled":policy["broker_write_enabled"] is False,
      "live_submission_disabled":policy["live_submission_enabled"] is False,
      "live_network_write_disabled":policy["live_network_write_enabled"] is False,
    }
    failed=[key for key,value in checks.items() if not value]
    certificate=build_certificate(root,inventory,integration,integrity,checks)
    state="V220_FINAL_PRODUCTION_RELEASE_COMPLETE" if not failed else "V220_FINAL_PRODUCTION_RELEASE_REVIEW_REQUIRED"
    observed=datetime.now(timezone.utc).isoformat()
    result={
      "stage":"V220.64",
      "state":state,
      "status":"PASS",
      "observed_at":observed,
      "policy":policy,
      "inventory":inventory,
      "integration":integration,
      "integrity":integrity,
      "checks":checks,
      "failed":failed,
      "certificate":certificate,
      "final_release_ready":not failed,
      "development_complete":not failed,
      "paper_trading_ready":True,
      "live_trading_ready":False,
      "manual_live_activation_required":True,
      "automatic_strategy_promotion_enabled":False,
      "automatic_order_submission_enabled":False,
      "broker_write_enabled":False,
      "live_submission_enabled":False,
      "live_network_write_enabled":False,
      "actual_live_orders_submitted":inventory["total_actual_live_orders_submitted"],
      "next_phase":"POST_V220_PAPER_OPERATION_AND_CONTROLLED_LIVE_QUALIFICATION",
    }
    actual=root/"release/v216_01_to_v220_64/actual"
    write_json(actual/"v220_final_production_result.json",result)
    append_jsonl(actual/"v220_final_release_ledger.jsonl",{
      "observed_at":observed,"state":state,
      "final_release_ready":not failed,
      "present_stage_count":inventory["present_stage_count"],
      "actual_live_orders_submitted":result["actual_live_orders_submitted"],
    })
    if create_release_bundle:
        result["bundle"]=create_bundle(root)
        write_json(actual/"v220_final_production_result.json",result)
    return result
