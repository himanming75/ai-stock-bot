from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_broker import (
    ActualPaperOrderValidator,
    AlpacaPaperClient,
    AlpacaPaperConfig,
    CredentialLoader,
    OrderValidationPolicy,
    UrllibHttpTransport,
)


VALIDATION_OPT_IN_ENV = "AI_STOCK_BOT_ENABLE_ALPACA_PAPER_ORDER_VALIDATION"
VALIDATION_CONFIRMATION_ENV = "AI_STOCK_BOT_ALPACA_PAPER_ORDER_VALIDATION_CONFIRMATION"
VALIDATION_CONFIRMATION_TEXT = "VALIDATE ONE EXISTING ALPACA PAPER ORDER ONLY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--client-order-id", required=True)
    parser.add_argument("--max-poll-attempts", type=int, default=5)
    parser.add_argument("--poll-interval-seconds", type=float, default=1.0)
    args = parser.parse_args()

    environ = dict(os.environ)
    if environ.get(VALIDATION_OPT_IN_ENV, "").strip().upper() != "YES":
        raise SystemExit(f"{VALIDATION_OPT_IN_ENV}=YES is required")
    if environ.get(VALIDATION_CONFIRMATION_ENV, "").strip() != VALIDATION_CONFIRMATION_TEXT:
        raise SystemExit(
            f"{VALIDATION_CONFIRMATION_ENV} must equal: {VALIDATION_CONFIRMATION_TEXT}"
        )

    key, secret = CredentialLoader().load(environ)
    client = AlpacaPaperClient(
        config=AlpacaPaperConfig(
            network_read_enabled=True,
            network_write_enabled=False,
            max_retries=2,
        ),
        api_key=key,
        secret_key=secret,
        transport=UrllibHttpTransport(),
    )
    validator = ActualPaperOrderValidator(
        client=client,
        policy=OrderValidationPolicy(
            max_poll_attempts=args.max_poll_attempts,
            poll_interval_seconds=args.poll_interval_seconds,
            require_terminal_status=True,
        ),
    )
    report = validator.validate(client_order_id=args.client_order_id)

    output = Path(args.repository_root).resolve() / "release" / "v113_00" / "actual_validation"
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "stage_range": "V112.01-V113.00",
        "status": "PASS",
        "validation_mode": "ACTUAL_ALPACA_PAPER_READ_ONLY_ORDER_VALIDATION",
        **report.to_json_dict(),
        "paper_base_url": client.config.base_url,
        "write_network_enabled": client.config.network_write_enabled,
        "next_phase": "V113_01_ALPACA_PAPER_ORDER_RECOVERY_AND_RESTART",
    }
    path = output / "actual_alpaca_paper_order_validation_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
