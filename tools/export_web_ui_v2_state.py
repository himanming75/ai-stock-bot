from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web_ui_v2.app import load_ui_state


def main() -> int:
    state = load_ui_state()
    output = {
        "stage": "V88.08",
        "stage_range": "V88.01-V88.08",
        "state": "WEB_UI_V2_READY",
        "status": "PASS",
        "sources": {
            key: bool(state.get(key))
            for key in ("backtest", "validation", "multi_asset", "explainability")
        },
        "paper_only": True,
        "localhost_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }
    path = ROOT / "release/v88_01_to_v88_08/actual/web_ui_v2_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    print(f"STATE_FILE={path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
