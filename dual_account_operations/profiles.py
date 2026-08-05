from __future__ import annotations
from .models import AccountPolicy, PolicyProfile


class PolicyProfileCatalog:
    def __init__(self) -> None:
        self._profiles = {
            "PAPER_TEST": PolicyProfile(
                name="PAPER_TEST",
                description=(
                    "Alpaca Paper monitoring and strategy testing. "
                    "Order submission remains separately approved."
                ),
                account_policies=(
                    AccountPolicy(
                        account_key="ALPACA_PAPER_PRIMARY",
                        read_allowed=True,
                        write_allowed=False,
                        strategy_execution_allowed=True,
                        kill_switch_required=False,
                    ),
                    AccountPolicy(
                        account_key="ETRADE_PRIMARY",
                        read_allowed=False,
                        write_allowed=False,
                        strategy_execution_allowed=False,
                        kill_switch_required=True,
                    ),
                ),
                global_read_allowed=True,
                global_write_allowed=False,
                operator_ack_required=False,
            ),
            "ETRADE_READ_ONLY": PolicyProfile(
                name="ETRADE_READ_ONLY",
                description=(
                    "E*TRADE actual account visibility only. "
                    "Actual connection validation is required."
                ),
                account_policies=(
                    AccountPolicy(
                        account_key="ALPACA_PAPER_PRIMARY",
                        read_allowed=False,
                        write_allowed=False,
                        strategy_execution_allowed=False,
                        kill_switch_required=True,
                    ),
                    AccountPolicy(
                        account_key="ETRADE_PRIMARY",
                        read_allowed=True,
                        write_allowed=False,
                        strategy_execution_allowed=False,
                        kill_switch_required=False,
                    ),
                ),
                global_read_allowed=True,
                global_write_allowed=False,
                operator_ack_required=True,
            ),
            "DUAL_MONITOR": PolicyProfile(
                name="DUAL_MONITOR",
                description=(
                    "Monitor Alpaca Paper and E*TRADE together. "
                    "All write routes are blocked."
                ),
                account_policies=(
                    AccountPolicy(
                        account_key="ALPACA_PAPER_PRIMARY",
                        read_allowed=True,
                        write_allowed=False,
                        strategy_execution_allowed=False,
                        kill_switch_required=False,
                    ),
                    AccountPolicy(
                        account_key="ETRADE_PRIMARY",
                        read_allowed=True,
                        write_allowed=False,
                        strategy_execution_allowed=False,
                        kill_switch_required=False,
                    ),
                ),
                global_read_allowed=True,
                global_write_allowed=False,
                operator_ack_required=True,
            ),
            "ALL_STOP": PolicyProfile(
                name="ALL_STOP",
                description=(
                    "Block all account read and write routes."
                ),
                account_policies=(
                    AccountPolicy(
                        account_key="ALPACA_PAPER_PRIMARY",
                        read_allowed=False,
                        write_allowed=False,
                        strategy_execution_allowed=False,
                        kill_switch_required=True,
                    ),
                    AccountPolicy(
                        account_key="ETRADE_PRIMARY",
                        read_allowed=False,
                        write_allowed=False,
                        strategy_execution_allowed=False,
                        kill_switch_required=True,
                    ),
                ),
                global_read_allowed=False,
                global_write_allowed=False,
                operator_ack_required=False,
            ),
            "MAINTENANCE": PolicyProfile(
                name="MAINTENANCE",
                description=(
                    "Configuration and health inspection only."
                ),
                account_policies=(
                    AccountPolicy(
                        account_key="ALPACA_PAPER_PRIMARY",
                        read_allowed=False,
                        write_allowed=False,
                        strategy_execution_allowed=False,
                        kill_switch_required=True,
                    ),
                    AccountPolicy(
                        account_key="ETRADE_PRIMARY",
                        read_allowed=False,
                        write_allowed=False,
                        strategy_execution_allowed=False,
                        kill_switch_required=True,
                    ),
                ),
                global_read_allowed=False,
                global_write_allowed=False,
                operator_ack_required=False,
            ),
        }

    def get(self, name: str) -> PolicyProfile:
        key = str(name or "").upper()
        if key not in self._profiles:
            raise KeyError(
                f"Unknown policy profile: {name}"
            )
        return self._profiles[key]

    def all(self) -> list[PolicyProfile]:
        return [
            self._profiles[key]
            for key in sorted(self._profiles)
        ]
