from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from audit_reconciliation.audit_reconciliation_pipeline_v78_66_70 import *

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--clean",action="store_true")
    a=p.parse_args()
    r=Path(a.repository_root).resolve()

    cert=r/"release/v78_65/output/fill_portfolio_bridge_certificate_v78_65.json"
    normalization=r/"release/v78_62/output/fill_normalization_portfolio_event_v78_62.json"
    reconciliation=r/"release/v78_63/output/fill_application_reconciliation_v78_63.json"
    cfg=r/"release/v78_66/config/audit_reconciliation_config_v78_66.json"
    for f in (cert,normalization,reconciliation,cfg):
        if not f.is_file():
            raise SystemExit(f"Missing required input: {f}")

    out={v:r/f"release/v{v}/output" for v in ("78_66","78_67","78_68","78_69","78_70")}
    if a.clean:
        for d in out.values():
            shutil.rmtree(d,ignore_errors=True)

    p66=build_audit_reconciliation_foundation(cert,cfg,out["78_66"])
    p67=run_cash_position_fill_cross_check(
        out["78_66"]/"audit_reconciliation_foundation_v78_66.json",
        normalization,reconciliation,out["78_67"])
    p68=run_ledger_integrity_replay_audit(
        normalization,reconciliation,out["78_68"])
    p69=run_audit_reconciliation_safety_gate(
        out["78_66"]/"audit_reconciliation_foundation_v78_66.json",
        out["78_67"]/"cash_position_fill_cross_check_v78_67.json",
        out["78_68"]/"ledger_integrity_replay_audit_v78_68.json",
        out["78_69"])
    p70=issue_audit_reconciliation_certificate(
        out["78_66"]/"audit_reconciliation_foundation_verification_v78_66.json",
        out["78_67"]/"cash_position_fill_cross_check_verification_v78_67.json",
        out["78_68"]/"ledger_integrity_replay_audit_verification_v78_68.json",
        out["78_69"]/"audit_reconciliation_safety_gate_verification_v78_69.json",
        out["78_66"]/"audit_reconciliation_foundation_v78_66.json",
        out["78_70"])

    stages=[p66,p67,p68,p69,p70]
    champion=p70.get("champion_candidate") or {}
    summary={
        "status":"PASS" if all(x.get("status")=="PASS" for x in stages) else "FAIL",
        "stage_count":5,
        "passed_stage_count":sum(x.get("status")=="PASS" for x in stages),
        "failed_stage_count":sum(x.get("status")!="PASS" for x in stages),
        **safety(),
        "champion_candidate_id":champion.get("candidate_id"),
        "failed_stages":[
            {"stage":x.get("stage"),"errors":x.get("errors",[]),"failed_checks":x.get("failed_checks",[])}
            for x in stages if x.get("status")!="PASS"
        ],
        "next_phase":p70.get("next_phase")
    }
    summary["pipeline_sha256"]=digest_json({k:v for k,v in summary.items() if k!="pipeline_sha256"})
    write_json(out["78_70"]/"audit_reconciliation_pipeline_summary_v78_66_to_v78_70.json",summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
