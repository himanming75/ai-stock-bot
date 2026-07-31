from __future__ import annotations
from pathlib import Path
from typing import Any
import csv, hashlib, html, json, math

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")

def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def safety() -> dict:
    return {"environment":"offline","network_allowed":False,"broker_connected":False,
            "actual_orders_submitted":0,"live_trading_authorized":False}

def build_report_generator(perf_path: Path, risk_path: Path, cert_path: Path, output_dir: Path) -> dict:
    perf,risk,cert=map(load_json,(perf_path,risk_path,cert_path)); errors=[]
    if perf.get("stage")!="V77.61" or perf.get("status")!="PASS":errors.append("performance_input")
    if risk.get("stage")!="V77.63" or risk.get("status")!="PASS":errors.append("risk_input")
    if cert.get("stage")!="V77.65" or cert.get("status")!="PASS":errors.append("certificate_input")
    status="PASS" if not errors else "FAIL"; metrics=risk.get("metrics",{})
    summary={"trade_count":perf.get("trade_count",0),"win_rate":perf.get("win_rate",0.0),
      "trade_pnl":perf.get("trade_pnl",0.0),"total_return":perf.get("total_return",0.0),
      "equity_before":perf.get("equity_before",0.0),"equity_after":perf.get("equity_after",0.0),
      "max_drawdown":metrics.get("max_drawdown",0.0),"sharpe_ratio":metrics.get("sharpe_ratio",0.0),
      "sortino_ratio":metrics.get("sortino_ratio",0.0),"profit_factor":metrics.get("profit_factor",0.0),
      "expectancy":metrics.get("expectancy",0.0)}
    doc={"schema_version":"v77.66.report_generator.1","stage":"V77.66","status":status,
      "summary":summary,"error_count":len(errors),"errors":errors,
      "actual_orders_submitted":0,"safety":safety(),"next_phase":"V77_67_EQUITY_CURVE_VISUALIZATION"}
    doc["report_sha256"]=digest_json({k:v for k,v in doc.items() if k!="report_sha256"})
    write_json(output_dir/"performance_report_v77_66.json",doc)
    lines=["# Offline Performance Report",""]+[f"- {k}: {v}" for k,v in summary.items()]+["","Offline only. No live orders."]
    write_text(output_dir/"performance_report_v77_66.md","\n".join(lines)+"\n")
    ver={"stage":"V77.66","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
      "report_sha256":doc["report_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"performance_report_verification_v77_66.json",ver); return doc

def build_equity_curve_visualization(perf_path: Path, output_dir: Path) -> dict:
    perf=load_json(perf_path); curve=perf.get("equity_curve",[]); errors=[]
    if perf.get("stage")!="V77.61" or perf.get("status")!="PASS":errors.append("performance_input")
    if len(curve)<2:errors.append("insufficient_curve_points")
    values=[float(p.get("equity",0.0)) for p in curve]
    if any(not math.isfinite(v) or v<0 for v in values):errors.append("invalid_equity_value")
    status="PASS" if not errors else "FAIL"
    output_dir.mkdir(parents=True,exist_ok=True)
    with (output_dir/"equity_curve_v77_67.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["sequence","equity","event"])
        for p in curve:w.writerow([p.get("sequence"),p.get("equity"),p.get("event")])
    width,height,pad=800,360,40; pts=[]
    if values:
        lo,hi=min(values),max(values); spread=max(hi-lo,1.0)
        for i,v in enumerate(values):
            x=pad+(width-2*pad)*(i/max(len(values)-1,1))
            y=height-pad-(height-2*pad)*((v-lo)/spread)
            pts.append(f"{x:.2f},{y:.2f}")
    poly=" ".join(pts)
    svg=("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"800\" height=\"360\">"
         "<rect width=\"800\" height=\"360\" fill=\"white\"/>"
         "<line x1=\"40\" y1=\"320\" x2=\"760\" y2=\"320\" stroke=\"black\"/>"
         "<line x1=\"40\" y1=\"40\" x2=\"40\" y2=\"320\" stroke=\"black\"/>"
         f"<polyline points=\"{html.escape(poly)}\" fill=\"none\" stroke=\"black\" stroke-width=\"2\"/>"
         "<text x=\"40\" y=\"24\" font-size=\"16\">Offline Equity Curve V77.67</text></svg>\n")
    write_text(output_dir/"equity_curve_v77_67.svg",svg)
    doc={"stage":"V77.67","status":status,"point_count":len(curve),
      "minimum_equity":min(values) if values else 0.0,"maximum_equity":max(values) if values else 0.0,
      "csv_file":"equity_curve_v77_67.csv","svg_file":"equity_curve_v77_67.svg",
      "error_count":len(errors),"errors":errors,"actual_orders_submitted":0,"safety":safety(),
      "next_phase":"V77_68_TRADE_STATISTICS_DASHBOARD"}
    doc["equity_visualization_sha256"]=digest_json({k:v for k,v in doc.items() if k!="equity_visualization_sha256"})
    write_json(output_dir/"equity_curve_visualization_v77_67.json",doc)
    ver={"stage":"V77.67","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
      "equity_visualization_sha256":doc["equity_visualization_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"equity_curve_visualization_verification_v77_67.json",ver);return doc

def build_trade_statistics_dashboard(report_path: Path,risk_path: Path,output_dir: Path)->dict:
    report,risk=map(load_json,(report_path,risk_path));errors=[]
    if report.get("stage")!="V77.66" or report.get("status")!="PASS":errors.append("report_input")
    if risk.get("stage")!="V77.63" or risk.get("status")!="PASS":errors.append("risk_input")
    status="PASS" if not errors else "FAIL"; s=report.get("summary",{});m=risk.get("metrics",{})
    cards=[{"label":"Trade Count","value":s.get("trade_count",0)},{"label":"Win Rate","value":s.get("win_rate",0)},
      {"label":"Trade PnL","value":s.get("trade_pnl",0)},{"label":"Total Return","value":s.get("total_return",0)},
      {"label":"Max Drawdown","value":m.get("max_drawdown",0)},{"label":"Sharpe Ratio","value":m.get("sharpe_ratio",0)},
      {"label":"Sortino Ratio","value":m.get("sortino_ratio",0)},{"label":"Profit Factor","value":m.get("profit_factor",0)}]
    doc={"stage":"V77.68","status":status,"cards":cards,"error_count":len(errors),"errors":errors,
      "actual_orders_submitted":0,"safety":safety(),"next_phase":"V77_69_REPORTING_SAFETY_GATE"}
    doc["dashboard_sha256"]=digest_json({k:v for k,v in doc.items() if k!="dashboard_sha256"})
    write_json(output_dir/"trade_statistics_dashboard_v77_68.json",doc)
    write_text(output_dir/"trade_statistics_dashboard_v77_68.md",
      "# Trade Statistics Dashboard\n\n"+"\n".join(f"- {c['label']}: {c['value']}" for c in cards)+"\n")
    ver={"stage":"V77.68","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
      "dashboard_sha256":doc["dashboard_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"trade_statistics_dashboard_verification_v77_68.json",ver);return doc

def run_reporting_safety_gate(report_path: Path,viz_path: Path,dashboard_path: Path,output_dir: Path)->dict:
    docs=list(map(load_json,(report_path,viz_path,dashboard_path)));errors=[]
    if [d.get("stage") for d in docs]!=["V77.66","V77.67","V77.68"]:errors.append("stage_chain")
    if any(d.get("status")!="PASS" for d in docs):errors.append("upstream_status")
    if any(d.get("actual_orders_submitted")!=0 for d in docs):errors.append("actual_orders")
    if docs[1].get("point_count",0)<2:errors.append("curve_points")
    if len(docs[2].get("cards",[]))<6:errors.append("dashboard_cards")
    status="PASS" if not errors else "FAIL"
    doc={"stage":"V77.69","status":status,"decision":"ALLOW_REPORTING_ARTIFACTS" if not errors else "BLOCK_REPORTING_ARTIFACTS",
      "error_count":len(errors),"errors":errors,"actual_orders_submitted":0,"safety":safety(),
      "next_phase":"V77_70_REPORTING_AUDIT_CERTIFICATE"}
    doc["reporting_safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="reporting_safety_gate_sha256"})
    write_json(output_dir/"reporting_safety_gate_v77_69.json",doc)
    ver={"stage":"V77.69","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
      "reporting_safety_gate_sha256":doc["reporting_safety_gate_sha256"],"next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"reporting_safety_gate_verification_v77_69.json",ver);return doc

def issue_reporting_certificate(v66:Path,v67:Path,v68:Path,v69:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v66,v67,v68,v69)));expected=["V77.66","V77.67","V77.68","V77.69"];errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={"stage":"V77.70","certificate_id":"REPORTING-AUDIT-V77.70","status":status,
      "decision":"reporting_certified" if not errors else "reporting_rejected","certified_stages":expected,
      "error_count":len(errors),"errors":errors,"actual_orders_submitted":0,"safety":safety(),
      "next_phase":"V77_71_STRATEGY_OPTIMIZATION_ENGINE" if not errors else "REPAIR_V77_70"}
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"reporting_audit_certificate_v77_70.json",cert)
    ver={"stage":"V77.70","status":status,"verified":not errors,"error_count":len(errors),"errors":errors,
      "certificate_sha256":cert["certificate_sha256"],"next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"reporting_audit_certificate_verification_v77_70.json",ver);return cert
