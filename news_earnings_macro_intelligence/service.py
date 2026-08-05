from __future__ import annotations
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .earnings import score_earnings
from .io import append_jsonl, read_json_optional, write_csv, write_json
from .macro import macro_regime, score_macro_event
from .text_scoring import sentiment_score, urgency_score


class NewsEarningsMacroIntelligenceService:
    def evaluate(
        self,
        *,
        news_path: Path,
        earnings_path: Path,
        macro_path: Path,
        output_dir: Path,
        now=None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        news_payload = read_json_optional(news_path)
        earnings_payload = read_json_optional(earnings_path)
        macro_payload = read_json_optional(macro_path)

        news_items = list(news_payload.get("items", []))
        earnings_items = list(earnings_payload.get("items", []))
        macro_items = list(macro_payload.get("items", []))

        blockers = []
        if not news_payload:
            blockers.append("NEWS_INPUT_MISSING")
        if not earnings_payload:
            blockers.append("EARNINGS_INPUT_MISSING")
        if not macro_payload:
            blockers.append("MACRO_INPUT_MISSING")

        scored_news = []
        for item in news_items:
            text = " ".join(
                str(item.get(key, ""))
                for key in ("headline", "summary", "source")
            )
            sentiment = sentiment_score(text)
            urgency = urgency_score(text)
            importance = max(
                0.0,
                min(1.0, float(item.get("importance", 0.5))),
            )
            impact = max(
                -1.0,
                min(1.0, sentiment * (0.6 + importance * 0.4)),
            )
            scored_news.append({
                **item,
                "sentiment_score": round(sentiment, 8),
                "urgency_score": round(urgency, 8),
                "impact_score": round(impact, 8),
            })

        scored_earnings = []
        for item in earnings_items:
            scored_earnings.append({
                **item,
                **score_earnings(item),
            })

        scored_macro = []
        for item in macro_items:
            scored_macro.append({
                **item,
                **score_macro_event(item),
            })

        macro_summary = macro_regime(scored_macro)

        symbol_news = defaultdict(list)
        symbol_earnings = defaultdict(list)

        for item in scored_news:
            for symbol in item.get("symbols", []):
                symbol_news[str(symbol).upper()].append(item)

        for item in scored_earnings:
            symbol = str(item.get("symbol", "")).upper()
            if symbol:
                symbol_earnings[symbol].append(item)

        symbols = sorted(set(symbol_news) | set(symbol_earnings))
        profiles = []
        for symbol in symbols:
            news_for_symbol = symbol_news.get(symbol, [])
            earnings_for_symbol = symbol_earnings.get(symbol, [])

            news_score = (
                sum(x["impact_score"] for x in news_for_symbol)
                / len(news_for_symbol)
                if news_for_symbol else 0.0
            )
            urgency = max(
                [x["urgency_score"] for x in news_for_symbol] or [0.0]
            )
            earnings_score = (
                sum(x["earnings_score"] for x in earnings_for_symbol)
                / len(earnings_for_symbol)
                if earnings_for_symbol else 0.0
            )
            macro_score = macro_summary["aggregate_macro_score"]

            composite = (
                news_score * 0.40
                + earnings_score * 0.40
                + macro_score * 0.20
            )
            composite = max(-1.0, min(1.0, composite))
            event_risk = max(
                urgency,
                min(1.0, abs(earnings_score) * 0.8),
            )

            if composite >= 0.20:
                signal = "BULLISH"
            elif composite <= -0.20:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            confidence = min(
                100.0,
                35.0
                + min(len(news_for_symbol) * 8.0, 24.0)
                + min(len(earnings_for_symbol) * 16.0, 24.0)
                + abs(composite) * 20.0,
            )

            profiles.append({
                "symbol": symbol,
                "news_item_count": len(news_for_symbol),
                "earnings_event_count": len(earnings_for_symbol),
                "news_score": round(news_score, 8),
                "earnings_score": round(earnings_score, 8),
                "macro_score": round(macro_score, 8),
                "event_risk": round(event_risk, 8),
                "intelligence_score": round(composite, 8),
                "intelligence_signal": signal,
                "confidence": round(confidence, 6),
            })

        profiles.sort(
            key=lambda x: (
                x["confidence"],
                abs(x["intelligence_score"]),
            ),
            reverse=True,
        )
        for index, profile in enumerate(profiles, 1):
            profile["rank"] = index

        status = (
            "PASS"
            if not blockers and (news_items or earnings_items or macro_items)
            else "BLOCKED"
        )

        seed = {
            "news": scored_news,
            "earnings": scored_earnings,
            "macro": scored_macro,
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
            "stage": "V1401_TO_V1600_NEWS_EARNINGS_MACRO_INTELLIGENCE",
            "status": status,
            "generated_at": now.isoformat(),
            "intelligence_bundle_fingerprint": fingerprint,
            "global_blockers": blockers,
            "news_item_count": len(scored_news),
            "earnings_event_count": len(scored_earnings),
            "macro_event_count": len(scored_macro),
            "symbol_profile_count": len(profiles),
            "macro_summary": macro_summary,
            "symbol_profiles": profiles,
            "scored_news": scored_news,
            "scored_earnings": scored_earnings,
            "scored_macro": scored_macro,
            "input_mode": "OFFLINE_FIXTURE_OR_USER_SUPPLIED_JSON",
            "live_news_network_enabled": False,
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
                "V1601_TO_V1800_FUNDAMENTAL_SECTOR_OPTIONS_INTELLIGENCE"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            output_dir / "news_earnings_macro_latest.json",
            result,
        )
        write_json(
            output_dir / "symbol_intelligence_profiles.json",
            {"records": profiles},
        )
        write_json(
            output_dir / "macro_regime_latest.json",
            macro_summary,
        )
        write_json(
            output_dir / "news_sentiment_latest.json",
            {"items": scored_news},
        )
        write_json(
            output_dir / "earnings_intelligence_latest.json",
            {"items": scored_earnings},
        )
        write_json(
            output_dir / "macro_events_latest.json",
            {"items": scored_macro},
        )
        write_csv(
            output_dir / "symbol_intelligence_dataset.csv",
            profiles,
        )
        for profile in profiles:
            append_jsonl(
                output_dir / "symbol_intelligence_store.jsonl",
                profile,
            )
        append_jsonl(
            output_dir / "news_earnings_macro_ledger.jsonl",
            result,
        )
        return result
