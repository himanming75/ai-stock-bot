from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
status = json.loads(
    (
        ROOT / "release/r3_secure_credential_storage/actual/"
               "r3_vault_status.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": status.get("stage") == "R3_VAULT_STATUS",
    "paper_live_separated": (
        status.get("paper_live_separated") is True
    ),
    "plaintext_files_not_expected": (
        status.get("plaintext_secret_files_expected") is False
    ),
    "network_unused": status.get("network_used") is False,
    "paper_orders_zero": (
        status.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        status.get("actual_live_orders_submitted") == 0
    ),
}
result = {
    "verification_stage": "R3_PREPARATION",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
