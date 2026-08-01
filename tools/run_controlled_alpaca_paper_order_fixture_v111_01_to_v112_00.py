from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import (
    ControlledPaperOrderOptIn,
    UrllibHttpTransport,
    WRITE_CONFIRMATION_ENV,
    WRITE_CONFIRMATION_TEXT,
    WRITE_OPT_IN_ENV,
)
from tools.test_controlled_alpaca_paper_order_optin_v111_01_to_v112_00 import (
    QueueOpener,
    submission_payloads,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v112_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    environ = {
        WRITE_OPT_IN_ENV: "YES",
        WRITE_CONFIRMATION_ENV: WRITE_CONFIRMATION_TEXT,
        "APCA_API_KEY_ID": "fixture-key",
        "APCA_API_SECRET_KEY": "fixture-secret",
    }
    opener = QueueOpener(submission_payloads())
    optin = ControlledPaperOrderOptIn.from_environment(
        environ,
        transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
    )
    plan = optin.build_plan(
        symbol="AAPL",
        side="buy",
        quantity=Decimal("1"),
        reference_price=Decimal("50"),
        client_order_id="BOT-PAPER-ONE-000001",
    )
    preview = optin.preview(plan)
    report = optin.submit_once(plan)

    result = {
        "stage_range": "V111.01-V112.00",
        "status": "PASS",
        "implementation_type": "CONTROLLED_ALPACA_PAPER_SINGLE_ORDER_OPT_IN",
        "validation_mode": "OFFLINE_FIXTURE",
        "preview": preview.to_json_dict(),
        "submission": report.to_json_dict(),
        "request_methods": [request.get_method() for request, _ in opener.requests],
        "actual_credentials_used": False,
        "actual_network_used": False,
        "next_phase": "V112_01_ACTUAL_ALPACA_PAPER_ORDER_VALIDATION",
    }
    (output / "controlled_alpaca_paper_order_fixture_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
