from __future__ import annotations
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .allocation import allocate
from .io import append_jsonl, read_json_optional, write_csv, write_json
from .reasoning import build_reasoning
from .utils import clamp, f, normalize_100, signal


class UnifiedAIDecisionReasoningService:
    WEIGHTS = {
        "technical": 0.30,
        "news_earnings_macro": 0.18,
        "fundamental": 0.22,
        "sector": 0.12,
        "options": 0.18,
    }

    def evaluate(
        self,
        *,
        ensemble_path: Path,
        news_path: Path,
        fundamental_path: Path,
        output_dir: Path,
        now=None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)

        ensemble_payload = read_json_optional(ensemble_path)
        news_payload = read_json_optional(news_path)
        fundamental_payload = read_json_optional(fundamental_path)

        ensemble_records = list(
            ensemble_payload.get("ranked_ensemble_results", [])
        )
        news_records = list(news_payload.get("symbol_profiles", []))
        fundamental_records = list(
            fundamental_payload.get("symbol_profiles", [])
        )

        global_blockers = []
        global_warnings = []

        if not ensemble_payload:
            global_warnings.append("ENSEMBLE_INPUT_MISSING")
        elif not ensemble_records:
            global_warnings.append("ENSEMBLE_RECORDS_EMPTY")

        if not news_payload:
            global_blockers.append("NEWS_INTELLIGENCE_INPUT_MISSING")

        if not fundamental_payload:
            global_blockers.append(
                "FUNDAMENTAL_SECTOR_OPTIONS_INPUT_MISSING"
            )

        by_symbol = defaultdict(dict)

        for item in ensemble_records:
            symbol = str(item.get("symbol", "")).upper()
            if symbol:
                by_symbol[symbol]["ensemble"] = item

        for item in news_records:
            symbol = str(item.get("symbol", "")).upper()
            if symbol:
                by_symbol[symbol]["news"] = item

        for item in fundamental_records:
            symbol = str(item.get("symbol", "")).upper()
            if symbol:
                by_symbol[symbol]["fundamental"] = item

        decisions = []
        for symbol in sorted(by_symbol):
            sources = by_symbol[symbol]
            missing = []
            blockers = []

            ensemble = sources.get("ensemble")
            news = sources.get("news")
            fundamental = sources.get("fundamental")

            if ensemble:
                technical_score = normalize_100(
                    ensemble.get("ensemble_score")
                )
                technical_confidence = f(
                    ensemble.get("confidence"),
                    0.0,
                )
                disagreement = f(
                    ensemble.get("disagreement"),
                    1.0,
                )
            else:
                technical_score = 0.0
                technical_confidence = 0.0
                disagreement = 1.0
                missing.append("technical")

            if news:
                news_score = f(
                    news.get("intelligence_score"),
                    0.0,
                )
                news_confidence = f(
                    news.get("confidence"),
                    0.0,
                )
                news_event_risk = f(
                    news.get("event_risk"),
                    0.0,
                )
            else:
                news_score = 0.0
                news_confidence = 0.0
                news_event_risk = 0.0
                missing.append("news_earnings_macro")

            if fundamental:
                fundamental_score = f(
                    fundamental.get("fundamental_score"),
                    0.0,
                )
                sector_score = f(
                    fundamental.get("sector_score"),
                    0.0,
                )
                options_score = f(
                    fundamental.get("options_score"),
                    0.0,
                )
                fundamental_confidence = f(
                    fundamental.get("confidence"),
                    0.0,
                )
                options_event_risk = f(
                    fundamental.get("options_event_risk"),
                    0.0,
                )
            else:
                fundamental_score = 0.0
                sector_score = 0.0
                options_score = 0.0
                fundamental_confidence = 0.0
                options_event_risk = 0.0
                missing.extend(["fundamental", "sector", "options"])

            component_scores = {
                "technical": technical_score,
                "news_earnings_macro": news_score,
                "fundamental": fundamental_score,
                "sector": sector_score,
                "options": options_score,
            }

            available_weights = sum(
                weight
                for name, weight in self.WEIGHTS.items()
                if name not in missing
            )
            weighted_sum = sum(
                component_scores[name] * weight
                for name, weight in self.WEIGHTS.items()
                if name not in missing
            )
            base_score = (
                weighted_sum / available_weights
                if available_weights else 0.0
            )

            event_risk = max(
                news_event_risk,
                options_event_risk,
            )
            disagreement_penalty = min(
                disagreement * 0.18,
                0.18,
            )
            risk_penalty = min(
                event_risk * 0.20,
                0.20,
            )
            final_score = clamp(
                base_score
                - disagreement_penalty
                - risk_penalty,
            )

            confidence_sources = [
                value
                for value in (
                    technical_confidence,
                    news_confidence,
                    fundamental_confidence,
                )
                if value > 0
            ]
            base_confidence = (
                sum(confidence_sources) / len(confidence_sources)
                if confidence_sources else 0.0
            )
            missing_penalty = len(set(missing)) * 8.0
            confidence = max(
                0.0,
                min(
                    100.0,
                    base_confidence
                    - disagreement * 20.0
                    - event_risk * 18.0
                    - missing_penalty,
                ),
            )

            final_signal = signal(final_score)

            if event_risk >= 0.90:
                blockers.append("EXTREME_EVENT_RISK")
            if options_event_risk >= 0.90:
                blockers.append("EXTREME_OPTIONS_EVENT_RISK")
            if confidence < 45.0:
                blockers.append("CONFIDENCE_BELOW_MINIMUM")
            if final_signal == "HOLD_OR_NEUTRAL":
                blockers.append("FINAL_SIGNAL_NEUTRAL")
            if final_signal == "SELL_OR_AVOID":
                blockers.append("NEGATIVE_FINAL_SIGNAL")

            decision_status = (
                "APPROVED_CANDIDATE"
                if not blockers
                and final_signal == "BUY_CANDIDATE"
                and confidence >= 55.0
                else "BLOCKED_OR_OBSERVE"
            )

            reasoning = build_reasoning(
                symbol=symbol,
                component_scores=component_scores,
                missing_components=sorted(set(missing)),
                blockers=blockers,
                confidence=confidence,
                final_signal=final_signal,
            )

            decisions.append({
                "symbol": symbol,
                "component_scores": component_scores,
                "available_weight": round(available_weights, 8),
                "base_score": round(base_score, 8),
                "disagreement": round(disagreement, 8),
                "event_risk": round(event_risk, 8),
                "disagreement_penalty": round(
                    disagreement_penalty,
                    8,
                ),
                "risk_penalty": round(risk_penalty, 8),
                "final_score": round(final_score, 8),
                "final_signal": final_signal,
                "confidence": round(confidence, 6),
                "missing_components": sorted(set(missing)),
                "blockers": blockers,
                "decision_status": decision_status,
                "reasoning": reasoning,
                "automatic_execution_enabled": False,
            })

        decisions.sort(
            key=lambda item: (
                item["decision_status"] == "APPROVED_CANDIDATE",
                item["confidence"],
                item["final_score"],
            ),
            reverse=True,
        )
        for rank, item in enumerate(decisions, 1):
            item["rank"] = rank

        allocations = allocate(decisions)

        if global_blockers:
            status = "BLOCKED"
        elif decisions:
            status = (
                "PASS"
                if not global_warnings
                else "PARTIAL_INPUT"
            )
        else:
            status = "BLOCKED"
            global_blockers.append("NO_SYMBOL_DECISIONS_CREATED")

        seed = {
            "decisions": decisions,
            "allocations": allocations,
            "blockers": global_blockers,
            "warnings": global_warnings,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V1801_TO_V2000_UNIFIED_AI_DECISION_AND_REASONING",
            "status": status,
            "generated_at": now.isoformat(),
            "unified_decision_fingerprint": fingerprint,
            "global_blockers": global_blockers,
            "global_warnings": global_warnings,
            "symbol_decision_count": len(decisions),
            "approved_candidate_count": sum(
                1
                for item in decisions
                if item["decision_status"] == "APPROVED_CANDIDATE"
            ),
            "allocation_count": len(allocations),
            "decisions": decisions,
            "portfolio_allocation_draft": allocations,
            "reasoning_mode": (
                "DETERMINISTIC_EXPLAINABLE_AI_NO_EXTERNAL_LLM"
            ),
            "llm_api_enabled": False,
            "live_data_network_enabled": False,
            "credentials_loaded": False,
            "automatic_execution_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V2001_TO_V2200_MODEL_VALIDATION_BACKTEST_AND_CALIBRATION"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            output_dir / "unified_ai_decision_latest.json",
            result,
        )
        write_json(
            output_dir / "explainable_decision_reports.json",
            {
                "records": [
                    {
                        "symbol": item["symbol"],
                        "rank": item["rank"],
                        "decision_status": item["decision_status"],
                        "final_signal": item["final_signal"],
                        "final_score": item["final_score"],
                        "confidence": item["confidence"],
                        "reasoning": item["reasoning"],
                    }
                    for item in decisions
                ]
            },
        )
        write_json(
            output_dir / "unified_candidate_queue.json",
            {
                "generated_at": now.isoformat(),
                "automatic_execution_enabled": False,
                "items": [
                    item
                    for item in decisions
                    if item["decision_status"] == "APPROVED_CANDIDATE"
                ],
            },
        )
        write_json(
            output_dir / "portfolio_allocation_draft.json",
            {
                "generated_at": now.isoformat(),
                "execution_enabled": False,
                "items": allocations,
            },
        )
        write_json(
            output_dir / "unified_decision_dashboard.json",
            {
                "status": status,
                "symbol_decision_count": len(decisions),
                "approved_candidate_count": result[
                    "approved_candidate_count"
                ],
                "allocation_count": len(allocations),
                "warning_count": len(global_warnings),
                "blocker_count": len(global_blockers),
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        write_csv(
            output_dir / "unified_decision_dataset.csv",
            [
                {
                    "symbol": item["symbol"],
                    "rank": item["rank"],
                    "final_score": item["final_score"],
                    "final_signal": item["final_signal"],
                    "confidence": item["confidence"],
                    "decision_status": item["decision_status"],
                    "event_risk": item["event_risk"],
                    "available_weight": item["available_weight"],
                    "missing_components": ",".join(
                        item["missing_components"]
                    ),
                    "blockers": ",".join(item["blockers"]),
                }
                for item in decisions
            ],
        )
        for item in decisions:
            append_jsonl(
                output_dir / "unified_decision_store.jsonl",
                item,
            )
        append_jsonl(
            output_dir / "unified_ai_decision_ledger.jsonl",
            result,
        )
        return result
