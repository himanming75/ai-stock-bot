from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
actual = (
    ROOT / "release/bundle_c_r14_to_r15_final_operations/actual"
)
result = json.loads(
    (actual / "bundle_c_result.json").read_text(
        encoding="utf-8-sig"
    )
)
diagnostics = json.loads(
    (actual / "final_diagnostics.json").read_text(
        encoding="utf-8-sig"
    )
)
gate = json.loads(
    (actual / "final_release_gate.json").read_text(
        encoding="utf-8-sig"
    )
)
manifest = json.loads(
    (actual / "final_release_manifest.json").read_text(
        encoding="utf-8-sig"
    )
)

checks = {
    "stage": result.get("stage") == "BUNDLE_C_R14_TO_R15",
    "status": result.get("status") == "PASS",
    "final_operations_ready": (
        result.get("r14_final_operations_integration") == "READY"
    ),
    "production_gate_ready": (
        result.get("r15_production_candidate_gate") == "READY"
    ),
    "diagnostics_pass": diagnostics.get("status") == "PASS",
    "manifest_present": manifest.get("tracked_file_count", 0) > 0,
    "manifest_hash_valid": (
        len(manifest.get("manifest_sha256", "")) == 64
    ),
    "candidate_ready": (
        result.get("production_candidate_ready") is True
    ),
    "release_blocked_until_actuals": (
        gate.get("production_release_allowed") is False
        and gate.get("release_state") == "BLOCKED"
    ),
    "actual_release_not_performed": (
        result.get("actual_release_performed") is False
    ),
    "task_registration_not_performed": (
        result.get("windows_task_registration_performed") is False
    ),
    "network_off": result.get("broker_network_enabled") is False,
    "write_off": result.get("broker_write_enabled") is False,
    "submission_off": (
        result.get("automatic_order_submission_enabled") is False
    ),
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
    "next_action_fixed": (
        result.get("next_fixed_action") ==
        "RUN_P2_TO_P5_ACTUAL_PAPER_VALIDATION"
    ),
}
verification = {
    "verification_stage": "BUNDLE_C_R14_TO_R15",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
