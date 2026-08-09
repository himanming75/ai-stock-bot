
from datetime import datetime, timezone
from pathlib import Path
import argparse
import importlib.util
import json


def load(path, name):
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

    source = load(root/"dashboard"/"canonical_lifecycle_source_v3_8.py", "v38_source")
    discovery = source.build_lifecycle_discovery(root)

    analytics = load(root/"dashboard"/"trade_analytics_v3_5.py", "v38_analytics")
    trades, sources = analytics.collect_closed_trades(root)
    numeric = [trade for trade in trades if trade.get("pnl") is not None]

    report = {
        "stage": "V3.8_CANONICAL_LIFECYCLE_SOURCE_DISCOVERY_AND_RECOVERY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": discovery["status"],
        "discovery": discovery,
        "analytics_after_canonical_recovery": {
            "source_ledgers": sources,
            "trade_count": len(trades),
            "numeric_trade_count": len(numeric),
            "net_realized_pnl": sum(trade["pnl"] for trade in numeric) if numeric else None,
        },
        "contracts": {
            "runtime_source_files_modified": False,
            "broker_network_used": False,
            "broker_write_performed": False,
            "order_submission_performed": False,
            "paper_runtime_modified": False,
            "production_parameter_modified": False,
            "duplicate_engine_created": False,
        },
    }

    if args.write:
        output = root/"runtime"/"dashboard_lifecycle_discovery_v3_8"/"latest_lifecycle_source_audit.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
