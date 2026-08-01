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
            / "v108_00"
            / "output"
            / "runtime_risk_manager_result.json"
        ).read_text(encoding="utf-8")
    )
    stats = result["stats"]
    checks = {
        "status_pass": result["status"] == "PASS",
        "real_implementation": result["implementation_type"] == "RUNTIME_RISK_MANAGER_FOUNDATION",
        "normal_approved": result["normal_decision"] == "APPROVED",
        "exposure_rejected": result["exposure_decision"] == "REJECTED",
        "exposure_reason": result["exposure_reason"] == "max_symbol_exposure",
        "halted_after_drawdown": result["halted_decision"] == "HALTED",
        "emergency_reason": result["halted_reason"] == "emergency_stop_engaged",
        "sell_also_halted": result["sell_after_halt_decision"] == "HALTED",
        "emergency_stop_true": result["emergency_stop_engaged"] is True,
        "new_buys_false": result["new_buys_allowed"] is False,
        "drawdown_100": Decimal(result["drawdown"]) == Decimal("100"),
        "daily_loss_50": Decimal(result["daily_realized_pnl"]) == Decimal("-50"),
        "intents_four": stats["intents_received"] == 4,
        "approved_one": stats["approved"] == 1,
        "rejected_one": stats["rejected"] == 1,
        "halted_two": stats["halted"] == 2,
        "network_zero": result["network_requests_executed"] == 0,
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_orders_zero": result["live_orders_submitted"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {
        "stage_range": "V107.01-V108.00",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
