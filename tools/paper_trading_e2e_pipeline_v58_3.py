#!/usr/bin/env python3
"""V58.3 End-to-End Paper Trading Pipeline Controller.

Runs one complete offline decision-to-execution flow:

V54 signal
 -> V58.2 handoff
 -> V55 sizing
 -> V58.2 handoff
 -> V56 risk
 -> V58.2 handoff
 -> V57 execution

The controller is fail-fast, blocks live mode, rejects network use, creates
stage and handoff audit records, and emits a deterministic SHA-256 ledger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

try:
    from tools.handoff_adapter_v58_2 import HandoffAdapterV582
except ModuleNotFoundError:
    # Supports direct execution:
    # python .\tools\paper_trading_e2e_pipeline_v58_3.py ...
    from handoff_adapter_v58_2 import HandoffAdapterV582

VERSION = "58.3"
VALID_MODES = {"replay", "paper", "live"}

def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload

@dataclass(frozen=True)
class StageCommand:
    name: str
    script: str
    input: str
    output: str

@dataclass(frozen=True)
class HandoffCommand:
    name: str
    handoff_type: str
    source_stage: str
    template: str
    output: str

@dataclass(frozen=True)
class PipelineConfig:
    pipeline_id: str
    python_executable: str
    mode: str
    stages: list[StageCommand]
    handoffs: list[HandoffCommand]

class EndToEndPipelineV583:
    EXPECTED_STAGES = ("v54_signal", "v55_sizing", "v56_risk", "v57_execution")
    EXPECTED_HANDOFFS = ("v54_to_v55", "v55_to_v56", "v56_to_v57")

    def __init__(
        self,
        config: PipelineConfig,
        *,
        enable_live: bool = False,
        runner: Callable[..., Any] | None = None,
        adapter: HandoffAdapterV582 | None = None,
    ) -> None:
        if not config.pipeline_id.strip():
            raise ValueError("pipeline_id is required")
        if config.mode not in VALID_MODES:
            raise ValueError("mode must be replay, paper, or live")
        if tuple(stage.name for stage in config.stages) != self.EXPECTED_STAGES:
            raise ValueError("stage order must be v54_signal, v55_sizing, v56_risk, v57_execution")
        if tuple(item.name for item in config.handoffs) != self.EXPECTED_HANDOFFS:
            raise ValueError("handoff order must be v54_to_v55, v55_to_v56, v56_to_v57")
        self.config = config
        self.enable_live = enable_live
        self.runner = runner or subprocess.run
        self.adapter = adapter or HandoffAdapterV582()
        self.audit: list[dict[str, Any]] = []
        self.ledger: list[dict[str, Any]] = []
        self.results: dict[str, dict[str, Any]] = {}

    def _live_gate(self) -> None:
        if self.config.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError("live end-to-end pipeline is intentionally not implemented in V58.3")

    def _append_ledger(self, event_type: str, component: str, status: str, payload: dict[str, Any]) -> None:
        previous = self.ledger[-1]["entry_sha256"] if self.ledger else "GENESIS"
        core = {
            "sequence": len(self.ledger) + 1,
            "event_type": event_type,
            "component": component,
            "status": status,
            "payload_sha256": canonical_hash(payload),
            "previous_entry_sha256": previous,
        }
        self.ledger.append({**core, "entry_sha256": canonical_hash(core)})

    def _record(self, event_type: str, component: str, status: str, details: dict[str, Any]) -> None:
        record = {
            "sequence": len(self.audit) + 1,
            "event_type": event_type,
            "component": component,
            "status": status,
            **details,
        }
        self.audit.append(record)
        self._append_ledger(event_type, component, status, record)

    @staticmethod
    def _unwrap(payload: dict[str, Any]) -> dict[str, Any]:
        result = payload.get("result", payload)
        if not isinstance(result, dict):
            raise ValueError("stage result must be a JSON object")
        return result

    def _run_stage(self, stage: StageCommand) -> dict[str, Any]:
        script, input_path, output_path = Path(stage.script), Path(stage.input), Path(stage.output)
        if not script.is_file():
            raise FileNotFoundError(f"missing stage script: {script}")
        if not input_path.is_file():
            raise FileNotFoundError(f"missing stage input: {input_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            self.config.python_executable,
            str(script),
            "--input", str(input_path),
            "--mode", self.config.mode,
            "--output", str(output_path),
        ]
        completed = self.runner(command, capture_output=True, text=True)
        if not output_path.exists():
            raise RuntimeError(f"{stage.name} did not create output")

        result = self._unwrap(load_json(output_path))
        status = str(result.get("status", "FAIL")).upper()
        network_used = bool(result.get("network_used", False))
        details = {
            "return_code": completed.returncode,
            "command": command,
            "output_path": str(output_path),
            "output_sha256": canonical_hash(result),
            "stdout_sha256": hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr.encode("utf-8")).hexdigest(),
            "network_used": network_used,
        }
        self._record("STAGE_COMPLETED", stage.name, status, details)

        if network_used:
            raise RuntimeError(f"{stage.name} network use detected")
        if completed.returncode != 0 or status != "PASS":
            raise RuntimeError(f"{stage.name} failed")
        self.results[stage.name] = result
        return result

    def _run_handoff(self, item: HandoffCommand) -> dict[str, Any]:
        if item.source_stage not in self.results:
            raise RuntimeError(f"missing source stage result: {item.source_stage}")
        template_path, output_path = Path(item.template), Path(item.output)
        if not template_path.is_file():
            raise FileNotFoundError(f"missing handoff template: {template_path}")
        source = self.results[item.source_stage]
        template = load_json(template_path)
        generated = self.adapter.transform(item.handoff_type, source, template)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.adapter.export(output_path, generated)

        handoff_block = generated.get("handoff", {})
        if bool(handoff_block.get("network_used", False)):
            raise RuntimeError(f"{item.name} network use detected")
        details = {
            "handoff_type": item.handoff_type,
            "source_stage": item.source_stage,
            "template_path": str(template_path),
            "output_path": str(output_path),
            "source_sha256": handoff_block.get("source_sha256"),
            "generated_input_sha256": handoff_block.get("generated_input_sha256"),
            "handoff_sha256": handoff_block.get("handoff_sha256"),
            "network_used": False,
        }
        self._record("HANDOFF_COMPLETED", item.name, "PASS", details)
        return generated

    def run(self) -> dict[str, Any]:
        self._live_gate()
        stopped_at: str | None = None
        error: str | None = None

        stage_by_name = {x.name: x for x in self.config.stages}
        handoff_by_name = {x.name: x for x in self.config.handoffs}

        flow = [
            ("stage", "v54_signal"),
            ("handoff", "v54_to_v55"),
            ("stage", "v55_sizing"),
            ("handoff", "v55_to_v56"),
            ("stage", "v56_risk"),
            ("handoff", "v56_to_v57"),
            ("stage", "v57_execution"),
        ]

        try:
            for kind, name in flow:
                stopped_at = name
                if kind == "stage":
                    stage = stage_by_name[name]
                    self._run_stage(stage)
                else:
                    handoff = handoff_by_name[name]
                    generated = self._run_handoff(handoff)
                    next_stage_name = {
                        "v54_to_v55": "v55_sizing",
                        "v55_to_v56": "v56_risk",
                        "v56_to_v57": "v57_execution",
                    }[name]
                    next_stage = stage_by_name[next_stage_name]
                    if Path(next_stage.input) != Path(handoff.output):
                        raise ValueError(f"{next_stage_name} input must equal {name} output")
            stopped_at = None
            status, decision = "PASS", "pipeline_completed"
        except (OSError, ValueError, RuntimeError, TypeError, json.JSONDecodeError) as exc:
            status, decision, error = "FAIL", "pipeline_failed", str(exc)

        final_execution = self.results.get("v57_execution", {})
        core = {
            "schema_version": "v58.3.end_to_end_pipeline.1",
            "version": VERSION,
            "pipeline_id": self.config.pipeline_id,
            "status": status,
            "decision": decision,
            "stopped_at": stopped_at,
            "error": error,
            "completed_component_count": len(self.audit),
            "expected_component_count": 7,
            "stage_results": self.results,
            "final_execution_state": final_execution.get("final_state"),
            "final_filled_quantity": final_execution.get("filled_quantity"),
            "final_average_fill_price": final_execution.get("average_fill_price"),
            "audit_trail": self.audit,
            "network_used": False,
        }
        return {**core, "pipeline_sha256": canonical_hash(core), "ledger": self.ledger}

    @staticmethod
    def export(path: Path, result: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

def load_config(path: Path) -> PipelineConfig:
    payload = load_json(path)
    return PipelineConfig(
        pipeline_id=payload["pipeline_id"],
        python_executable=payload.get("python_executable", sys.executable),
        mode=payload.get("mode", "paper"),
        stages=[StageCommand(**item) for item in payload["stages"]],
        handoffs=[HandoffCommand(**item) for item in payload["handoffs"]],
    )

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V58.3 End-to-End Pipeline Controller")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--enable-live", action="store_true")
    return parser

def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output)
    try:
        pipeline = EndToEndPipelineV583(load_config(Path(args.config)), enable_live=args.enable_live)
        result = pipeline.run()
        pipeline.export(output, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    except (OSError, ValueError, PermissionError, NotImplementedError, TypeError, json.JSONDecodeError) as exc:
        error = {
            "schema_version": "v58.3.end_to_end_pipeline_error.1",
            "version": VERSION,
            "status": "FAIL",
            "error": str(exc),
            "network_used": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(error, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
