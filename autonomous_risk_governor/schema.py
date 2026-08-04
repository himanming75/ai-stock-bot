from __future__ import annotations


REQUIRED_KEYS = {
    "stage",
    "mode",
    "risk_governor_enabled",
    "paper_endpoint_only",
    "live_submission_enabled",
    "broker_write_enabled",
    "daily_loss_limit_pct",
    "maximum_drawdown_pct",
    "maximum_position_pct",
    "maximum_total_exposure_pct",
    "maximum_symbol_exposure_pct",
    "maximum_consecutive_losses",
    "kill_switch_required",
    "kill_switch_active",
    "manual_resume_required",
}


def missing_keys(policy: dict) -> list[str]:
    return sorted(REQUIRED_KEYS - set(policy))
