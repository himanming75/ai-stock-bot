from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .models import CertificationCheck


@dataclass(frozen=True)
class RuntimeIntegrityValidator:
    required_components: tuple[str, ...] = (
        "continuous_paper_runtime",
        "paper_runtime_stability",
        "paper_runtime_scheduler",
        "paper_scheduler",
        "paper_runtime",
        "risk_engine",
        "portfolio_engine",
        "execution_engine",
        "strategy_engine",
        "runtime_engine",
        "alpaca_broker",
    )

    def validate_components(self, available: Iterable[str]) -> CertificationCheck:
        present = set(available)
        missing = [name for name in self.required_components if name not in present]
        return CertificationCheck(
            name="component_integrity",
            passed=not missing,
            detail="all required components present" if not missing else f"missing: {missing}",
        )

    def validate_event_order(self, events: Sequence[str]) -> CertificationCheck:
        expected_prefix = ["PREPARE", "START_SESSION"]
        expected_suffix = ["CLOSE_SESSION", "STOPPED"]
        passed = (
            len(events) >= 4
            and list(events[:2]) == expected_prefix
            and list(events[-2:]) == expected_suffix
            and events.count("RUN_CYCLE") >= 1
        )
        return CertificationCheck(
            name="event_ordering",
            passed=passed,
            detail="event order valid" if passed else f"invalid events: {list(events)}",
        )

    def validate_state_consistency(self, state: Mapping[str, object]) -> CertificationCheck:
        passed = (
            state.get("runtime_state") == "STOPPED"
            and state.get("session_active") is False
            and state.get("session_closed") is True
            and state.get("circuit_open") is False
        )
        return CertificationCheck(
            name="state_consistency",
            passed=passed,
            detail="runtime state consistent" if passed else f"inconsistent state: {dict(state)}",
        )

    def validate_recovery(self, snapshot: Mapping[str, object]) -> CertificationCheck:
        passed = (
            snapshot.get("exists") is True
            and snapshot.get("valid") is True
            and int(snapshot.get("generation", -1)) >= 1
        )
        return CertificationCheck(
            name="recovery_snapshot",
            passed=passed,
            detail="recovery snapshot valid" if passed else f"invalid recovery: {dict(snapshot)}",
        )

    def validate_portfolio(self, portfolio: Mapping[str, object]) -> CertificationCheck:
        passed = (
            portfolio.get("cash_nonnegative") is True
            and portfolio.get("positions_nonnegative") is True
            and portfolio.get("equity_consistent") is True
        )
        return CertificationCheck(
            name="portfolio_consistency",
            passed=passed,
            detail="portfolio consistent" if passed else f"inconsistent portfolio: {dict(portfolio)}",
        )

    def validate_safety(self, counters: Mapping[str, int]) -> CertificationCheck:
        passed = all(
            counters.get(name, -1) == 0
            for name in (
                "network_requests_executed",
                "write_requests_executed",
                "actual_paper_orders_submitted",
                "live_orders_submitted",
            )
        )
        return CertificationCheck(
            name="safety_zero_write",
            passed=passed,
            detail="all network/write/order counters are zero"
            if passed else f"unsafe counters: {dict(counters)}",
        )
