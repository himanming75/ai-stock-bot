import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v88_17_to_v88_24/actual/"
        "paper_production_release_result.json"
    )
    if not path.exists():
        print(f"RESULT NOT FOUND: {path}")
        return 1

    result = json.loads(path.read_text(encoding="utf-8"))
    checks = {
        "stage_range": result.get("stage_range") == "V88.17-V88.24",
        "status_pass_or_blocked": result.get("status") in {"PASS", "BLOCKED"},
        "allowed_state": result.get("state") in {
            "PAPER_AUTOMATED_TRADING_PRODUCTION_READY",
            "PAPER_PRODUCTION_RELEASE_PENDING_PREREQUISITES",
            "PAPER_PRODUCTION_RELEASE_BLOCKED",
        },
        "certificate_hash": (
            len(
                result.get("certificate", {}).get(
                    "certificate_sha256", ""
                )
            )
            == 64
        ),
        "backup_supported": result.get("backup_supported") is True,
        "rollback_supported": result.get("rollback_supported") is True,
        "paper_only": result.get("paper_only") is True,
        "continuous_loop_disabled": (
            result.get("continuous_loop_enabled") is False
        ),
        "windows_task_disabled": (
            result.get("windows_task_enabled") is False
        ),
        "broker_write_disabled": (
            result.get("broker_write_enabled") is False
        ),
        "order_submission_disabled": (
            result.get("order_submission_enabled") is False
        ),
        "live_trading_disabled": (
            result.get("live_trading_enabled") is False
        ),
        "external_network_disabled": (
            result.get("external_network_enabled") is False
        ),
        "paper_orders_zero": (
            result.get("actual_paper_orders_submitted") == 0
        ),
        "live_orders_zero": result.get("live_orders_submitted") == 0,
        "network_requests_zero": (
            result.get("network_requests_executed") == 0
        ),
        "write_requests_zero": (
            result.get("write_requests_executed") == 0
        ),
    }

    # A valid pending release is a successful verification when only
    # time-based prerequisites remain.
    if result.get("state") == "PAPER_PRODUCTION_RELEASE_PENDING_PREREQUISITES":
        checks["pending_only_time_based"] = (
            bool(result.get("time_based_pending"))
            and not result.get("system_based_pending")
        )

    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "verification_stage": "V88.24",
        "verification_status": "PASS" if not failed else "FAIL",
        "state": result.get("state"),
        "technical_ready": result.get("technical_ready"),
        "production_ready": result.get("production_ready"),
        "blocking_prerequisites": result.get("blocking_prerequisites"),
        "time_based_pending": result.get("time_based_pending"),
        "system_based_pending": result.get("system_based_pending"),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
