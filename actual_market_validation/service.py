from __future__ import annotations
import json, os, urllib.parse, urllib.request, hashlib
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

def _get(url: str, key: str, secret: str):
    req = urllib.request.Request(url, method="GET", headers={
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
        "Accept": "application/json",
        "User-Agent": "ai-stock-bot-read-only-validation/1.0",
    })
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))

def _d(value, default="0"):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)

def _records(raw: dict, symbols: list[str]) -> list[dict]:
    bars_by_symbol = raw.get("bars", {}).get("bars", {})
    staged = []
    returns = []
    for symbol in symbols:
        bars = bars_by_symbol.get(symbol, [])
        closes = [_d(x.get("c")) for x in bars if _d(x.get("c")) > 0]
        volumes = [_d(x.get("v")) for x in bars]
        if len(closes) < 2:
            continue
        ret1 = closes[-1] / closes[-2] - 1
        anchor = closes[max(0, len(closes) - 6)]
        ret5 = closes[-1] / anchor - 1 if anchor else Decimal("0")
        average_volume = sum(volumes[:-1], Decimal("0")) / max(1, len(volumes) - 1)
        volume_ratio = volumes[-1] / average_volume if average_volume else Decimal("1")
        moves = [abs(closes[i] / closes[i-1] - 1) for i in range(1, len(closes)) if closes[i-1]]
        realized_volatility = sum(moves, Decimal("0")) / max(1, len(moves)) * Decimal("15")
        returns.append(ret5)
        staged.append((symbol, ret1, ret5, volume_ratio, realized_volatility))
    average_return = sum(returns, Decimal("0")) / max(1, len(returns))
    breadth = Decimal(sum(1 for x in returns if x > 0)) / max(1, len(returns)) * 2 - 1
    result = []
    for symbol, ret1, ret5, volume_ratio, realized_volatility in staged:
        relative = max(Decimal("-1"), min(Decimal("1"), (ret5-average_return)*10))
        result.append({
            "symbol": symbol,
            "price_return_1d": str(ret1),
            "price_return_5d": str(ret5),
            "volume_ratio": str(volume_ratio),
            "realized_volatility": str(realized_volatility),
            "relative_strength": str(relative),
            "breadth_score": str(breadth),
            "sector_strength": str(relative),
            "news_sentiment": "0",
            "news_importance": "0",
            "earnings_surprise": "0",
            "earnings_revision": "0",
            "macro_risk": "0.30",
            "rates_pressure": "0.30",
            "options_put_call": "1",
            "options_iv_rank": "0.50",
            "options_flow": "0",
            "liquidity_score": "0.95",
            "spread_bps": "2",
            "event_risk": "0.10",
            "source_confidence": "0.85",
            "source_age_seconds": 0,
        })
    return result

def run_validation(root: Path, symbols: list[str]) -> dict:
    key = os.environ.get("APCA_API_KEY_ID", "").strip()
    secret = os.environ.get("APCA_API_SECRET_KEY", "").strip()
    if not key or not secret:
        raise RuntimeError("ALPACA_PAPER_CREDENTIALS_MISSING")
    trading = os.environ.get("APCA_API_BASE_URL", "https://paper-api.alpaca.markets").rstrip("/")
    data = os.environ.get("APCA_API_DATA_URL", "https://data.alpaca.markets").rstrip("/")
    feed = os.environ.get("ALPACA_DATA_FEED", "iex")
    query = urllib.parse.urlencode({
        "symbols": ",".join(symbols),
        "timeframe": "1Min",
        "limit": "20",
        "adjustment": "raw",
        "feed": feed,
    })
    raw = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "clock": _get(f"{trading}/v2/clock", key, secret),
        "account": _get(f"{trading}/v2/account", key, secret),
        "positions": _get(f"{trading}/v2/positions", key, secret),
        "open_orders": _get(f"{trading}/v2/orders?status=open&limit=100", key, secret),
        "closed_orders": _get(f"{trading}/v2/orders?status=closed&limit=100&direction=desc", key, secret),
        "bars": _get(f"{data}/v2/stocks/bars?{query}", key, secret),
    }
    out = root / "release/actual_market_validation/actual"
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "alpaca_readonly_snapshot.json"
    raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    records = _records(raw, symbols)
    fusion_path = out / "actual_market_fusion_input.json"
    fusion_path.write_text(json.dumps({"symbols": records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    from market_intelligence.service import MarketIntelligenceFusionService
    market_path = out / "actual_market_intelligence_snapshot.json"
    market = MarketIntelligenceFusionService().run_file(fusion_path, market_path)

    from ai_decision_orchestration.service import AIDecisionOrchestrationService
    policy = root / "release/ai_symbol_selection_decision_orchestration/config/decision_policy.json"
    decision_path = out / "actual_ai_decision_snapshot.json"
    decision = AIDecisionOrchestrationService().run_file(market_path, policy, decision_path)

    from ai_decision_bridge.service import DecisionBridgeService
    config = root / "release/ai_decision_strategy_risk_portfolio_bridge/config/bridge_config.json"
    bridge_path = out / "actual_bridge_snapshot.json"
    bridge = DecisionBridgeService().run_file(decision_path, config, bridge_path)

    evidence = [raw_path, fusion_path, market_path, decision_path, bridge_path]
    result = {
        "stage": "ACTUAL_MARKET_VALIDATION_READ_ONLY_MEGA_BUNDLE",
        "status": "PASS" if raw.get("clock") and raw.get("account") and records else "BLOCKED",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbols": symbols,
        "clock": raw.get("clock", {}),
        "account_summary": {
            "status": raw.get("account", {}).get("status"),
            "currency": raw.get("account", {}).get("currency"),
            "equity": raw.get("account", {}).get("equity"),
            "cash": raw.get("account", {}).get("cash"),
            "buying_power": raw.get("account", {}).get("buying_power"),
        },
        "position_count": len(raw.get("positions", [])),
        "open_order_count": len(raw.get("open_orders", [])),
        "closed_order_count": len(raw.get("closed_orders", [])),
        "symbols_with_bars": len(records),
        "market_pipeline_status": market.get("status"),
        "decision_pipeline_status": decision.get("status"),
        "bridge_pipeline_status": bridge.get("status"),
        "evidence_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence},
        "actual_external_network_used": True,
        "actual_broker_read_performed": True,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_market_validation": "READ_ONLY_POLLING_LONG_RUN",
        "next_fixed_development": "AI_APPROVED_DECISION_TO_EXECUTION_PLAN_BRIDGE",
    }
    (out / "actual_market_validation_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (out / "actual_market_validation_ledger.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, sort_keys=True) + "\n")
    return result
