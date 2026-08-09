from __future__ import annotations
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from .market_session_freshness_guard_v2_1_14 import regular_session_window
from .persistent_market_observer_v2_1_13 import ObservationPolicyV2113
from .session_freshness_aware_runtime_v2_1_14 import SessionFreshnessAwareRuntimeV2114
from .freshness_guarded_persistent_observer_v2_1_15 import FreshnessGuardedPersistentObserverV2115
from .fresh_eligible_signal_evidence_capture_v2_1_16 import FreshEligibleSignalEvidenceCaptureV2116
from .canonical_reward_risk_provenance_bridge_v2_1_20 import CanonicalRewardRiskProvenanceBridgeV2120
from .evidence_qualification_sandbox_readiness_gate_v2_1_17 import EvidenceQualificationSandboxReadinessGateV2117

DEFAULT_SYMBOLS=("AAPL","MSFT","SPY")

class _RecordingRuntime:
    def __init__(self,base):
        self.base=base; self.last_plan=None
    def build_runtime_plan(self,*args,**kwargs):
        self.last_plan=self.base.build_runtime_plan(*args,**kwargs)
        return self.last_plan

def _default_canonical_snapshot(root):
    from tools.build_real_market_multitimeframe_shadow import snapshot
    return snapshot(Path(root))

class ActualIntradayCanonicalEndToEndValidatorV2121:
    def __init__(self,root,symbols=DEFAULT_SYMBOLS,quantity=Decimal("1"),now_fn=None,
                 runtime_factory=None,observer_factory=None,evidence_factory=None,
                 canonical_snapshot_fn=None,provenance_factory=None,qualification_factory=None):
        self.root=Path(root)
        self.symbols=tuple(sorted({str(x).upper().strip() for x in symbols if str(x).strip()}))
        self.quantity=Decimal(str(quantity))
        self.now_fn=now_fn or (lambda: datetime.now(timezone.utc))
        self.runtime_factory=runtime_factory or (lambda symbols: SessionFreshnessAwareRuntimeV2114(symbols))
        self.observer_factory=observer_factory
        self.evidence_factory=evidence_factory or FreshEligibleSignalEvidenceCaptureV2116
        self.canonical_snapshot_fn=canonical_snapshot_fn or _default_canonical_snapshot
        self.provenance_factory=provenance_factory or CanonicalRewardRiskProvenanceBridgeV2120
        self.qualification_factory=qualification_factory or EvidenceQualificationSandboxReadinessGateV2117
        self.runtime_dir=self.root/"runtime"/"actual_intraday_canonical_e2e_v2_1_21"
        self.runtime_dir.mkdir(parents=True,exist_ok=True)
        self.ledger=self.runtime_dir/"validation_ledger.jsonl"
        self.latest=self.runtime_dir/"latest_validation.json"
    def _write(self,row):
        self.latest.write_text(json.dumps(row,indent=2,sort_keys=True,default=str),encoding="utf-8")
        with self.ledger.open("a",encoding="utf-8") as f: f.write(json.dumps(row,sort_keys=True,default=str)+"\n")
        return row
    def _base(self,now,session):
        return {"stage":"BROKER_INTEGRATION_V2_1_21_ACTUAL_INTRADAY_CANONICAL_END_TO_END_VALIDATION",
                "observed_at_utc":now.isoformat(),"symbols":list(self.symbols),"quantity":str(self.quantity),
                "session":session,"bounded_cycles":1,"automatic_repeat":False,
                "etrade_oauth_started":False,"sandbox_preview_sent":False,"sandbox_place_sent":False,
                "broker_orders_submitted":0,"production_order_submission":False,"live_trading":False}
    def run_once(self):
        now=self.now_fn().astimezone(timezone.utc); session=regular_session_window(now); base=self._base(now,session)
        if not session["inside_regular_clock_window"]:
            return self._write({**base,"status":"WAITING_FOR_MARKET_SESSION","market_data_runtime_called":False,"market_data_fetch_skipped":True})
        recording=_RecordingRuntime(self.runtime_factory(self.symbols))
        policy=ObservationPolicyV2113(max_iterations=1,interval_seconds=1,stop_after_unchanged=1)
        observer=(self.observer_factory(recording,self.root,policy,now) if self.observer_factory else
                  FreshnessGuardedPersistentObserverV2115(recording,self.root,policy=policy,sleep_fn=lambda _:None,now_fn=lambda:now))
        obs=observer.run(quantity=self.quantity)
        plan=recording.last_plan or {}; allowed=bool(plan.get("signal_capture_allowed_by_v2_1_14"))
        if not allowed:
            return self._write({**base,"status":"BLOCKED_BY_SESSION_FRESHNESS","observer_result":obs,"session_freshness_gate":plan.get("session_freshness_gate")})
        evidence=self.evidence_factory(self.root).capture()
        current_observation_path=(
            self.root/"runtime"/"freshness_guarded_persistent_observer_v2_1_15"/"latest_snapshot.json"
        )
        current_evidence_key=None
        if current_observation_path.exists():
            current_observation=json.loads(current_observation_path.read_text(encoding="utf-8"))
            current_evidence_key=current_observation.get("snapshot_fingerprint")
        if int(obs.get("eligible_capture_count") or 0)==0:
            return self._write({**base,"status":"PASS_FRESH_NO_ELIGIBLE_SIGNAL","observer_result":obs,"evidence_result":evidence})
        report=self.canonical_snapshot_fn(self.root)
        prov=self.provenance_factory(self.root).build()
        if prov.get("status")!="PASS_CANONICAL_REWARD_RISK_PROVENANCE_BRIDGE":
            return self._write({**base,"status":"BLOCKED_BY_CANONICAL_PROVENANCE","observer_result":obs,"evidence_result":evidence,"provenance_result":prov})
        qual=self.qualification_factory(self.root).evaluate()
        lp=self.root/"runtime"/"sandbox_readiness_gate_v2_1_17"/"latest_qualification.json"
        latest_q=json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {}
        ready=bool(
            current_evidence_key
            and latest_q.get("evidence_key")==current_evidence_key
            and latest_q.get("ready") is True
            and latest_q.get("qualification_status")=="READY_FOR_MANUAL_SANDBOX_REVIEW"
        )
        return self._write({**base,"status":"PASS_ACTUAL_INTRADAY_CANONICAL_READY" if ready else "PASS_ACTUAL_INTRADAY_CANONICAL_NOT_READY",
                            "observer_result":obs,"evidence_result":evidence,
                            "canonical_snapshot_result":{"status":report.get("status"),"generated_at_utc":report.get("generated_at_utc"),
                                                         "thresholds":report.get("thresholds"),"analysis_count":len(report.get("analyses") or [])},
                            "provenance_result":prov,"qualification_result":qual,"latest_qualification":latest_q or None,
                            "ready_for_manual_sandbox_review":ready,"automatic_sandbox_execution_allowed":False})
