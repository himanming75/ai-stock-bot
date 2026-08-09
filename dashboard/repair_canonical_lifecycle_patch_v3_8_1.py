
from __future__ import annotations

from pathlib import Path
import argparse

TARGET = Path("dashboard/trade_analytics_v3_5.py")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\stock-bot")
    args = parser.parse_args()

    target = Path(args.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if "ai_stock_bot_canonical_lifecycle_v3_8" in text:
        print("V3.8.1 CANONICAL PATCH ALREADY PRESENT")
        return 0

    # Current main (V3.7) exact function start.
    old_start = "\n".join([
        "def collect_closed_trades(root: Path):",
        "    rows, sources, seen = [], [], set()",
        "    normalizer = _load_v3_6_normalizer(root)",
        "",
        "    for path in _candidate_ledgers(root):",
    ])

    new_start = "\n".join([
        "def collect_closed_trades(root: Path):",
        "    rows, sources, seen = [], [], set()",
        "    normalizer = _load_v3_6_normalizer(root)",
        "",
        "    import importlib.util",
        "    canonical_path = root / \"dashboard\" / \"canonical_lifecycle_source_v3_8.py\"",
        "    canonical_spec = importlib.util.spec_from_file_location(",
        "        \"ai_stock_bot_canonical_lifecycle_v3_8\",",
        "        canonical_path,",
        "    )",
        "    if canonical_spec is None or canonical_spec.loader is None:",
        "        raise ModuleNotFoundError(str(canonical_path))",
        "    canonical_module = importlib.util.module_from_spec(canonical_spec)",
        "    canonical_spec.loader.exec_module(canonical_module)",
        "    canonical_trades = canonical_module.load_canonical_trades(root)",
        "",
        "    for trade in canonical_trades:",
        "        key = (\"CANONICAL\", trade.get(\"record_id\"))",
        "        if key in seen:",
        "            continue",
        "        seen.add(key)",
        "        rows.append(trade)",
        "",
        "    if canonical_trades:",
        "        sources.append(\"runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl\")",
        "",
        "    for path in _candidate_ledgers(root):",
    ])

    if old_start not in text:
        raise RuntimeError("V3.8.1 CURRENT V3.7 FUNCTION START NOT FOUND")

    text = text.replace(old_start, new_start, 1)

    # Current V3.7 exact compact sequence.
    old_sequence = "\n".join([
        '    rows.sort(key=lambda x: x["time"])',
        '    import importlib.util',
        '    reconstruction_path = root / "dashboard" / "cross_ledger_trade_reconstruction_v3_7.py"',
    ])

    new_sequence = "\n".join([
        "    canonical_rows = [",
        "        row for row in rows",
        "        if row.get(\"canonical_actual_round_trip\")",
        "    ]",
        "",
        "    if canonical_rows:",
        "        rows = canonical_rows",
        "        sources = [",
        "            \"runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl\"",
        "        ]",
        "",
        '    rows.sort(key=lambda x: x["time"])',
        '    import importlib.util',
        '    reconstruction_path = root / "dashboard" / "cross_ledger_trade_reconstruction_v3_7.py"',
    ])

    if old_sequence not in text:
        raise RuntimeError("V3.8.1 CURRENT V3.7 RECONSTRUCTION SEQUENCE NOT FOUND")

    text = text.replace(old_sequence, new_sequence, 1)

    # Current build_trade_analytics exact compact block.
    old_build = "\n".join([
        "    normalizer = _load_v3_6_normalizer(root)",
        "    recovery_audit = normalizer.build_recovery_audit(trades)",
        '    reconstruction_audit = getattr(collect_closed_trades, "last_reconstruction_audit", {"status":"NOT_RUN"})',
        "",
        "    return {",
    ])

    new_build = "\n".join([
        "    normalizer = _load_v3_6_normalizer(root)",
        "    recovery_audit = normalizer.build_recovery_audit(trades)",
        "",
        "    import importlib.util",
        "    lifecycle_path = root / \"dashboard\" / \"canonical_lifecycle_source_v3_8.py\"",
        "    lifecycle_spec = importlib.util.spec_from_file_location(",
        "        \"ai_stock_bot_canonical_lifecycle_v3_8_status\",",
        "        lifecycle_path,",
        "    )",
        "    if lifecycle_spec is None or lifecycle_spec.loader is None:",
        "        raise ModuleNotFoundError(str(lifecycle_path))",
        "    lifecycle_module = importlib.util.module_from_spec(lifecycle_spec)",
        "    lifecycle_spec.loader.exec_module(lifecycle_module)",
        "    lifecycle_discovery = lifecycle_module.build_lifecycle_discovery(root)",
        "",
        '    reconstruction_audit = getattr(collect_closed_trades, "last_reconstruction_audit", {"status":"NOT_RUN"})',
        "",
        "    return {",
    ])

    if old_build not in text:
        raise RuntimeError("V3.8.1 CURRENT BUILD ANALYTICS BLOCK NOT FOUND")

    text = text.replace(old_build, new_build, 1)

    old_return = '        "cross_ledger_reconstruction": reconstruction_audit,\n        "validation": '
    new_return = '        "cross_ledger_reconstruction": reconstruction_audit,\n        "canonical_lifecycle_discovery": lifecycle_discovery,\n        "validation": '

    if old_return not in text:
        raise RuntimeError("V3.8.1 RETURN BLOCK NOT FOUND")

    text = text.replace(old_return, new_return, 1)

    target.write_text(text, encoding="utf-8")
    print("V3.8.1 CANONICAL LIFECYCLE PATCH REPAIR: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
