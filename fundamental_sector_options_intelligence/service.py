from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .fundamental import score_fundamental
from .io import append_jsonl, read_json_optional, write_csv, write_json
from .options import score_options
from .sector import score_sector
from .utils import clamp, signal


class FundamentalSectorOptionsIntelligenceService:
    def evaluate(
        self,
        *,
        fundamentals_path: Path,
        sectors_path: Path,
        options_path: Path,
        output_dir: Path,
        now=None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)

        fundamentals_payload = read_json_optional(fundamentals_path)
        sectors_payload = read_json_optional(sectors_path)
        options_payload = read_json_optional(options_path)

        fundamentals = list(fundamentals_payload.get("items", []))
        sectors = list(sectors_payload.get("items", []))
        options = list(options_payload.get("items", []))

        blockers = []
        if not fundamentals_payload:
            blockers.append("FUNDAMENTALS_INPUT_MISSING")
        if not sectors_payload:
            blockers.append("SECTOR_INPUT_MISSING")
        if not options_payload:
            blockers.append("OPTIONS_INPUT_MISSING")

        sector_scores = [score_sector(item) for item in sectors]
        sector_scores.sort(
            key=lambda x: x["sector_score"],
            reverse=True,
        )
        for rank, item in enumerate(sector_scores, 1):
            item["sector_rank"] = rank

        sector_map = {
            item["sector"]: item
            for item in sector_scores
        }
        options_map = {
            str(item.get("symbol", "")).upper(): item
            for item in options
            if item.get("symbol")
        }

        profiles = []
        for item in fundamentals:
            symbol = str(item.get("symbol", "")).upper()
            if not symbol:
                continue

            fundamental_result = score_fundamental(item)
            sector_name = str(item.get("sector", "UNKNOWN"))
            sector_result = sector_map.get(
                sector_name,
                {
                    "sector": sector_name,
                    "sector_score": 0.0,
                    "sector_rank": None,
                },
            )

            options_item = options_map.get(symbol)
            options_result = (
                score_options(options_item)
                if options_item
                else {
                    "options_score": 0.0,
                    "options_signal": "NEUTRAL",
                    "positioning_score": 0.0,
                    "volatility_bias_score": 0.0,
                    "gamma_score": 0.0,
                    "options_event_risk": 0.0,
                }
            )

            composite = clamp(
                fundamental_result["fundamental_score"] * 0.55
                + sector_result["sector_score"] * 0.25
                + options_result["options_score"] * 0.20
            )
            confidence = min(
                100.0,
                45.0
                + abs(composite) * 35.0
                + (8.0 if options_item else 0.0)
                + (7.0 if sector_result.get("sector_rank") else 0.0),
            )

            profiles.append({
                "symbol": symbol,
                "sector": sector_name,
                "sector_rank": sector_result.get("sector_rank"),
                **fundamental_result,
                **options_result,
                "sector_score": sector_result["sector_score"],
                "composite_score": round(composite, 8),
                "composite_signal": signal(composite),
                "confidence": round(confidence, 6),
                "decision_eligible": (
                    confidence >= 55.0
                    and signal(composite) != "NEUTRAL"
                    and options_result["options_event_risk"] <= 0.85
                ),
            })

        profiles.sort(
            key=lambda x: (
                x["decision_eligible"],
                x["confidence"],
                abs(x["composite_score"]),
            ),
            reverse=True,
        )
        for rank, profile in enumerate(profiles, 1):
            profile["rank"] = rank

        status = (
            "PASS"
            if not blockers and (fundamentals or sectors or options)
            else "BLOCKED"
        )

        seed = {
            "fundamentals": fundamentals,
            "sectors": sector_scores,
            "options": options,
            "profiles": profiles,
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
            "stage": "V1601_TO_V1800_FUNDAMENTAL_SECTOR_OPTIONS_INTELLIGENCE",
            "status": status,
            "generated_at": now.isoformat(),
            "intelligence_bundle_fingerprint": fingerprint,
            "global_blockers": blockers,
            "fundamental_record_count": len(fundamentals),
            "sector_record_count": len(sector_scores),
            "options_record_count": len(options),
            "symbol_profile_count": len(profiles),
            "decision_eligible_count": sum(
                1 for item in profiles if item["decision_eligible"]
            ),
            "sector_ranking": sector_scores,
            "symbol_profiles": profiles,
            "input_mode": "OFFLINE_FIXTURE_OR_USER_SUPPLIED_JSON",
            "live_fundamental_network_enabled": False,
            "live_options_network_enabled": False,
            "credentials_loaded": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V1801_TO_V2000_UNIFIED_AI_DECISION_AND_LLM_REASONING"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            output_dir / "fundamental_sector_options_latest.json",
            result,
        )
        write_json(
            output_dir / "fundamental_profiles.json",
            {
                "records": [
                    {
                        key: value
                        for key, value in item.items()
                        if key in {
                            "symbol", "sector", "fundamental_score",
                            "fundamental_signal", "valuation_score",
                            "quality_score", "growth_score",
                            "balance_sheet_score",
                            "shareholder_return_score",
                        }
                    }
                    for item in profiles
                ]
            },
        )
        write_json(
            output_dir / "sector_rotation_ranking.json",
            {"records": sector_scores},
        )
        write_json(
            output_dir / "options_intelligence_profiles.json",
            {
                "records": [
                    {
                        key: value
                        for key, value in item.items()
                        if key in {
                            "symbol", "options_score", "options_signal",
                            "positioning_score",
                            "volatility_bias_score", "gamma_score",
                            "options_event_risk",
                        }
                    }
                    for item in profiles
                ]
            },
        )
        write_json(
            output_dir / "composite_candidate_queue.json",
            {
                "generated_at": now.isoformat(),
                "automatic_execution_enabled": False,
                "items": [
                    item for item in profiles
                    if item["decision_eligible"]
                ],
            },
        )
        write_csv(
            output_dir / "fundamental_sector_options_dataset.csv",
            profiles,
        )
        for profile in profiles:
            append_jsonl(
                output_dir / "fundamental_sector_options_store.jsonl",
                profile,
            )
        append_jsonl(
            output_dir / "fundamental_sector_options_ledger.jsonl",
            result,
        )
        return result
