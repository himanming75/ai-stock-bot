
from pathlib import Path
import argparse

TARGET = Path("dashboard/trade_analytics_v3_5.py")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()

    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if '"readiness_history": readiness_history' in text:
        print("V3.13 READINESS HISTORY API ALREADY PRESENT")
        return 0

    marker = '''    readiness = readiness_module.build_strategy_readiness({
        "historical": historical,
        "performance_diagnostics": diagnostics,
    })

    return {
'''
    replacement = '''    readiness = readiness_module.build_strategy_readiness({
        "historical": historical,
        "performance_diagnostics": diagnostics,
    })

    history_path = root / "dashboard" / "readiness_history_v3_13.py"
    history_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_readiness_history_v3_13",
        history_path,
    )
    if history_spec is None or history_spec.loader is None:
        raise ModuleNotFoundError(str(history_path))
    history_module = importlib.util.module_from_spec(history_spec)
    history_spec.loader.exec_module(history_module)
    readiness_history = history_module.build_history_summary(
        root,
        readiness,
    )

    return {
'''
    if marker not in text:
        raise RuntimeError("V3.13 HISTORY INSERT MARKER NOT FOUND")
    text = text.replace(marker, replacement, 1)

    marker2 = '''        "strategy_readiness": readiness,
        "source_ledgers": sources,
'''
    replacement2 = '''        "strategy_readiness": readiness,
        "readiness_history": readiness_history,
        "source_ledgers": sources,
'''
    if marker2 not in text:
        raise RuntimeError("V3.13 HISTORY RETURN MARKER NOT FOUND")
    text = text.replace(marker2, replacement2, 1)

    target.write_text(text, encoding="utf-8")
    print("V3.13 READINESS HISTORY API: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
