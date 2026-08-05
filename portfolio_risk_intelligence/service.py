from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .analytics import (
    correlation_value,
    current_exposure,
    sector_exposure,
    serialize_decimal_map,
    symbol_exposure,
)
from .io import append_jsonl, read_json, read_json_optional, write_json
from .models import D, ZERO, HUNDRED, text
from .sizing import candidate_budget

class PortfolioRiskIntelligenceService:
    def evaluate(
        self,
        *,
        ai_decision_path: Path,
        portfolio_path: Path,
        risk_path: Path,
        metadata_path: Path,
        correlation_path: Path,
        policy_path: Path,
        output_dir: Path,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        ai = read_json_optional(ai_decision_path)
        portfolio = read_json_optional(portfolio_path)
        risk = read_json_optional(risk_path)
        metadata = read_json_optional(metadata_path)
        correlations = read_json_optional(correlation_path)
        policy = read_json(policy_path)

        exposure = current_exposure(portfolio)
        sectors = sector_exposure(exposure["positions"])
        symbols = symbol_exposure(exposure["positions"])
        risk_level = str(risk.get("risk_level", "UNKNOWN"))
        candidates = list(ai.get("candidate_queue", []))

        input_blockers = []
        if not ai:
            input_blockers.append("AI_DECISION_INPUT_MISSING")
        if not portfolio:
            input_blockers.append("PORTFOLIO_INPUT_MISSING")
        if exposure["equity"] <= ZERO:
            input_blockers.append("ACCOUNT_EQUITY_MISSING_OR_ZERO")

        plans = []
        max_sector_percent = D(
            policy.get("max_sector_exposure_percent", "35")
        )
        max_symbol_percent = D(
            policy.get("max_single_position_percent", "5")
        )
        max_corr = D(policy.get("maximum_pair_correlation", "0.85"))

        for candidate in candidates:
            plan = candidate_budget(
                candidate,
                equity=exposure["equity"],
                cash=exposure["cash"],
                policy=policy,
                portfolio_risk_level=risk_level,
            )
            symbol = str(candidate.get("symbol"))
            info = metadata.get("symbols", {}).get(symbol, {})
            sector = str(info.get("sector") or "UNKNOWN")
            proposed = D(plan["proposed_notional"])

            current_sector = sectors.get(sector, ZERO)
            projected_sector = current_sector + proposed
            projected_sector_percent = (
                projected_sector / exposure["equity"] * HUNDRED
                if exposure["equity"] else ZERO
            )
            current_symbol = symbols.get(symbol, ZERO)
            projected_symbol = current_symbol + proposed
            projected_symbol_percent = (
                projected_symbol / exposure["equity"] * HUNDRED
                if exposure["equity"] else ZERO
            )

            correlation_conflicts = []
            for position in exposure["positions"]:
                held = str(position.get("symbol") or "")
                if not held or held == symbol:
                    continue
                corr = correlation_value(
                    correlations.get("matrix", {}),
                    symbol,
                    held,
                )
                if abs(corr) > max_corr:
                    correlation_conflicts.append(
                        {"held_symbol": held, "correlation": text(corr)}
                    )

            blockers = list(plan["blockers"])
            if projected_sector_percent > max_sector_percent:
                blockers.append("SECTOR_EXPOSURE_LIMIT_EXCEEDED")
            if projected_symbol_percent > max_symbol_percent:
                blockers.append("SYMBOL_EXPOSURE_LIMIT_EXCEEDED")
            if correlation_conflicts:
                blockers.append("CORRELATION_LIMIT_EXCEEDED")
            if sector == "UNKNOWN" and policy.get(
                "block_unknown_sector", True
            ):
                blockers.append("SECTOR_METADATA_MISSING")

            plan.update(
                {
                    "sector": sector,
                    "current_sector_exposure": text(current_sector),
                    "projected_sector_exposure": text(projected_sector),
                    "projected_sector_percent": text(
                        projected_sector_percent
                    ),
                    "current_symbol_exposure": text(current_symbol),
                    "projected_symbol_exposure": text(projected_symbol),
                    "projected_symbol_percent": text(
                        projected_symbol_percent
                    ),
                    "correlation_conflicts": correlation_conflicts,
                    "blockers": sorted(set(blockers)),
                    "status": "READY" if not blockers else "BLOCKED",
                    "order_ticket_created": False,
                    "order_submission_enabled": False,
                }
            )
            plans.append(plan)

        ready = [item for item in plans if item["status"] == "READY"]
        blocked = [item for item in plans if item["status"] == "BLOCKED"]
        ready.sort(
            key=lambda item: D(item.get("proposed_notional")),
            reverse=True,
        )
        for index, item in enumerate(ready, start=1):
            item["allocation_rank"] = index

        total_proposed = sum(
            (D(item["proposed_notional"]) for item in ready),
            ZERO,
        )
        daily_cap = D(policy.get("max_daily_new_notional", "1000"))
        portfolio_blockers = list(input_blockers)
        if total_proposed > daily_cap:
            portfolio_blockers.append(
                "DAILY_NEW_NOTIONAL_LIMIT_EXCEEDED"
            )
            for item in ready:
                item["status"] = "BLOCKED"
                item["blockers"].append(
                    "DAILY_NEW_NOTIONAL_LIMIT_EXCEEDED"
                )
            blocked.extend(ready)
            ready = []

        status = (
            "INSUFFICIENT_PORTFOLIO_INPUT"
            if input_blockers
            else "PASS"
        )
        seed = {
            "ai_fingerprint": ai.get("decision_fingerprint"),
            "risk_level": risk_level,
            "plans": plans,
            "portfolio_blockers": portfolio_blockers,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V541_TO_V590_PORTFOLIO_AND_RISK_INTELLIGENCE",
            "status": status,
            "generated_at": now.isoformat(),
            "portfolio_intelligence_fingerprint": fingerprint,
            "source_ai_decision_fingerprint": ai.get(
                "decision_fingerprint"
            ),
            "risk_level": risk_level,
            "input_blockers": input_blockers,
            "portfolio_blockers": portfolio_blockers,
            "account_exposure": {
                "equity": text(exposure["equity"]),
                "cash": text(exposure["cash"]),
                "gross_exposure": text(exposure["gross"]),
                "net_exposure": text(exposure["net"]),
                "gross_exposure_percent": text(
                    exposure["gross_percent"]
                ),
                "net_exposure_percent": text(
                    exposure["net_percent"]
                ),
            },
            "sector_exposure": serialize_decimal_map(sectors),
            "symbol_exposure": serialize_decimal_map(symbols),
            "candidate_plan_count": len(plans),
            "ready_allocation_count": len(ready),
            "blocked_allocation_count": len(blocked),
            "total_ready_notional": text(
                sum((D(item["proposed_notional"]) for item in ready), ZERO)
            ),
            "allocation_queue": ready,
            "blocked_candidates": blocked,
            "all_candidate_plans": plans,
            "rebalance_orders_created": False,
            "actual_external_network_used": False,
            "actual_market_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_ticket_created": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "next_fixed_development": (
                "V591_TO_V640_APPROVAL_AND_EXECUTION_PLANNING"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "portfolio_risk_latest.json", result)
        write_json(
            output_dir / "allocation_queue.json",
            {
                "generated_at": now.isoformat(),
                "ready_allocation_count": len(ready),
                "allocation_queue": ready,
                "order_ticket_created": False,
                "order_submission_enabled": False,
            },
        )
        write_json(
            output_dir / "portfolio_risk_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "status": status,
                "risk_level": risk_level,
                "candidate_plan_count": len(plans),
                "ready_allocation_count": len(ready),
                "blocked_allocation_count": len(blocked),
                "total_ready_notional": result["total_ready_notional"],
                "account_exposure": result["account_exposure"],
                "sector_exposure": result["sector_exposure"],
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        write_json(
            output_dir / "exposure_snapshot.json",
            {
                "generated_at": now.isoformat(),
                "account_exposure": result["account_exposure"],
                "sector_exposure": result["sector_exposure"],
                "symbol_exposure": result["symbol_exposure"],
            },
        )
        append_jsonl(
            output_dir / "portfolio_risk_ledger.jsonl",
            result,
        )
        for plan in plans:
            append_jsonl(
                output_dir / "allocation_plan_ledger.jsonl",
                {
                    "generated_at": now.isoformat(),
                    **plan,
                    "order_ticket_created": False,
                    "order_submission_enabled": False,
                },
            )
        return result
