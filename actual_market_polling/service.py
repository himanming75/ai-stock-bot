from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


def D(value, default="0") -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


class ReadOnlyAlpaca:
    def __init__(self) -> None:
        self.key = os.environ.get("APCA_API_KEY_ID", "").strip()
        self.secret = os.environ.get("APCA_API_SECRET_KEY", "").strip()
        self.trading = os.environ.get(
            "APCA_API_BASE_URL", "https://paper-api.alpaca.markets"
        ).rstrip("/")
        self.data = os.environ.get(
            "APCA_API_DATA_URL", "https://data.alpaca.markets"
        ).rstrip("/")
        self.feed = os.environ.get("ALPACA_DATA_FEED", "iex")
        if not self.key or not self.secret:
            raise RuntimeError("ALPACA_PAPER_CREDENTIALS_MISSING")

    def get(self, url: str):
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "APCA-API-KEY-ID": self.key,
                "APCA-API-SECRET-KEY": self.secret,
                "Accept": "application/json",
                "User-Agent": "ai-stock-bot-read-only-polling-validation/1.0",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def clock(self):
        return self.get(f"{self.trading}/v2/clock")

    def account(self):
        return self.get(f"{self.trading}/v2/account")

    def positions(self):
        return self.get(f"{self.trading}/v2/positions")

    def orders(self, status: str):
        return self.get(
            f"{self.trading}/v2/orders?status={status}&limit=100&direction=desc"
        )

    def bars_for_symbol(self, symbol: str, limit: int = 30):
        query = urllib.parse.urlencode(
            {
                "timeframe": "1Min",
                "limit": str(limit),
                "adjustment": "raw",
                "feed": self.feed,
                "sort": "desc",
            }
        )
        payload = self.get(f"{self.data}/v2/stocks/{symbol}/bars?{query}")
        bars = payload.get("bars", [])

        # Alpaca returns the newest bars first when sort=desc.
        # The strategy calculations below expect chronological order,
        # so normalize them back to oldest -> newest.
        return sorted(
            bars,
            key=lambda bar: bar.get("t", ""),
        )


def build_record(symbol: str, bars: list[dict], all_returns: list[Decimal]) -> dict | None:
    closes = [D(x.get("c")) for x in bars if D(x.get("c")) > 0]
    volumes = [D(x.get("v")) for x in bars]
    if len(closes) < 6:
        return None

    ret1 = closes[-1] / closes[-2] - 1
    ret5 = closes[-1] / closes[-6] - 1
    avg_volume = sum(volumes[:-1], Decimal("0")) / max(1, len(volumes) - 1)
    volume_ratio = volumes[-1] / avg_volume if avg_volume else Decimal("1")
    moves = [
        abs(closes[i] / closes[i - 1] - 1)
        for i in range(1, len(closes))
        if closes[i - 1]
    ]
    volatility = (
        sum(moves, Decimal("0")) / max(1, len(moves)) * Decimal("15")
    )
    all_returns.append(ret5)

    return {
        "symbol": symbol,
        "price_return_1d": str(ret1),
        "price_return_5d": str(ret5),
        "volume_ratio": str(volume_ratio),
        "realized_volatility": str(volatility),
        "relative_strength": "0",
        "breadth_score": "0",
        "sector_strength": "0",
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
        "source_confidence": "0.90",
        "source_age_seconds": 0,
    }


def finalize_records(records: list[dict], returns: list[Decimal]) -> list[dict]:
    if not records:
        return records
    average_return = sum(returns, Decimal("0")) / len(returns)
    breadth = Decimal(sum(1 for x in returns if x > 0)) / len(returns) * 2 - 1
    for record in records:
        current = D(record["price_return_5d"])
        relative = max(
            Decimal("-1"),
            min(Decimal("1"), (current - average_return) * Decimal("10")),
        )
        record["relative_strength"] = str(relative)
        record["breadth_score"] = str(breadth)
        record["sector_strength"] = str(relative)
    return records


class ActualMarketPollingValidationService:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.client = ReadOnlyAlpaca()
        self.output = root / "release/actual_market_polling_validation/actual"
        self.output.mkdir(parents=True, exist_ok=True)

    def run_cycle(self, symbols: list[str], cycle_number: int) -> dict:
        started = datetime.now(timezone.utc)
        clock = self.client.clock()
        account = self.client.account()
        positions = self.client.positions()
        open_orders = self.client.orders("open")
        closed_orders = self.client.orders("closed")

        bars_by_symbol: dict[str, list[dict]] = {}
        errors: dict[str, str] = {}
        for symbol in symbols:
            try:
                bars_by_symbol[symbol] = self.client.bars_for_symbol(symbol)
            except Exception as exc:
                errors[symbol] = f"{type(exc).__name__}:{exc}"
                bars_by_symbol[symbol] = []

        returns: list[Decimal] = []
        records = []
        coverage = {}
        for symbol in symbols:
            bars = bars_by_symbol.get(symbol, [])
            coverage[symbol] = {
                "bar_count": len(bars),
                "covered": len(bars) >= 6,
                "latest_timestamp": bars[-1].get("t") if bars else None,
            }
            record = build_record(symbol, bars, returns)
            if record:
                records.append(record)
        records = finalize_records(records, returns)

        cycle_dir = self.output / f"cycle_{cycle_number:04d}"
        cycle_dir.mkdir(parents=True, exist_ok=True)
        raw = {
            "clock": clock,
            "account": account,
            "positions": positions,
            "open_orders": open_orders,
            "closed_orders": closed_orders,
            "bars_by_symbol": bars_by_symbol,
            "errors": errors,
        }
        raw_path = cycle_dir / "raw_readonly_snapshot.json"
        raw_path.write_text(
            json.dumps(raw, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        fusion_path = cycle_dir / "fusion_input.json"
        fusion_path.write_text(
            json.dumps({"symbols": records}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        market_status = decision_status = bridge_status = "BLOCKED"
        selected_symbols: list[str] = []
        approved_symbols: list[str] = []

        if records:
            from market_intelligence.service import MarketIntelligenceFusionService

            market_path = cycle_dir / "market_snapshot.json"
            market = MarketIntelligenceFusionService().run_file(
                fusion_path, market_path
            )
            market_status = market.get("status", "BLOCKED")

            from ai_decision_orchestration.service import (
                AIDecisionOrchestrationService,
            )

            policy_path = (
                self.root
                / "release/ai_symbol_selection_decision_orchestration/config/decision_policy.json"
            )
            decision_path = cycle_dir / "decision_snapshot.json"
            decision = AIDecisionOrchestrationService().run_file(
                market_path, policy_path, decision_path
            )
            decision_status = decision.get("status", "BLOCKED")
            selected_symbols = decision.get(
                "decision_orchestration", {}
            ).get("selected_symbols", [])

            from ai_decision_bridge.service import DecisionBridgeService

            bridge_config = (
                self.root
                / "release/ai_decision_strategy_risk_portfolio_bridge/config/bridge_config.json"
            )
            bridge_path = cycle_dir / "bridge_snapshot.json"
            bridge = DecisionBridgeService().run_file(
                decision_path, bridge_config, bridge_path
            )
            bridge_status = bridge.get("status", "BLOCKED")
            approved_symbols = bridge.get("bridge", {}).get(
                "approved_symbols", []
            )

        coverage_count = sum(
            1 for x in coverage.values() if x["covered"]
        )
        cycle = {
            "cycle_number": cycle_number,
            "started_at": started.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "market_is_open": bool(clock.get("is_open", False)),
            "symbols_requested": len(symbols),
            "symbols_covered": coverage_count,
            "coverage": coverage,
            "errors": errors,
            "account_equity": account.get("equity"),
            "position_count": len(positions),
            "open_order_count": len(open_orders),
            "closed_order_count": len(closed_orders),
            "market_pipeline_status": market_status,
            "decision_pipeline_status": decision_status,
            "bridge_pipeline_status": bridge_status,
            "selected_symbols": selected_symbols,
            "approved_symbols": approved_symbols,
            "actual_external_network_used": True,
            "actual_broker_read_performed": True,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "raw_snapshot_sha256": hashlib.sha256(
                raw_path.read_bytes()
            ).hexdigest(),
        }
        with (
            self.output / "polling_ledger.jsonl"
        ).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(cycle, sort_keys=True) + "\n")
        return cycle

    def run(
        self,
        symbols: list[str],
        interval_seconds: int,
        max_cycles: int,
    ) -> dict:
        cycles = []
        for number in range(1, max_cycles + 1):
            cycle = self.run_cycle(symbols, number)
            cycles.append(cycle)
            print(
                json.dumps(cycle, indent=2, sort_keys=True),
                flush=True,
            )

            if not cycle["market_is_open"]:
                break
            if number < max_cycles:
                time.sleep(interval_seconds)

        coverage_pass_cycles = sum(
            1
            for cycle in cycles
            if cycle["symbols_covered"] == len(symbols)
        )
        fatal_errors = sum(
            1 for cycle in cycles if cycle["errors"]
        )
        summary = {
            "stage": "ACTUAL_MARKET_COVERAGE_POLLING_VALIDATION_MEGA_BUNDLE",
            "status": (
                "PASS"
                if cycles and coverage_pass_cycles > 0
                else "BLOCKED"
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "symbols": symbols,
            "requested_cycles": max_cycles,
            "completed_cycles": len(cycles),
            "coverage_pass_cycles": coverage_pass_cycles,
            "cycles_with_errors": fatal_errors,
            "market_closed_detected": bool(
                cycles and not cycles[-1]["market_is_open"]
            ),
            "last_cycle": cycles[-1] if cycles else None,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_market_validation": (
                "RESTART_RECOVERY_AND_MARKET_CLOSE_VALIDATION"
            ),
            "next_fixed_development": (
                "AI_APPROVED_DECISION_TO_EXECUTION_PLAN_BRIDGE"
            ),
        }
        (self.output / "polling_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return summary
