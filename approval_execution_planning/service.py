from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .guards import evaluate_guards
from .io import append_jsonl, read_json, read_json_optional, write_json
from .planner import build_plan

class ApprovalExecutionPlanningService:
    def evaluate(
        self,
        *,
        allocation_path: Path,
        approval_path: Path,
        market_path: Path,
        policy_path: Path,
        prior_plans_path: Path,
        output_dir: Path,
        now: datetime | None = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        allocation = read_json_optional(allocation_path)
        approval = read_json_optional(approval_path)
        market = read_json_optional(market_path)
        policy = read_json(policy_path)
        prior = read_json_optional(prior_plans_path)

        allocation_queue = allocation.get("allocation_queue", [])
        duplicate_keys = set(prior.get("duplicate_keys", []))
        results = []

        for item in allocation_queue:
            symbol = str(item.get("symbol", ""))
            symbol_market = market.get("symbols", {}).get(symbol, {})
            blockers = evaluate_guards(
                item,
                approval=approval,
                market=symbol_market,
                policy=policy,
                duplicate_keys=duplicate_keys,
            )
            plan = build_plan(item, policy)
            plan["blockers"] = blockers
            plan["status"] = "READY_FOR_MANUAL_REVIEW" if not blockers else "BLOCKED"
            plan["market_snapshot"] = symbol_market
            plan["approval_status"] = approval.get("status")
            plan["execution_submission_allowed"] = False
            results.append(plan)

        ready = [
            item for item in results
            if item["status"] == "READY_FOR_MANUAL_REVIEW"
        ]
        blocked = [
            item for item in results
            if item["status"] == "BLOCKED"
        ]

        global_blockers = []
        if not allocation:
            global_blockers.append("ALLOCATION_INPUT_MISSING")
        if not approval:
            global_blockers.append("APPROVAL_INPUT_MISSING")
        if not market:
            global_blockers.append("MARKET_EXECUTION_INPUT_MISSING")

        status = (
            "INSUFFICIENT_INPUT"
            if global_blockers
            else "PASS"
        )

        seed = {
            "allocation_fingerprint": allocation.get(
                "portfolio_intelligence_fingerprint"
            ),
            "approval_hash": approval.get("audit_record_hash"),
            "plans": results,
        }
        fingerprint = hashlib.sha256(
            json.dumps(
                seed,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        result = {
            "stage": "V591_TO_V640_APPROVAL_AND_EXECUTION_PLANNING",
            "status": status,
            "generated_at": now.isoformat(),
            "execution_planning_fingerprint": fingerprint,
            "global_blockers": global_blockers,
            "plan_count": len(results),
            "ready_for_manual_review_count": len(ready),
            "blocked_plan_count": len(blocked),
            "plans": results,
            "ready_plans": ready,
            "blocked_plans": blocked,
            "approval_status": approval.get("status"),
            "execution_mode": "DRY_RUN_PLANNING_ONLY",
            "manual_review_required": True,
            "approval_token_consumed": False,
            "order_ticket_generation_enabled": False,
            "paper_order_submission_enabled": False,
            "live_order_submission_enabled": False,
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
                "V641_TO_V690_PAPER_ORDER_TICKET_BUILDER"
            ),
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "execution_planning_latest.json", result)
        write_json(
            output_dir / "manual_review_queue.json",
            {
                "generated_at": now.isoformat(),
                "ready_for_manual_review_count": len(ready),
                "plans": ready,
                "order_ticket_generation_enabled": False,
                "submission_enabled": False,
            },
        )
        write_json(
            output_dir / "execution_planning_dashboard.json",
            {
                "generated_at": now.isoformat(),
                "status": status,
                "plan_count": len(results),
                "ready_for_manual_review_count": len(ready),
                "blocked_plan_count": len(blocked),
                "execution_mode": "DRY_RUN_PLANNING_ONLY",
                "paper_orders_submitted": 0,
                "live_orders_submitted": 0,
            },
        )
        append_jsonl(
            output_dir / "execution_planning_ledger.jsonl",
            result,
        )
        for plan in results:
            append_jsonl(
                output_dir / "execution_plan_ledger.jsonl",
                {
                    "generated_at": now.isoformat(),
                    **plan,
                    "order_ticket_created": False,
                    "submission_enabled": False,
                },
            )
        return result
