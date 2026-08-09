
from pathlib import Path
import argparse

TARGET = Path("dashboard/trade_analytics_v3_5.py")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()

    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if '"strategy_stress_test": stress_test' in text:
        print("V3.14 STRESS TEST API ALREADY PRESENT")
        return 0

    marker = '''    readiness_history = history_module.build_history_summary(
        root,
        readiness,
    )

    return {
'''
    replacement = '''    readiness_history = history_module.build_history_summary(
        root,
        readiness,
    )

    stress_path = root / "dashboard" / "strategy_stress_test_v3_14.py"
    stress_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_strategy_stress_test_v3_14",
        stress_path,
    )
    if stress_spec is None or stress_spec.loader is None:
        raise ModuleNotFoundError(str(stress_path))
    stress_module = importlib.util.module_from_spec(stress_spec)
    stress_spec.loader.exec_module(stress_module)
    stress_test = stress_module.build_strategy_stress_test(
        root,
        list(reversed(numeric[-500:])),
    )

    return {
'''
    if marker not in text:
        raise RuntimeError("V3.14 STRESS INSERT MARKER NOT FOUND")
    text = text.replace(marker, replacement, 1)

    marker2 = '''        "readiness_history": readiness_history,
        "source_ledgers": sources,
'''
    replacement2 = '''        "readiness_history": readiness_history,
        "strategy_stress_test": stress_test,
        "source_ledgers": sources,
'''
    if marker2 not in text:
        raise RuntimeError("V3.14 STRESS RETURN MARKER NOT FOUND")
    text = text.replace(marker2, replacement2, 1)

    target.write_text(text, encoding="utf-8")
    print("V3.14 STRATEGY STRESS TEST API: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
