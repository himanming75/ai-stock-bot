from __future__ import annotations

import hashlib
import json
from pathlib import Path


DEFAULT_CHAMPION={
    "policy_id":"CHAMPION_V2_2_5_BASELINE",
    "min_confidence":0.75,
    "min_reward_risk":1.00,
    "execution_enabled":True,
}

SEED_CHALLENGERS=(
    {
        "policy_id":"SEED_CHALLENGER_A",
        "policy_type":"SEED_SHADOW_ONLY",
        "min_confidence":0.70,
        "min_reward_risk":1.15,
        "execution_enabled":False,
        "calibrated":False,
    },
    {
        "policy_id":"SEED_CHALLENGER_B",
        "policy_type":"SEED_SHADOW_ONLY",
        "min_confidence":0.80,
        "min_reward_risk":0.90,
        "execution_enabled":False,
        "calibrated":False,
    },
)


def _sha(payload):
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",",":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _f(value,default=0.0):
    try:
        return float(value)
    except (TypeError,ValueError):
        return default


class ChampionChallengerShadowComparatorV225:
    """
    Compare the current Champion selector threshold against shadow-only
    Challenger policies on exactly the same V2.2.1 canonical feature snapshot.

    No broker call and no order submission occur here.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.feature_latest=(
            self.root/"runtime"/
            "ai_signal_scoring_feature_snapshot_v2_2_1"/
            "latest_feature_snapshot.json"
        )
        self.policy_registry=(
            self.root/"runtime"/
            "ai_threshold_calibration_challenger_policy_v2_2_4"/
            "challenger_policy_registry.json"
        )
        self.runtime_dir=(
            self.root/"runtime"/
            "ai_champion_challenger_shadow_comparator_v2_2_5"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.ledger=self.runtime_dir/"comparison_ledger.jsonl"
        self.latest=self.runtime_dir/"latest_comparison.json"
        self.summary=self.runtime_dir/"latest_comparison_summary.json"

    @staticmethod
    def _confidence(row):
        calibration=row.get("confidence_calibration") or {}
        return _f(
            calibration.get(
                "calibrated_confidence",
                calibration.get("raw_confidence",0.0),
            )
        )

    @staticmethod
    def _canonical_guardrail_ok(row):
        explanation=row.get("selector_explanation") or {}
        reasons=set(
            explanation.get("current_selector_block_reasons") or []
        )
        return "CANONICAL_ANALYSIS_GUARDRAIL_MISSING" not in reasons

    @classmethod
    def _eligible(cls,row,policy):
        action=str(row.get("action") or "HOLD").upper()
        confidence=cls._confidence(row)
        rr=_f(row.get("reward_risk"))
        guardrail_ok=cls._canonical_guardrail_ok(row)

        reasons=[]
        if action not in {"BUY","SELL"}:
            reasons.append("ACTION_NOT_BUY_OR_SELL")
        if confidence<_f(policy.get("min_confidence")):
            reasons.append("CONFIDENCE_BELOW_POLICY")
        if rr<_f(policy.get("min_reward_risk")):
            reasons.append("REWARD_RISK_BELOW_POLICY")
        if not guardrail_ok:
            reasons.append("CANONICAL_GUARDRAIL_BLOCK")

        return {
            "eligible":len(reasons)==0,
            "block_reasons":reasons,
            "inputs":{
                "action":action,
                "calibrated_confidence":round(confidence,6),
                "reward_risk":round(rr,6),
                "min_confidence":_f(policy.get("min_confidence")),
                "min_reward_risk":_f(policy.get("min_reward_risk")),
            },
        }

    def _load_registry(self):
        if not self.policy_registry.exists():
            return (
                dict(DEFAULT_CHAMPION),
                [dict(x) for x in SEED_CHALLENGERS],
                "SEED_FALLBACK_NO_V2_2_4_REGISTRY",
                None,
            )

        data=json.loads(
            self.policy_registry.read_text(encoding="utf-8-sig")
        )
        champion=dict(data.get("champion") or DEFAULT_CHAMPION)
        challengers=[
            dict(x) for x in list(data.get("challengers") or [])
            if x.get("min_confidence") is not None
            and x.get("min_reward_risk") is not None
        ]

        if challengers:
            for c in challengers:
                c["execution_enabled"]=False
                c["calibrated"]=True
            source="V2_2_4_CALIBRATED_REGISTRY"
        else:
            challengers=[dict(x) for x in SEED_CHALLENGERS]
            source="SEED_FALLBACK_EMPTY_V2_2_4_REGISTRY"

        return (
            champion,
            challengers[:5],
            source,
            data.get("registry_sha256"),
        )

    @staticmethod
    def _classification(champion_ok,challenger_ok):
        if champion_ok and challenger_ok:
            return "BOTH"
        if champion_ok:
            return "CHAMPION_ONLY"
        if challenger_ok:
            return "CHALLENGER_ONLY"
        return "NEITHER"

    @staticmethod
    def _best(rows,policy):
        eligible=[]
        for row in rows:
            result=ChampionChallengerShadowComparatorV225._eligible(
                row,policy
            )
            if result["eligible"]:
                eligible.append(row)
        if not eligible:
            return None
        best=max(
            eligible,
            key=lambda r:_f(r.get("quality_score_shadow")),
        )
        return {
            "symbol":str(best.get("symbol") or "").upper(),
            "action":str(best.get("action") or "").upper(),
            "quality_score_shadow":best.get("quality_score_shadow"),
            "calibrated_confidence":
                ChampionChallengerShadowComparatorV225._confidence(best),
            "reward_risk":best.get("reward_risk"),
        }

    def _existing_ids(self):
        out=set()
        if not self.ledger.exists():
            return out
        for line in self.ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row=json.loads(line)
            except Exception:
                continue
            if row.get("comparison_id"):
                out.add(row["comparison_id"])
        return out

    def build(self):
        if not self.feature_latest.exists():
            result={
                "status":"WAITING_FOR_V2_2_1_FEATURE_SNAPSHOT",
                "feature_snapshot_exists":False,
                "challengers_compared":0,
                "comparison_rows":0,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
            self.summary.write_text(
                json.dumps(result,indent=2,sort_keys=True),
                encoding="utf-8",
            )
            return result

        snapshot=json.loads(
            self.feature_latest.read_text(encoding="utf-8-sig")
        )
        rows=list(snapshot.get("symbol_rows") or [])
        champion,challengers,policy_source,registry_sha=(
            self._load_registry()
        )

        comparisons=[]
        counts={
            "BOTH":0,
            "CHAMPION_ONLY":0,
            "CHALLENGER_ONLY":0,
            "NEITHER":0,
        }

        for challenger in challengers:
            policy_rows=[]
            for row in rows:
                champ=self._eligible(row,champion)
                chall=self._eligible(row,challenger)
                classification=self._classification(
                    champ["eligible"],chall["eligible"]
                )
                counts[classification]+=1
                policy_rows.append({
                    "symbol":str(row.get("symbol") or "").upper(),
                    "action":str(row.get("action") or "HOLD").upper(),
                    "market_regime":row.get("market_regime"),
                    "quality_score_shadow":
                        row.get("quality_score_shadow"),
                    "champion":champ,
                    "challenger":chall,
                    "classification":classification,
                    "canonical_analysis_sha256":
                        row.get("canonical_analysis_sha256"),
                })

            comparisons.append({
                "challenger_policy":challenger,
                "champion_best_shadow_candidate":
                    self._best(rows,champion),
                "challenger_best_shadow_candidate":
                    self._best(rows,challenger),
                "symbol_comparisons":policy_rows,
            })

        payload={
            "stage":
                "AI_TRADING_ENGINE_V2_2_5_CHAMPION_CHALLENGER_SHADOW_COMPARATOR",
            "status":"PASS_CHAMPION_CHALLENGER_SHADOW_COMPARISON",
            "feature_snapshot_id":snapshot.get("snapshot_id"),
            "feature_observed_at_utc":snapshot.get("observed_at_utc"),
            "feature_source_sha256":
                snapshot.get("source_snapshot_sha256"),
            "policy_source":policy_source,
            "policy_registry_sha256":registry_sha,
            "champion_policy":champion,
            "challenger_count":len(challengers),
            "comparisons":comparisons,
            "classification_counts":counts,
            "shadow_only":True,
            "challenger_execution_enabled":False,
            "promotion_enabled":False,
            "execution_selector_modified":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }

        comparison_id=_sha(payload)
        payload["comparison_id"]=comparison_id
        existing=self._existing_ids()
        new_rows=0
        if comparison_id not in existing:
            with self.ledger.open("a",encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        payload,
                        sort_keys=True,
                        ensure_ascii=False,
                    )+"\n"
                )
            new_rows=1

        self.latest.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        result={
            "status":"PASS_CHAMPION_CHALLENGER_SHADOW_COMPARISON",
            "feature_snapshot_id":snapshot.get("snapshot_id"),
            "policy_source":policy_source,
            "challengers_compared":len(challengers),
            "symbols_compared":len(rows),
            "comparison_rows":
                len(rows)*len(challengers),
            "both_count":counts["BOTH"],
            "champion_only_count":counts["CHAMPION_ONLY"],
            "challenger_only_count":counts["CHALLENGER_ONLY"],
            "neither_count":counts["NEITHER"],
            "new_ledger_rows":new_rows,
            "duplicate_comparison":new_rows==0,
            "shadow_only":True,
            "challenger_execution_enabled":False,
            "promotion_enabled":False,
            "execution_selector_modified":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }
        self.summary.write_text(
            json.dumps(result,indent=2,sort_keys=True),
            encoding="utf-8",
        )
        return result
