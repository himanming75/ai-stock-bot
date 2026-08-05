from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .io import append_jsonl, read_json_optional, write_csv, write_json
from .metrics import (
    calibration_metrics,
    classification_metrics,
    performance_metrics,
    strategy_returns,
)
from .monte_carlo import simulate
from .walk_forward import walk_forward


class ModelValidationBacktestService:
    def evaluate(
        self,
        *,
        prediction_path: Path,
        output_dir: Path,
        now=None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        payload = read_json_optional(prediction_path)
        rows = list(payload.get("items", []))

        blockers = []
        if not payload:
            blockers.append("PREDICTION_INPUT_MISSING")
        if not rows:
            blockers.append("PREDICTION_ROWS_EMPTY")

        normalized = []
        for item in rows:
            try:
                normalized.append({
                    "timestamp": str(item["timestamp"]),
                    "symbol": str(item["symbol"]).upper(),
                    "final_score": float(item["final_score"]),
                    "confidence": float(item["confidence"]),
                    "forward_return": float(item["forward_return"]),
                    "technical_score": float(
                        item.get("technical_score", 0.0)
                    ),
                    "news_score": float(
                        item.get("news_score", 0.0)
                    ),
                    "fundamental_score": float(
                        item.get("fundamental_score", 0.0)
                    ),
                    "sector_score": float(
                        item.get("sector_score", 0.0)
                    ),
                    "options_score": float(
                        item.get("options_score", 0.0)
                    ),
                })
            except (KeyError, TypeError, ValueError):
                blockers.append("INVALID_PREDICTION_ROW")

        normalized.sort(
            key=lambda row: (row["timestamp"], row["symbol"])
        )

        thresholds = [
            0.00, 0.05, 0.10, 0.15, 0.20,
            0.25, 0.30, 0.35, 0.40,
        ]
        threshold_results = []

        for threshold in thresholds:
            returns = strategy_returns(normalized, threshold)
            threshold_results.append({
                "threshold": threshold,
                "classification": classification_metrics(
                    normalized,
                    threshold,
                ),
                "performance": performance_metrics(returns),
            })

        best_threshold = max(
            threshold_results,
            key=lambda item: (
                item["classification"]["balanced_accuracy"],
                item["performance"]["sharpe_like"],
                item["performance"]["cumulative_return"],
            ),
            default={
                "threshold": 0.0,
                "classification": {},
                "performance": {},
            },
        )

        selected_threshold = float(best_threshold["threshold"])
        selected_returns = strategy_returns(
            normalized,
            selected_threshold,
        )

        calibration = calibration_metrics(normalized)

        train_size = max(10, int(len(normalized) * 0.50))
        test_size = max(5, int(len(normalized) * 0.20))
        walk_forward_results = (
            walk_forward(
                normalized,
                train_size=train_size,
                test_size=test_size,
                threshold=selected_threshold,
            )
            if len(normalized) >= train_size + test_size
            else []
        )

        monte_carlo = simulate(
            selected_returns,
            simulations=500,
            seed=42,
        )

        status = (
            "PASS"
            if not blockers and len(normalized) >= 20
            else "BLOCKED"
        )
        if normalized and len(normalized) < 20:
            blockers.append("MINIMUM_SAMPLE_SIZE_NOT_MET")

        seed = {
            "rows": normalized,
            "threshold_results": threshold_results,
            "calibration": calibration,
            "walk_forward": walk_forward_results,
            "monte_carlo": monte_carlo,
            "blockers": blockers,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V2001_TO_V2200_MODEL_VALIDATION_BACKTEST_CALIBRATION",
            "status": status,
            "generated_at": now.isoformat(),
            "validation_fingerprint": fingerprint,
            "global_blockers": sorted(set(blockers)),
            "sample_count": len(normalized),
            "symbol_count": len(
                {row["symbol"] for row in normalized}
            ),
            "time_order_verified": normalized == sorted(
                normalized,
                key=lambda row: (
                    row["timestamp"],
                    row["symbol"],
                ),
            ),
            "best_threshold": selected_threshold,
            "best_threshold_result": best_threshold,
            "threshold_sweep": threshold_results,
            "calibration": calibration,
            "walk_forward_fold_count": len(walk_forward_results),
            "walk_forward_results": walk_forward_results,
            "monte_carlo": monte_carlo,
            "weight_changes_applied": False,
            "threshold_changes_applied": False,
            "automatic_model_promotion_enabled": False,
            "input_mode": "OFFLINE_FIXTURE_OR_USER_SUPPLIED_JSON",
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V2201_TO_V2400_WALK_FORWARD_OPTIMIZATION_AND_MODEL_GOVERNANCE"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            output_dir / "model_validation_latest.json",
            result,
        )
        write_json(
            output_dir / "threshold_sweep.json",
            {"records": threshold_results},
        )
        write_json(
            output_dir / "confidence_calibration.json",
            calibration,
        )
        write_json(
            output_dir / "walk_forward_results.json",
            {"records": walk_forward_results},
        )
        write_json(
            output_dir / "monte_carlo_summary.json",
            monte_carlo,
        )
        write_json(
            output_dir / "model_promotion_recommendation.json",
            {
                "generated_at": now.isoformat(),
                "recommendation": (
                    "REVIEW_BEST_THRESHOLD_MANUALLY"
                    if status == "PASS"
                    else "DO_NOT_PROMOTE"
                ),
                "best_threshold": selected_threshold,
                "automatic_promotion_enabled": False,
                "changes_applied": False,
            },
        )
        write_csv(
            output_dir / "normalized_validation_dataset.csv",
            normalized,
        )
        write_csv(
            output_dir / "threshold_performance_dataset.csv",
            [
                {
                    "threshold": item["threshold"],
                    **{
                        f"classification_{key}": value
                        for key, value
                        in item["classification"].items()
                        if key != "threshold"
                    },
                    **{
                        f"performance_{key}": value
                        for key, value
                        in item["performance"].items()
                    },
                }
                for item in threshold_results
            ],
        )
        append_jsonl(
            output_dir / "model_validation_ledger.jsonl",
            result,
        )
        return result
