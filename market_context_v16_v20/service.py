from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MarketContextIntelligence:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _append(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _v6_v10(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/shadow_intelligence_v6_v10/"
              "latest_shadow_intelligence_report.json"
        )

    def _v11_v15(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/shadow_validation_v11_v15/"
              "latest_validation_report.json"
        )

    def _market_snapshot(self) -> dict[str, Any]:
        candidates = [
            self.root
            / "runtime/market_context_inputs/latest_market_context_snapshot.json",
            self.root
            / "release/market_context_inputs/latest_market_context_snapshot.json",
        ]
        for path in candidates:
            payload = self._load(path)
            if payload:
                return payload
        return {}

    def market_regime_predictor(self) -> dict[str, Any]:
        shadow = self._v6_v10()
        existing = shadow.get("market_regime_engine", {})
        snapshot = self._market_snapshot()

        trend = self._float(
            snapshot.get(
                "trend_score",
                existing.get("trend_score", 0.5),
            ),
            0.5,
        )
        volatility = self._float(
            snapshot.get(
                "volatility_risk",
                existing.get("volatility_risk", 0.5),
            ),
            0.5,
        )
        breadth = self._float(snapshot.get("breadth_score"), 0.5)
        liquidity = self._float(snapshot.get("liquidity_score"), 0.5)

        available = bool(snapshot) or bool(existing)

        if not available:
            label = "UNKNOWN"
            confidence = 0.0
            status = "COLLECTING_DATA"
        elif volatility >= 0.85:
            label = "EXTREME_VOLATILITY"
            confidence = volatility
            status = "PASS"
        elif trend >= 0.75 and breadth >= 0.60:
            label = "BULL_TREND"
            confidence = min((trend + breadth + liquidity) / 3.0, 1.0)
            status = "PASS"
        elif trend <= 0.35 and breadth <= 0.40:
            label = "BEAR_TREND"
            confidence = min(
                ((1.0 - trend) + (1.0 - breadth) + volatility) / 3.0,
                1.0,
            )
            status = "PASS"
        elif volatility >= 0.65:
            label = "HIGH_VOLATILITY_SIDEWAYS"
            confidence = volatility
            status = "PASS"
        else:
            label = "SIDEWAYS_OR_UNCERTAIN"
            confidence = 1.0 - abs(trend - 0.5) * 2.0
            status = "PASS"

        return {
            "status": status,
            "label": label,
            "confidence": round(max(min(confidence, 1.0), 0.0), 6),
            "trend_score": round(trend, 6),
            "volatility_risk": round(volatility, 6),
            "breadth_score": round(breadth, 6),
            "liquidity_score": round(liquidity, 6),
            "prediction_horizon": "INTRADAY_CONTEXT_ONLY",
            "enforced": False,
            "order_effect": "NONE",
        }

    def sector_rotation(self) -> dict[str, Any]:
        snapshot = self._market_snapshot()
        sectors = snapshot.get("sectors", {})
        if not isinstance(sectors, dict) or not sectors:
            return {
                "status": "COLLECTING_DATA",
                "ranked_sectors": [],
                "leading_sectors": [],
                "lagging_sectors": [],
                "automatic_sector_switching": False,
            }

        normalized = []
        for symbol, values in sectors.items():
            if isinstance(values, dict):
                momentum = self._float(values.get("momentum"), 0.0)
                breadth = self._float(values.get("breadth"), 0.0)
                relative_strength = self._float(
                    values.get("relative_strength"), 0.0
                )
            else:
                momentum = self._float(values)
                breadth = 0.5
                relative_strength = self._float(values)

            score = (
                0.40 * momentum
                + 0.30 * breadth
                + 0.30 * relative_strength
            )
            normalized.append({
                "sector": str(symbol).upper(),
                "momentum": round(momentum, 6),
                "breadth": round(breadth, 6),
                "relative_strength": round(relative_strength, 6),
                "rotation_score": round(score, 6),
            })

        normalized.sort(
            key=lambda item: (-item["rotation_score"], item["sector"])
        )

        return {
            "status": "PASS",
            "ranked_sectors": normalized,
            "leading_sectors": [
                item["sector"] for item in normalized[:3]
            ],
            "lagging_sectors": [
                item["sector"] for item in normalized[-3:]
            ],
            "automatic_sector_switching": False,
        }

    def cross_asset_correlation(self) -> dict[str, Any]:
        snapshot = self._market_snapshot()
        assets = snapshot.get("cross_asset", {})
        if not isinstance(assets, dict) or not assets:
            return {
                "status": "COLLECTING_DATA",
                "assets": {},
                "risk_on_score": None,
                "risk_off_score": None,
                "context": "UNKNOWN",
                "enforced": False,
            }

        spy = self._float(assets.get("SPY"))
        qqq = self._float(assets.get("QQQ"))
        vix = self._float(assets.get("VIX"))
        tlt = self._float(assets.get("TLT"))

        risk_on = (
            0.40 * max(spy, 0.0)
            + 0.40 * max(qqq, 0.0)
            + 0.20 * max(-vix, 0.0)
        )
        risk_off = (
            0.50 * max(vix, 0.0)
            + 0.30 * max(tlt, 0.0)
            + 0.20 * max(-spy, 0.0)
        )

        if risk_on > risk_off + 0.10:
            context = "RISK_ON"
        elif risk_off > risk_on + 0.10:
            context = "RISK_OFF"
        else:
            context = "MIXED"

        return {
            "status": "PASS",
            "assets": {
                "SPY": spy,
                "QQQ": qqq,
                "VIX": vix,
                "TLT": tlt,
            },
            "risk_on_score": round(risk_on, 6),
            "risk_off_score": round(risk_off, 6),
            "context": context,
            "enforced": False,
            "order_effect": "NONE",
        }

    def volatility_forecast(self) -> dict[str, Any]:
        snapshot = self._market_snapshot()
        vol = snapshot.get("volatility", {})
        existing = self._v6_v10().get("market_regime_engine", {})

        if isinstance(vol, dict) and vol:
            realized = self._float(vol.get("realized"), 0.0)
            implied = self._float(vol.get("implied"), 0.0)
            short_term = self._float(vol.get("short_term_forecast"), 0.0)
            available = True
        else:
            realized = 0.0
            implied = self._float(
                existing.get("volatility_risk"), 0.0
            )
            short_term = implied
            available = bool(existing)

        if not available:
            return {
                "status": "COLLECTING_DATA",
                "forecast_level": "UNKNOWN",
                "forecast_score": None,
                "enforced": False,
            }

        forecast = max(realized, implied, short_term)
        if forecast >= 0.85:
            level = "EXTREME"
        elif forecast >= 0.70:
            level = "HIGH"
        elif forecast >= 0.45:
            level = "NORMAL"
        else:
            level = "LOW"

        return {
            "status": "PASS",
            "forecast_level": level,
            "forecast_score": round(forecast, 6),
            "realized_volatility": round(realized, 6),
            "implied_volatility": round(implied, 6),
            "short_term_forecast": round(short_term, 6),
            "recommended_observation": (
                "REQUIRE_STRONGER_CONFIRMATION"
                if level in {"HIGH", "EXTREME"}
                else "NORMAL_REVIEW"
            ),
            "enforced": False,
            "order_effect": "NONE",
        }

    def market_breadth(self) -> dict[str, Any]:
        snapshot = self._market_snapshot()
        breadth = snapshot.get("breadth", {})
        if not isinstance(breadth, dict) or not breadth:
            return {
                "status": "COLLECTING_DATA",
                "breadth_score": None,
                "breadth_state": "UNKNOWN",
                "enforced": False,
            }

        advancers = self._float(breadth.get("advancers"))
        decliners = self._float(breadth.get("decliners"))
        above_50dma = self._float(breadth.get("above_50dma"))
        new_highs = self._float(breadth.get("new_highs"))
        new_lows = self._float(breadth.get("new_lows"))

        total = advancers + decliners
        advance_ratio = advancers / total if total > 0 else 0.5

        high_low_total = new_highs + new_lows
        high_ratio = (
            new_highs / high_low_total if high_low_total > 0 else 0.5
        )

        score = (
            0.45 * advance_ratio
            + 0.35 * above_50dma
            + 0.20 * high_ratio
        )

        if score >= 0.70:
            state = "STRONG"
        elif score >= 0.55:
            state = "POSITIVE"
        elif score >= 0.40:
            state = "MIXED"
        else:
            state = "WEAK"

        return {
            "status": "PASS",
            "breadth_score": round(score, 6),
            "breadth_state": state,
            "advance_ratio": round(advance_ratio, 6),
            "above_50dma": round(above_50dma, 6),
            "new_high_ratio": round(high_ratio, 6),
            "enforced": False,
            "order_effect": "NONE",
        }

    def context_summary(self) -> dict[str, Any]:
        regime = self.market_regime_predictor()
        sectors = self.sector_rotation()
        cross_asset = self.cross_asset_correlation()
        volatility = self.volatility_forecast()
        breadth = self.market_breadth()
        false_signal = self._v11_v15().get(
            "v12_false_signal_detector", {}
        )

        blockers = []
        if regime["label"] in {
            "BEAR_TREND",
            "EXTREME_VOLATILITY",
        }:
            blockers.append("UNFAVORABLE_MARKET_REGIME")
        if cross_asset.get("context") == "RISK_OFF":
            blockers.append("CROSS_ASSET_RISK_OFF")
        if volatility.get("forecast_level") in {
            "HIGH",
            "EXTREME",
        }:
            blockers.append("ELEVATED_VOLATILITY")
        if breadth.get("breadth_state") == "WEAK":
            blockers.append("WEAK_MARKET_BREADTH")
        if false_signal.get("false_signal_risk") == "HIGH":
            blockers.append("HIGH_FALSE_SIGNAL_RISK")

        return {
            "market_entry_context": (
                "UNFAVORABLE"
                if blockers
                else "FAVORABLE_OR_NEUTRAL"
            ),
            "blockers": blockers,
            "leading_sectors": sectors.get("leading_sectors", []),
            "risk_context": cross_asset.get("context", "UNKNOWN"),
            "volatility_level": volatility.get(
                "forecast_level", "UNKNOWN"
            ),
            "breadth_state": breadth.get(
                "breadth_state", "UNKNOWN"
            ),
            "enforced": False,
            "order_effect": "NONE",
        }

    def run(self) -> dict[str, Any]:
        runtime = self.root / "runtime/market_context_v16_v20"

        result = {
            "stage": "MARKET_CONTEXT_INTELLIGENCE_V16_TO_V20",
            "status": "PASS",
            "mode": "READ_ONLY_SHADOW",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "v16_market_regime_predictor": (
                self.market_regime_predictor()
            ),
            "v17_sector_rotation": self.sector_rotation(),
            "v18_cross_asset_correlation": (
                self.cross_asset_correlation()
            ),
            "v19_volatility_forecast": self.volatility_forecast(),
            "v20_market_breadth": self.market_breadth(),
            "market_context_summary": self.context_summary(),
            "generated_at_utc": self._now(),
        }

        self._write(
            runtime / "latest_market_context_report.json",
            result,
        )
        self._append(
            runtime / "market_context_ledger.jsonl",
            result,
        )

        summary = {
            "generated_at_utc": self._now(),
            "status": "PASS",
            "market_regime": result[
                "v16_market_regime_predictor"
            ]["label"],
            "market_entry_context": result[
                "market_context_summary"
            ]["market_entry_context"],
            "risk_context": result[
                "market_context_summary"
            ]["risk_context"],
            "volatility_level": result[
                "market_context_summary"
            ]["volatility_level"],
            "breadth_state": result[
                "market_context_summary"
            ]["breadth_state"],
            "broker_write_performed": False,
            "etrade_live_write_enabled": False,
        }
        self._write(
            runtime / "daily_market_context_summary.json",
            summary,
        )

        return result
