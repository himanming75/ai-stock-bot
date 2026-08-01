from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import ControlledPaperReadValidator, UrllibHttpTransport


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--closed-order-limit", type=int, default=50)
    args = parser.parse_args()

    validator = ControlledPaperReadValidator.from_environment(
        dict(os.environ),
        transport=UrllibHttpTransport(),
        timeout_seconds=10.0,
        max_retries=2,
    )
    report = validator.run(closed_order_limit=args.closed_order_limit)

    output = Path(args.repository_root).resolve() / "release" / "v111_00" / "actual_read"
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "stage_range": "V110.01-V111.00",
        "status": "PASS",
        "validation_mode": "ACTUAL_ALPACA_PAPER_READ_ONLY",
        **report.to_json_dict(),
        "actual_network_used": True,
        "write_network_enabled": False,
        "next_phase": "V111_01_CONTROLLED_ALPACA_PAPER_ORDER_OPT_IN",
    }
    path = output / "actual_alpaca_paper_read_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
