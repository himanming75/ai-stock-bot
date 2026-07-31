from __future__ import annotations

import argparse, hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from broker.broker_state_checkpoint_v77_5 import BrokerStateCheckpointManager
from broker.multi_order_continuation_stress_v77_8 import MultiOrderContinuationStress

NEXT_PHASE = "V77_9_FAILURE_INJECTION_RECOVERY"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if p.returncode:
        raise ValueError(p.stderr.strip())
    return p.stdout.strip()


def ancestor(root: Path, sha: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=root
    ).returncode == 0


def verify(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    head = git(root, "rev-parse", "HEAD")
    origin = git(root, "rev-parse", "origin/main")
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    source = load_json(
        root/"release/v77_7/output/recovery_continuation_safety_verification_v77_7.json"
    )
    checkpoint = BrokerStateCheckpointManager().read(
        root/"release/v77_5/output/sample_broker_state_checkpoint_v77_5.json"
    )
    simulator, report = MultiOrderContinuationStress().run(checkpoint)

    gates: list[dict[str, str]] = []
    def gate(name: str, passed: bool) -> None:
        gates.append({"gate_id": name, "status": "PASS" if passed else "FAIL"})

    gate("GIT_HEAD_MATCHES_ORIGIN", head == origin)
    gate("GIT_BRANCH_MAIN", branch == "main")
    gate("BASE_COMMIT_ANCESTOR", ancestor(root, config["expected_framework_commit_sha"]))
    gate("V77_7_STATUS_PASS", source.get("status") == "PASS")
    gate("V77_7_SAFETY_ANCHOR", source.get("recovery_continuation_safety_sha256")
         == config["expected_v77_7_safety_sha256"])
    gate("V77_7_CHECKPOINT_ANCHOR", source.get("continuation_report", {}).get(
         "continued_checkpoint_sha256") == config["expected_v77_7_continued_checkpoint_sha256"])
    gate("V77_7_VERIFICATION_ANCHOR", source.get("verification_sha256")
         == config["expected_v77_7_verification_sha256"])
    gate("V77_7_NEXT_PHASE", source.get("next_phase")
         == "V77_8_MULTI_ORDER_CONTINUATION_STRESS")
    gate("STRESS_STATUS_PASS", report.status == "PASS")
    for key, passed in report.checks.items():
        gate(key.upper(), bool(passed))

    definition = {
        "new_orders": report.submitted_order_count,
        "new_fills": report.applied_fill_count,
        "duplicate_rejections": report.duplicate_rejection_count,
        "symbols": list(report.symbols),
        "partial_and_full_fills": True,
        "actual_network_calls": 0,
        "actual_orders_submitted": 0,
    }
    framework_sha = digest(definition)
    gate("STRESS_FRAMEWORK_DIGEST_CREATED", len(framework_sha) == 64)

    failed = [g["gate_id"] for g in gates if g["status"] == "FAIL"]
    status = "PASS" if not failed else "FAIL"
    result = {
        "schema_version": "v77.8.multi_order_continuation_stress_verification.1",
        "version": "77.8",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "decision": "multi_order_continuation_stress_established"
            if status == "PASS" else "multi_order_continuation_stress_rejected",
        "repository": {"framework_commit_sha": head, "origin_main_sha": origin, "branch": branch},
        "source_anchors": {
            "v77_7_recovery_continuation_safety_sha256":
                source.get("recovery_continuation_safety_sha256"),
            "v77_7_continued_checkpoint_sha256":
                source.get("continuation_report", {}).get("continued_checkpoint_sha256"),
            "v77_7_verification_sha256": source.get("verification_sha256"),
        },
        "multi_order_continuation_stress_sha256": framework_sha,
        "stress_report": report.as_dict(),
        "verification_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates)-len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "environment": "offline",
        "network_allowed": False,
        "broker_connected": False,
        "actual_orders_submitted": 0,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS"
            else "REPAIR_V77_8_MULTI_ORDER_CONTINUATION_STRESS",
    }
    result["verification_sha256"] = digest(
        {k:v for k,v in result.items() if k not in {"verification_sha256","issued_at_utc"}}
    )
    return result


def summary(r: dict[str, Any]) -> dict[str, Any]:
    vr, sr = r["verification_result"], r["stress_report"]
    return {
        "status": r["status"], "decision": r["decision"],
        "framework_commit_sha": r["repository"]["framework_commit_sha"],
        "multi_order_continuation_stress_sha256":
            r["multi_order_continuation_stress_sha256"],
        "source_state_sha256": sr["source_state_sha256"],
        "stressed_state_sha256": sr["stressed_state_sha256"],
        "verification_sha256": r["verification_sha256"],
        **r["source_anchors"],
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "stress_status": sr["status"],
        "submitted_order_count": sr["submitted_order_count"],
        "applied_fill_count": sr["applied_fill_count"],
        "duplicate_rejection_count": sr["duplicate_rejection_count"],
        "symbols": sr["symbols"],
        "environment": r["environment"], "network_allowed": r["network_allowed"],
        "broker_connected": r["broker_connected"],
        "actual_orders_submitted": r["actual_orders_submitted"],
        "live_trading_authorized": r["live_trading_authorized"],
        "next_phase": r["next_phase"],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    result = verify(Path(a.repository_root).resolve(), load_json(Path(a.config)))
    out = Path(a.output_dir); out.mkdir(parents=True, exist_ok=True)
    (out/"multi_order_continuation_stress_verification_v77_8.json").write_text(
        json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    (out/"multi_order_continuation_stress_summary_v77_8.json").write_text(
        json.dumps(summary(result), indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(summary(result), indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
