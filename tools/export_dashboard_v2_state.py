from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard_v2.dashboard_state import build_dashboard_state


def main() -> int:
    state = build_dashboard_state(ROOT)
    path = (
        ROOT / "release/v85_01_to_v85_08/actual/"
        "dashboard_v2_state.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(state, indent=2, sort_keys=True))
    print(f"STATE_FILE={path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
