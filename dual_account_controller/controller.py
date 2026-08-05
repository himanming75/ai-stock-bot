from __future__ import annotations
from dataclasses import replace
from pathlib import Path

from dual_account_operations.profiles import (
    PolicyProfileCatalog,
)
from dual_account_operations.transition import (
    validate_transition,
)

from .audit import AuditLedger
from .models import (
    ControllerCommandResult,
    ControllerState,
)
from .store import ControllerStateStore


class DualAccountOperationsController:
    def __init__(
        self,
        *,
        state_path: Path,
        ledger_path: Path,
        etrade_actual_connection_validated: bool,
    ) -> None:
        self.catalog = PolicyProfileCatalog()
        self.store = ControllerStateStore(
            state_path
        )
        self.ledger = AuditLedger(
            ledger_path
        )
        self.etrade_actual_connection_validated = (
            etrade_actual_connection_validated
        )
        self.state = self.store.load()

    def restore(self) -> ControllerState:
        self.state = self.store.load()
        self._audit(
            command="RESTORE",
            status="PASS",
            reason="STATE_RESTORED",
        )
        return self.state

    def lock_profile(self) -> ControllerState:
        self.state = replace(
            self.state,
            profile_locked=True,
            sequence=self.state.sequence + 1,
            last_transition_reason="PROFILE_LOCKED",
            last_transition_status="PASS",
        )
        self._persist_and_audit(
            command="LOCK_PROFILE",
            status="PASS",
            reason="PROFILE_LOCKED",
        )
        return self.state

    def unlock_profile(
        self,
        *,
        operator_ack: bool,
    ) -> ControllerState:
        if not operator_ack:
            self._audit(
                command="UNLOCK_PROFILE",
                status="BLOCKED",
                reason="OPERATOR_ACK_REQUIRED",
            )
            return self.state

        self.state = replace(
            self.state,
            profile_locked=False,
            sequence=self.state.sequence + 1,
            last_transition_reason="PROFILE_UNLOCKED",
            last_transition_status="PASS",
        )
        self._persist_and_audit(
            command="UNLOCK_PROFILE",
            status="PASS",
            reason="PROFILE_UNLOCKED",
        )
        return self.state

    def transition(
        self,
        target_profile: str,
        *,
        operator_ack: bool,
        reason: str,
    ) -> ControllerCommandResult:
        previous = self.state.active_profile
        target = str(
            target_profile or ""
        ).upper()

        if self.state.profile_locked and target != "ALL_STOP":
            return self._blocked_result(
                "PROFILE_LOCK_ACTIVE",
                previous,
                target,
            )

        decision = validate_transition(
            previous,
            target,
            operator_ack=operator_ack,
            etrade_actual_connection_validated=(
                self.etrade_actual_connection_validated
            ),
        )
        if not decision["allowed"]:
            return self._blocked_result(
                decision["reason"],
                previous,
                target,
            )

        profile = self.catalog.get(target)
        switches = {
            item.account_key: (
                item.kill_switch_required
            )
            for item in profile.account_policies
        }
        global_kill = (
            not profile.global_read_allowed
            and not profile.global_write_allowed
        )

        self.state = replace(
            self.state,
            active_profile=target,
            global_kill_switch=global_kill,
            account_kill_switches=switches,
            sequence=self.state.sequence + 1,
            last_transition_reason=reason,
            last_transition_status="PASS",
        )
        self._persist_and_audit(
            command="TRANSITION_PROFILE",
            status="PASS",
            reason=reason,
            previous_profile=previous,
            current_profile=target,
        )

        return ControllerCommandResult(
            command="TRANSITION_PROFILE",
            status="PASS",
            allowed=True,
            previous_profile=previous,
            current_profile=target,
            reason=reason,
            sequence=self.state.sequence,
        )

    def activate_account_kill_switch(
        self,
        account_key: str,
        *,
        reason: str,
    ) -> ControllerState:
        switches = dict(
            self.state.account_kill_switches
        )
        switches[account_key] = True
        self.state = replace(
            self.state,
            account_kill_switches=switches,
            sequence=self.state.sequence + 1,
            last_transition_reason=reason,
            last_transition_status="PASS",
        )
        self._persist_and_audit(
            command="ACCOUNT_KILL_SWITCH_ON",
            status="PASS",
            reason=reason,
            account_key=account_key,
        )
        return self.state

    def deactivate_account_kill_switch(
        self,
        account_key: str,
        *,
        operator_ack: bool,
        reason: str,
    ) -> ControllerState:
        if not operator_ack:
            self._audit(
                command="ACCOUNT_KILL_SWITCH_OFF",
                status="BLOCKED",
                reason="OPERATOR_ACK_REQUIRED",
                account_key=account_key,
            )
            return self.state

        switches = dict(
            self.state.account_kill_switches
        )
        switches[account_key] = False
        self.state = replace(
            self.state,
            account_kill_switches=switches,
            sequence=self.state.sequence + 1,
            last_transition_reason=reason,
            last_transition_status="PASS",
        )
        self._persist_and_audit(
            command="ACCOUNT_KILL_SWITCH_OFF",
            status="PASS",
            reason=reason,
            account_key=account_key,
        )
        return self.state

    def activate_global_kill_switch(
        self,
        *,
        reason: str,
    ) -> ControllerState:
        switches = {
            key: True
            for key in self.state.account_kill_switches
        }
        self.state = replace(
            self.state,
            active_profile="ALL_STOP",
            global_kill_switch=True,
            account_kill_switches=switches,
            sequence=self.state.sequence + 1,
            last_transition_reason=reason,
            last_transition_status="PASS",
        )
        self._persist_and_audit(
            command="GLOBAL_KILL_SWITCH_ON",
            status="PASS",
            reason=reason,
            previous_profile="UNKNOWN",
            current_profile="ALL_STOP",
        )
        return self.state

    def emergency_guard(
        self,
        *,
        critical_condition: bool,
        reason: str,
    ) -> ControllerState:
        if not critical_condition:
            self._audit(
                command="EMERGENCY_GUARD",
                status="PASS",
                reason="NO_CRITICAL_CONDITION",
            )
            return self.state

        return self.activate_global_kill_switch(
            reason=reason,
        )

    def _blocked_result(
        self,
        reason: str,
        previous: str,
        target: str,
    ) -> ControllerCommandResult:
        self._audit(
            command="TRANSITION_PROFILE",
            status="BLOCKED",
            reason=reason,
            previous_profile=previous,
            current_profile=target,
        )
        return ControllerCommandResult(
            command="TRANSITION_PROFILE",
            status="BLOCKED",
            allowed=False,
            previous_profile=previous,
            current_profile=previous,
            reason=reason,
            sequence=self.state.sequence,
        )

    def _persist_and_audit(
        self,
        *,
        command: str,
        status: str,
        reason: str,
        **extra,
    ) -> None:
        self.store.save(self.state)
        self._audit(
            command=command,
            status=status,
            reason=reason,
            **extra,
        )

    def _audit(
        self,
        *,
        command: str,
        status: str,
        reason: str,
        **extra,
    ) -> None:
        self.ledger.append({
            "command": command,
            "status": status,
            "reason": reason,
            "sequence": self.state.sequence,
            "active_profile": (
                self.state.active_profile
            ),
            "profile_locked": (
                self.state.profile_locked
            ),
            "global_kill_switch": (
                self.state.global_kill_switch
            ),
            "account_kill_switches": (
                self.state.account_kill_switches
            ),
            **extra,
        })
