from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from dynamic_live_risk.io import load_json,write_json,append_jsonl,digest
from dynamic_live_risk.sizing import calculate
from dynamic_live_risk.budget import allocate
from dynamic_live_risk.exposure import evaluate as evaluate_exposure
from dynamic_live_risk.loss_limits import evaluate as evaluate_losses
from dynamic_live_risk.concentration import evaluate as evaluate_concentration
from dynamic_live_risk.certificate import build as build_certificate

def evaluate(root:Path)->dict[str,Any]:
    policy=load_json(root/"release/v134_01_to_v136_64/input/dynamic_live_risk_policy.json")
    fixture=load_json(root/"release/v134_01_to_v136_64/input/dynamic_live_risk_fixture.json")
    source=load_json(root/"release/v131_01_to_v133_64/actual/controlled_micro_live_result.json")
    actual=root/"release/v134_01_to_v136_64/actual"

    ready=source.get("state") in {
        "CONTROLLED_MICRO_LIVE_EXECUTION_REVIEW_COMPLETE",
        "CONTROLLED_MICRO_LIVE_EXECUTION_REVIEW_REQUIRED",
    }
    candidate=dict(source.get("candidate",{})) if ready else {}
    if not ready:
        body={
            "stage":"V136.64","stage_range":"V134.01-V136.64",
            "state":"DYNAMIC_LIVE_RISK_SOURCE_REQUIRED","status":"PASS",
            "actual_live_orders_submitted":0,
            "next_phase":"V137_01_TO_V139_64_AUTONOMOUS_TRADING_ORCHESTRATOR",
        }
        body["result_sha256"]=digest(body)
        write_json(actual/"dynamic_live_risk_result.json",body)
        return body

    if candidate:
        candidate.setdefault("reference_price",fixture.get("reference_prices",{}).get(candidate.get("symbol"),candidate.get("estimated_notional",0)))
        candidate.setdefault("volatility_pct",fixture.get("volatility_pct",{}).get(candidate.get("symbol"),policy.get("default_volatility_pct",1.5)))
        candidate.setdefault("stop_distance_pct",fixture.get("stop_distance_pct",{}).get(candidate.get("symbol"),policy.get("default_stop_distance_pct",2.0)))

    account=fixture.get("account",{})
    positions=fixture.get("positions",[])
    sizing=calculate(candidate,account,policy) if candidate else {}
    budget=allocate(candidate,sizing,policy) if candidate else {"budget_passed":False}
    exposure=evaluate_exposure(account,positions,sizing,policy) if candidate else {"passed":False}
    losses=evaluate_losses(account,policy)
    concentration=evaluate_concentration(candidate,positions,policy) if candidate else {"passed":False}

    checks={
        "candidate_present":bool(candidate),
        "final_quantity_positive":int(sizing.get("final_quantity",0))>0,
        "risk_budget_passed":budget.get("budget_passed") is True,
        "exposure_passed":exposure.get("passed") is True,
        "loss_limits_passed":losses.get("passed") is True,
        "concentration_passed":concentration.get("passed") is True,
        "live_network_disabled":policy.get("live_network_enabled") is False,
        "live_submission_disabled":policy.get("live_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    risk_passed=not failed
    state="DYNAMIC_LIVE_RISK_ENGINE_READY" if risk_passed else "DYNAMIC_LIVE_RISK_REVIEW_REQUIRED"
    observed=datetime.now(timezone.utc).isoformat()
    certificate=build_certificate(risk_passed,{
        "candidate":candidate,"sizing":sizing,"budget":budget,
        "exposure":exposure,"losses":losses,"concentration":concentration,
    })
    body={
        "stage":"V136.64","stage_range":"V134.01-V136.64",
        "state":state,"status":"PASS","observed_at":observed,
        "risk_assessment_id":digest({
            "candidate":candidate,
            "account":account,
            "policy_version":policy.get("policy_version"),
        })[:24],
        "candidate":candidate,
        "account_snapshot":account,
        "position_snapshot":positions,
        "dynamic_sizing":sizing,
        "risk_budget":budget,
        "exposure_control":exposure,
        "loss_limits":losses,
        "concentration_control":concentration,
        "risk_gate":{"checks":checks,"failed":failed,"passed":risk_passed},
        "risk_certificate":certificate,
        "execution_authorized":False,
        "live_network_enabled":False,
        "live_submission_enabled":False,
        "real_live_network_attempted":False,
        "real_live_submission_attempted":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V137_01_TO_V139_64_AUTONOMOUS_TRADING_ORCHESTRATOR",
    }
    body["result_sha256"]=digest(body)
    write_json(actual/"dynamic_live_risk_result.json",body)
    write_json(actual/"dynamic_position_sizing.json",sizing)
    write_json(actual/"risk_budget_report.json",budget)
    write_json(actual/"exposure_control_report.json",exposure)
    write_json(actual/"loss_limit_report.json",losses)
    write_json(actual/"concentration_report.json",concentration)
    write_json(actual/"dynamic_live_risk_certificate.json",certificate)
    append_jsonl(actual/"dynamic_live_risk_ledger.jsonl",{
        "observed_at":observed,
        "risk_assessment_id":body["risk_assessment_id"],
        "state":state,
        "risk_passed":risk_passed,
        "final_quantity":sizing.get("final_quantity",0),
        "actual_live_orders_submitted":0,
    })
    return body
