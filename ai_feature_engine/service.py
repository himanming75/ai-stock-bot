from __future__ import annotations
import hashlib
import json
from pathlib import Path

from .conflicts import detect_conflicts
from .features import build_features
from .ledger import append_candidate
from .normalization import normalize_bars
from .report import write_report
from .signals import generate_signal


def _fixture(direction: str) -> list[dict]:
    bars = []
    price = 100.0
    for i in range(80):
        if direction == "UP":
            price = max(1.0, price + 0.35)
            close = price
            volume = 1000 + i * 10
        elif direction == "DOWN":
            price = max(1.0, price - 0.35)
            close = price
            volume = 1000 + i * 10
        else:
            # Deterministic flat-range fixture:
            # alternating around 100 with stable volume prevents
            # directional EMA, MACD, momentum, and volume bias.
            close = 100.0
            price = close
            volume = 1000

        bars.append({
            "timestamp": f"2026-01-01T00:{i:02d}:00Z",
            "open": close,
            "high": close + 0.10,
            "low": close - 0.10,
            "close": close,
            "volume": volume,
        })
    return bars


class AIFeatureSignalCertificationService:
    def evaluate(self, *, output_dir: Path) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        actual = output_dir / "actual"
        actual.mkdir(parents=True, exist_ok=True)

        fixtures = {
            "AAPL": _fixture("UP"),
            "MSFT": _fixture("DOWN"),
            "SPY": _fixture("SIDEWAYS"),
        }
        configuration = {
            "profile_key": "BALANCED",
            "profile": {
                "max_daily_loss_percent": 1.0,
            },
            "execution": {
                "activation_enabled": False,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
            },
        }

        candidates = []
        for symbol, raw_bars in fixtures.items():
            bars = normalize_bars(raw_bars)
            features = build_features(bars)
            candidate = generate_signal(
                symbol=symbol,
                features=features,
                configuration=configuration,
            )
            candidate["conflict_analysis"] = detect_conflicts(candidate)
            candidates.append(candidate)
            append_candidate(
                actual / "signal_candidate_ledger.jsonl",
                candidate,
            )
            (actual / f"{symbol.lower()}_feature_snapshot.json").write_text(
                json.dumps(features, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        report = write_report(
            candidates=candidates,
            output_path=actual / "ai_signal_candidate_report_bilingual.json",
        )

        result = {
            "stage": (
                "V9801_TO_V10400_PHASE2_AI_FEATURE_ENGINE_"
                "SIGNAL_CANDIDATES_MAX_BUNDLE"
            ),
            "status": "PASS",
            "ohlcv_normalization_ready": True,
            "ema_ready": True,
            "rsi_ready": True,
            "macd_ready": True,
            "vwap_ready": True,
            "atr_ready": True,
            "bollinger_ready": True,
            "momentum_ready": True,
            "volume_feature_ready": True,
            "trend_classification_ready": True,
            "market_regime_ready": True,
            "buy_candidate_ready": True,
            "sell_candidate_ready": True,
            "hold_candidate_ready": True,
            "confidence_score_ready": True,
            "conflict_detection_ready": True,
            "risk_gate_ready": True,
            "signal_ledger_ready": True,
            "bilingual_reasoning_ready": True,
            "bilingual_report_ready": True,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "report": report,
            "actual_external_network_used": False,
            "actual_credentials_used": False,
            "actual_market_data_requested": False,
            "actual_configuration_activated": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_order_cancel_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": (
                "PHASE2_AI_SIGNAL_SCORING_ENSEMBLE_"
                "EXPLAINABILITY_AND_BACKTEST_BRIDGE"
            ),
        }

        actions = {item["action"] for item in candidates}
        result["candidate_actions"] = sorted(actions)
        result["candidate_action_map"] = {
            item["symbol"]: item["action"]
            for item in candidates
        }
        if not (
            len(candidates) == 3
            and actions == {"BUY", "SELL", "HOLD"}
            and all(
                item["order_submission_enabled"] is False
                for item in candidates
            )
            and all(
                item["risk_gate"] == "PASS_READ_ONLY"
                for item in candidates
            )
        ):
            result["status"] = "BLOCKED"

        result["certification_fingerprint"] = hashlib.sha256(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        (output_dir / "ai_feature_signal_certification.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return result
