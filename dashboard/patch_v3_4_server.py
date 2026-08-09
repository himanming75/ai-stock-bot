
from __future__ import annotations

from pathlib import Path
import argparse

TARGET = Path("dashboard/operations_dashboard_v3_2.py")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\stock-bot")
    args = parser.parse_args()

    target = Path(args.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if "def _build_status_v3_2(root: Path):" in text:
        print("V3.4 SERVER WRAPPER ALREADY PRESENT")
        return 0

    original = "def build_status(root: Path):"
    if original not in text:
        raise RuntimeError("build_status definition not found")

    text = text.replace(
        original,
        "def _build_status_v3_2(root: Path):",
        1,
    )

    marker = "\n\nclass Handler(BaseHTTPRequestHandler):"
    index = text.find(marker)
    if index < 0:
        raise RuntimeError("Handler marker not found")

    wrapper_lines = [
        "",
        "",
        "def build_status(root: Path):",
        "    payload = _build_status_v3_2(root)",
        "",
        "    try:",
        "        from dashboard.visualization_v3_4 import build_visualization",
        "        payload[\"visualization\"] = build_visualization(root, payload)",
        "        payload[\"visualization_status\"] = \"PASS\"",
        "    except Exception as exc:",
        "        payload[\"visualization\"] = {",
        "            \"equity_history\": [],",
        "            \"daily_realized_pnl\": [],",
        "            \"generic_pnl_history\": [],",
        "            \"position_allocation\": [],",
        "            \"validation_slots\": [],",
        "            \"summary\": {},",
        "            \"contracts\": {",
        "                \"read_only\": True,",
        "                \"broker_network_used\": False,",
        "                \"broker_write_performed\": False,",
        "                \"order_submission_performed\": False,",
        "                \"production_parameter_modified\": False,",
        "            },",
        "        }",
        "        payload[\"visualization_status\"] = (",
        "            \"ISOLATED_VISUALIZATION_ERROR: \" + type(exc).__name__",
        "        )",
        "",
        "    return payload",
        "",
    ]
    wrapper = "\n".join(wrapper_lines)

    text = text[:index] + wrapper + text[index:]
    target.write_text(text, encoding="utf-8")
    print("V3.4 SERVER VISUALIZATION WRAPPER: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
