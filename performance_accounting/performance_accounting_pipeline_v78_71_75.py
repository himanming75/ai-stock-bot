from __future__ import annotations
from dataclasses import dataclass, asdict
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
        "real_credentials_allowed":False,
    }

@dataclass(frozen=True)
class EquityPoint:
    sequence: int
    label: str
    equity: float
    period_return: float
    cumulative_return: float
    drawdown: float
    equity_sha256: str

def finite(value: float) -> bool:
    return math.isfinite(float(value))

def build_equity_curve(starting_equity: float, equity_values: list[float], labels: list[str]) -> list[EquityPoint]:
    if starting_equity <= 0:
        raise ValueError("starting_equity must be positive")
    if len(equity_values) != len(labels):
        raise ValueError("equity and label length mismatch")
    if not equity_values:
        raise ValueError("equity_values required")

    points=[]
    previous=float(starting_equity)
    peak=float(starting_equity)
    for idx,(label,equity_raw) in enumerate(zip(labels,equity_values),1):
        equity=float(equity_raw)
        if equity <= 0 or not finite(equity):
            raise ValueError("invalid equity")
        period_return=equity/previous-1.0
        cumulative_return=equity/starting_equity-1.0
        peak=max(peak,equity)
        drawdown=equity/peak-1.0
        base={
            "sequence":idx,
            "label":str(label),
            "equity":round(equity,8),
            "period_return":round(period_return,12),
            "cumulative_return":round(cumulative_return,12),
            "drawdown":round(drawdown,12),
        }
        points.append(EquityPoint(
            sequence=idx,
            label=str(label),
            equity=round(equity,8),
            period_return=round(period_return,12),
            cumulative_return=round(cumulative_return,12),
            drawdown=round(drawdown,12),
            equity_sha256=digest_json(base),
        ))
        previous=equity
    return points

def calculate_performance_metrics(points:list[EquityPoint], trade_pnls:list[float],
                                  annualization_factor:float)->dict:
    if not points:
        raise ValueError("equity points required")
    if annualization_factor <= 0:
        raise ValueError("annualization_factor must be positive")
    returns=[float(x.period_return) for x in points]
    cumulative=float(points[-1].cumulative_return)
    max_drawdown=min(float(x.drawdown) for x in points)
    mean_return=sum(returns)/len(returns)
    stdev=statistics.pstdev(returns) if len(returns)>1 else 0.0
    sharpe=0.0 if stdev==0 else (mean_return/stdev)*math.sqrt(annualization_factor)

    wins=[float(x) for x in trade_pnls if float(x)>0]
    losses=[float(x) for x in trade_pnls if float(x)<0]
    flats=[float(x) for x in trade_pnls if float(x)==0]
    trade_count=len(trade_pnls)
    win_rate=0.0 if trade_count==0 else len(wins)/trade_count
    gross_profit=sum(wins)
    gross_loss=abs(sum(losses))
    if gross_loss==0:
        profit_factor=None if gross_profit==0 else float("inf")
    else:
        profit_factor=gross_profit/gross_loss
    expectancy=0.0 if trade_count==0 else sum(float(x) for x in trade_pnls)/trade_count
    avg_win=0.0 if not wins else sum(wins)/len(wins)
    avg_loss=0.0 if not losses else sum(losses)/len(losses)

    metrics={
        "ending_equity":points[-1].equity,
        "cumulative_return":round(cumulative,12),
        "max_drawdown":round(max_drawdown,12),
        "mean_period_return":round(mean_return,12),
        "return_volatility":round(stdev,12),
        "sharpe_ratio":round(sharpe,12),
        "trade_count":trade_count,
        "win_count":len(wins),
        "loss_count":len(losses),
        "flat_count":len(flats),
        "win_rate":round(win_rate,12),
        "gross_profit":round(gross_profit,8),
        "gross_loss":round(gross_loss,8),
        "profit_factor":None if profit_factor is None else (
            "INF" if math.isinf(profit_factor) else round(profit_factor,12)
        ),
        "expectancy":round(expectancy,8),
        "average_win":round(avg_win,8),
        "average_loss":round(avg_loss,8),
    }
    for key,value in metrics.items():
        if isinstance(value,(int,str)) or value is None:
            continue
        if not finite(value):
            raise ValueError(f"non-finite metric:{key}")
    return metrics

def build_performance_accounting_foundation(certificate_path:Path, config_path:Path,
                                            output_dir:Path)->dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.70" or cert.get("status")!="PASS":
        errors.append("audit_reconciliation_certificate")
    if cert.get("certification_scope")!="OFFLINE_PERFORMANCE_ACCOUNTING_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    perf=config.get("performance_accounting",{})
    for key in ("starting_equity","equity_values","labels","trade_pnls","annualization_factor"):
        if key not in perf:
            errors.append(f"config_{key}")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.71.performance_accounting_foundation.1",
        "stage":"V78.71","status":status,
        "scope":"OFFLINE_PERFORMANCE_ANALYTICS_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "performance_accounting":perf,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_72_EQUITY_CURVE_RETURN_LEDGER",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"performance_accounting_foundation_v78_71.json",doc)
    ver={"stage":"V78.71","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"performance_accounting_foundation_verification_v78_71.json",ver)
    return doc

def run_equity_curve_return_ledger(foundation_path:Path,output_dir:Path)->dict:
    foundation=load_json(foundation_path)
    errors=[]
    if foundation.get("stage")!="V78.71" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    perf=foundation.get("performance_accounting",{})
    points=[]
    try:
        points=build_equity_curve(
            float(perf.get("starting_equity",0)),
            [float(x) for x in perf.get("equity_values",[])],
            [str(x) for x in perf.get("labels",[])],
        )
    except Exception as exc:
        errors.append(f"equity_curve_exception:{type(exc).__name__}")

    checks={
        "point_count_matches_input":len(points)==len(perf.get("equity_values",[])),
        "sequences_contiguous":[x.sequence for x in points]==list(range(1,len(points)+1)),
        "hashes_unique":len({x.equity_sha256 for x in points})==len(points),
        "returns_finite":all(finite(x.period_return) for x in points),
        "drawdowns_non_positive":all(x.drawdown<=0 for x in points),
        "cumulative_return_matches_end":(
            not points or points[-1].cumulative_return==
            round(points[-1].equity/float(perf["starting_equity"])-1.0,12)
        ),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("equity_curve_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.72.equity_curve_return_ledger.1",
        "stage":"V78.72","status":status,
        "equity_curve":[asdict(x) for x in points],
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_73_PERFORMANCE_METRICS_ENGINE",
    }
    doc["equity_curve_sha256"]=digest_json({k:v for k,v in doc.items() if k!="equity_curve_sha256"})
    write_json(output_dir/"equity_curve_return_ledger_v78_72.json",doc)
    ver={"stage":"V78.72","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "equity_curve_sha256":doc["equity_curve_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"equity_curve_return_ledger_verification_v78_72.json",ver)
    return doc

def run_performance_metrics_engine(foundation_path:Path,equity_path:Path,output_dir:Path)->dict:
    foundation,equity_doc=map(load_json,(foundation_path,equity_path))
    errors=[]
    if foundation.get("stage")!="V78.71" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if equity_doc.get("stage")!="V78.72" or equity_doc.get("status")!="PASS":
        errors.append("equity_input")
    perf=foundation.get("performance_accounting",{})
    metrics={}
    try:
        points=[EquityPoint(**x) for x in equity_doc.get("equity_curve",[])]
        metrics=calculate_performance_metrics(
            points,
            [float(x) for x in perf.get("trade_pnls",[])],
            float(perf.get("annualization_factor",252.0)),
        )
    except Exception as exc:
        errors.append(f"metrics_exception:{type(exc).__name__}")

    checks={
        "metrics_present":bool(metrics),
        "ending_equity_positive":metrics.get("ending_equity",0)>0,
        "max_drawdown_non_positive":metrics.get("max_drawdown",1)<=0,
        "win_rate_bounded":0<=metrics.get("win_rate",0)<=1,
        "trade_counts_balance":(
            metrics.get("trade_count",0)==
            metrics.get("win_count",0)+metrics.get("loss_count",0)+metrics.get("flat_count",0)
        ),
        "expectancy_matches_trades":metrics.get("expectancy")==round(
            sum(float(x) for x in perf.get("trade_pnls",[]))/max(1,len(perf.get("trade_pnls",[]))),8
        ),
        "sharpe_finite":finite(metrics.get("sharpe_ratio",0)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("performance_metric_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.73.performance_metrics_engine.1",
        "stage":"V78.73","status":status,
        "performance_metrics":metrics,
        "trade_pnls":[float(x) for x in perf.get("trade_pnls",[])],
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_74_PERFORMANCE_ACCOUNTING_SAFETY_GATE",
    }
    doc["metrics_sha256"]=digest_json({k:v for k,v in doc.items() if k!="metrics_sha256"})
    write_json(output_dir/"performance_metrics_engine_v78_73.json",doc)
    ver={"stage":"V78.73","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "metrics_sha256":doc["metrics_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"performance_metrics_engine_verification_v78_73.json",ver)
    return doc

def run_performance_accounting_safety_gate(foundation_path:Path,equity_path:Path,
                                           metrics_path:Path,output_dir:Path)->dict:
    foundation,equity_doc,metrics_doc=map(load_json,(foundation_path,equity_path,metrics_path))
    errors=[]
    for expected,doc in (("V78.71",foundation),("V78.72",equity_doc),("V78.73",metrics_doc)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    points=equity_doc.get("equity_curve",[])
    metrics=metrics_doc.get("performance_metrics",{})
    checks={
        "offline_performance_scope":foundation.get("scope")=="OFFLINE_PERFORMANCE_ANALYTICS_ONLY",
        "equity_checks_passed":equity_doc.get("failed_checks")==[],
        "metrics_checks_passed":metrics_doc.get("failed_checks")==[],
        "equity_sequence_contiguous":[x["sequence"] for x in points]==list(range(1,len(points)+1)),
        "ending_equity_consistent":not points or metrics.get("ending_equity")==points[-1]["equity"],
        "cumulative_return_consistent":not points or metrics.get("cumulative_return")==points[-1]["cumulative_return"],
        "max_drawdown_consistent":not points or metrics.get("max_drawdown")==min(x["drawdown"] for x in points),
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,equity_doc,metrics_doc)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,equity_doc,metrics_doc)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,equity_doc,metrics_doc)),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("performance_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.74.performance_accounting_safety_gate.1",
        "stage":"V78.74","status":status,
        "gate_scope":"OFFLINE_REPORTING_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_REPORTING" if not errors else "BLOCK_REPORTING",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_75_PERFORMANCE_ACCOUNTING_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"performance_accounting_safety_gate_v78_74.json",doc)
    ver={"stage":"V78.74","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "safety_gate_sha256":doc["safety_gate_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"performance_accounting_safety_gate_verification_v78_74.json",ver)
    return doc

def issue_performance_accounting_certificate(v71:Path,v72:Path,v73:Path,v74:Path,
                                             foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v71,v72,v73,v74)))
    foundation=load_json(foundation_path)
    expected=["V78.71","V78.72","V78.73","V78.74"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.75.performance_accounting_certificate.1",
        "stage":"V78.75",
        "certificate_id":"PERFORMANCE-ACCOUNTING-V78.75",
        "status":status,
        "decision":"certified_for_offline_reporting" if not errors else "performance_accounting_rejected",
        "certification_scope":"OFFLINE_REPORTING_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_76_REPORTING_FOUNDATION" if not errors else "REPAIR_V78_75",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"performance_accounting_certificate_v78_75.json",cert)
    ver={"stage":"V78.75","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],
         "next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"performance_accounting_certificate_verification_v78_75.json",ver)
    return cert
