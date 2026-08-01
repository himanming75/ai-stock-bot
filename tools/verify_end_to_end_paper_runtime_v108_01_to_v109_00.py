from pathlib import Path
from decimal import Decimal
import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    result = json.loads(
        (
            Path(args.repository_root).resolve()
            / "release"
            / "v109_00"
            / "output"
            / "end_to_end_paper_runtime_result.json"
        ).read_text(encoding="utf-8")
    )
    stats = result["stats"]
    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "END_TO_END_PAPER_RUNTIME_FOUNDATION",
        "runtime_stopped": result["runtime_final_state"] == "STOPPED",
        "cycle_completed": result["cycle_completed"] is True,
        "signal_one": result["signal_count"] == 1,
        "risk_approved": result["risk_status"] == "APPROVED",
        "execution_accepted": result["execution_status"] == "ACCEPTED",
        "fill_completed": result["fill_status"] == "FILLED",
        "position_one": Decimal(result["position_quantity"]) == Decimal("1"),
        "cash_950": Decimal(result["final_cash"]) == Decimal("950"),
        "equity_1000": Decimal(result["final_equity"]) == Decimal("1000"),
        "heartbeat_two": result["heartbeat_count"] == 2,
        "recovery_exists": result["recovery_exists"] is True,
        "recovery_stopped": result["recovery_state"] == "STOPPED",
        "cycles_one": stats["cycles_started"] == 1,
        "completed_one": stats["cycles_completed"] == 1,
        "fills_one": stats["fills_completed"] == 1,
        "network_zero": result["network_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_orders_zero": result["live_orders_submitted"] == 0,
        "actual_transport_disabled": result["actual_broker_transport_enabled"] is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V108.01-V109.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
