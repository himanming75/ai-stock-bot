
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import importlib.util
import json


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\stock-bot")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)

    analytics = load_module(
        root / "dashboard" / "trade_analytics_v3_5.py",
        "ai_stock_bot_v3_5_for_v3_6_audit",
    )
    trades, sources = analytics.collect_closed_trades(root)

    normalizer = load_module(
        root / "dashboard" / "trade_ledger_normalizer_v3_6.py",
        "ai_stock_bot_v3_6_normalizer_audit",
    )
    audit = normalizer.build_recovery_audit(trades)

    report = {
        "stage": "V3.6_TRADE_LEDGER_NORMALIZATION_AND_PERFORMANCE_DATA_RECOVERY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "PASS_RECOVERED_NUMERIC_PNL"
            if audit["numeric_pnl_recovered_count"] > 0
            else "PASS_DIAGNOSTIC_NO_NUMERIC_PNL"
        ),
        "source_ledgers": sources,
        "recovery_audit": audit,
        "contracts": {
            "runtime_source_files_modified": False,
            "normalized_copy_created": False,
            "broker_network_used": False,
            "broker_write_performed": False,
            "order_submission_performed": False,
            "paper_runtime_modified": False,
            "production_parameter_modified": False,
            "production_selector_modified": False,
            "duplicate_engine_created": False,
        },
    }

    if args.write:
        output = root / "runtime" / "dashboard_trade_recovery_v3_6" / "latest_trade_recovery_audit.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, default=str),
            encoding="utf-8",
        )

    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
