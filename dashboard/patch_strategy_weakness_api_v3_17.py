
from pathlib import Path
import argparse

TARGET = Path("dashboard/trade_analytics_v3_5.py")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()

    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if '"strategy_weakness_map": weakness_map' in text:
        print("V3.17 WEAKNESS API ALREADY PRESENT")
        return 0

    marker = '''    regime_analysis = regime_module.build_market_regime_analysis(
        root,
        list(reversed(numeric[-500:])),
    )

    return {
'''

    replacement = '''    regime_analysis = regime_module.build_market_regime_analysis(
        root,
        list(reversed(numeric[-500:])),
    )

    weakness_path = root / "dashboard" / "strategy_weakness_map_v3_17.py"
    weakness_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_strategy_weakness_map_v3_17",
        weakness_path,
    )
    if weakness_spec is None or weakness_spec.loader is None:
        raise ModuleNotFoundError(str(weakness_path))
    weakness_module = importlib.util.module_from_spec(weakness_spec)
    weakness_spec.loader.exec_module(weakness_module)
    weakness_map = weakness_module.build_strategy_weakness_map({
        "historical": historical,
        "performance_diagnostics": diagnostics,
        "strategy_readiness": readiness,
        "strategy_stress_test": stress_test,
        "strategy_robustness": robustness,
        "market_regime_analysis": regime_analysis,
    })

    return {
'''

    if marker not in text:
        raise RuntimeError("V3.17 WEAKNESS INSERT MARKER NOT FOUND")

    text = text.replace(marker, replacement, 1)

    marker2 = '''        "market_regime_analysis": regime_analysis,
        "source_ledgers": sources,
'''

    replacement2 = '''        "market_regime_analysis": regime_analysis,
        "strategy_weakness_map": weakness_map,
        "source_ledgers": sources,
'''

    if marker2 not in text:
        raise RuntimeError("V3.17 WEAKNESS RETURN MARKER NOT FOUND")

    text = text.replace(marker2, replacement2, 1)
    target.write_text(text, encoding="utf-8")

    print("V3.17 STRATEGY WEAKNESS API: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
