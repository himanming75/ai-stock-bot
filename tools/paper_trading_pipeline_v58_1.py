#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

VERSION = "58.1"
STAGES = ("v54_signal", "v55_sizing", "v56_risk", "v57_execution")
VALID_MODES = {"replay", "paper", "live"}

def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

@dataclass(frozen=True)
class StageSpec:
    name: str
    script: str
    input: str
    output: str

@dataclass(frozen=True)
class PipelineConfig:
    pipeline_id: str
    python_executable: str
    mode: str
    fail_fast: bool
    stages: list[StageSpec]

class PaperTradingPipelineV581:
    def __init__(self, config: PipelineConfig, *, enable_live: bool=False, runner: Callable|None=None):
        if config.mode not in VALID_MODES:
            raise ValueError("mode must be replay, paper, or live")
        if not config.pipeline_id.strip():
            raise ValueError("pipeline_id is required")
        if [x.name for x in config.stages] != list(STAGES):
            raise ValueError("stages must be ordered v54_signal, v55_sizing, v56_risk, v57_execution")
        self.config=config; self.enable_live=enable_live
        self.runner=runner or subprocess.run
        self.ledger=[]

    def _live_gate(self):
        if self.config.mode=="live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError("live pipeline is intentionally not implemented in V58.1")

    def _append_ledger(self, stage, status, payload):
        previous=self.ledger[-1]["entry_sha256"] if self.ledger else "GENESIS"
        core={"sequence":len(self.ledger)+1,"event_type":"STAGE_COMPLETED","stage":stage,
              "status":status,"payload_sha256":canonical_hash(payload),"previous_entry_sha256":previous}
        self.ledger.append({**core,"entry_sha256":canonical_hash(core)})

    @staticmethod
    def _load_result(path: Path):
        data=json.loads(path.read_text(encoding="utf-8"))
        return data.get("result",data)

    def run(self):
        self._live_gate()
        audit=[]; results={}; pipeline_status="PASS"; stopped_at=None
        for spec in self.config.stages:
            script,inp,out=Path(spec.script),Path(spec.input),Path(spec.output)
            if not script.is_file(): raise FileNotFoundError(f"missing stage script: {script}")
            if not inp.is_file(): raise FileNotFoundError(f"missing stage input: {inp}")
            out.parent.mkdir(parents=True,exist_ok=True)
            command=[self.config.python_executable,str(script),"--input",str(inp),
                     "--mode",self.config.mode,"--output",str(out)]
            completed=self.runner(command,capture_output=True,text=True)
            result=self._load_result(out) if out.exists() else {"status":"FAIL","error":"stage output missing"}
            status=str(result.get("status","FAIL")).upper()
            record={"sequence":len(audit)+1,"stage":spec.name,"status":status,
                    "return_code":completed.returncode,"command":command,
                    "output_sha256":canonical_hash(result),
                    "stdout_sha256":hashlib.sha256(completed.stdout.encode()).hexdigest(),
                    "stderr_sha256":hashlib.sha256(completed.stderr.encode()).hexdigest(),
                    "network_used":bool(result.get("network_used",False))}
            audit.append(record);results[spec.name]=result;self._append_ledger(spec.name,status,record)
            if record["network_used"]:
                pipeline_status,stopped_at="FAIL",spec.name;record["failure_reason"]="network_use_detected"
            elif completed.returncode!=0 or status!="PASS":
                pipeline_status,stopped_at="FAIL",spec.name;record["failure_reason"]="stage_failed"
            if pipeline_status=="FAIL" and self.config.fail_fast: break
        core={"schema_version":"v58.1.decision_execution_pipeline.1","version":VERSION,
              "pipeline_id":self.config.pipeline_id,"status":pipeline_status,
              "decision":"pipeline_completed" if pipeline_status=="PASS" else "pipeline_failed",
              "completed_stage_count":len(audit),"expected_stage_count":len(STAGES),
              "stopped_at":stopped_at,"stage_results":results,"audit_trail":audit,"network_used":False}
        return {**core,"pipeline_sha256":canonical_hash(core),"ledger":self.ledger}

    @staticmethod
    def export(path:Path,result):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")

def load_config(path:Path):
    p=json.loads(path.read_text(encoding="utf-8"))
    return PipelineConfig(p["pipeline_id"],p.get("python_executable",sys.executable),
                          p.get("mode","paper"),bool(p.get("fail_fast",True)),
                          [StageSpec(**x) for x in p["stages"]])

def main(argv:Sequence[str]|None=None):
    ap=argparse.ArgumentParser();ap.add_argument("--config",required=True);ap.add_argument("--output",required=True)
    ap.add_argument("--enable-live",action="store_true");args=ap.parse_args(argv);out=Path(args.output)
    try:
        result=PaperTradingPipelineV581(load_config(Path(args.config)),enable_live=args.enable_live).run()
        PaperTradingPipelineV581.export(out,result);print(json.dumps(result,indent=2,sort_keys=True))
        return 0 if result["status"]=="PASS" else 1
    except Exception as exc:
        error={"schema_version":"v58.1.decision_execution_pipeline_error.1","version":VERSION,
               "status":"FAIL","error":str(exc),"network_used":False}
        out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(error,indent=2,sort_keys=True))
        print(json.dumps(error,indent=2,sort_keys=True));return 1
if __name__=="__main__":raise SystemExit(main())
