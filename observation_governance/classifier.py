from __future__ import annotations


def classify(checks: dict[str, bool], statistics: dict, corrupt_records: int) -> tuple[str, list[str]]:
    incidents: list[str] = []
    if not checks.get("qualification_gate"):
        incidents.append("QUALIFICATION_GATE_FAILED")
    if not checks.get("continuity_healthy"):
        incidents.append("CONTINUITY_DEGRADED")
    if not checks.get("zero_blocked_cycles"):
        incidents.append("BLOCKED_CYCLE_DETECTED")
    if not checks.get("zero_errors"):
        incidents.append("ERROR_RECORD_DETECTED")
    if corrupt_records:
        incidents.append("CORRUPT_LEDGER_RECORD")
    if not checks.get("safety_policy_valid"):
        incidents.append("SAFETY_POLICY_VIOLATION")

    if not incidents:
        return "HEALTHY", []
    critical = {"QUALIFICATION_GATE_FAILED", "SAFETY_POLICY_VIOLATION", "CORRUPT_LEDGER_RECORD"}
    if any(item in critical for item in incidents):
        return "CRITICAL", incidents
    return "WARNING", incidents
