from .common import safe_status

def build_strategy_registry(shadow):
    entries=[{
        "strategy_id":"CURRENT_CHAMPION","role":"CHAMPION","state":"ACTIVE_REFERENCE",
        "write_locked":True,
    }]
    for c in shadow.get("challengers") or []:
        entries.append({
            "strategy_id":c.get("challenger_id"),"role":"CHALLENGER",
            "state":"SHADOW_ONLY","source_candidate_id":c.get("source_candidate_id"),
            "write_locked":True,
        })
    return safe_status("V3.22_ADAPTIVE_STRATEGY_REGISTRY","PASS",
        entry_count=len(entries),entries=entries,registry_write_performed=False)
