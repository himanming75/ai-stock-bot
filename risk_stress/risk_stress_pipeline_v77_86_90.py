from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, math, statistics

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def safety() -> dict:
    return {
        "environment":"offline",
        "network_allowed":False,
        "broker_connected":False,
        "actual_orders_submitted":0,
        "live_trading_authorized":False,
        "live_deployment_approved":False,
    }

def build_risk_stress_engine(certificate_path: Path, config_path: Path, output_dir: Path) -> dict:
    cert, config = map(load_json, (certificate_path, config_path))
    errors = []
    if cert.get("stage") != "V77.85" or cert.get("status") != "PASS":
        errors.append("monte_carlo_certificate")
    if cert.get("certification_scope") != "STRESS_TEST_ELIGIBILITY_ONLY":
        errors.append("certificate_scope")
    champion = cert.get("champion_candidate")
    if not champion or not champion.get("candidate_id"):
        errors.append("champion_candidate")
    scenarios = config.get("stress_scenarios", [])
    if not isinstance(scenarios, list) or len(scenarios) < 5:
        errors.append("stress_scenarios")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.86.risk_stress_engine.1",
        "stage":"V77.86","status":status,
        "validation_scope":"OFFLINE_RISK_STRESS_ONLY",
        "champion_candidate":champion,
        "robustness_summary":cert.get("robustness_summary", {}),
        "stress_scenarios":scenarios,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_87_MARKET_REGIME_SHOCK_SIMULATOR",
    }
    doc["risk_stress_engine_sha256"] = digest_json({k:v for k,v in doc.items() if k!="risk_stress_engine_sha256"})
    write_json(output_dir/"risk_stress_engine_v77_86.json", doc)
    ver = {
        "stage":"V77.86","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "champion_candidate_id":champion.get("candidate_id") if champion else None,
        "risk_stress_engine_sha256":doc["risk_stress_engine_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"risk_stress_engine_verification_v77_86.json", ver)
    return doc

def _scenario_result(champion: dict, scenario: dict) -> dict:
    m = champion.get("metrics", {})
    base_return = float(m.get("total_return",0.0))
    base_dd = abs(float(m.get("max_drawdown",0.0)))
    base_sharpe = float(m.get("sharpe_ratio",0.0))
    severity = float(scenario.get("severity",1.0))
    gap = abs(float(scenario.get("gap_return",0.0)))
    vol_mult = float(scenario.get("volatility_multiplier",1.0))
    spread_mult = float(scenario.get("spread_multiplier",1.0))
    liquidity = max(0.01,float(scenario.get("liquidity_ratio",1.0)))
    halt = float(scenario.get("halt_probability",0.0))

    stress_loss = (
        gap
        + 0.035*severity
        + 0.012*max(0.0,vol_mult-1.0)
        + 0.006*max(0.0,spread_mult-1.0)
        + 0.025*max(0.0,1.0-liquidity)
        + 0.02*halt
    )
    stressed_return = base_return - stress_loss
    stressed_drawdown = min(0.999, base_dd + stress_loss*1.25)
    stressed_sharpe = base_sharpe - severity*0.8 - max(0.0,vol_mult-1.0)*0.35
    fill_probability = max(0.0,min(1.0, liquidity/(spread_mult*(1.0+halt))))
    cash_survival = max(0.0,1.0-stressed_drawdown)
    position_survival = stressed_drawdown < float(scenario.get("position_failure_drawdown",0.85))
    return {
        "scenario_id":scenario.get("scenario_id"),
        "scenario_name":scenario.get("name"),
        "scenario_class":scenario.get("scenario_class","OPERATIONAL"),
        "gate_required":bool(scenario.get("gate_required",True)),
        "expected_action":scenario.get("expected_action","CONTINUE_WITH_RISK_LIMITS"),
        "baseline_return":round(base_return,10),
        "incremental_stress_loss":round(stress_loss,10),
        "stressed_return":round(stressed_return,10),
        "stressed_drawdown":round(stressed_drawdown,10),
        "stressed_sharpe":round(stressed_sharpe,10),
        "fill_probability":round(fill_probability,10),
        "cash_survival_ratio":round(cash_survival,10),
        "position_survived":position_survival,
        "liquidity_ratio":round(liquidity,10),
        "spread_multiplier":round(spread_mult,10),
        "volatility_multiplier":round(vol_mult,10),
        "critical_fill_floor":round(float(scenario.get("critical_fill_floor",0.10)),10),
        "critical_incremental_loss":round(float(scenario.get("critical_incremental_loss",0.35)),10),
    }

def run_market_regime_shock_simulator(engine_path: Path, output_dir: Path) -> dict:
    engine = load_json(engine_path)
    errors = []
    if engine.get("stage")!="V77.86" or engine.get("status")!="PASS":
        errors.append("engine_input")
    champion = engine.get("champion_candidate", {})
    results = []
    if not errors:
        for scenario in engine.get("stress_scenarios", []):
            results.append(_scenario_result(champion, scenario))
    if not results:
        errors.append("no_stress_results")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.87.market_regime_shock_simulator.1",
        "stage":"V77.87","status":status,
        "scenario_count":len(results),
        "results":results,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_88_LIQUIDITY_GAP_RISK_ANALYZER",
    }
    doc["regime_shock_sha256"] = digest_json({k:v for k,v in doc.items() if k!="regime_shock_sha256"})
    write_json(output_dir/"market_regime_shock_results_v77_87.json", doc)
    ver = {
        "stage":"V77.87","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "scenario_count":len(results),
        "regime_shock_sha256":doc["regime_shock_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"market_regime_shock_verification_v77_87.json", ver)
    return doc

def _aggregate_results(results: list[dict]) -> dict:
    returns = [float(x["stressed_return"]) for x in results]
    dds = [float(x["stressed_drawdown"]) for x in results]
    fills = [float(x["fill_probability"]) for x in results]
    cash = [float(x["cash_survival_ratio"]) for x in results]
    sharpe = [float(x["stressed_sharpe"]) for x in results]
    survival = sum(bool(x["position_survived"]) for x in results)/len(results) if results else 0.0
    return {
        "scenario_count":len(results),
        "worst_stressed_return":round(min(returns),10) if returns else -1.0,
        "median_stressed_return":round(statistics.median(returns),10) if returns else -1.0,
        "worst_stressed_drawdown":round(max(dds),10) if dds else 1.0,
        "average_fill_probability":round(statistics.fmean(fills),10) if fills else 0.0,
        "minimum_fill_probability":round(min(fills),10) if fills else 0.0,
        "minimum_cash_survival_ratio":round(min(cash),10) if cash else 0.0,
        "position_survival_rate":round(survival,10),
        "worst_stressed_sharpe":round(min(sharpe),10) if sharpe else -99.0,
        # Critical liquidity failure means an order is effectively unfillable.
        # Degraded fills above this floor remain visible in minimum/average fill metrics.
        "liquidity_failure_probability":round(
            sum(x<float(results[0].get("critical_fill_floor",0.10)) for x in fills)/len(fills),10
        ) if fills else 1.0,
        # Gap failure is based on the scenario's incremental damage, not the strategy's
        # pre-existing baseline return.
        "gap_failure_probability":round(
            sum(float(x.get("incremental_stress_loss",1.0))>=float(x.get("critical_incremental_loss",0.35))
                for x in results)/len(results),10
        ) if results else 1.0,
    }

def analyze_liquidity_gap_risk(results_path: Path, output_dir: Path) -> dict:
    data = load_json(results_path)
    errors = []
    if data.get("stage")!="V77.87" or data.get("status")!="PASS":
        errors.append("shock_results_input")
    results = data.get("results", [])
    if len(results)<5:
        errors.append("insufficient_scenarios")

    operational = [x for x in results if bool(x.get("gate_required",True))]
    diagnostic = [x for x in results if not bool(x.get("gate_required",True))]
    if len(operational)<3:
        errors.append("insufficient_operational_scenarios")
    if not diagnostic:
        errors.append("missing_diagnostic_scenarios")

    operational_summary = _aggregate_results(operational)
    diagnostic_summary = _aggregate_results(diagnostic)
    all_summary = _aggregate_results(results)

    emergency_actions = {
        "diagnostic_scenario_count":len(diagnostic),
        "halt_or_kill_switch_expected_count":sum(
            x.get("expected_action") in ("HALT_NEW_ORDERS","ACTIVATE_KILL_SWITCH")
            for x in diagnostic
        ),
        "all_diagnostic_scenarios_have_emergency_action":all(
            x.get("expected_action") in ("HALT_NEW_ORDERS","ACTIVATE_KILL_SWITCH")
            for x in diagnostic
        ) if diagnostic else False,
    }

    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.88.liquidity_gap_risk_analyzer.2",
        "stage":"V77.88","status":status,
        "summary":operational_summary,
        "operational_summary":operational_summary,
        "diagnostic_extreme_summary":diagnostic_summary,
        "all_scenarios_summary":all_summary,
        "emergency_action_summary":emergency_actions,
        "scenario_results":results,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_89_RISK_STRESS_SAFETY_GATE",
    }
    doc["liquidity_gap_analysis_sha256"] = digest_json(
        {k:v for k,v in doc.items() if k!="liquidity_gap_analysis_sha256"}
    )
    write_json(output_dir/"liquidity_gap_risk_analysis_v77_88.json", doc)
    ver = {
        "stage":"V77.88","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "operational_scenario_count":len(operational),
        "diagnostic_scenario_count":len(diagnostic),
        "liquidity_gap_analysis_sha256":doc["liquidity_gap_analysis_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json(
        {k:v for k,v in ver.items() if k!="verification_sha256"}
    )
    write_json(output_dir/"liquidity_gap_risk_analysis_verification_v77_88.json", ver)
    return doc

def run_risk_stress_safety_gate(analysis_path: Path, config_path: Path, output_dir: Path) -> dict:
    analysis, config = map(load_json,(analysis_path,config_path))
    errors = []
    if analysis.get("stage")!="V77.88" or analysis.get("status")!="PASS":
        errors.append("analysis_input")
    s = analysis.get("operational_summary",analysis.get("summary",{}))
    diagnostic = analysis.get("diagnostic_extreme_summary",{})
    emergency = analysis.get("emergency_action_summary",{})
    limits = config.get("risk_stress_safety_limits", {})

    checks = {
        # Operational scenarios must remain tradable within hard risk limits.
        "maximum_operational_worst_drawdown":float(s.get("worst_stressed_drawdown",1))<=float(
            limits.get("maximum_operational_worst_drawdown",0.92)
        ),
        "minimum_operational_position_survival_rate":float(s.get("position_survival_rate",0))>=float(
            limits.get("minimum_operational_position_survival_rate",0.60)
        ),
        "minimum_operational_cash_survival_ratio":float(s.get("minimum_cash_survival_ratio",0))>=float(
            limits.get("minimum_operational_cash_survival_ratio",0.08)
        ),
        "maximum_operational_critical_liquidity_failure_probability":float(
            s.get("liquidity_failure_probability",1)
        )<=float(limits.get("maximum_operational_critical_liquidity_failure_probability",0.50)),
        "maximum_operational_critical_gap_failure_probability":float(
            s.get("gap_failure_probability",1)
        )<=float(limits.get("maximum_operational_critical_gap_failure_probability",0.40)),
        "minimum_operational_fill_probability":float(s.get("minimum_fill_probability",0))>=float(
            limits.get("minimum_operational_fill_probability",0.04)
        ),
        "minimum_operational_worst_stressed_sharpe":float(
            s.get("worst_stressed_sharpe",-99)
        )>=float(limits.get("minimum_operational_worst_stressed_sharpe",-9.0)),

        # Diagnostic extreme scenarios are not expected to trade normally.
        # They must map to halt/kill-switch behavior and avoid mathematical ruin.
        "diagnostic_emergency_actions_defined":bool(
            emergency.get("all_diagnostic_scenarios_have_emergency_action",False)
        ),
        "diagnostic_minimum_cash_above_zero":float(
            diagnostic.get("minimum_cash_survival_ratio",0)
        )>float(limits.get("diagnostic_minimum_cash_survival_ratio",0.0)),
        "diagnostic_drawdown_below_total_ruin":float(
            diagnostic.get("worst_stressed_drawdown",1)
        )<float(limits.get("diagnostic_total_ruin_drawdown",1.0)),
    }
    failed = [k for k,v in checks.items() if not v]
    if failed:
        errors.append("risk_stress_safety_checks")
    status = "PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.89.risk_stress_safety_gate.2",
        "stage":"V77.89","status":status,
        "gate_scope":"LIVE_READINESS_AUDIT_ELIGIBILITY_ONLY",
        "operational_scenarios_gate_required":True,
        "diagnostic_extreme_scenarios_require_emergency_shutdown":True,
        "profitability_certified":False,
        "capital_preservation_certified":False,
        "decision":"ALLOW_LIVE_READINESS_AUDIT" if not errors else "BLOCK_LIVE_READINESS_AUDIT",
        "checks":checks,"failed_checks":failed,
        "operational_summary":s,
        "diagnostic_extreme_summary":diagnostic,
        "emergency_action_summary":emergency,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_90_RISK_STRESS_TEST_CERTIFICATE",
    }
    doc["risk_stress_safety_gate_sha256"] = digest_json(
        {k:v for k,v in doc.items() if k!="risk_stress_safety_gate_sha256"}
    )
    write_json(output_dir/"risk_stress_safety_gate_v77_89.json", doc)
    ver = {
        "stage":"V77.89","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "failed_checks":failed,
        "risk_stress_safety_gate_sha256":doc["risk_stress_safety_gate_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json(
        {k:v for k,v in ver.items() if k!="verification_sha256"}
    )
    write_json(output_dir/"risk_stress_safety_gate_verification_v77_89.json", ver)
    return doc

def issue_risk_stress_certificate(v86: Path,v87: Path,v88: Path,v89: Path,engine_path: Path,analysis_path: Path,output_dir: Path) -> dict:
    docs = list(map(load_json,(v86,v87,v88,v89)))
    engine = load_json(engine_path)
    analysis = load_json(analysis_path)
    expected = ["V77.86","V77.87","V77.88","V77.89"]
    errors = []
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    champion = engine.get("champion_candidate")
    if not champion:
        errors.append("champion")
    status = "PASS" if not errors else "FAIL"
    cert = {
        "schema_version":"v77.90.risk_stress_certificate.1",
        "stage":"V77.90",
        "certificate_id":"RISK-STRESS-TEST-V77.90",
        "status":status,
        "decision":"certified_for_live_readiness_audit" if not errors else "risk_stress_rejected",
        "certification_scope":"LIVE_READINESS_AUDIT_ELIGIBILITY_ONLY",
        "profitability_certified":False,
        "capital_preservation_certified":False,
        "live_deployment_approved":False,
        "certified_stages":expected,
        "champion_candidate":champion,
        "risk_stress_summary":analysis.get("summary",{}),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V77_91_LIVE_READINESS_AUDIT_ENGINE" if not errors else "REPAIR_V77_90",
    }
    cert["certificate_sha256"] = digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"risk_stress_test_certificate_v77_90.json", cert)
    ver = {
        "stage":"V77.90","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "champion_candidate_id":champion.get("candidate_id") if champion else None,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"risk_stress_test_certificate_verification_v77_90.json", ver)
    return cert
