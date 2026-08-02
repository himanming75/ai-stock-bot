from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Sequence


class RecoveryGateState(str, Enum):
    SAFE_MODE = "SAFE_MODE"
    READ_ONLY_READY = "READ_ONLY_READY"
    PAPER_WRITE_READY = "PAPER_WRITE_READY"


@dataclass(frozen=True)
class RecoveryGateCheck:
    name: str
    passed: bool
    blocking: bool
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecoveryGatePolicy:
    require_account_active: bool = True
    require_trading_unblocked: bool = True
    require_ledger_recovered: bool = True
    require_portfolio_matched: bool = True
    require_recovery_valid: bool = True
    require_runtime_ready: bool = True
    require_risk_ready: bool = True
    require_kill_switch_off: bool = True
    require_emergency_stop_off: bool = True
    require_live_trading_disabled: bool = True
    require_zero_unknown_orders: bool = True
    require_zero_external_orders: bool = True


@dataclass(frozen=True)
class RecoveryGateReport:
    state: RecoveryGateState
    safe_mode_engaged: bool
    autonomous_order_allowed: bool
    paper_write_ready: bool
    all_blocking_checks_passed: bool
    passed_check_count: int
    failed_check_count: int
    blocking_failure_count: int
    checks: tuple[RecoveryGateCheck, ...]
    approval_token_verified: bool
    write_enablement_requested: bool
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "safe_mode_engaged": self.safe_mode_engaged,
            "autonomous_order_allowed": self.autonomous_order_allowed,
            "paper_write_ready": self.paper_write_ready,
            "all_blocking_checks_passed": self.all_blocking_checks_passed,
            "passed_check_count": self.passed_check_count,
            "failed_check_count": self.failed_check_count,
            "blocking_failure_count": self.blocking_failure_count,
            "checks": [item.to_json_dict() for item in self.checks],
            "approval_token_verified": self.approval_token_verified,
            "write_enablement_requested": self.write_enablement_requested,
            "network_requests_executed": self.network_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


class AutonomousSafeModeRecoveryGate:
    APPROVAL_TEXT = "AUTHORIZE PAPER WRITE READINESS ONLY NO ORDER SUBMISSION"

    def __init__(self, *, policy: RecoveryGatePolicy | None = None) -> None:
        self.policy = policy or RecoveryGatePolicy()

    def evaluate(
        self,
        *,
        account_state: Mapping[str, Any],
        ledger_state: Mapping[str, Any],
        portfolio_state: Mapping[str, Any],
        recovery_state: Mapping[str, Any],
        runtime_state: Mapping[str, Any],
        risk_state: Mapping[str, Any],
        write_enablement_requested: bool = False,
        approval_text: str = "",
    ) -> RecoveryGateReport:
        checks = (
            self._check(
                "ACCOUNT_ACTIVE",
                (not self.policy.require_account_active)
                or str(account_state.get("account_status", "")).upper() == "ACTIVE",
                "Alpaca Paper account must be ACTIVE",
            ),
            self._check(
                "TRADING_UNBLOCKED",
                (not self.policy.require_trading_unblocked)
                or not bool(account_state.get("trading_blocked", True)),
                "broker trading_blocked must be false",
            ),
            self._check(
                "LEDGER_RECOVERED",
                (not self.policy.require_ledger_recovered)
                or str(ledger_state.get("ledger_recovery_status", "")).upper()
                in {"RECOVERED", "NO_OPEN_ORDERS"},
                "order ledger must be recovered or contain no open orders",
            ),
            self._check(
                "UNKNOWN_ORDERS_ZERO",
                (not self.policy.require_zero_unknown_orders)
                or int(ledger_state.get("unknown_count", 0)) == 0,
                "unknown broker orders must be zero",
            ),
            self._check(
                "EXTERNAL_ORDERS_ZERO",
                (not self.policy.require_zero_external_orders)
                or int(ledger_state.get("external_count", 0)) == 0,
                "external or manual broker orders must be zero",
            ),
            self._check(
                "PORTFOLIO_MATCHED",
                (not self.policy.require_portfolio_matched)
                or (
                    str(portfolio_state.get("reconciliation_status", "")).upper()
                    == "MATCHED"
                    and int(portfolio_state.get("blocking_mismatch_count", 0)) == 0
                ),
                "broker and internal portfolio states must match",
            ),
            self._check(
                "RECOVERY_VALID",
                (not self.policy.require_recovery_valid)
                or bool(recovery_state.get("recovery_valid", False)),
                "runtime recovery snapshot must be valid",
            ),
            self._check(
                "RUNTIME_READY",
                (not self.policy.require_runtime_ready)
                or str(runtime_state.get("runtime_state", "")).upper()
                in {"READY", "WAITING", "STOPPED"},
                "runtime must be READY, WAITING, or STOPPED",
            ),
            self._check(
                "RISK_READY",
                (not self.policy.require_risk_ready)
                or bool(risk_state.get("risk_ready", False)),
                "risk manager must report ready",
            ),
            self._check(
                "KILL_SWITCH_OFF",
                (not self.policy.require_kill_switch_off)
                or not bool(risk_state.get("kill_switch_engaged", True)),
                "kill switch must be disengaged",
            ),
            self._check(
                "EMERGENCY_STOP_OFF",
                (not self.policy.require_emergency_stop_off)
                or not bool(risk_state.get("emergency_stop_engaged", True)),
                "emergency stop must be disengaged",
            ),
            self._check(
                "LIVE_TRADING_DISABLED",
                (not self.policy.require_live_trading_disabled)
                or not bool(runtime_state.get("live_trading_enabled", True)),
                "live trading must remain disabled",
            ),
        )

        blocking_failures = sum(
            1 for item in checks if item.blocking and not item.passed
        )
        all_passed = blocking_failures == 0
        approval_verified = (
            write_enablement_requested
            and approval_text.strip() == self.APPROVAL_TEXT
        )

        if not all_passed:
            state = RecoveryGateState.SAFE_MODE
        elif approval_verified:
            state = RecoveryGateState.PAPER_WRITE_READY
        else:
            state = RecoveryGateState.READ_ONLY_READY

        return RecoveryGateReport(
            state=state,
            safe_mode_engaged=state == RecoveryGateState.SAFE_MODE,
            autonomous_order_allowed=state == RecoveryGateState.PAPER_WRITE_READY,
            paper_write_ready=state == RecoveryGateState.PAPER_WRITE_READY,
            all_blocking_checks_passed=all_passed,
            passed_check_count=sum(1 for item in checks if item.passed),
            failed_check_count=sum(1 for item in checks if not item.passed),
            blocking_failure_count=blocking_failures,
            checks=checks,
            approval_token_verified=approval_verified,
            write_enablement_requested=write_enablement_requested,
            network_requests_executed=0,
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )

    @staticmethod
    def _check(name: str, passed: bool, detail: str) -> RecoveryGateCheck:
        return RecoveryGateCheck(
            name=name,
            passed=bool(passed),
            blocking=True,
            detail=detail,
        )
