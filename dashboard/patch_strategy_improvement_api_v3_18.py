from pathlib import Path
import argparse
TARGET=Path("dashboard/trade_analytics_v3_5.py")
def main():
 p=argparse.ArgumentParser(); p.add_argument("--root",default=r"C:\stock-bot"); a=p.parse_args()
 t=Path(a.root)/TARGET; s=t.read_text(encoding="utf-8")
 if '"strategy_improvement_candidates": improvement_candidates' in s:
  print("V3.18 IMPROVEMENT API ALREADY PRESENT"); return 0
 marker='''    weakness_map = weakness_module.build_strategy_weakness_map({
        "historical": historical,
        "performance_diagnostics": diagnostics,
        "strategy_readiness": readiness,
        "strategy_stress_test": stress_test,
        "strategy_robustness": robustness,
        "market_regime_analysis": regime_analysis,
    })

    return {
'''
 repl='''    weakness_map = weakness_module.build_strategy_weakness_map({
        "historical": historical,
        "performance_diagnostics": diagnostics,
        "strategy_readiness": readiness,
        "strategy_stress_test": stress_test,
        "strategy_robustness": robustness,
        "market_regime_analysis": regime_analysis,
    })

    improvement_path = root / "dashboard" / "strategy_improvement_candidates_v3_18.py"
    improvement_spec = importlib.util.spec_from_file_location("ai_stock_bot_strategy_improvement_candidates_v3_18", improvement_path)
    if improvement_spec is None or improvement_spec.loader is None:
        raise ModuleNotFoundError(str(improvement_path))
    improvement_module = importlib.util.module_from_spec(improvement_spec)
    improvement_spec.loader.exec_module(improvement_module)
    improvement_candidates = improvement_module.build_strategy_improvement_candidates({
        "historical": historical,
        "strategy_weakness_map": weakness_map,
    })

    return {
'''
 if marker not in s: raise RuntimeError("V3.18 API INSERT MARKER NOT FOUND")
 s=s.replace(marker,repl,1)
 marker2='''        "strategy_weakness_map": weakness_map,
        "source_ledgers": sources,
'''
 repl2='''        "strategy_weakness_map": weakness_map,
        "strategy_improvement_candidates": improvement_candidates,
        "source_ledgers": sources,
'''
 if marker2 not in s: raise RuntimeError("V3.18 API RETURN MARKER NOT FOUND")
 t.write_text(s.replace(marker2,repl2,1),encoding="utf-8")
 print("V3.18 IMPROVEMENT API: PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
