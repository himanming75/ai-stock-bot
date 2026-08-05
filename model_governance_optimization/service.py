from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from .io import append_jsonl, read_json_optional, write_csv, write_json
from .scoring import governance_score

class ModelGovernanceOptimizationService:
    def evaluate(self, *, candidates_path: Path, champion_path: Path, policy_path: Path, output_dir: Path, now=None) -> dict:
        now = now or datetime.now(timezone.utc)
        candidates_payload = read_json_optional(candidates_path)
        champion_payload = read_json_optional(champion_path)
        policy = read_json_optional(policy_path)

        candidates = list(candidates_payload.get("items", []))
        champion = champion_payload.get("champion", {})
        blockers = []
        if not candidates_payload:
            blockers.append("CANDIDATE_INPUT_MISSING")
        if not champion_payload:
            blockers.append("CHAMPION_INPUT_MISSING")
        if not policy:
            blockers.append("GOVERNANCE_POLICY_MISSING")

        scored = []
        for candidate in candidates:
            item = {**candidate, **governance_score(candidate)}
            item["eligible_for_promotion_review"] = (
                item["sample_count"] >= int(policy.get("minimum_sample_count", 50))
                and item["test_score"] >= float(policy.get("minimum_test_score", 0.55))
                and item["max_drawdown"] >= -abs(float(policy.get("maximum_drawdown", 0.20)))
                and item["calibration_error"] <= float(policy.get("maximum_calibration_error", 0.20))
                and not item["warnings"]
            )
            scored.append(item)

        scored.sort(key=lambda x: (x["eligible_for_promotion_review"], x["governance_score"]), reverse=True)
        for rank, item in enumerate(scored, 1):
            item["rank"] = rank

        champion_score = governance_score(champion) if champion else {"governance_score": 0.0}
        best = scored[0] if scored else None
        improvement = (
            best["governance_score"] - champion_score["governance_score"]
            if best else 0.0
        )
        minimum_improvement = float(policy.get("minimum_promotion_improvement", 0.03))

        if (
            best
            and best["eligible_for_promotion_review"]
            and improvement >= minimum_improvement
        ):
            recommendation = "RECOMMEND_CHALLENGER_PROMOTION_REVIEW"
        else:
            recommendation = "KEEP_CURRENT_CHAMPION"

        promotion = {
            "recommendation": recommendation,
            "current_champion_id": champion.get("model_id"),
            "recommended_challenger_id": best.get("model_id") if best else None,
            "governance_score_improvement": round(improvement, 8),
            "minimum_required_improvement": minimum_improvement,
            "automatic_promotion_enabled": False,
            "promotion_applied": False,
            "manual_approval_required": True,
        }

        rollback = {
            "rollback_ready": bool(champion),
            "rollback_model_id": champion.get("model_id"),
            "rollback_snapshot": champion,
            "automatic_rollback_enabled": False,
            "rollback_applied": False,
        }

        status = "PASS" if not blockers and scored else "BLOCKED"
        seed = {"scored": scored, "champion": champion, "promotion": promotion, "policy": policy}
        fingerprint = hashlib.sha256(json.dumps(seed, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

        result = {
            "stage": "V2201_TO_V2400_WALK_FORWARD_OPTIMIZATION_MODEL_GOVERNANCE",
            "status": status,
            "generated_at": now.isoformat(),
            "governance_fingerprint": fingerprint,
            "global_blockers": blockers,
            "candidate_count": len(scored),
            "promotion_eligible_count": sum(1 for x in scored if x["eligible_for_promotion_review"]),
            "champion": champion,
            "champion_governance": champion_score,
            "challenger_ranking": scored,
            "promotion_recommendation": promotion,
            "rollback_plan": rollback,
            "automatic_promotion_enabled": False,
            "automatic_rollback_enabled": False,
            "weights_changed": False,
            "thresholds_changed": False,
            "controller_files_modified": False,
            "runtime_files_modified": False,
            "actual_external_network_used": False,
            "actual_broker_read_performed": False,
            "actual_broker_write_performed": False,
            "actual_order_submission_performed": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
            "next_fixed_development": "V2401_TO_V2600_AI_ENGINE_FINAL_CERTIFICATION",
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "model_governance_latest.json", result)
        write_json(output_dir / "challenger_ranking.json", {"items": scored})
        write_json(output_dir / "promotion_recommendation.json", promotion)
        write_json(output_dir / "rollback_plan.json", rollback)
        write_json(output_dir / "champion_registry_snapshot.json", {"champion": champion, "modified": False})
        write_json(output_dir / "governance_dashboard.json", {
            "status": status,
            "candidate_count": len(scored),
            "promotion_eligible_count": result["promotion_eligible_count"],
            "recommendation": recommendation,
            "automatic_promotion_enabled": False,
            "automatic_rollback_enabled": False,
        })
        write_csv(output_dir / "challenger_performance_dataset.csv", scored)
        append_jsonl(output_dir / "model_governance_ledger.jsonl", result)
        return result
