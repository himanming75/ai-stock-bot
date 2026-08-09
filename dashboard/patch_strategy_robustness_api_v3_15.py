
from pathlib import Path
import argparse

TARGET = Path("dashboard/trade_analytics_v3_5.py")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()

    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if '"strategy_robustness": robustness' in text:
        print("V3.15 ROBUSTNESS API ALREADY PRESENT")
        return 0

    marker = '''    stress_test = stress_module.build_strategy_stress_test(
        root,
        list(reversed(numeric[-500:])),
    )

    return {
'''
    replacement = '''    stress_test = stress_module.build_strategy_stress_test(
        root,
        list(reversed(numeric[-500:])),
    )

    robustness_path = root / "dashboard" / "strategy_robustness_v3_15.py"
    robustness_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_strategy_robustness_v3_15",
        robustness_path,
    )
    if robustness_spec is None or robustness_spec.loader is None:
        raise ModuleNotFoundError(str(robustness_path))
    robustness_module = importlib.util.module_from_spec(robustness_spec)
    robustness_spec.loader.exec_module(robustness_module)
    robustness = robustness_module.build_strategy_robustness(
        root,
        list(reversed(numeric[-500:])),
    )

    return {
'''
    if marker not in text:
        raise RuntimeError("V3.15 ROBUSTNESS INSERT MARKER NOT FOUND")
    text = text.replace(marker, replacement, 1)

    marker2 = '''        "strategy_stress_test": stress_test,
        "source_ledgers": sources,
'''
    replacement2 = '''        "strategy_stress_test": stress_test,
        "strategy_robustness": robustness,
        "source_ledgers": sources,
'''
    if marker2 not in text:
        raise RuntimeError("V3.15 ROBUSTNESS RETURN MARKER NOT FOUND")
    text = text.replace(marker2, replacement2, 1)

    target.write_text(text, encoding="utf-8")
    print("V3.15 STRATEGY ROBUSTNESS API: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
