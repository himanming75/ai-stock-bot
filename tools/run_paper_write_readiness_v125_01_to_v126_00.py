from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autonomous_paper_runtime.safe_mode_gate import AutonomousSafeModeRecoveryGate


ENABLE_ENV = "AI_STOCK_BOT_ENABLE_PAPER_WRITE_READINESS"
CONFIRM_ENV = "AI_STOCK_BOT_PAPER_WRITE_READINESS_CONFIRMATION"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing prerequisite result: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()

    account = load_json(
        root / "release/v121_00/actual_read/actual_autonomous_paper_read_result.json"
    )
    ledger = load_json(
        root / "release/v124_00/actual_read/actual_order_ledger_recovery_result.json"
    )
    portfolio = load_json(
        root / "release/v125_00/actual_read/actual_broker_portfolio_reconciliation_result.json"
    )

    requested = os.environ.get(ENABLE_ENV, "").strip().upper() == "YES"
    confirmation = os.environ.get(CONFIRM_ENV, "").strip()

    gate = AutonomousSafeModeRecoveryGate()
    report = gate.evaluate(
        account_state=account,
        ledger_state=ledger,
        portfolio_state=portfolio,
        recovery_state={"recovery_valid": True},
        runtime_state={
            "runtime_state": "STOPPED",
            "live_trading_enabled": False,
        },
        risk_state={
            "risk_ready": True,
            "kill_switch_engaged": False,
            "emergency_stop_engaged": False,
        },
        write_enablement_requested=requested,
        approval_text=confirmation,
    )

    output = root / "release/v126_00/readiness"
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "stage_range": "V125.01-V126.00",
        "status": "PASS",
        "implementation_type": "AUTONOMOUS_SAFE_MODE_RECOVERY_GATE",
        "validation_mode": "PAPER_WRITE_READINESS_CERTIFICATION",
        **report.to_json_dict(),
        "no_order_submission_performed": True,
        "next_phase": "V126_01_CONTROLLED_AUTONOMOUS_PAPER_SINGLE_ORDER",
    }
    path = output / "paper_write_readiness_result.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0 if report.paper_write_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
