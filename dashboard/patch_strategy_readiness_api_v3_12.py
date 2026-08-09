
from pathlib import Path
import argparse

TARGET=Path("dashboard/trade_analytics_v3_5.py")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if '"strategy_readiness": readiness' in text:
        print("V3.12 READINESS API ALREADY PRESENT")
        return 0

    marker='''    diagnostics = diagnostics_module.build_performance_diagnostics(
        list(reversed(numeric[-500:]))
    )

    return {
'''
    replacement='''    diagnostics = diagnostics_module.build_performance_diagnostics(
        list(reversed(numeric[-500:]))
    )

    readiness_path = root / "dashboard" / "strategy_readiness_v3_12.py"
    readiness_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_strategy_readiness_v3_12",
        readiness_path,
    )
    if readiness_spec is None or readiness_spec.loader is None:
        raise ModuleNotFoundError(str(readiness_path))
    readiness_module = importlib.util.module_from_spec(readiness_spec)
    readiness_spec.loader.exec_module(readiness_module)
    readiness = readiness_module.build_strategy_readiness({
        "historical": historical,
        "performance_diagnostics": diagnostics,
    })

    return {
'''
    if marker not in text:
        raise RuntimeError("V3.12 READINESS INSERT MARKER NOT FOUND")
    text=text.replace(marker,replacement,1)

    marker2='''        "performance_diagnostics": diagnostics,
        "source_ledgers": sources,
'''
    repl2='''        "performance_diagnostics": diagnostics,
        "strategy_readiness": readiness,
        "source_ledgers": sources,
'''
    if marker2 not in text:
        raise RuntimeError("V3.12 READINESS RETURN MARKER NOT FOUND")
    text=text.replace(marker2,repl2,1)

    target.write_text(text,encoding="utf-8")
    print("V3.12 STRATEGY READINESS API: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
