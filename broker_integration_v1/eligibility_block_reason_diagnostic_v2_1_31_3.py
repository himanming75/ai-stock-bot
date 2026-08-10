from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ai_engine_v2.signal_scoring_feature_snapshot_v2_2_1 import (
    SignalScoringFeatureSnapshotV221,
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


class EligibilityBlockReasonDiagnosticV21313:
    """
    Read-only diagnostic for the currently running canonical selector.

    It calls the already-shipped V2.2.1 explanation layer, which reproduces
    the CURRENT selector inputs and thresholds without changing execution.

    No broker network, no order submission, no threshold mutation.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.v221=SignalScoringFeatureSnapshotV221(self.root)
        self.runtime=(
            self.root/"runtime"/
            "eligibility_block_reason_diagnostic_v2_1_31_3"
        )
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.latest=self.runtime/"latest_eligibility_diagnostic.json"
        self.ledger=self.runtime/"eligibility_diagnostic_ledger.jsonl"

    def _append_once(self,payload):
        diag_id=payload["diagnostic_id"]
        if self.ledger.exists():
            for line in self.ledger.read_text(
                encoding="utf-8"
            ).splitlines():
                if not line.strip():
                    continue
                try:
                    row=json.loads(line)
                except Exception:
                    continue
                if row.get("diagnostic_id")==diag_id:
                    return False
        with self.ledger.open("a",encoding="utf-8") as f:
            f.write(json.dumps(payload,sort_keys=True)+"\n")
        return True

    def run(self):
        refresh=self.v221.build()
        if refresh.get("status")!="PASS_AI_SIGNAL_SCORING_FEATURE_SNAPSHOT":
            result={
                "stage":"BROKER_INTEGRATION_V2_1_31_3_ELIGIBILITY_BLOCK_REASON_DIAGNOSTIC",
                "status":"WAITING_FOR_CANONICAL_REAL_MARKET_SHADOW",
                "v2_2_1_status":refresh.get("status"),
                "execution_selector_modified":False,
                "thresholds_modified":False,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
            self.latest.write_text(
                json.dumps(result,indent=2,sort_keys=True),
                encoding="utf-8",
            )
            return result

        snap=json.loads(
            self.v221.latest.read_text(encoding="utf-8")
        )
        thresholds=dict(
            snap.get("current_selector_thresholds") or {}
        )
        rows=[]
        reasons=Counter()

        for src in snap.get("symbol_rows") or []:
            ex=dict(src.get("selector_explanation") or {})
            inputs=dict(ex.get("current_selector_inputs") or {})
            block=list(ex.get("current_selector_block_reasons") or [])
            for reason in block:
                reasons[reason]+=1

            confidence=float(inputs.get("calibrated_confidence",0.0))
            min_conf=float(inputs.get("min_confidence",0.0))
            rr=float(inputs.get("reward_risk",0.0))
            min_rr=float(inputs.get("min_reward_risk",0.0))
            action=str(inputs.get("action") or "HOLD").upper()

            rows.append({
                "symbol":str(src.get("symbol") or "").upper(),
                "eligible":bool(ex.get("current_selector_eligible")),
                "action":action,
                "calibrated_confidence":confidence,
                "min_confidence":min_conf,
                "confidence_margin":
                    round(confidence-min_conf,6),
                "reward_risk":rr,
                "min_reward_risk":min_rr,
                "reward_risk_margin":
                    round(rr-min_rr,6),
                "execution_mode":(
                    "ANALYSIS_ONLY"
                    if "CANONICAL_ANALYSIS_GUARDRAIL_MISSING"
                       not in block
                    else "NOT_ANALYSIS_ONLY"
                ),
                "block_reasons":block,
                "quality_score_shadow":
                    src.get("quality_score_shadow"),
                "consensus_score":src.get("consensus_score"),
                "trend_alignment":src.get("trend_alignment"),
                "market_regime":src.get("market_regime"),
                "probability":src.get("probability"),
                "timeframe_consensus":
                    src.get("timeframe_consensus"),
                "timeframes":src.get("timeframes"),
            })

        rows.sort(key=lambda x:x["symbol"])
        generated=snap.get("observed_at_utc") or datetime.now(
            timezone.utc
        ).isoformat()

        payload={
            "stage":"BROKER_INTEGRATION_V2_1_31_3_ELIGIBILITY_BLOCK_REASON_DIAGNOSTIC",
            "status":"PASS_ELIGIBILITY_BLOCK_REASON_DIAGNOSTIC",
            "observed_at_utc":generated,
            "canonical_engine":snap.get("canonical_engine"),
            "canonical_selector":snap.get("canonical_selector"),
            "thresholds":thresholds,
            "symbols":rows,
            "symbol_count":len(rows),
            "eligible_count":sum(1 for r in rows if r["eligible"]),
            "blocked_count":sum(1 for r in rows if not r["eligible"]),
            "block_reason_counts":dict(sorted(reasons.items())),
            "source_v2_2_1_snapshot_id":snap.get("snapshot_id"),
            "execution_selector_modified":False,
            "thresholds_modified":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
            "live_trading_modified":False,
        }
        payload["diagnostic_id"]=_sha({
            "source_v2_2_1_snapshot_id":
                payload["source_v2_2_1_snapshot_id"],
            "symbols":rows,
            "thresholds":thresholds,
        })
        payload["new_ledger_row"]=self._append_once(payload)

        self.latest.write_text(
            json.dumps(payload,indent=2,sort_keys=True),
            encoding="utf-8",
        )
        return payload

    def summary(self):
        if not self.latest.exists():
            return {
                "status":"WAITING_FOR_FIRST_DIAGNOSTIC",
                "execution_selector_modified":False,
                "thresholds_modified":False,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
        return json.loads(self.latest.read_text(encoding="utf-8"))
