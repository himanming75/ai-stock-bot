from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import argparse, json, py_compile, subprocess

RUNNER_REL=Path("paper_daily_session/runner.py")
HOOK_LEDGER_REL=Path("runtime/regime_aware_buy_shadow_v2_8_1/hook_ledger.jsonl")
SHADOW_LEDGER_REL=Path("runtime/regime_aware_buy_shadow_v2_7/shadow_candidate_ledger.jsonl")
SESSION_LEDGER_REL=Path("runtime/paper_autonomous_daily_session/session_ledger.jsonl")
OUT_REL=Path("runtime/regime_aware_buy_shadow_v2_9/latest_runtime_shadow_certification_v2_9.json")

METHOD_MARKER="def _run_regime_shadow_cycle(self) -> dict[str, Any]:"
CALL_MARKER="regime_shadow_v2_8_1 = self._run_regime_shadow_cycle()"

def read_jsonl(path:Path):
    if not path.exists():
        return []
    rows=[]
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            rows.append({"_parse_error":True,"_raw":line[:500]})
    return rows

def certify(root:Path):
    root=root.resolve()
    runner=root/RUNNER_REL
    if not runner.exists():
        raise RuntimeError(f"RUNNER_MISSING:{runner}")

    py_compile.compile(str(runner),doraise=True)
    text=runner.read_text(encoding="utf-8",errors="replace")
    method_count=text.count(METHOD_MARKER)
    call_count=text.count(CALL_MARKER)

    hook_rows=read_jsonl(root/HOOK_LEDGER_REL)
    shadow_rows=read_jsonl(root/SHADOW_LEDGER_REL)
    session_rows=read_jsonl(root/SESSION_LEDGER_REL)

    hook_status=Counter(str(r.get("status","UNKNOWN")) for r in hook_rows)
    hook_parse_errors=sum(1 for r in hook_rows if r.get("_parse_error"))
    attempted=sum(1 for r in hook_rows if r.get("attempted") is True)
    blocked_flags=sum(1 for r in hook_rows if r.get("primary_paper_flow_blocked") is True)
    broker_write_flags=sum(1 for r in hook_rows if r.get("broker_write_performed") is True)
    paper_submit_flags=sum(1 for r in hook_rows if r.get("paper_order_submission_performed") is True)
    live_submit_flags=sum(1 for r in hook_rows if r.get("live_order_submission_performed") is True)

    signals=[r for r in shadow_rows if r.get("event_type")=="SHADOW_SIGNAL"]
    outcomes=[r for r in shadow_rows if r.get("event_type")=="SHADOW_OUTCOME"]
    signal_ids=[str(r.get("signal_id")) for r in signals if r.get("signal_id")]
    outcome_ids=[str(r.get("signal_id")) for r in outcomes if r.get("signal_id")]
    duplicate_signal_ids=sorted([k for k,v in Counter(signal_ids).items() if v>1])
    duplicate_outcome_ids=sorted([k for k,v in Counter(outcome_ids).items() if v>1])
    orphan_outcomes=sorted(set(outcome_ids)-set(signal_ids))

    isolated_failures=sum(
        hook_status.get(k,0)
        for k in ("SHADOW_NONZERO_ISOLATED","SHADOW_TIMEOUT_ISOLATED","SHADOW_EXCEPTION_ISOLATED")
    )
    successful_hooks=hook_status.get("PASS",0)

    structural_pass=(
        method_count==1
        and call_count==1
        and hook_parse_errors==0
        and blocked_flags==0
        and broker_write_flags==0
        and paper_submit_flags==0
        and live_submit_flags==0
        and not duplicate_signal_ids
        and not duplicate_outcome_ids
        and not orphan_outcomes
    )

    if not structural_pass:
        status="BLOCKED_CERTIFICATION_INTEGRITY_FAILURE"
    elif len(hook_rows)==0:
        status="PASS_WAITING_FOR_RUNTIME_OBSERVATION"
    elif successful_hooks==0 and isolated_failures>0:
        status="PASS_HOOK_ISOLATION_OBSERVED_NO_SUCCESS_YET"
    elif successful_hooks>=3:
        status="PASS_RUNTIME_SHADOW_OBSERVED"
    else:
        status="PASS_RUNTIME_OBSERVATION_PARTIAL"

    report={
        "stage":"V2.9_RUNTIME_SHADOW_OBSERVATION_CERTIFICATION",
        "status":status,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "runner_integrity":{
            "path":str(RUNNER_REL).replace("\\","/"),
            "compile_pass":True,
            "method_marker_count":method_count,
            "call_marker_count":call_count,
        },
        "hook_observation":{
            "ledger_exists":(root/HOOK_LEDGER_REL).exists(),
            "record_count":len(hook_rows),
            "attempted_count":attempted,
            "status_counts":dict(hook_status),
            "successful_hook_count":successful_hooks,
            "isolated_failure_count":isolated_failures,
            "parse_error_count":hook_parse_errors,
            "primary_paper_flow_blocked_true_count":blocked_flags,
        },
        "shadow_ledger":{
            "ledger_exists":(root/SHADOW_LEDGER_REL).exists(),
            "signal_count":len(signals),
            "outcome_count":len(outcomes),
            "duplicate_signal_ids":duplicate_signal_ids,
            "duplicate_outcome_ids":duplicate_outcome_ids,
            "orphan_outcome_ids":orphan_outcomes,
        },
        "paper_session_observation":{
            "ledger_exists":(root/SESSION_LEDGER_REL).exists(),
            "session_record_count":len(session_rows),
            "latest_stage":session_rows[-1].get("stage") if session_rows else None,
        },
        "certification_rules":{
            "structural_integrity_pass":structural_pass,
            "runtime_full_observation_min_successful_hooks":3,
            "zero_runtime_records_is_not_failure":True,
        },
        "contracts":{
            "cleanup_only_failed_intermediates":True,
            "paper_runtime_logic_modified_by_v2_9":False,
            "production_parameter_modified":False,
            "production_selector_modified":False,
            "broker_write_performed_by_v2_9":False,
            "paper_order_submission_performed_by_v2_9":False,
            "live_order_submission_performed_by_v2_9":False,
            "network_used_by_v2_9":False,
            "automatic_promotion":False,
        },
    }
    out=root/OUT_REL
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    return 0 if not status.startswith("BLOCKED") else 2

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    return certify(Path(a.root))

if __name__=="__main__":
    raise SystemExit(main())
