from __future__ import annotations
from .models import RoutedAccount
from .policy import ProductionReadOnlyPolicy


class ETradeAccountRouter:
    def __init__(
        self,
        *,
        policy: ProductionReadOnlyPolicy,
        aliases: dict[str, str] | None = None,
    ) -> None:
        self.policy = policy
        self.aliases = aliases or {}

    def build_registry(
        self,
        accounts: list[dict],
    ) -> list[RoutedAccount]:
        routed = []
        for account in accounts:
            account_id_key = str(
                account.get("accountIdKey") or ""
            )
            if not account_id_key:
                continue

            enabled = (
                not self.policy.allowed_account_id_keys
                or account_id_key
                in self.policy.allowed_account_id_keys
            )
            is_default = (
                account_id_key
                == self.policy.default_account_id_key
            )
            routed.append(
                RoutedAccount(
                    account_id_key=account_id_key,
                    account_id_masked=str(
                        account.get("accountId") or ""
                    ),
                    account_type=str(
                        account.get("accountType") or "UNKNOWN"
                    ).upper(),
                    account_mode=str(
                        account.get("accountMode") or "UNKNOWN"
                    ).upper(),
                    account_status=str(
                        account.get("accountStatus") or "UNKNOWN"
                    ).upper(),
                    alias=self.aliases.get(
                        account_id_key,
                        f"ETRADE_{len(routed)+1}",
                    ),
                    enabled=enabled,
                    default=is_default,
                    production_read_allowed=(
                        self.policy.production_read_enabled
                        and enabled
                    ),
                )
            )

        routed.sort(
            key=lambda item: (
                not item.default,
                not item.enabled,
                item.alias,
                item.account_id_key,
            )
        )
        return routed

    def select(
        self,
        accounts: list[RoutedAccount],
        requested: str | None = None,
    ) -> RoutedAccount:
        enabled = [
            item for item in accounts
            if item.enabled
        ]
        if not enabled:
            raise RuntimeError("No enabled E*TRADE accounts")

        if requested:
            for item in enabled:
                if (
                    item.account_id_key == requested
                    or item.alias == requested
                ):
                    return item
            raise KeyError(
                f"Requested E*TRADE account not found: {requested}"
            )

        for item in enabled:
            if item.default:
                return item

        if len(enabled) == 1:
            return enabled[0]

        raise RuntimeError(
            "Multiple enabled E*TRADE accounts require an explicit "
            "default account or requested account."
        )
