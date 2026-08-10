from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_ENGINE="multi_timeframe_ai.engine.analyze_symbol"
EXPECTED_SELECTOR="paper_autonomous_execution.signals.select_candidate"


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo,min(hi,float(v)))


def _sha256_payload(payload):
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",",":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


class SignalScoringFeatureSnapshotV221:
    """
    Shadow-only AI diagnostics over the existing canonical multi-timeframe
    analysis output.

    No signal thresholds or Paper execution behavior are changed.

    Responsibilities:
      - read existing canonical real-market shadow snapshot;
      - preserve canonical analysis fields and timeframe features;
      - calculate an observational quality score for ranking/diagnostics only;
      - explain why each symbol would or would not pass the CURRENT selector;
      - append deduplicated JSONL feature snapshots for later outcome analysis.
    """

    def __init__(self,root):
        self.root=Path(root)
        self.source=(
            self.root/"runtime"/"real_market_multitimeframe_shadow"/
            "latest_real_market_shadow.json"
        )
        self.runtime_dir=(
            self.root/"runtime"/
            "ai_signal_scoring_feature_snapshot_v2_2_1"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.ledger=self.runtime_dir/"feature_snapshot_ledger.jsonl"
        self.latest=self.runtime_dir/"latest_feature_snapshot.json"

    @staticmethod
    def _confidence(item):
        return float(
            (item.get("confidence_calibration") or {}).get(
                "calibrated_confidence",0.0
            )
        )

    @staticmethod
    def _selector_explanation(item,min_conf,min_rr):
        symbol=str(item.get("symbol") or "").upper()
        action=str(item.get("action") or "HOLD").upper()
        confidence=SignalScoringFeatureSnapshotV221._confidence(item)
        rr=float(item.get("reward_risk",0.0))
        mode=str(item.get("execution_mode") or "")

        reasons=[]
        if action not in {"BUY","SELL"}:
            reasons.append("ACTION_NOT_BUY_OR_SELL")
        if confidence<min_conf:
            reasons.append("CONFIDENCE_BELOW_CURRENT_SELECTOR")
        if rr<min_rr:
            reasons.append("REWARD_RISK_BELOW_CURRENT_SELECTOR")
        if mode!="ANALYSIS_ONLY":
            reasons.append("CANONICAL_ANALYSIS_GUARDRAIL_MISSING")

        return {
            "symbol":symbol,
            "current_selector_eligible":len(reasons)==0,
            "current_selector_block_reasons":reasons,
            "current_selector_inputs":{
                "action":action,
                "calibrated_confidence":round(confidence,6),
                "reward_risk":round(rr,6),
                "min_confidence":round(float(min_conf),6),
                "min_reward_risk":round(float(min_rr),6),
            },
        }

    @staticmethod
    def _quality_score(item):
        """
        Observational score only. It is deliberately NOT consumed by the
        execution selector in V2.2.1.
        """
        confidence=SignalScoringFeatureSnapshotV221._confidence(item)
        rr=float(item.get("reward_risk",0.0))
        alignment=float(
            (item.get("timeframe_consensus") or {}).get("alignment",0.0)
        )
        probability=float(item.get("probability",0.0))
        consensus=abs(float(item.get("consensus_score",0.0)))

        rr_component=_clamp(rr/2.0)
        consensus_component=_clamp(consensus/0.60)

        score=(
            _clamp(confidence)*0.34
            +rr_component*0.22
            +_clamp(alignment)*0.18
            +_clamp(probability)*0.14
            +consensus_component*0.12
        )
        return round(_clamp(score),6)

    @staticmethod
    def _timeframe_snapshot(item):
        rows=[]
        for tf in list(item.get("timeframes") or []):
            features=dict(tf.get("features") or {})
            rows.append({
                "timeframe":tf.get("timeframe"),
                "signal":tf.get("signal"),
                "directional_score":tf.get("directional_score"),
                "trend_score":tf.get("trend_score"),
                "momentum_score":tf.get("momentum_score"),
                "regime":tf.get("regime"),
                "structure":tf.get("structure"),
                "probability":tf.get("probability"),
                "expected_return":tf.get("expected_return"),
                "expected_risk":tf.get("expected_risk"),
                "reward_risk":tf.get("reward_risk"),
                "features":{
                    "close":features.get("close"),
                    "ema_fast":features.get("ema_fast"),
                    "ema_slow":features.get("ema_slow"),
                    "momentum":features.get("momentum"),
                    "rsi":features.get("rsi"),
                    "volume_ratio":features.get("volume_ratio"),
                    "atr_percent":features.get("atr_percent"),
                    "gap_percent":features.get("gap_percent"),
                    "close_vs_range":features.get("close_vs_range"),
                    "follow_through":features.get("follow_through"),
                },
            })
        return rows

    def _existing_snapshot_ids(self):
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
            if row.get("snapshot_id"):
                out.add(str(row["snapshot_id"]))
        return out

    def build(self):
        if not self.source.exists():
            return {
                "status":"WAITING_FOR_CANONICAL_REAL_MARKET_SHADOW",
                "source_exists":False,
                "snapshot_rows":0,
                "new_ledger_rows":0,
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }

        report=json.loads(self.source.read_text(encoding="utf-8-sig"))
        if report.get("canonical_engine")!=EXPECTED_ENGINE:
            return {
                "status":"BLOCKED_CANONICAL_ENGINE_MISMATCH",
                "actual":report.get("canonical_engine"),
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }
        if report.get("canonical_selector")!=EXPECTED_SELECTOR:
            return {
                "status":"BLOCKED_CANONICAL_SELECTOR_MISMATCH",
                "actual":report.get("canonical_selector"),
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }

        thresholds=dict(report.get("thresholds") or {})
        min_conf=float(thresholds.get("min_confidence",0.75))
        min_rr=float(thresholds.get("min_reward_risk",1.0))
        analyses=list(report.get("analyses") or [])

        observed_at=(
            report.get("generated_at_utc")
            or datetime.now(timezone.utc).isoformat()
        )

        symbol_rows=[]
        for item in analyses:
            explanation=self._selector_explanation(
                item,min_conf,min_rr
            )
            symbol_rows.append({
                "symbol":str(item.get("symbol") or "").upper(),
                "action":str(item.get("action") or "HOLD").upper(),
                "quality_score_shadow":
                    self._quality_score(item),
                "quality_score_execution_enabled":False,
                "consensus_score":item.get("consensus_score"),
                "trend_alignment":item.get("trend_alignment"),
                "market_regime":item.get("market_regime_2"),
                "dominant_structure":item.get("dominant_structure"),
                "probability":item.get("probability"),
                "expected_return":item.get("expected_return"),
                "expected_risk":item.get("expected_risk"),
                "reward_risk":item.get("reward_risk"),
                "confidence_calibration":
                    item.get("confidence_calibration"),
                "timeframe_consensus":
                    item.get("timeframe_consensus"),
                "selector_explanation":explanation,
                "timeframes":self._timeframe_snapshot(item),
                "canonical_analysis_sha256":
                    _sha256_payload(item),
            })

        symbol_rows.sort(
            key=lambda x:x["quality_score_shadow"],
            reverse=True,
        )
        snapshot_payload={
            "stage":"AI_TRADING_ENGINE_V2_2_1_SIGNAL_SCORING_FEATURE_SNAPSHOT",
            "observed_at_utc":observed_at,
            "source_snapshot":str(self.source),
            "source_snapshot_sha256":
                hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "source_dataset":report.get("source_dataset"),
            "canonical_engine":report.get("canonical_engine"),
            "canonical_selector":report.get("canonical_selector"),
            "current_selector_thresholds":{
                "min_confidence":min_conf,
                "min_reward_risk":min_rr,
            },
            "symbol_rows":symbol_rows,
            "symbol_count":len(symbol_rows),
            "current_selector_eligible_count":sum(
                1 for row in symbol_rows
                if row["selector_explanation"][
                    "current_selector_eligible"
                ]
            ),
            "shadow_quality_score_only":True,
            "execution_selector_modified":False,
            "market_data_fetch_from_stage":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
            "live_trading_enabled":False,
        }
        snapshot_id=_sha256_payload(snapshot_payload)
        snapshot_payload["snapshot_id"]=snapshot_id

        existing=self._existing_snapshot_ids()
        new_rows=0
        if snapshot_id not in existing:
            with self.ledger.open("a",encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        snapshot_payload,
                        sort_keys=True,
                        ensure_ascii=False,
                    )+"\n"
                )
            new_rows=1

        self.latest.write_text(
            json.dumps(
                snapshot_payload,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return {
            "status":"PASS_AI_SIGNAL_SCORING_FEATURE_SNAPSHOT",
            "source_exists":True,
            "snapshot_rows":len(symbol_rows),
            "current_selector_eligible_count":
                snapshot_payload[
                    "current_selector_eligible_count"
                ],
            "new_ledger_rows":new_rows,
            "duplicate_snapshot":new_rows==0,
            "ledger":str(self.ledger),
            "latest":str(self.latest),
            "top_shadow_symbol":(
                None if not symbol_rows else symbol_rows[0]["symbol"]
            ),
            "top_shadow_quality_score":(
                None if not symbol_rows
                else symbol_rows[0]["quality_score_shadow"]
            ),
            "shadow_quality_score_only":True,
            "execution_selector_modified":False,
            "market_data_fetch_from_stage":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }
