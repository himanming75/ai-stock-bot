from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import (
    ControlledPaperReadValidator,
    READ_CONFIRMATION_ENV,
    READ_CONFIRMATION_TEXT,
    READ_OPT_IN_ENV,
    UrllibHttpTransport,
)
from tools.test_controlled_alpaca_paper_read_v110_01_to_v111_00 import (
    QueueOpener,
    fixture_payloads,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v111_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    environ = {
        READ_OPT_IN_ENV: "YES",
        READ_CONFIRMATION_ENV: READ_CONFIRMATION_TEXT,
        "APCA_API_KEY_ID": "fixture-key",
        "APCA_API_SECRET_KEY": "fixture-secret",
    }
    opener = QueueOpener(fixture_payloads())
    validator = ControlledPaperReadValidator.from_environment(
        environ,
        transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
    )
    report = validator.run()
    result = {
        "stage_range": "V110.01-V111.00",
        "status": "PASS",
        "implementation_type": "CONTROLLED_ALPACA_PAPER_READ_VALIDATION",
        "validation_mode": "OFFLINE_FIXTURE",
        **report.to_json_dict(),
        "request_methods": [
            request.get_method() for request, _ in opener.requests
        ],
        "actual_credentials_used": False,
        "actual_network_used": False,
        "next_phase": "V111_01_CONTROLLED_ALPACA_PAPER_ORDER_OPT_IN",
    }
    (output / "controlled_alpaca_paper_read_fixture_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
