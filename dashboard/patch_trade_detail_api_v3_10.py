
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

    if '"trade_details": list(reversed(numeric[-500:]))' in text:
        print("V3.10 TRADE DETAIL API ALREADY PRESENT")
        return 0

    old = '''        "recent_numeric_trades": list(reversed(numeric[-20:])),
        "source_ledgers": sources,
'''

    new = '''        "recent_numeric_trades": list(reversed(numeric[-20:])),
        "trade_details": list(reversed(numeric[-500:])),
        "trade_detail_contract": {
            "canonical_source_only_when_available": True,
            "max_rows": 500,
            "read_only": True,
        },
        "source_ledgers": sources,
'''

    if old not in text:
        raise RuntimeError("V3.10 TRADE ANALYTICS RETURN MARKER NOT FOUND")

    target.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("V3.10 CANONICAL TRADE DETAIL API: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
