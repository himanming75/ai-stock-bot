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

    if "ai_stock_bot_trade_ledger_normalizer_v3_6" in text:
        print("V3.6 NORMALIZER INTEGRATION ALREADY PRESENT")
        return 0

    start = text.find("def _normalize_closed_trade(record, source):")
    end = text.find("\n\ndef collect_closed_trades(root: Path):", start)

    if start < 0 or end < 0:
        raise RuntimeError("V3.5 normalize function block not found")

    replacement = "\n".join([
        "def _load_v3_6_normalizer(root: Path):",
        "    import importlib.util",
        "",
        "    module_path = root / \"dashboard\" / \"trade_ledger_normalizer_v3_6.py\"",
        "",
        "    spec = importlib.util.spec_from_file_location(",
        "        \"ai_stock_bot_trade_ledger_normalizer_v3_6\",",
        "        module_path,",
        "    )",
        "",
        "    if spec is None or spec.loader is None:",
        "        raise ModuleNotFoundError(f\"Unable to load V3.6 normalizer: {module_path}\")",
        "",
        "    module = importlib.util.module_from_spec(spec)",
        "    spec.loader.exec_module(module)",
        "    return module",
        "",
    ])

    text = text[:start] + replacement + text[end:]

    old_collect = "\n".join([
        "def collect_closed_trades(root: Path):",
        "    rows, sources, seen = [], [], set()",
        "    for path in _candidate_ledgers(root):",
        "        rel = str(path.relative_to(root)).replace(\"\\\\\", \"/\")",
        "        source_used = False",
        "        for record in _read_jsonl(path):",
        "            trade = _normalize_closed_trade(record, rel)",
    ])

    new_collect = "\n".join([
        "def collect_closed_trades(root: Path):",
        "    rows, sources, seen = [], [], set()",
        "    normalizer = _load_v3_6_normalizer(root)",
        "",
        "    for path in _candidate_ledgers(root):",
        "        rel = str(path.relative_to(root)).replace(\"\\\\\", \"/\")",
        "        source_used = False",
        "",
        "        for record in _read_jsonl(path):",
        "            trade = normalizer.normalize_closed_trade(record, rel)",
    ])

    if old_collect not in text:
        raise RuntimeError("V3.5 collect_closed_trades marker not found")

    text = text.replace(old_collect, new_collect, 1)

    old_return = "\n".join([
        "    return {",
        "        \"status\": historical[\"data_status\"],",
        "        \"historical\": historical,",
    ])

    new_return = "\n".join([
        "    normalizer = _load_v3_6_normalizer(root)",
        "    recovery_audit = normalizer.build_recovery_audit(trades)",
        "",
        "    return {",
        "        \"status\": historical[\"data_status\"],",
        "        \"historical\": historical,",
        "        \"recovery_audit\": recovery_audit,",
    ])

    if old_return not in text:
        raise RuntimeError("V3.5 return marker not found")

    text = text.replace(old_return, new_return, 1)
    target.write_text(text, encoding="utf-8")
    print("V3.6 TRADE LEDGER NORMALIZATION INTEGRATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())