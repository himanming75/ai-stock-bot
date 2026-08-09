
from pathlib import Path

root=Path(r"C:\stock-bot")
html=(root/"dashboard"/"templates"/"operations_dashboard_v3_2.html").read_text(encoding="utf-8")
analytics=(root/"dashboard"/"trade_analytics_v3_5.py").read_text(encoding="utf-8")

required_html=[
    'id="improvementCandidatesSection"',
    'function loadImprovementCandidates(d)',
    'async function refreshImprovementCandidates()',
    'refreshImprovementCandidates();',
    'AI Strategy Improvement Candidates / AI 전략 개선 후보',
    'Auto Apply OFF / 자동 적용 없음',
]
required_api=[
    '"strategy_improvement_candidates": improvement_candidates',
    'strategy_improvement_candidates_v3_18.py',
]

missing=[x for x in required_html if x not in html]
missing += [x for x in required_api if x not in analytics]

print("V3.18.1 STATIC REPAIR CHECK")
print("HTML/API REQUIRED:",len(required_html)+len(required_api))
print("MISSING:",len(missing))

if missing:
    for item in missing:
        print("MISSING:",item)
    raise SystemExit(2)

print("V3.18.1 STATIC REPAIR CHECK: PASS")
