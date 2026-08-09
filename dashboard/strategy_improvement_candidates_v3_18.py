from __future__ import annotations
from datetime import datetime, timezone

WEIGHT={"INFO":0,"LOW":1,"MEDIUM":2,"HIGH":3,"CRITICAL":4}
EVIDENCE={
"SAMPLE":("COLLECT_MORE_EVIDENCE","Canonical sample / 정규 거래 표본"),
"DOWNSIDE":("COLLECT_DOWNSIDE_EVIDENCE","Downside evidence / 하방 증거"),
"DIVERSIFICATION":("EXPAND_SYMBOL_EVIDENCE","Symbol coverage / 종목 범위"),
"STRESS":("COLLECT_STRESS_EVIDENCE","Stress evidence / 스트레스 증거"),
"ROBUSTNESS":("COLLECT_ROBUSTNESS_EVIDENCE","Robustness evidence / 견고성 증거"),
"REGIME":("CAPTURE_REGIME_METADATA","Regime metadata / 시장환경 메타데이터"),
"READINESS":("CLEAR_READINESS_EVIDENCE_GAPS","Readiness evidence / 준비도 증거")}
PERFORMANCE={
"PROFITABILITY":("EXIT_RULE_CANDIDATE","Exit rules / 청산 규칙"),
"RISK":("RISK_LIMIT_CANDIDATE","Risk limits / 리스크 한도"),
"STRESS":("EXECUTION_FRICTION_CANDIDATE","Execution robustness / 체결 견고성"),
"ROBUSTNESS":("ENTRY_FILTER_CANDIDATE","Entry filters / 진입 필터"),
"REGIME":("REGIME_FILTER_CANDIDATE","Regime filter / 시장환경 필터"),
"READINESS":("READINESS_BLOCKER_CANDIDATE","Readiness blockers / 준비도 차단요인")}

def _candidate(i,n):
    wt=i.get("weakness_type","EVIDENCE_GAP"); cat=i.get("category","UNKNOWN")
    sev=i.get("severity","INFO")
    if wt=="PERFORMANCE_RISK" and n>=10:
        action,target=PERFORMANCE.get(cat,("STRATEGY_REVIEW_CANDIDATE","Strategy logic / 전략 로직"))
        expected="Test whether the observed performance weakness can be reduced without damaging other metrics."
        side="A local improvement can reduce trade frequency, increase concentration, or worsen another regime."
        validation="Build an isolated Shadow Challenger and compare it with the current Champion. Do not apply to Paper or Live."
    else:
        action,target=EVIDENCE.get(cat,("COLLECT_MORE_EVIDENCE","Evidence / 증거"))
        expected="Increase confidence before proposing a strategy-rule change."
        side="More evidence may confirm the current strategy or reveal a different weakness."
        validation="Continue canonical Paper evidence collection and re-score only after new observed evidence exists."
    return {"candidate_id":"V3.18-"+str(i.get("code","UNKNOWN")),
      "source_weakness_code":i.get("code"),"source_category":cat,"source_severity":sev,
      "weakness_type":wt,"proposal_type":action,"change_target":target,
      "problem_evidence":i.get("evidence") or {},"expected_effect":expected,
      "potential_side_effects":side,"required_validation":validation,
      "priority_score":min(100,WEIGHT.get(sev,0)*20+(10 if wt=="PERFORMANCE_RISK" else 0)),
      "confidence":i.get("confidence","LOW"),"execution_eligible":False,
      "auto_apply":False,"paper_parameter_change_allowed":False,"live_change_allowed":False}

def build_strategy_improvement_candidates(analytics):
    h=analytics.get("historical") or {}; w=analytics.get("strategy_weakness_map") or {}
    n=int(h.get("numeric_trade_count") or 0)
    cs=[_candidate(i,n) for i in (w.get("issues") or [])]
    cs.sort(key=lambda x:x["priority_score"],reverse=True)
    evidence_actions={x[0] for x in EVIDENCE.values()}|{"COLLECT_MORE_EVIDENCE"}
    ec=sum(c["proposal_type"] in evidence_actions for c in cs); sc=len(cs)-ec
    mode="EVIDENCE_COLLECTION_ONLY" if n<10 else ("SHADOW_CANDIDATES_AVAILABLE" if sc else "EVIDENCE_FIRST")
    return {"stage":"V3.18_AI_STRATEGY_IMPROVEMENT_CANDIDATES",
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),"status":"PASS","mode":mode,
      "canonical_numeric_trade_count":n,"candidate_count":len(cs),
      "evidence_collection_candidate_count":ec,"strategy_change_candidate_count":sc,
      "candidates":cs,"top_candidates":cs[:5],
      "contracts":{"diagnostic_proposal_only":True,"automatic_strategy_change":False,
      "automatic_parameter_change":False,"automatic_promotion":False,"paper_parameter_change":False,
      "live_change":False,"broker_write_performed":False,"order_submission_performed":False,
      "paper_runtime_modified":False,"canonical_runtime_modified":False}}
