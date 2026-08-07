from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PaperObservabilityIntelligence:
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

    def _candidate_sources(self) -> list[Path]:
        return [
            self.root
            / "release/v14001_15000_paper_autonomous_execution/actual/"
              "latest_paper_execution_cycle.json",
            self.root
            / "release/smart_safe_trading_guard_1_0/input/"
              "shadow_snapshot.json",
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "latest_shadow_guard_decision.json",
        ]

    def _selected_candidate(self) -> dict[str, Any]:
        for path in self._candidate_sources():
            payload = self._load(path)
            candidate = (
                payload.get("selected_candidate")
                or payload.get("candidate")
            )
            if isinstance(candidate, dict):
                return {
                    "symbol": str(candidate.get("symbol", "")).upper(),
                    "side": str(candidate.get("side", "HOLD")).upper(),
                    "confidence": self._float(
                        candidate.get("confidence")
                    ),
                    "consensus_score": self._float(
                        candidate.get("consensus_score")
                    ),
                    "reward_risk": self._float(
                        candidate.get("reward_risk")
                    ),
                    "quantity": self._float(
                        candidate.get("quantity")
                    ),
                    "reference_price": self._float(
                        candidate.get("reference_price")
                    ),
                }
        return {
            "symbol": "",
            "side": "HOLD",
            "confidence": 0.0,
            "consensus_score": 0.0,
            "reward_risk": 0.0,
            "quantity": 0.0,
            "reference_price": 0.0,
        }

    def _top_candidates(self) -> list[dict[str, Any]]:
        selected = self._selected_candidate()
        result = [dict(selected, rank=1, source="SELECTED_CANDIDATE")]

        # Read-only fallback candidates. These do not alter selection or orders.
        watchlist_path = (
            self.root
            / "release/operator_dashboard_1_1/config/watchlist.json"
        )
        watchlist = self._load(watchlist_path)
        symbols = watchlist.get("symbols", [])
        if not isinstance(symbols, list):
            symbols = []

        seen = {selected.get("symbol", "")}
        for symbol in symbols:
            normalized = str(symbol).upper().strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append({
                "rank": len(result) + 1,
                "symbol": normalized,
                "side": "HOLD",
                "confidence": 0.0,
                "consensus_score": 0.0,
                "reward_risk": 0.0,
                "quantity": 0.0,
                "reference_price": 0.0,
                "source": "WATCHLIST_OBSERVATION_ONLY",
            })
            if len(result) >= 5:
                break

        return result[:5]

    def _guard(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "latest_shadow_guard_decision.json"
        )

    def _session(self) -> dict[str, Any]:
        return self._load(
            self.root
            / "runtime/paper_autonomous_daily_session/"
              "latest_status.json"
        )

    def _explanation(
        self,
        candidate: dict[str, Any],
        guard: dict[str, Any],
        session: dict[str, Any],
    ) -> dict[str, Any]:
        positive: list[str] = []
        cautions: list[str] = []

        if candidate["confidence"] >= 0.8:
            positive.append("HIGH_CONFIDENCE")
        if candidate["consensus_score"] >= 0.75:
            positive.append("STRONG_CONSENSUS")
        if candidate["reward_risk"] >= 1.5:
            positive.append("ACCEPTABLE_REWARD_RISK")

        for issue in guard.get("issues", []):
            code = issue.get("code")
            if code:
                cautions.append(str(code))

        for warning in guard.get("warnings", []):
            code = warning.get("code")
            if code:
                cautions.append(str(code))

        return {
            "summary": (
                f"{candidate['side']} {candidate['symbol']}"
                if candidate["symbol"]
                else "NO_ACTIVE_CANDIDATE"
            ),
            "positive_reasons": positive,
            "caution_reasons": sorted(set(cautions)),
            "guard_action": guard.get("action", "NOT_AVAILABLE"),
            "guard_enforced": bool(guard.get("enforced", False)),
            "session_stage": session.get("stage", "NOT_AVAILABLE"),
            "interpretation": (
                "OBSERVATION_ONLY_NO_ORDER_EFFECT"
            ),
        }

    def run(self) -> dict[str, Any]:
        candidate = self._selected_candidate()
        guard = self._guard()
        session = self._session()
        top5 = self._top_candidates()
        explanation = self._explanation(
            candidate, guard, session
        )

        runtime = (
            self.root / "runtime/paper_observability_intelligence"
        )

        journal_entry = {
            "observed_at_utc": self._now(),
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "selected_candidate": candidate,
            "top_candidates": top5,
            "explanation": explanation,
            "shadow_guard": {
                "action": guard.get("action"),
                "would_allow_order": guard.get(
                    "would_allow_order"
                ),
                "quality_score": guard.get("quality_score"),
                "issue_codes": [
                    item.get("code")
                    for item in guard.get("issues", [])
                    if item.get("code")
                ],
            },
            "daily_session": {
                "stage": session.get("stage"),
                "status": session.get("status"),
                "today_order_count": session.get(
                    "today_order_count"
                ),
                "maximum_daily_orders": session.get(
                    "maximum_daily_orders"
                ),
            },
        }

        self._write(
            runtime / "latest_observability_report.json",
            journal_entry,
        )
        self._append(
            runtime / "trade_journal.jsonl",
            journal_entry,
        )

        daily_summary = {
            "generated_at_utc": self._now(),
            "mode": "READ_ONLY_OBSERVABILITY",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "selected_symbol": candidate["symbol"],
            "selected_side": candidate["side"],
            "confidence": candidate["confidence"],
            "consensus_score": candidate["consensus_score"],
            "reward_risk": candidate["reward_risk"],
            "guard_action": guard.get("action"),
            "guard_enforced": bool(
                guard.get("enforced", False)
            ),
            "session_stage": session.get("stage"),
            "today_order_count": session.get(
                "today_order_count"
            ),
            "top_candidate_count": len(top5),
            "broker_write_performed": False,
            "status": "PASS",
        }
        self._write(runtime / "daily_summary.json", daily_summary)

        return {
            "stage": "PAPER_OBSERVABILITY_INTELLIGENCE_1_0",
            "status": "PASS",
            "mode": "READ_ONLY_OBSERVABILITY",
            "paper_only": True,
            "etrade_live_write_enabled": False,
            "broker_write_performed": False,
            "report_path": str(
                runtime / "latest_observability_report.json"
            ),
            "journal_path": str(runtime / "trade_journal.jsonl"),
            "daily_summary_path": str(
                runtime / "daily_summary.json"
            ),
            "top_candidate_count": len(top5),
            "selected_candidate": candidate,
            "explanation": explanation,
        }
