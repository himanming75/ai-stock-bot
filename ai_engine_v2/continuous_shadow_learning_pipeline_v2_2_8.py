from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ai_engine_v2.signal_scoring_feature_snapshot_v2_2_1 import (
    SignalScoringFeatureSnapshotV221,
)
from ai_engine_v2.outcome_labeling_feature_trade_binding_v2_2_2 import (
    OutcomeLabelingFeatureTradeBindingV222,
)
from ai_engine_v2.performance_segmentation_feature_attribution_v2_2_3 import (
    PerformanceSegmentationFeatureAttributionV223,
)
from ai_engine_v2.threshold_calibration_challenger_policy_builder_v2_2_4 import (
    ThresholdCalibrationChallengerPolicyBuilderV224,
)
from ai_engine_v2.champion_challenger_shadow_comparator_v2_2_5 import (
    ChampionChallengerShadowComparatorV225,
)
from ai_engine_v2.champion_challenger_outcome_comparator_v2_2_6 import (
    ChampionChallengerOutcomeComparatorV226,
)
from ai_engine_v2.challenger_shadow_execution_simulator_v2_2_7 import (
    ChallengerShadowExecutionSimulatorV227,
)


PIPELINE_VERSION="V2.2.8"
DEFAULT_POLL_SECONDS=60
DEFAULT_MAX_RUNTIME_SECONDS=28800


def _utcnow():
    return datetime.now(timezone.utc)


def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _json_sha(payload):
    return _sha_bytes(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",",":"),
            default=str,
        ).encode("utf-8")
    )


class ContinuousShadowLearningPipelineV228:
    """
    Local-only supervisor for the Phase-2 AI evidence pipeline.

    It watches canonical-shadow and completed-Paper-trade inputs. When either
    changes, it refreshes V2.2.1 -> V2.2.7 in dependency order.

    It never starts the Paper trading engine and never calls broker APIs.
    """

    def __init__(self, root, *, sleep_fn=time.sleep, now_fn=_utcnow):
        self.root=Path(root)
        self.sleep_fn=sleep_fn
        self.now_fn=now_fn

        self.canonical_shadow=(
            self.root/"runtime"/"real_market_multitimeframe_shadow"/
            "latest_real_market_shadow.json"
        )
        self.completed_actual=(
            self.root/"runtime"/"final_round_trip_ledger_v2_1_27"/
            "completed_round_trips.jsonl"
        )

        self.runtime_dir=(
            self.root/"runtime"/
            "ai_continuous_shadow_learning_pipeline_v2_2_8"
        )
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.state_path=self.runtime_dir/"collector_state.json"
        self.cycle_ledger=self.runtime_dir/"pipeline_cycle_ledger.jsonl"
        self.latest_cycle=self.runtime_dir/"latest_pipeline_cycle.json"
        self.scorecard_path=self.runtime_dir/"latest_performance_scorecard.json"
        self.stop_file=self.runtime_dir/"STOP"

    @staticmethod
    def _file_fingerprint(path):
        if not path.exists():
            return {
                "exists":False,
                "size":0,
                "sha256":None,
            }
        data=path.read_bytes()
        return {
            "exists":True,
            "size":len(data),
            "sha256":_sha_bytes(data),
        }

    def input_fingerprint(self):
        payload={
            "canonical_shadow":
                self._file_fingerprint(self.canonical_shadow),
            "completed_actual":
                self._file_fingerprint(self.completed_actual),
        }
        return {
            "components":payload,
            "composite_sha256":_json_sha(payload),
        }

    def _load_state(self):
        if not self.state_path.exists():
            return {
                "pipeline_version":PIPELINE_VERSION,
                "cycles_completed":0,
                "last_input_sha256":None,
                "last_cycle_status":None,
            }
        try:
            return json.loads(
                self.state_path.read_text(encoding="utf-8")
            )
        except Exception:
            return {
                "pipeline_version":PIPELINE_VERSION,
                "cycles_completed":0,
                "last_input_sha256":None,
                "last_cycle_status":"RECOVERED_FROM_INVALID_STATE",
            }

    def _save_state(self,state):
        self.state_path.write_text(
            json.dumps(state,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )

    @staticmethod
    def _safe_stage(name, fn):
        started=_utcnow()
        try:
            result=fn()
            return {
                "stage":name,
                "ok":not str(result.get("status","")).startswith("BLOCKED_"),
                "status":result.get("status"),
                "result":result,
                "started_at_utc":started.isoformat(),
                "finished_at_utc":_utcnow().isoformat(),
                "error":None,
            }
        except Exception as exc:
            return {
                "stage":name,
                "ok":False,
                "status":"STAGE_EXCEPTION",
                "result":None,
                "started_at_utc":started.isoformat(),
                "finished_at_utc":_utcnow().isoformat(),
                "error":f"{type(exc).__name__}: {exc}",
            }

    def _pipeline_stages(self):
        # Dependency order matters:
        # features -> actual labels -> stats -> calibration -> comparison
        # -> challenger simulation -> actual-vs-shadow outcome comparison.
        return [
            ("V2.2.1_FEATURE_SNAPSHOT",
             lambda: SignalScoringFeatureSnapshotV221(self.root).build()),
            ("V2.2.2_OUTCOME_LABELING",
             lambda: OutcomeLabelingFeatureTradeBindingV222(self.root).build()),
            ("V2.2.3_SEGMENTATION",
             lambda: PerformanceSegmentationFeatureAttributionV223(self.root).build()),
            ("V2.2.4_CALIBRATION",
             lambda: ThresholdCalibrationChallengerPolicyBuilderV224(self.root).build()),
            ("V2.2.5_SHADOW_COMPARATOR",
             lambda: ChampionChallengerShadowComparatorV225(self.root).build()),
            ("V2.2.7_SHADOW_SIMULATOR",
             lambda: ChallengerShadowExecutionSimulatorV227(self.root).build()),
            ("V2.2.6_OUTCOME_COMPARATOR",
             lambda: ChampionChallengerOutcomeComparatorV226(self.root).build()),
        ]

    @staticmethod
    def _read_jsonl(path):
        rows=[]
        if not path.exists():
            return rows
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        return rows

    @staticmethod
    def _read_json(path):
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    def build_scorecard(self):
        labeled_path=(
            self.root/"runtime"/
            "ai_outcome_labeling_feature_trade_binding_v2_2_2"/
            "labeled_outcomes.jsonl"
        )
        comparison_path=(
            self.root/"runtime"/
            "ai_champion_challenger_shadow_comparator_v2_2_5"/
            "comparison_ledger.jsonl"
        )
        shadow_completed_path=(
            self.root/"runtime"/
            "ai_challenger_shadow_execution_simulator_v2_2_7"/
            "completed_shadow_round_trips.jsonl"
        )
        segmentation_path=(
            self.root/"runtime"/
            "ai_performance_segmentation_feature_attribution_v2_2_3"/
            "latest_performance_segmentation.json"
        )
        calibration_path=(
            self.root/"runtime"/
            "ai_threshold_calibration_challenger_policy_v2_2_4"/
            "latest_challenger_calibration.json"
        )
        outcome_compare_path=(
            self.root/"runtime"/
            "ai_champion_challenger_outcome_comparator_v2_2_6"/
            "latest_outcome_comparison_report.json"
        )

        labeled=self._read_jsonl(labeled_path)
        comparisons=self._read_jsonl(comparison_path)
        completed_shadow=self._read_jsonl(shadow_completed_path)
        segmentation=self._read_json(segmentation_path)
        calibration=self._read_json(calibration_path)
        outcome_compare=self._read_json(outcome_compare_path)

        counts={"BOTH":0,"CHAMPION_ONLY":0,"CHALLENGER_ONLY":0,"NEITHER":0}
        for comp_snapshot in comparisons:
            for comp in list(comp_snapshot.get("comparisons") or []):
                for row in list(comp.get("symbol_comparisons") or []):
                    cls=str(row.get("classification") or "")
                    if cls in counts:
                        counts[cls]+=1

        shadow_wins=shadow_losses=shadow_flats=0
        shadow_pnl=0.0
        for row in completed_shadow:
            sim=row.get("simulation") or {}
            pnl=float(sim.get("gross_pnl_before_fees") or 0)
            shadow_pnl+=pnl
            if pnl>0:
                shadow_wins+=1
            elif pnl<0:
                shadow_losses+=1
            else:
                shadow_flats+=1

        actual_wins=actual_losses=actual_flats=0
        actual_pnl=0.0
        for row in labeled:
            outcome=row.get("outcome") or {}
            label=str(outcome.get("outcome_label") or "")
            pnl=float(outcome.get("gross_pnl_from_fills") or 0)
            actual_pnl+=pnl
            if label=="WIN":
                actual_wins+=1
            elif label=="LOSS":
                actual_losses+=1
            elif label=="FLAT":
                actual_flats+=1

        actual_n=len(labeled)
        shadow_n=len(completed_shadow)
        scorecard={
            "stage":
                "AI_TRADING_ENGINE_V2_2_8_PERFORMANCE_SCORECARD_FOUNDATION",
            "generated_at_utc":self.now_fn().isoformat(),
            "champion_actual":{
                "completed_outcomes":actual_n,
                "wins":actual_wins,
                "losses":actual_losses,
                "flats":actual_flats,
                "win_rate_pct":
                    round(actual_wins/actual_n*100,4) if actual_n else 0.0,
                "gross_pnl_before_fees":round(actual_pnl,8),
            },
            "challenger_shadow":{
                "completed_counterfactual_round_trips":shadow_n,
                "wins":shadow_wins,
                "losses":shadow_losses,
                "flats":shadow_flats,
                "win_rate_pct":
                    round(shadow_wins/shadow_n*100,4) if shadow_n else 0.0,
                "gross_pnl_before_fees":round(shadow_pnl,8),
                "actual_broker_fills":0,
            },
            "shadow_classification_counts":counts,
            "segmentation_status":segmentation.get("status"),
            "calibration_status":calibration.get("status"),
            "calibration_ready":bool(calibration.get("calibration_ready",False)),
            "outcome_comparator_status":outcome_compare.get("status"),
            "promotion_evidence_ready":any(
                bool(x.get("promotion_evidence_ready",False))
                for x in (outcome_compare.get("per_challenger") or {}).values()
            ),
            "promotion_enabled":False,
            "automatic_policy_change_enabled":False,
            "challenger_broker_execution_enabled":False,
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }
        scorecard["scorecard_sha256"]=_json_sha(scorecard)
        self.scorecard_path.write_text(
            json.dumps(scorecard,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )
        return scorecard

    def run_cycle(self, *, force=False):
        state=self._load_state()
        inputs=self.input_fingerprint()
        current_sha=inputs["composite_sha256"]

        if (
            not force
            and state.get("last_input_sha256")==current_sha
        ):
            return {
                "status":"NO_CHANGE_SKIPPED",
                "input_sha256":current_sha,
                "cycles_completed":state.get("cycles_completed",0),
                "broker_network_used":False,
                "paper_orders_submitted":0,
                "live_orders_submitted":0,
            }

        stages=[]
        for name,fn in self._pipeline_stages():
            stage=self._safe_stage(name,fn)
            stages.append(stage)
            if not stage["ok"]:
                break

        all_ok=all(x["ok"] for x in stages)
        scorecard=self.build_scorecard()

        cycle={
            "stage":"AI_TRADING_ENGINE_V2_2_8_CONTINUOUS_SHADOW_LEARNING_PIPELINE",
            "cycle_id":_json_sha({
                "input":current_sha,
                "at":self.now_fn().isoformat(),
                "prior_cycles":state.get("cycles_completed",0),
            }),
            "observed_at_utc":self.now_fn().isoformat(),
            "status":
                "PASS_CONTINUOUS_SHADOW_LEARNING_CYCLE"
                if all_ok else "BLOCKED_SHADOW_LEARNING_STAGE_FAILURE",
            "force":bool(force),
            "input_fingerprint":inputs,
            "stages":stages,
            "scorecard_sha256":scorecard.get("scorecard_sha256"),
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
            "promotion_enabled":False,
            "automatic_policy_change_enabled":False,
        }

        with self.cycle_ledger.open("a",encoding="utf-8") as f:
            f.write(json.dumps(cycle,sort_keys=True,default=str)+"\n")
        self.latest_cycle.write_text(
            json.dumps(cycle,indent=2,sort_keys=True,default=str),
            encoding="utf-8",
        )

        state.update({
            "pipeline_version":PIPELINE_VERSION,
            "cycles_completed":int(state.get("cycles_completed",0))+1,
            "last_input_sha256":current_sha if all_ok else state.get("last_input_sha256"),
            "last_cycle_status":cycle["status"],
            "last_cycle_id":cycle["cycle_id"],
            "last_cycle_at_utc":cycle["observed_at_utc"],
        })
        self._save_state(state)
        return {
            "status":cycle["status"],
            "cycle_id":cycle["cycle_id"],
            "stages_run":len(stages),
            "stages_passed":sum(1 for x in stages if x["ok"]),
            "input_sha256":current_sha,
            "scorecard":scorecard,
            "cycles_completed":state["cycles_completed"],
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }

    def run_continuous(
        self,
        *,
        poll_seconds=DEFAULT_POLL_SECONDS,
        max_runtime_seconds=DEFAULT_MAX_RUNTIME_SECONDS,
        max_cycles=0,
    ):
        poll_seconds=int(poll_seconds)
        max_runtime_seconds=int(max_runtime_seconds)
        max_cycles=int(max_cycles)
        if poll_seconds<5 or poll_seconds>3600:
            raise ValueError("INVALID_POLL_SECONDS")
        if max_runtime_seconds<1 or max_runtime_seconds>172800:
            raise ValueError("INVALID_MAX_RUNTIME_SECONDS")
        if max_cycles<0 or max_cycles>100000:
            raise ValueError("INVALID_MAX_CYCLES")

        if self.stop_file.exists():
            self.stop_file.unlink()

        started=self.now_fn()
        supervisor_polls=0
        executed_cycles=0
        last_result=None
        stop_reason=None

        while True:
            now=self.now_fn()
            elapsed=(now-started).total_seconds()

            if self.stop_file.exists():
                stop_reason="STOP_FILE"
                break
            if elapsed>=max_runtime_seconds:
                stop_reason="MAX_RUNTIME"
                break
            if max_cycles and executed_cycles>=max_cycles:
                stop_reason="MAX_CYCLES"
                break

            supervisor_polls+=1
            result=self.run_cycle(force=(supervisor_polls==1))
            last_result=result
            if result.get("status")!="NO_CHANGE_SKIPPED":
                executed_cycles+=1
                if str(result.get("status","")).startswith("BLOCKED_"):
                    stop_reason="FAIL_CLOSED_STAGE_FAILURE"
                    break

            self.sleep_fn(poll_seconds)

        return {
            "status":"PASS_CONTINUOUS_SHADOW_LEARNING_SUPERVISOR"
                     if stop_reason!="FAIL_CLOSED_STAGE_FAILURE"
                     else "BLOCKED_CONTINUOUS_SHADOW_LEARNING_SUPERVISOR",
            "started_at_utc":started.isoformat(),
            "finished_at_utc":self.now_fn().isoformat(),
            "supervisor_polls":supervisor_polls,
            "executed_cycles":executed_cycles,
            "stop_reason":stop_reason,
            "last_cycle_status":
                None if last_result is None else last_result.get("status"),
            "broker_network_used":False,
            "paper_orders_submitted":0,
            "live_orders_submitted":0,
        }
