
from pathlib import Path
import argparse

TARGET = Path("dashboard/trade_analytics_v3_5.py")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()
    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if '"market_regime_analysis": regime_analysis' in text:
        print("V3.16 REGIME API ALREADY PRESENT")
        return 0

    marker = '''    robustness = robustness_module.build_strategy_robustness(
        root,
        list(reversed(numeric[-500:])),
    )

    return {
'''
    replacement = '''    robustness = robustness_module.build_strategy_robustness(
        root,
        list(reversed(numeric[-500:])),
    )

    regime_path = root / "dashboard" / "market_regime_analysis_v3_16.py"
    regime_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_market_regime_analysis_v3_16",
        regime_path,
    )
    if regime_spec is None or regime_spec.loader is None:
        raise ModuleNotFoundError(str(regime_path))
    regime_module = importlib.util.module_from_spec(regime_spec)
    regime_spec.loader.exec_module(regime_module)
    regime_analysis = regime_module.build_market_regime_analysis(
        root,
        list(reversed(numeric[-500:])),
    )

    return {
'''
    if marker not in text:
        raise RuntimeError("V3.16 REGIME INSERT MARKER NOT FOUND")
    text = text.replace(marker, replacement, 1)

    marker2 = '''        "strategy_robustness": robustness,
        "source_ledgers": sources,
'''
    replacement2 = '''        "strategy_robustness": robustness,
        "market_regime_analysis": regime_analysis,
        "source_ledgers": sources,
'''
    if marker2 not in text:
        raise RuntimeError("V3.16 REGIME RETURN MARKER NOT FOUND")
    text = text.replace(marker2, replacement2, 1)

    target.write_text(text, encoding="utf-8")
    print("V3.16 MARKET REGIME API: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
