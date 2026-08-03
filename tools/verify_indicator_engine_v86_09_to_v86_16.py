import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v86_09_to_v86_16/actual/"
        "indicator_engine_result.json"
    )
    if not path.exists():
        print(f"RESULT NOT FOUND: {path}")
        return 1

    result = json.loads(path.read_text(encoding="utf-8"))
    indicators = result.get("indicators", {})
    checks = {
        "stage_range": result.get("stage_range") == "V86.09-V86.16",
        "status_pass": result.get("status") == "PASS",
        "state_ready": result.get("state") == "INDICATOR_ENGINE_READY",
        "rsi_available": indicators.get("rsi_14") is not None,
        "ema_20_available": indicators.get("ema_20") is not None,
        "ema_50_available": indicators.get("ema_50") is not None,
        "ema_200_available": indicators.get("ema_200") is not None,
        "macd_available": indicators.get("macd") is not None,
        "atr_available": indicators.get("atr_14") is not None,
        "bollinger_available": indicators.get("bollinger_middle") is not None,
        "vwap_available": indicators.get("vwap") is not None,
        "signals_available": len(indicators.get("strategy_signals", [])) >= 4,
        "paper_only": result.get("paper_only") is True,
        "broker_write_disabled": result.get("broker_write_enabled") is False,
        "order_submission_disabled": result.get("order_submission_enabled") is False,
        "live_trading_disabled": result.get("live_trading_enabled") is False,
        "external_network_disabled": result.get("external_network_enabled") is False,
        "network_requests_zero": result.get("network_requests_executed") == 0,
        "write_requests_zero": result.get("write_requests_executed") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "verification_stage": "V86.16",
        "verification_status": "PASS" if not failed else "FAIL",
        "symbol": indicators.get("symbol"),
        "indicator_count": indicators.get("indicator_count"),
        "signal_count": len(indicators.get("strategy_signals", [])),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
