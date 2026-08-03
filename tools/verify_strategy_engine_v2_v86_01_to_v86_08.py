import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v86_01_to_v86_08/actual/"
        "strategy_engine_v2_result.json"
    )
    if not path.exists():
        print(f"RESULT NOT FOUND: {path}")
        return 1

    result = json.loads(path.read_text(encoding="utf-8"))
    decision = result.get("decision", {})
    checks = {
        "stage_range": result.get("stage_range") == "V86.01-V86.08",
        "status_pass": result.get("status") == "PASS",
        "state_ready": result.get("state") == "AI_STRATEGY_ENGINE_V2_READY",
        "decision_valid": decision.get("decision") in {
            "BUY", "SELL", "HOLD", "WATCH"
        },
        "confidence_valid": 0 <= float(decision.get("confidence", -1)) <= 100,
        "paper_only": result.get("paper_only") is True,
        "broker_write_disabled": result.get("broker_write_enabled") is False,
        "order_submission_disabled": (
            result.get("order_submission_enabled") is False
        ),
        "live_trading_disabled": result.get("live_trading_enabled") is False,
        "external_network_disabled": (
            result.get("external_network_enabled") is False
        ),
        "network_requests_zero": result.get("network_requests_executed") == 0,
        "write_requests_zero": result.get("write_requests_executed") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "verification_stage": "V86.08",
        "verification_status": "PASS" if not failed else "FAIL",
        "decision": decision.get("decision"),
        "confidence": decision.get("confidence"),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
