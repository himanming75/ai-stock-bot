from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import csv, hashlib, io, json

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest_json(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

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
class ReportArtifact:
    artifact_type: str
    relative_path: str
    sha256: str
    byte_size: int

def build_report_payload(metrics_doc: dict, equity_doc: dict, config: dict) -> dict:
    if metrics_doc.get("stage")!="V78.73" or metrics_doc.get("status")!="PASS":
        raise ValueError("invalid metrics input")
    if equity_doc.get("stage")!="V78.72" or equity_doc.get("status")!="PASS":
        raise ValueError("invalid equity input")

    required_sections=config.get("required_sections",[])
    payload={
        "schema_version":"v78.77.performance_report.1",
        "report_id":str(config.get("report_id","V78-PERFORMANCE-REPORT")),
        "report_version":str(config.get("report_version","1.0")),
        "title":str(config.get("title","Offline Performance Report")),
        "generated_mode":"deterministic_offline",
        "summary":{
            "ending_equity":metrics_doc["performance_metrics"]["ending_equity"],
            "cumulative_return":metrics_doc["performance_metrics"]["cumulative_return"],
            "max_drawdown":metrics_doc["performance_metrics"]["max_drawdown"],
            "sharpe_ratio":metrics_doc["performance_metrics"]["sharpe_ratio"],
        },
        "trade_statistics":{
            k:metrics_doc["performance_metrics"][k]
            for k in (
                "trade_count","win_count","loss_count","flat_count","win_rate",
                "gross_profit","gross_loss","profit_factor","expectancy",
                "average_win","average_loss"
            )
        },
        "equity_curve":equity_doc["equity_curve"],
        "safety":safety(),
    }
    missing=[x for x in required_sections if x not in payload]
    if missing:
        raise ValueError(f"missing required report sections:{','.join(missing)}")
    payload["report_sha256"]=digest_json({k:v for k,v in payload.items() if k!="report_sha256"})
    return payload

def report_to_markdown(payload: dict) -> str:
    summary=payload["summary"]
    trades=payload["trade_statistics"]
    lines=[
        f"# {payload['title']}",
        "",
        f"- Report ID: `{payload['report_id']}`",
        f"- Version: `{payload['report_version']}`",
        f"- Mode: `{payload['generated_mode']}`",
        "",
        "## Performance Summary",
        "",
        f"- Ending Equity: {summary['ending_equity']}",
        f"- Cumulative Return: {summary['cumulative_return']}",
        f"- Maximum Drawdown: {summary['max_drawdown']}",
        f"- Sharpe Ratio: {summary['sharpe_ratio']}",
        "",
        "## Trade Summary",
        "",
        f"- Trade Count: {trades['trade_count']}",
        f"- Win Rate: {trades['win_rate']}",
        f"- Profit Factor: {trades['profit_factor']}",
        f"- Expectancy: {trades['expectancy']}",
        "",
        "## Equity Curve",
        "",
        "| Sequence | Label | Equity | Period Return | Cumulative Return | Drawdown |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for p in payload["equity_curve"]:
        lines.append(
            f"| {p['sequence']} | {p['label']} | {p['equity']} | "
            f"{p['period_return']} | {p['cumulative_return']} | {p['drawdown']} |"
        )
    lines += [
        "",
        "## Safety",
        "",
        "- Environment: offline",
        "- Network allowed: false",
        "- Broker connected: false",
        "- Actual orders submitted: 0",
        "",
        f"Report SHA256: `{payload['report_sha256']}`",
        "",
    ]
    return "\n".join(lines)

def report_to_csv(payload: dict) -> str:
    output=io.StringIO(newline="")
    writer=csv.writer(output, lineterminator="\n")
    writer.writerow(["sequence","label","equity","period_return","cumulative_return","drawdown"])
    for p in payload["equity_curve"]:
        writer.writerow([
            p["sequence"],p["label"],p["equity"],p["period_return"],
            p["cumulative_return"],p["drawdown"]
        ])
    return output.getvalue()

def verify_report_payload(payload: dict, required_sections: list[str]) -> list[str]:
    errors=[]
    for section in required_sections:
        if section not in payload:
            errors.append(f"missing_section:{section}")
    expected=digest_json({k:v for k,v in payload.items() if k!="report_sha256"})
    if payload.get("report_sha256")!=expected:
        errors.append("report_sha256")
    if payload.get("generated_mode")!="deterministic_offline":
        errors.append("generated_mode")
    s=payload.get("safety",{})
    if s.get("network_allowed") is not False:
        errors.append("network_allowed")
    if s.get("broker_connected") is not False:
        errors.append("broker_connected")
    if s.get("actual_orders_submitted")!=0:
        errors.append("actual_orders_submitted")
    return errors

def build_reporting_foundation(certificate_path:Path,config_path:Path,output_dir:Path)->dict:
    cert,config=map(load_json,(certificate_path,config_path))
    errors=[]
    if cert.get("stage")!="V78.75" or cert.get("status")!="PASS":
        errors.append("performance_accounting_certificate")
    if cert.get("certification_scope")!="OFFLINE_REPORTING_DEVELOPMENT_ONLY":
        errors.append("certificate_scope")
    reporting=config.get("reporting",{})
    for key in ("report_id","report_version","title","required_sections","export_formats"):
        if key not in reporting:
            errors.append(f"config_{key}")
    supported={"json","csv","markdown"}
    if not set(reporting.get("export_formats",[])).issubset(supported):
        errors.append("unsupported_export_format")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.76.reporting_foundation.1",
        "stage":"V78.76","status":status,
        "scope":"OFFLINE_DETERMINISTIC_REPORTING_ONLY",
        "champion_candidate":cert.get("champion_candidate"),
        "reporting":reporting,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_77_PERFORMANCE_REPORT_BUILDER",
    }
    doc["foundation_sha256"]=digest_json({k:v for k,v in doc.items() if k!="foundation_sha256"})
    write_json(output_dir/"reporting_foundation_v78_76.json",doc)
    ver={"stage":"V78.76","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "foundation_sha256":doc["foundation_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"reporting_foundation_verification_v78_76.json",ver)
    return doc

def run_performance_report_builder(foundation_path:Path,metrics_path:Path,
                                   equity_path:Path,output_dir:Path)->dict:
    foundation,metrics_doc,equity_doc=map(load_json,(foundation_path,metrics_path,equity_path))
    errors=[]
    if foundation.get("stage")!="V78.76" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    payload={}
    try:
        payload=build_report_payload(
            metrics_doc,equity_doc,foundation.get("reporting",{})
        )
    except Exception as exc:
        errors.append(f"report_build_exception:{type(exc).__name__}")
    checks={
        "payload_present":bool(payload),
        "required_sections_present":all(
            x in payload for x in foundation.get("reporting",{}).get("required_sections",[])
        ),
        "report_hash_valid":not payload or payload.get("report_sha256")==digest_json(
            {k:v for k,v in payload.items() if k!="report_sha256"}
        ),
        "equity_curve_present":len(payload.get("equity_curve",[]))>0,
        "trade_summary_present":bool(payload.get("trade_statistics")),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("report_builder_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.77.performance_report_builder.1",
        "stage":"V78.77","status":status,
        "report_payload":payload,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_78_REPORT_EXPORT_ENGINE",
    }
    doc["builder_sha256"]=digest_json({k:v for k,v in doc.items() if k!="builder_sha256"})
    write_json(output_dir/"performance_report_builder_v78_77.json",doc)
    ver={"stage":"V78.77","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "builder_sha256":doc["builder_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"performance_report_builder_verification_v78_77.json",ver)
    return doc

def run_report_export_engine(foundation_path:Path,builder_path:Path,output_dir:Path)->dict:
    foundation,builder=map(load_json,(foundation_path,builder_path))
    errors=[]
    if foundation.get("stage")!="V78.76" or foundation.get("status")!="PASS":
        errors.append("foundation_input")
    if builder.get("stage")!="V78.77" or builder.get("status")!="PASS":
        errors.append("builder_input")
    payload=builder.get("report_payload",{})
    exports=foundation.get("reporting",{}).get("export_formats",[])
    artifacts=[]
    try:
        output_dir.mkdir(parents=True,exist_ok=True)
        if "json" in exports:
            text=json.dumps(payload,indent=2,sort_keys=True,ensure_ascii=False)+"\n"
            path=output_dir/"performance_report_v78_78.json"
            path.write_text(text,encoding="utf-8")
            artifacts.append(ReportArtifact("json",path.name,digest_text(text),len(text.encode("utf-8"))))
        if "csv" in exports:
            text=report_to_csv(payload)
            path=output_dir/"equity_curve_v78_78.csv"
            path.write_text(text,encoding="utf-8",newline="\n")
            artifacts.append(ReportArtifact("csv",path.name,digest_text(text),len(text.encode("utf-8"))))
        if "markdown" in exports:
            text=report_to_markdown(payload)
            path=output_dir/"performance_report_v78_78.md"
            path.write_text(text,encoding="utf-8",newline="\n")
            artifacts.append(ReportArtifact("markdown",path.name,digest_text(text),len(text.encode("utf-8"))))
    except Exception as exc:
        errors.append(f"export_exception:{type(exc).__name__}")

    manifest={
        "schema_version":"v78.78.report_manifest.1",
        "artifact_count":len(artifacts),
        "artifacts":[asdict(x) for x in artifacts],
        "report_sha256":payload.get("report_sha256"),
    }
    manifest["manifest_sha256"]=digest_json({k:v for k,v in manifest.items() if k!="manifest_sha256"})
    write_json(output_dir/"report_manifest_v78_78.json",manifest)

    checks={
        "artifact_count_matches_formats":len(artifacts)==len(exports),
        "artifact_types_unique":len({x.artifact_type for x in artifacts})==len(artifacts),
        "artifact_hashes_unique":len({x.sha256 for x in artifacts})==len(artifacts),
        "all_artifacts_nonempty":all(x.byte_size>0 for x in artifacts),
        "manifest_hash_valid":manifest["manifest_sha256"]==digest_json(
            {k:v for k,v in manifest.items() if k!="manifest_sha256"}
        ),
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:errors.append("report_export_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.78.report_export_engine.1",
        "stage":"V78.78","status":status,
        "manifest":manifest,
        "checks":checks,"failed_checks":failed,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_79_REPORTING_SAFETY_GATE",
    }
    doc["export_engine_sha256"]=digest_json({k:v for k,v in doc.items() if k!="export_engine_sha256"})
    write_json(output_dir/"report_export_engine_v78_78.json",doc)
    ver={"stage":"V78.78","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "export_engine_sha256":doc["export_engine_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"report_export_engine_verification_v78_78.json",ver)
    return doc

def run_reporting_safety_gate(foundation_path:Path,builder_path:Path,
                              export_path:Path,output_dir:Path)->dict:
    foundation,builder,export_doc=map(load_json,(foundation_path,builder_path,export_path))
    errors=[]
    for expected,doc in (("V78.76",foundation),("V78.77",builder),("V78.78",export_doc)):
        if doc.get("stage")!=expected or doc.get("status")!="PASS":
            errors.append(expected)
    payload=builder.get("report_payload",{})
    manifest=export_doc.get("manifest",{})
    report_errors=verify_report_payload(
        payload,foundation.get("reporting",{}).get("required_sections",[])
    )
    checks={
        "offline_reporting_scope":foundation.get("scope")=="OFFLINE_DETERMINISTIC_REPORTING_ONLY",
        "report_payload_valid":report_errors==[],
        "builder_checks_passed":builder.get("failed_checks")==[],
        "export_checks_passed":export_doc.get("failed_checks")==[],
        "manifest_report_hash_matches":manifest.get("report_sha256")==payload.get("report_sha256"),
        "artifact_count_positive":manifest.get("artifact_count",0)>0,
        "network_disabled":all(x.get("network_allowed") is False for x in (foundation,builder,export_doc)),
        "broker_disconnected":all(x.get("broker_connected") is False for x in (foundation,builder,export_doc)),
        "actual_orders_zero":all(x.get("actual_orders_submitted")==0 for x in (foundation,builder,export_doc)),
    }
    failed=[k for k,v in checks.items() if not v]
    if report_errors:
        errors.extend(report_errors)
    if failed:
        errors.append("reporting_safety_checks")
    status="PASS" if not errors else "FAIL"
    doc={
        "schema_version":"v78.79.reporting_safety_gate.1",
        "stage":"V78.79","status":status,
        "gate_scope":"OFFLINE_DEPLOYMENT_PACKAGING_ELIGIBILITY_ONLY",
        "decision":"ALLOW_OFFLINE_DEPLOYMENT_PACKAGING" if not errors else "BLOCK_DEPLOYMENT_PACKAGING",
        "real_broker_connection_approved":False,
        "actual_order_submission_approved":False,
        "checks":checks,"failed_checks":failed,
        "report_validation_errors":report_errors,
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_80_REPORTING_CERTIFICATE",
    }
    doc["safety_gate_sha256"]=digest_json({k:v for k,v in doc.items() if k!="safety_gate_sha256"})
    write_json(output_dir/"reporting_safety_gate_v78_79.json",doc)
    ver={"stage":"V78.79","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,"failed_checks":failed,
         "safety_gate_sha256":doc["safety_gate_sha256"],
         "next_phase":doc["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"reporting_safety_gate_verification_v78_79.json",ver)
    return doc

def issue_reporting_certificate(v76:Path,v77:Path,v78:Path,v79:Path,
                                foundation_path:Path,output_dir:Path)->dict:
    docs=list(map(load_json,(v76,v77,v78,v79)))
    foundation=load_json(foundation_path)
    expected=["V78.76","V78.77","V78.78","V78.79"]
    errors=[]
    for stage,doc in zip(expected,docs):
        if doc.get("stage")!=stage or doc.get("status")!="PASS" or doc.get("verified") is not True:
            errors.append(stage)
    status="PASS" if not errors else "FAIL"
    cert={
        "schema_version":"v78.80.reporting_certificate.1",
        "stage":"V78.80",
        "certificate_id":"REPORTING-V78.80",
        "status":status,
        "decision":"certified_for_offline_deployment_packaging" if not errors else "reporting_rejected",
        "certification_scope":"OFFLINE_DEPLOYMENT_PACKAGING_DEVELOPMENT_ONLY",
        "real_broker_connection_approved":False,
        "real_credentials_approved":False,
        "network_transport_approved":False,
        "actual_order_submission_approved":False,
        "live_trading_approved":False,
        "certified_stages":expected,
        "champion_candidate":foundation.get("champion_candidate"),
        "error_count":len(errors),"errors":errors,
        **safety(),
        "next_phase":"V78_81_DEPLOYMENT_FOUNDATION" if not errors else "REPAIR_V78_80",
    }
    cert["certificate_sha256"]=digest_json({k:v for k,v in cert.items() if k!="certificate_sha256"})
    write_json(output_dir/"reporting_certificate_v78_80.json",cert)
    ver={"stage":"V78.80","status":status,"verified":not errors,
         "error_count":len(errors),"errors":errors,
         "certificate_sha256":cert["certificate_sha256"],
         "next_phase":cert["next_phase"]}
    ver["verification_sha256"]=digest_json({k:v for k,v in ver.items() if k!="verification_sha256"})
    write_json(output_dir/"reporting_certificate_verification_v78_80.json",ver)
    return cert
