from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import (
    ActualPaperOrderValidator,
    AlpacaPaperClient,
    AlpacaPaperConfig,
    OrderValidationPolicy,
    UrllibHttpTransport,
)
from tools.test_actual_alpaca_paper_order_validation_v112_01_to_v113_00 import (
    QueueOpener,
    account,
    order,
    positions,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v113_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    opener = QueueOpener([
        order("accepted"),
        order("partially_filled", "0.5"),
        order("filled", "1"),
        account(),
        positions(),
    ])
    client = AlpacaPaperClient(
        config=AlpacaPaperConfig(
            network_read_enabled=True,
            network_write_enabled=False,
            max_retries=0,
        ),
        api_key="fixture-key",
        secret_key="fixture-secret",
        transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
    )
    validator = ActualPaperOrderValidator(
        client=client,
        policy=OrderValidationPolicy(
            max_poll_attempts=5,
            poll_interval_seconds=0,
            require_terminal_status=True,
        ),
        sleep=lambda _: None,
    )
    report = validator.validate(
        client_order_id="BOT-PAPER-ONE-000001"
    )
    result = {
        "stage_range": "V112.01-V113.00",
        "status": "PASS",
        "implementation_type": "ACTUAL_ALPACA_PAPER_ORDER_VALIDATION",
        "validation_mode": "OFFLINE_FIXTURE",
        **report.to_json_dict(),
        "request_methods": [request.get_method() for request, _ in opener.requests],
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "next_phase": "V113_01_ALPACA_PAPER_ORDER_RECOVERY_AND_RESTART",
    }
    (output / "actual_alpaca_paper_order_validation_fixture_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
