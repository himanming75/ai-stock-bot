from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.data_loader import load_dashboard_sources
from dashboard.panels import build_dashboard_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    payload = build_dashboard_payload(load_dashboard_sources(root))
    output = root/"release/dash1_01_to_dash1_04/actual/dashboard_snapshot.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    print("DASHBOARD_SNAPSHOT=" + str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
