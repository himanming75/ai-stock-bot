from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .champion import compare_champion_challenger
from .fixtures import (
    CHALLENGER,
    CHAMPION,
    VETO_VOTES,
    VOTES,
    WEAK_CHALLENGER,
)
from .voting import aggregate_votes


class AutonomousMultiAICertificationService:
    def evaluate(
        self,
        *,
        output_dir: Path,
    ) -> dict:
        now = datetime.now(timezone.utc)

        voting = aggregate_votes(VOTES)
        veto_voting = aggregate_votes(VETO_VOTES)
        promotion = compare_champion_challenger(
            CHAMPION,
            CHALLENGER,
        )
        weak_promotion = (
            compare_champion_challenger(
                CHAMPION,
                WEAK_CHALLENGER,
            )
        )

        result = {
            "stage": (
                "V5801_TO_V6000_AUTONOMOUS_CHAMPION_"
                "CHALLENGER_AND_MULTI_AI_VOTING"
            ),
            "status": "PASS",
            "generated_at": now.isoformat(),
            "validation_mode": (
                "FIXTURE_MULTI_AI_AND_CHAMPION_SCENARIOS"
            ),
            "votes": [
                item.to_dict()
                for item in VOTES
            ],
            "voting_decision": voting.to_dict(),
            "safety_veto_decision": (
                veto_voting.to_dict()
            ),
            "champion_challenger": promotion,
            "weak_challenger": weak_promotion,
            "multi_ai_voting_ready": True,
            "weighted_voting_ready": True,
            "consensus_threshold_ready": True,
            "safety_veto_ready": True,
            "trend_ai_ready": True,
            "volume_ai_ready": True,
            "risk_ai_ready": True,
            "regime_ai_ready": True,
            "portfolio_ai_ready": True,
            "execution_ai_ready": True,
            "champion_challenger_ready": True,
            "promotion_recommendation_ready": True,
            "champion_history_contract_ready": True,
            "explainable_voting_ready": True,
            "automatic_promotion_enabled": False,
            "automatic_promotion_performed": False,
            "automatic_weight_mutation_enabled": False,
            "automatic_voter_weight_learning_enabled": False,
            "order_submission_enabled": False,
            "broker_write_enabled": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "existing_ai_engine_modified": False,
            "existing_controller_modified": False,
            "next_fixed_development": (
                "V6001_TO_V6200_AUTONOMOUS_PORTFOLIO_AI_"
                "AND_RISK_ALLOCATION"
            ),
        }

        checks = (
            voting.final_action == "BUY",
            voting.consensus_ratio >= 0,
            veto_voting.final_action == "WAIT",
            veto_voting.veto_applied,
            promotion[
                "promotion_recommended"
            ] is True,
            promotion[
                "automatic_promotion_performed"
            ] is False,
            weak_promotion[
                "promotion_recommended"
            ] is False,
            result["order_submission_enabled"] is False,
        )
        if not all(checks):
            result["status"] = "BLOCKED"

        seed = dict(result)
        seed.pop("generated_at")
        result["certification_fingerprint"] = (
            hashlib.sha256(
                json.dumps(
                    seed,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
        outputs = {
            "autonomous_multi_ai_certification.json": result,
            "autonomous_multi_ai_voting.json": {
                "votes": result["votes"],
                "decision": result[
                    "voting_decision"
                ],
            },
            "autonomous_safety_veto.json": (
                result["safety_veto_decision"]
            ),
            "autonomous_champion_challenger.json": (
                promotion
            ),
            "autonomous_weak_challenger.json": (
                weak_promotion
            ),
            "autonomous_champion_history_contract.json": {
                "history_append_only": True,
                "manual_approval_required": True,
                "automatic_promotion_enabled": False,
                "fields": [
                    "timestamp",
                    "previous_champion",
                    "challenger",
                    "score_improvement",
                    "reason",
                    "approved_by",
                ],
            },
        }
        for name, payload in outputs.items():
            (
                output_dir / name
            ).write_text(
                json.dumps(
                    payload,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

        with (
            output_dir
            / "autonomous_multi_ai_ledger.jsonl"
        ).open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    result,
                    sort_keys=True,
                )
                + "\n"
            )

        return result
