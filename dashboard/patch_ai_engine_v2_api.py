
from pathlib import Path
import argparse

TARGET=Path("dashboard/trade_analytics_v3_5.py")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if '"ai_engine_v2": ai_engine_v2' in text:
        print("AI ENGINE V2 API ALREADY PRESENT")
        return 0

    marker = '''    improvement_candidates = improvement_module.build_strategy_improvement_candidates({
        "historical": historical,
        "strategy_weakness_map": weakness_map,
    })

    return {
'''

    replacement = '''    improvement_candidates = improvement_module.build_strategy_improvement_candidates({
        "historical": historical,
        "strategy_weakness_map": weakness_map,
    })

    import sys
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from ai_engine_v2.integrated_engine_v3_30 import build_integrated_ai_engine_v2

    ai_engine_v2 = build_integrated_ai_engine_v2(
        {
            "historical": historical,
            "market_regime_analysis": regime_analysis,
            "strategy_improvement_candidates": improvement_candidates,
        },
        status_payload,
    )

    return {
'''

    if marker not in text:
        raise RuntimeError("AI ENGINE V2 API INSERT MARKER NOT FOUND")
    text=text.replace(marker,replacement,1)

    marker2 = '''        "strategy_improvement_candidates": improvement_candidates,
        "source_ledgers": sources,
'''
    replacement2 = '''        "strategy_improvement_candidates": improvement_candidates,
        "ai_engine_v2": ai_engine_v2,
        "source_ledgers": sources,
'''

    if marker2 not in text:
        raise RuntimeError("AI ENGINE V2 API RETURN MARKER NOT FOUND")
    text=text.replace(marker2,replacement2,1)

    target.write_text(text,encoding="utf-8")
    print("AI ENGINE V2 API INTEGRATION: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
