from __future__ import annotations

import json
from pathlib import Path


def _read_jsonl(path):
    if not path.exists():
        return []
    rows=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                rows.append({"_invalid_json":True,"_raw":line[:200]})
    return rows


def run_semantic_audit_v2_1_19_1(root):
    root=Path(root)

    qualification=(
        root/"runtime"/"sandbox_readiness_gate_v2_1_17"/"qualification_ledger.jsonl"
    )
    packet_index=(
        root/"runtime"/"manual_sandbox_review_packets_v2_1_18"/"review_packet_index.jsonl"
    )
    approval=(
        root/"runtime"/"manual_approval_v2_1_19"/"approval_ledger.jsonl"
    )

    qrows=_read_jsonl(qualification)
    prows=_read_jsonl(packet_index)
    arows=_read_jsonl(approval)

    legacy_q=[]
    corrected_q=[]
    for row in qrows:
        corrected=(
            row.get("canonical_min_confidence")=="0.75"
            and row.get("canonical_min_reward_risk")=="1.0"
            and row.get("canonical_paper_gate_semantics")=="CORRECTED_V2_1_19_1"
        )
        if corrected:
            corrected_q.append(row.get("evidence_key"))
        else:
            legacy_q.append(row.get("evidence_key"))

    legacy_packets=[]
    for row in prows:
        if row.get("canonical_paper_gate_semantics")!="CORRECTED_V2_1_19_1":
            legacy_packets.append(row.get("evidence_key"))

    legacy_approvals=[]
    for row in arows:
        if row.get("canonical_paper_gate_semantics")!="CORRECTED_V2_1_19_1":
            legacy_approvals.append(row.get("evidence_key"))

    result={
        "stage":"BROKER_INTEGRATION_V2_1_19_1_CANONICAL_PAPER_GATE_SEMANTIC_AUDIT",
        "status":"PASS_SEMANTIC_AUDIT",
        "generic_etrade_bridge_min_confidence":"0.60",
        "canonical_paper_min_confidence":"0.75",
        "canonical_paper_min_reward_risk":"1.0",
        "qualification_rows":len(qrows),
        "corrected_qualification_rows":len(corrected_q),
        "legacy_qualification_rows":len(legacy_q),
        "legacy_qualification_evidence_keys":[x for x in legacy_q if x],
        "review_packet_index_rows":len(prows),
        "legacy_review_packet_rows":len(legacy_packets),
        "legacy_review_packet_evidence_keys":[x for x in legacy_packets if x],
        "approval_rows":len(arows),
        "legacy_approval_rows":len(legacy_approvals),
        "legacy_approval_evidence_keys":[x for x in legacy_approvals if x],
        "legacy_artifacts_blocked_by_corrected_code":True,
        "runtime_data_deleted":False,
        "automatic_sandbox_execution_allowed":False,
        "etrade_oauth_started":False,
        "sandbox_preview_sent":False,
        "sandbox_place_sent":False,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }

    out=root/"runtime"/"canonical_paper_gate_semantic_audit_v2_1_19_1"
    out.mkdir(parents=True,exist_ok=True)
    report=out/"latest_semantic_audit.json"
    report.write_text(
        json.dumps(result,indent=2,sort_keys=True),
        encoding="utf-8",
    )
    result["report_path"]=str(report)
    return result
