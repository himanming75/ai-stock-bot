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
    AlpacaPaperClient,
    AlpacaPaperConfig,
    CredentialLoader,
    UrllibHttpTransport,
)
from autonomous_paper_runtime import AutonomousPaperReadSession


OPT_IN_ENV = "AI_STOCK_BOT_ENABLE_ACTUAL_AUTONOMOUS_PAPER_READ"
CONFIRMATION_ENV = "AI_STOCK_BOT_ACTUAL_AUTONOMOUS_PAPER_READ_CONFIRMATION"
CONFIRMATION_TEXT = "READ ACTUAL ALPACA PAPER ACCOUNT AUTONOMOUSLY GET ONLY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--closed-order-limit", type=int, default=50)
    args = parser.parse_args()

    environ = dict(os.environ)
    if environ.get(OPT_IN_ENV, "").strip().upper() != "YES":
        raise SystemExit(f"{OPT_IN_ENV}=YES is required")
    if environ.get(CONFIRMATION_ENV, "").strip() != CONFIRMATION_TEXT:
        raise SystemExit(f"{CONFIRMATION_ENV} must equal: {CONFIRMATION_TEXT}")

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
    # Older client versions may not track request methods. The read session
    # treats a missing audit list as the known five-GET contract.
    snapshot = AutonomousPaperReadSession(
        client=client,
        closed_order_limit=args.closed_order_limit,
    ).run()

    output = (
        Path(args.repository_root).resolve()
        / "release" / "v121_00" / "actual_read"
    )
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "stage_range": "V120.01-V121.00",
        "status": "PASS",
        "implementation_type": "ACTUAL_AUTONOMOUS_PAPER_READ_SESSION",
        "validation_mode": "ACTUAL_ALPACA_PAPER_GET_ONLY",
        "actual_credentials_used": True,
        "actual_external_network_used": True,
        **snapshot.to_json_dict(),
        "next_phase": "V121_01_AUTONOMOUS_PAPER_READ_RECONCILIATION",
    }
    path = output / "actual_autonomous_paper_read_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
