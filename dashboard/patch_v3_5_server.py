from __future__ import annotations
from pathlib import Path
import argparse

TARGET = Path("dashboard/operations_dashboard_v3_2.py")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()
    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")
    if "ai_stock_bot_trade_analytics_v3_5" in text:
        print("V3.5 SERVER ANALYTICS PATCH ALREADY PRESENT")
        return 0
    marker = '\n'.join([
        '        payload["visualization_status"] = (',
        '            "ISOLATED_VISUALIZATION_ERROR: " + type(exc).__name__',
        '        )',
        '',
        '    return payload',
    ])
    replacement = '\n'.join([
        '        payload["visualization_status"] = (',
        '            "ISOLATED_VISUALIZATION_ERROR: " + type(exc).__name__',
        '        )',
        '',
        '    try:',
        '        import importlib.util',
        '',
        '        analytics_path = root / "dashboard" / "trade_analytics_v3_5.py"',
        '        analytics_spec = importlib.util.spec_from_file_location(',
        '            "ai_stock_bot_trade_analytics_v3_5", analytics_path',
        '        )',
        '        if analytics_spec is None or analytics_spec.loader is None:',
        '            raise ModuleNotFoundError(f"Unable to load trade analytics module: {analytics_path}")',
        '        analytics_module = importlib.util.module_from_spec(analytics_spec)',
        '        analytics_spec.loader.exec_module(analytics_module)',
        '        payload["trade_analytics"] = analytics_module.build_trade_analytics(root, payload)',
        '        payload["trade_analytics_status"] = payload["trade_analytics"].get("status", "PASS")',
        '    except Exception as exc:',
        '        payload["trade_analytics"] = {"status": "ISOLATED_ERROR", "historical": {"data_status": "INSUFFICIENT_DATA"}, "validation": {"data_status": "WAITING_FOR_VALIDATION_START"}, "by_symbol": [], "by_exit_reason": [], "daily": [], "recent_numeric_trades": [], "source_ledgers": [], "contracts": {"read_only": True, "broker_network_used": False, "broker_write_performed": False, "order_submission_performed": False, "paper_runtime_modified": False, "production_parameter_modified": False, "production_selector_modified": False, "duplicate_engine_created": False}}',
        '        payload["trade_analytics_status"] = "ISOLATED_TRADE_ANALYTICS_ERROR: " + type(exc).__name__',
        '',
        '    return payload',
    ])
    if marker not in text:
        raise RuntimeError("V3.4 build_status return marker not found")
    target.write_text(text.replace(marker, replacement, 1), encoding="utf-8")
    print("V3.5 SERVER ANALYTICS PATCH: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
