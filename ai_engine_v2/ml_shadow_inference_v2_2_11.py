from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .fast_data_acceleration_v2_2_8 import FastDataAccelerationV228


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _sha_payload(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
    ).hexdigest()


def _finite(v):
    try:
        return math.isfinite(float(v))
    except (TypeError, ValueError):
        return False


def _read_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _append_once(path, payload, key_name="inference_id"):
    key = payload.get(key_name)
    if not key:
        raise RuntimeError("INFERENCE_ID_MISSING")
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get(key_name) == key:
                    return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
    return True


class MLShadowInferenceV2211:
    """
    Research-only inference bridge from V2.2.10 trained models to the exact
    V2.2.8.1 feature engineering path.

    No broker calls, no orders, no canonical-selector mutation, no promotion.
    """

    def __init__(self, root):
        self.root = Path(root)
        self.training_runtime = (
            self.root / "runtime" / "ai_ml_model_training_validation_v2_2_10"
        )
        self.training_report = self.training_runtime / "latest_training_report.json"
        self.models_dir = self.training_runtime / "models"
        self.fast = FastDataAccelerationV228(self.root)
        self.runtime = (
            self.root / "runtime" / "ai_ml_shadow_inference_v2_2_11"
        )
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.latest = self.runtime / "latest_ml_shadow_inference.json"
        self.ledger = self.runtime / "ml_shadow_inference_ledger.jsonl"

    @staticmethod
    def _ml_available():
        return all(
            importlib.util.find_spec(name) is not None
            for name in ("numpy", "joblib", "sklearn")
        )

    def preflight(self):
        missing = []
        if not self.training_report.exists():
            missing.append(str(self.training_report))
        if not self.fast.raw_bars.exists():
            missing.append(str(self.fast.raw_bars))
        if missing:
            result = {
                "status": "WAITING_FOR_V2_2_10_AND_V2_2_8_1_ARTIFACTS",
                "missing": missing,
                "ml_dependencies_available": self._ml_available(),
                "broker_network_used": False,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
                "execution_selector_modified": False,
                "automatic_promotion": False,
                "live_trading": False,
            }
            _atomic_json(self.latest, result)
            return result

        report = json.loads(
            self.training_report.read_text(encoding="utf-8-sig")
        )
        if report.get("status") != "PASS_ML_MODEL_TRAINING_VALIDATION":
            result = {
                "status": "WAITING_FOR_PASS_V2_2_10_TRAINING",
                "training_status": report.get("status"),
                "ml_dependencies_available": self._ml_available(),
                "broker_network_used": False,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
                "execution_selector_modified": False,
                "automatic_promotion": False,
                "live_trading": False,
            }
            _atomic_json(self.latest, result)
            return result

        missing_models = []
        for hkey, hreport in (report.get("horizons") or {}).items():
            rel = hreport.get("model_path")
            if not rel:
                missing_models.append(f"{hkey}:MODEL_PATH_MISSING")
                continue
            path = self.root / rel
            if not path.exists():
                missing_models.append(str(path))
        if missing_models:
            result = {
                "status": "WAITING_FOR_V2_2_10_MODEL_FILES",
                "missing_models": missing_models,
                "ml_dependencies_available": self._ml_available(),
                "broker_network_used": False,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
                "execution_selector_modified": False,
                "automatic_promotion": False,
                "live_trading": False,
            }
            _atomic_json(self.latest, result)
            return result

        result = {
            "status": "PASS_ML_SHADOW_INFERENCE_PREFLIGHT",
            "ml_dependencies_available": self._ml_available(),
            "training_report_sha256": _sha_file(self.training_report),
            "historical_raw_exists": True,
            "live_shadow_exists": self.fast.live_ledger.exists(),
            "broker_network_used": False,
            "paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "execution_selector_modified": False,
            "automatic_promotion": False,
            "live_trading": False,
        }
        _atomic_json(self.latest, result)
        return result

    def _combined_bars(self):
        grouped = defaultdict(dict)
        for source in (self.fast.raw_bars, self.fast.live_ledger):
            for row in _read_jsonl(source):
                symbol = str(row.get("symbol") or "").upper()
                ts = str(row.get("timestamp") or "")
                if not symbol or not ts:
                    continue
                if not all(
                    _finite(row.get(k))
                    for k in ("open", "high", "low", "close", "volume")
                ):
                    continue
                grouped[symbol][ts] = {
                    "symbol": symbol,
                    "timestamp": ts,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                    "trade_count": int(row.get("trade_count") or 0),
                    "vwap": float(row.get("vwap") or 0.0),
                    "feed": row.get("feed") or "iex",
                }
        return {
            symbol: sorted(rows.values(), key=lambda r: r["timestamp"])
            for symbol, rows in grouped.items()
        }

    def _latest_feature_rows(self, feature_columns):
        grouped = self._combined_bars()
        latest = {}
        for symbol, rows in grouped.items():
            # Exact feature function from V2.2.8.1; no future labels requested.
            features = self.fast._feature_rows_for_symbol(rows, ())
            for row in reversed(features):
                vals = row.get("features") or {}
                if all(_finite(vals.get(c)) for c in feature_columns):
                    latest[symbol] = row
                    break
        return latest

    @staticmethod
    def _probabilities(model, X):
        if not hasattr(model, "predict_proba"):
            return None
        probs = model.predict_proba(X)[0]
        classes = [str(x) for x in getattr(model, "classes_", [])]
        if len(classes) != len(probs):
            return None
        return {
            cls: round(float(prob), 8)
            for cls, prob in zip(classes, probs)
        }

    def run(self):
        pre = self.preflight()
        if pre.get("status") != "PASS_ML_SHADOW_INFERENCE_PREFLIGHT":
            return pre
        if not pre.get("ml_dependencies_available"):
            result = {
                **pre,
                "status": "BLOCKED_ML_DEPENDENCIES_MISSING_USE_VENV_ML",
            }
            _atomic_json(self.latest, result)
            return result

        import joblib
        import numpy as np

        training = json.loads(
            self.training_report.read_text(encoding="utf-8-sig")
        )
        horizons = training.get("horizons") or {}
        if not horizons:
            raise RuntimeError("V2_2_10_HORIZON_REPORTS_MISSING")

        feature_columns = None
        for hreport in horizons.values():
            cols = list(hreport.get("feature_columns") or [])
            if feature_columns is None:
                feature_columns = cols
            elif cols != feature_columns:
                raise RuntimeError("FEATURE_COLUMN_MISMATCH_ACROSS_HORIZONS")
        if not feature_columns:
            raise RuntimeError("FEATURE_COLUMNS_MISSING")

        latest_rows = self._latest_feature_rows(feature_columns)
        if not latest_rows:
            result = {
                "status": "WAITING_FOR_USABLE_LATEST_FEATURE_ROWS",
                "feature_columns": feature_columns,
                "training_report_sha256": pre["training_report_sha256"],
                "broker_network_used": False,
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
                "execution_selector_modified": False,
                "automatic_promotion": False,
                "live_trading": False,
            }
            _atomic_json(self.latest, result)
            return result

        model_cache = {}
        horizon_meta = {}
        for hkey, hreport in horizons.items():
            model_path = self.root / hreport["model_path"]
            actual_sha = _sha_file(model_path)
            expected_sha = hreport.get("model_sha256")
            if expected_sha and actual_sha != expected_sha:
                raise RuntimeError(f"MODEL_SHA256_MISMATCH_{hkey}")
            model_cache[hkey] = joblib.load(model_path)
            horizon_meta[hkey] = {
                "selected_model": hreport.get("selected_model"),
                "edge_ready": bool(hreport.get("edge_ready")),
                "selected_validation_score": hreport.get(
                    "selected_validation_score"
                ),
                "test_selection_score": (
                    hreport.get("test_metrics") or {}
                ).get("selection_score"),
                "model_sha256": actual_sha,
            }

        symbol_predictions = []
        for symbol in sorted(latest_rows):
            row = latest_rows[symbol]
            vals = row["features"]
            X = np.asarray(
                [[float(vals[c]) for c in feature_columns]],
                dtype=np.float32,
            )
            preds = {}
            for hkey in sorted(
                model_cache,
                key=lambda k: int(str(k).replace("m", "")),
            ):
                model = model_cache[hkey]
                direction = str(model.predict(X)[0])
                probs = self._probabilities(model, X)
                confidence = max(probs.values()) if probs else None
                preds[hkey] = {
                    **horizon_meta[hkey],
                    "predicted_direction": direction,
                    "class_probabilities": probs,
                    "prediction_confidence": confidence,
                }
            symbol_predictions.append(
                {
                    "symbol": symbol,
                    "feature_timestamp": row.get("timestamp"),
                    "feature_feed": row.get("feed"),
                    "feature_values": {
                        c: float(vals[c]) for c in feature_columns
                    },
                    "predictions": preds,
                }
            )

        best_horizon = training.get("best_test_horizon_for_shadow_research")
        research_rank = []
        if best_horizon and best_horizon in horizons:
            for row in symbol_predictions:
                pred = row["predictions"].get(best_horizon) or {}
                research_rank.append(
                    {
                        "symbol": row["symbol"],
                        "horizon": best_horizon,
                        "direction": pred.get("predicted_direction"),
                        "confidence": pred.get("prediction_confidence"),
                        "edge_ready": pred.get("edge_ready"),
                    }
                )
            research_rank.sort(
                key=lambda r: (
                    r.get("confidence") is not None,
                    r.get("confidence") or -1.0,
                ),
                reverse=True,
            )

        identity = {
            "training_report_sha256": pre["training_report_sha256"],
            "model_shas": {
                h: horizon_meta[h]["model_sha256"]
                for h in sorted(horizon_meta)
            },
            "feature_rows": [
                (r["symbol"], r["feature_timestamp"])
                for r in symbol_predictions
            ],
        }
        result = {
            "stage": "AI_TRADING_ENGINE_V2_2_11_ML_SHADOW_INFERENCE",
            "status": "PASS_ML_SHADOW_INFERENCE",
            "generated_at_utc": _utcnow(),
            "inference_id": _sha_payload(identity),
            "training_report_sha256": pre["training_report_sha256"],
            "feature_engineering_reused_from_v2_2_8_1": True,
            "model_training_reused_from_v2_2_10": True,
            "feature_columns": feature_columns,
            "symbol_count": len(symbol_predictions),
            "horizons": horizon_meta,
            "best_shadow_research_horizon": best_horizon,
            "symbol_predictions": symbol_predictions,
            "research_rank": research_rank,
            "shadow_only": True,
            "broker_network_used": False,
            "paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "execution_selector_modified": False,
            "automatic_promotion": False,
            "live_trading": False,
        }
        result["new_ledger_row"] = _append_once(self.ledger, result)
        _atomic_json(self.latest, result)
        return result

    def status(self):
        if self.latest.exists():
            try:
                return json.loads(self.latest.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self.preflight()
