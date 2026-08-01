from pathlib import Path
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads((
        Path(args.repository_root).resolve()
        / "release" / "v110_00" / "output"
        / "alpaca_paper_broker_integration_result.json"
    ).read_text(encoding="utf-8"))

    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "ALPACA_PAPER_BROKER_INTEGRATION_FOUNDATION",
        "paper_url_locked": result["paper_base_url"] == "https://paper-api.alpaca.markets",
        "live_url_blocked": result["live_url_blocked"] is True,
        "credentials_configured": result["credential_headers_configured"] is True,
        "read_default_off": result["read_network_enabled"] is False,
        "write_default_off": result["write_network_enabled"] is False,
        "read_blocked": result["read_network_blocked"] is True,
        "write_blocked": result["write_network_blocked"] is True,
        "preview_ready": result["order_preview_ready"] is True,
        "reconciliation_match": result["reconciliation_matched"] is True,
        "network_zero": result["network_requests_executed"] == 0,
        "write_zero": result["write_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_orders_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V109.01-V110.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
