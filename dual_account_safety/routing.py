from __future__ import annotations
from .models import RouteDecision, RouteRequest
from .policy import operation_class
from .registry import AccountRegistry


class SafeAccountRouter:
    def __init__(self, registry: AccountRegistry) -> None:
        self.registry = registry

    def decide(self, request: RouteRequest) -> RouteDecision:
        try:
            profile = self.registry.get(request.account_key)
        except KeyError:
            return RouteDecision(
                status="BLOCKED",
                allowed=False,
                account_key=request.account_key,
                route="NONE",
                reason="UNKNOWN_ACCOUNT",
                read_allowed=False,
                write_allowed=False,
                kill_switch_active=True,
            )

        if profile.broker.upper() != request.broker.upper():
            return self._blocked(
                profile,
                "BROKER_MISMATCH",
            )

        if (
            profile.environment.upper()
            != request.environment.upper()
        ):
            return self._blocked(
                profile,
                "ENVIRONMENT_MISMATCH",
            )

        if profile.kill_switch_active:
            return self._blocked(
                profile,
                "ACCOUNT_KILL_SWITCH_ACTIVE",
            )

        kind = operation_class(request.operation)

        if kind == "READ":
            if not profile.read_enabled:
                return self._blocked(
                    profile,
                    "READ_DISABLED",
                )
            if (
                profile.environment.upper() == "PRODUCTION"
                and not profile.actual_connection_validated
            ):
                return self._blocked(
                    profile,
                    "ACTUAL_CONNECTION_NOT_VALIDATED",
                )
            return RouteDecision(
                status="PASS",
                allowed=True,
                account_key=profile.account_key,
                route=(
                    f"{profile.broker.upper()}:"
                    f"{profile.environment.upper()}:READ"
                ),
                reason="READ_ROUTE_APPROVED",
                read_allowed=True,
                write_allowed=False,
                kill_switch_active=False,
            )

        if kind == "WRITE":
            if not profile.write_enabled:
                return self._blocked(
                    profile,
                    "WRITE_DISABLED",
                )
            if not profile.strategy_execution_enabled:
                return self._blocked(
                    profile,
                    "STRATEGY_EXECUTION_DISABLED",
                )
            if profile.role.upper() != "PAPER_EXECUTION":
                return self._blocked(
                    profile,
                    "NON_PAPER_WRITE_ROUTE_BLOCKED",
                )
            if profile.environment.upper() != "PAPER":
                return self._blocked(
                    profile,
                    "PAPER_ENVIRONMENT_REQUIRED",
                )
            return RouteDecision(
                status="PASS",
                allowed=True,
                account_key=profile.account_key,
                route=(
                    f"{profile.broker.upper()}:"
                    f"{profile.environment.upper()}:WRITE"
                ),
                reason="PAPER_WRITE_ROUTE_APPROVED",
                read_allowed=True,
                write_allowed=True,
                kill_switch_active=False,
            )

        return self._blocked(
            profile,
            "UNKNOWN_OPERATION",
        )

    @staticmethod
    def _blocked(profile, reason: str) -> RouteDecision:
        return RouteDecision(
            status="BLOCKED",
            allowed=False,
            account_key=profile.account_key,
            route="NONE",
            reason=reason,
            read_allowed=False,
            write_allowed=False,
            kill_switch_active=profile.kill_switch_active,
        )
