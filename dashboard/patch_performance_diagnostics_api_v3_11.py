
from pathlib import Path
import argparse

TARGET = Path("dashboard/trade_analytics_v3_5.py")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()
    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if '"performance_diagnostics": diagnostics' in text:
        print("V3.11 DIAGNOSTICS API ALREADY PRESENT")
        return 0

    marker = '    reconstruction_audit = getattr(collect_closed_trades, "last_reconstruction_audit", {"status":"NOT_RUN"})\n\n    return {\n'
    insert = '''    reconstruction_audit = getattr(collect_closed_trades, "last_reconstruction_audit", {"status":"NOT_RUN"})

    import importlib.util
    diagnostics_path = root / "dashboard" / "performance_diagnostics_v3_11.py"
    diagnostics_spec = importlib.util.spec_from_file_location(
        "ai_stock_bot_performance_diagnostics_v3_11",
        diagnostics_path,
    )
    if diagnostics_spec is None or diagnostics_spec.loader is None:
        raise ModuleNotFoundError(str(diagnostics_path))
    diagnostics_module = importlib.util.module_from_spec(diagnostics_spec)
    diagnostics_spec.loader.exec_module(diagnostics_module)
    diagnostics = diagnostics_module.build_performance_diagnostics(
        list(reversed(numeric[-500:]))
    )

    return {
'''
    if marker not in text:
        raise RuntimeError("V3.11 ANALYTICS INSERT MARKER NOT FOUND")
    text = text.replace(marker, insert, 1)

    marker2 = '''        "trade_detail_contract": {
            "canonical_source_only_when_available": True,
            "max_rows": 500,
            "read_only": True,
        },
        "source_ledgers": sources,
'''
    repl2 = '''        "trade_detail_contract": {
            "canonical_source_only_when_available": True,
            "max_rows": 500,
            "read_only": True,
        },
        "performance_diagnostics": diagnostics,
        "source_ledgers": sources,
'''
    if marker2 not in text:
        raise RuntimeError("V3.11 ANALYTICS RETURN MARKER NOT FOUND")
    text = text.replace(marker2, repl2, 1)
    target.write_text(text, encoding="utf-8")
    print("V3.11 PERFORMANCE DIAGNOSTICS API: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
