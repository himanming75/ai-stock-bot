from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, math, statistics

class PerformanceAnalyticsError(ValueError):
    pass

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def safety() -> dict:
    return {
        "environment":"offline",
        "network_allowed":False,
        "broker_connected":False,
        "actual_orders_submitted":0,
        "live_trading_authorized":False,
    }

def finite_number(v: Any) -> bool:
    return isinstance(v, (int,float)) and math.isfinite(float(v))

def build_performance_analytics(reconciliation_path: Path, output_dir: Path) -> dict:
    rec = load_json(reconciliation_path)
    if rec.get("stage") != "V77.56" or rec.get("status") != "PASS":
        raise PerformanceAnalyticsError("invalid V77.56 reconciliation input")

    equity_after = float(rec.get("portfolio_equity_after", 0.0))
    cash_before = float(rec.get("cash_before", 0.0))
    positions_before_value = float(rec.get("position_market_value_after", 0.0))
    inferred_equity_before = cash_before + positions_before_value
    realized = float(rec.get("realized_pnl_after", 0.0))
    trade_pnl = round(realized - float(rec.get("realized_pnl_before", 0.0)), 2)

    if inferred_equity_before <= 0:
        raise PerformanceAnalyticsError("equity before must be positive")

    total_return = round((equity_after / inferred_equity_before) - 1.0, 10)
    trade_count = 1
    win_count = 1 if trade_pnl > 0 else 0
    loss_count = 1 if trade_pnl < 0 else 0
    flat_count = 1 if trade_pnl == 0 else 0
    win_rate = round(win_count / trade_count, 10)

    equity_curve = [
        {"sequence":0,"equity":round(inferred_equity_before,2),"event":"pre_reconciliation"},
        {"sequence":1,"equity":round(equity_after,2),"event":"post_reconciliation"},
    ]
    periodic_returns = [total_return]

    doc = {
        "schema_version":"v77.61.performance_analytics_engine.1",
        "stage":"V77.61","status":"PASS",
        "trade_count":trade_count,
        "win_count":win_count,"loss_count":loss_count,"flat_count":flat_count,
        "win_rate":win_rate,
        "trade_pnl":trade_pnl,
        "equity_before":round(inferred_equity_before,2),
        "equity_after":round(equity_after,2),
        "total_return":total_return,
        "periodic_returns":periodic_returns,
        "equity_curve":equity_curve,
        "source_portfolio_reconciliation_sha256":rec.get("portfolio_reconciliation_sha256"),
        "actual_orders_submitted":0,"safety":safety(),
        "next_phase":"V77_62_RETURN_ATTRIBUTION_LEDGER",
    }
    doc["performance_analytics_sha256"] = digest_json({k:v for k,v in doc.items() if k!="performance_analytics_sha256"})
    ver = {
        "schema_version":"v77.61.performance_analytics_verification.1",
        "stage":"V77.61","status":"PASS","verified":True,
        "error_count":0,"errors":[],
        "performance_analytics_sha256":doc["performance_analytics_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"performance_analytics_v77_61.json", doc)
    write_json(output_dir/"performance_analytics_verification_v77_61.json", ver)
    return doc

def build_return_attribution(performance_path: Path, reconciliation_path: Path, output_dir: Path) -> dict:
    perf = load_json(performance_path)
    rec = load_json(reconciliation_path)
    errors=[]
    if perf.get("stage")!="V77.61" or perf.get("status")!="PASS":
        errors.append("invalid_performance_input")
    if rec.get("stage")!="V77.56" or rec.get("status")!="PASS":
        errors.append("invalid_reconciliation_input")

    symbol = rec.get("symbol")
    trade_pnl = float(perf.get("trade_pnl",0.0))
    direction = rec.get("side")
    contributions = [{
        "symbol":symbol,
        "direction":direction,
        "realized_pnl_contribution":round(trade_pnl,2),
        "return_contribution":float(perf.get("total_return",0.0)),
    }]
    contribution_total = round(sum(x["realized_pnl_contribution"] for x in contributions),2)
    if abs(contribution_total-trade_pnl)>0.01:
        errors.append("attribution_total_mismatch")
    status="PASS" if not errors else "FAIL"
    doc = {
        "schema_version":"v77.62.return_attribution_ledger.1",
        "stage":"V77.62","status":status,
        "entry_count":len(contributions),
        "contributions":contributions,
        "attributed_pnl_total":contribution_total,
        "performance_trade_pnl":round(trade_pnl,2),
        "attribution_delta":round(contribution_total-trade_pnl,2),
        "error_count":len(errors),"errors":errors,
        "source_performance_analytics_sha256":perf.get("performance_analytics_sha256"),
        "source_portfolio_reconciliation_sha256":rec.get("portfolio_reconciliation_sha256"),
        "actual_orders_submitted":0,"safety":safety(),
        "next_phase":"V77_63_RISK_METRICS_ENGINE",
    }
    doc["return_attribution_sha256"] = digest_json({k:v for k,v in doc.items() if k!="return_attribution_sha256"})
    ver = {
        "schema_version":"v77.62.return_attribution_verification.1",
        "stage":"V77.62","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "return_attribution_sha256":doc["return_attribution_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"] = digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"return_attribution_ledger_v77_62.json", doc)
    write_json(output_dir/"return_attribution_ledger_verification_v77_62.json", ver)
    return doc

def _max_drawdown(equity_curve: list[dict]) -> float:
    peak = None
    max_dd = 0.0
    for point in equity_curve:
        equity=float(point["equity"])
        peak=equity if peak is None else max(peak,equity)
        if peak>0:
            dd=(peak-equity)/peak
            max_dd=max(max_dd,dd)
    return round(max_dd,10)

def build_risk_metrics(performance_path: Path, output_dir: Path) -> dict:
    perf=load_json(performance_path)
    if perf.get("stage")!="V77.61" or perf.get("status")!="PASS":
        raise PerformanceAnalyticsError("invalid V77.61 performance input")
    returns=[float(x) for x in perf.get("periodic_returns",[])]
    avg_return=statistics.fmean(returns) if returns else 0.0
    volatility=statistics.pstdev(returns) if len(returns)>1 else 0.0
    downside=[min(x,0.0) for x in returns]
    downside_dev=(sum(x*x for x in downside)/len(downside))**0.5 if downside else 0.0
    sharpe=0.0 if volatility==0 else avg_return/volatility
    sortino=0.0 if downside_dev==0 else avg_return/downside_dev
    max_dd=_max_drawdown(perf.get("equity_curve",[]))
    calmar=0.0 if max_dd==0 else avg_return/max_dd
    pnl=float(perf.get("trade_pnl",0.0))
    gross_profit=max(pnl,0.0)
    gross_loss=abs(min(pnl,0.0))
    profit_factor=(gross_profit/gross_loss) if gross_loss>0 else (999999.0 if gross_profit>0 else 0.0)
    expectancy=pnl/max(int(perf.get("trade_count",1)),1)

    metrics={
        "average_return":round(avg_return,10),
        "volatility":round(volatility,10),
        "sharpe_ratio":round(sharpe,10),
        "sortino_ratio":round(sortino,10),
        "max_drawdown":max_dd,
        "calmar_ratio":round(calmar,10),
        "profit_factor":round(profit_factor,10),
        "win_rate":float(perf.get("win_rate",0.0)),
        "expectancy":round(expectancy,10),
    }
    if not all(finite_number(v) for v in metrics.values()):
        raise PerformanceAnalyticsError("non-finite metric")
    doc={
        "schema_version":"v77.63.risk_metrics_engine.1",
        "stage":"V77.63","status":"PASS",
        "metrics":metrics,
        "source_performance_analytics_sha256":perf.get("performance_analytics_sha256"),
        "actual_orders_submitted":0,"safety":safety(),
        "next_phase":"V77_64_PERFORMANCE_SAFETY_GATE",
    }
    doc["risk_metrics_sha256"]=digest_json({k:v for k,v in doc.items() if k!="risk_metrics_sha256"})
    ver={
        "schema_version":"v77.63.risk_metrics_verification.1",
        "stage":"V77.63","status":"PASS","verified":True,
        "error_count":0,"errors":[],
        "risk_metrics_sha256":doc["risk_metrics_sha256"],
        "next_phase":doc["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"risk_metrics_v77_63.json",doc)
    write_json(output_dir/"risk_metrics_verification_v77_63.json",ver)
    return doc

def run_performance_safety_gate(performance_path: Path, attribution_path: Path, risk_path: Path, output_dir: Path) -> dict:
    perf=load_json(performance_path);attr=load_json(attribution_path);risk=load_json(risk_path);errors=[]
    if [perf.get("stage"),attr.get("stage"),risk.get("stage")]!=["V77.61","V77.62","V77.63"]:
        errors.append("stage_chain")
    if any(x.get("status")!="PASS" for x in (perf,attr,risk)):
        errors.append("upstream_status")
    if float(perf.get("equity_before",0))<=0 or float(perf.get("equity_after",0))<0:
        errors.append("invalid_equity")
    if abs(float(attr.get("attribution_delta",0.0)))>0.01:
        errors.append("attribution_delta")
    metric_values=list(risk.get("metrics",{}).values())
    if not metric_values or not all(finite_number(v) for v in metric_values):
        errors.append("non_finite_metrics")
    if any(x.get("actual_orders_submitted")!=0 for x in (perf,attr,risk)):
        errors.append("actual_order_submission")
    status="PASS" if not errors else "FAIL"
    gate={
        "schema_version":"v77.64.performance_safety_gate.1",
        "stage":"V77.64","status":status,
        "decision":"ALLOW_PERFORMANCE_RESULT" if not errors else "BLOCK_PERFORMANCE_RESULT",
        "error_count":len(errors),"errors":errors,
        "source_performance_analytics_sha256":perf.get("performance_analytics_sha256"),
        "source_return_attribution_sha256":attr.get("return_attribution_sha256"),
        "source_risk_metrics_sha256":risk.get("risk_metrics_sha256"),
        "actual_orders_submitted":0,"safety":safety(),
        "next_phase":"V77_65_PERFORMANCE_AUDIT_CERTIFICATE",
    }
    gate["performance_safety_gate_sha256"]=digest_json({k:v for k,v in gate.items() if k!="performance_safety_gate_sha256"})
    ver={
        "schema_version":"v77.64.performance_safety_gate_verification.1",
        "stage":"V77.64","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "performance_safety_gate_sha256":gate["performance_safety_gate_sha256"],
        "next_phase":gate["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"performance_safety_gate_v77_64.json",gate)
    write_json(output_dir/"performance_safety_gate_verification_v77_64.json",ver)
    return gate

def issue_performance_certificate(v61: Path,v62: Path,v63: Path,v64: Path,output_dir: Path)->dict:
    docs=[load_json(x) for x in (v61,v62,v63,v64)]
    expected=["V77.61","V77.62","V77.63","V77.64"];errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v77.65.performance_audit_certificate.1",
        "stage":"V77.65",
        "certificate_id":"PERFORMANCE-AUDIT-V77.65",
        "status":status,
        "decision":"performance_certified" if not errors else "performance_rejected",
        "certified_stages":expected,
        "error_count":len(errors),"errors":errors,
        "actual_orders_submitted":0,"safety":safety(),
        "next_phase":"V77_66_REPORTING_ENGINE" if not errors else "REPAIR_V77_65",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    ver={
        "schema_version":"v77.65.performance_audit_certificate_verification.1",
        "stage":"V77.65","status":status,"verified":not errors,
        "error_count":len(errors),"errors":errors,
        "certificate_sha256":cert["certificate_sha256"],
        "next_phase":cert["next_phase"],
    }
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"performance_audit_certificate_v77_65.json",cert)
    write_json(output_dir/"performance_audit_certificate_verification_v77_65.json",ver)
    return cert
