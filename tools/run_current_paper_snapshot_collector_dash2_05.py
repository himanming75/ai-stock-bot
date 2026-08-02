from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.current_paper_snapshot_collector import (
    PAPER_BASE_URL,
    CurrentPaperSnapshotCollector,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--base-url", default=PAPER_BASE_URL)
    parser.add_argument("--timeout-seconds", type=int, default=10)
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    result = CurrentPaperSnapshotCollector().run(
        output_path=root/"release/dash2_05/actual/current_paper_snapshot.json",
        result_path=root/"release/dash2_05/actual/current_paper_snapshot_collector_result.json",
        enable_network=args.enable_network,
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print("RESULT_FILE=" + result["result_path"])
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
