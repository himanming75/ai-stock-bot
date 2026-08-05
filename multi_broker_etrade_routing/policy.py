from __future__ import annotations
from dataclasses import asdict, dataclass
import os


@dataclass(frozen=True)
class ProductionReadOnlyPolicy:
    production_read_enabled: bool
    broker_write_enabled: bool
    order_submission_enabled: bool
    order_cancel_enabled: bool
    require_explicit_environment_ack: bool
    allowed_account_id_keys: tuple[str, ...]
    default_account_id_key: str | None

    def to_dict(self) -> dict:
        value = asdict(self)
        value["allowed_account_id_keys"] = list(
            self.allowed_account_id_keys
        )
        return value

    @classmethod
    def from_environment(cls) -> "ProductionReadOnlyPolicy":
        allow = os.environ.get(
            "ETRADE_ALLOW_PRODUCTION_READ",
            "",
        ).strip().upper() == "YES"

        allowed = tuple(
            item.strip()
            for item in os.environ.get(
                "ETRADE_ALLOWED_ACCOUNT_ID_KEYS",
                "",
            ).split(",")
            if item.strip()
        )

        default = os.environ.get(
            "ETRADE_DEFAULT_ACCOUNT_ID_KEY",
            "",
        ).strip() or None

        return cls(
            production_read_enabled=allow,
            broker_write_enabled=False,
            order_submission_enabled=False,
            order_cancel_enabled=False,
            require_explicit_environment_ack=True,
            allowed_account_id_keys=allowed,
            default_account_id_key=default,
        )

    def assert_production_read_allowed(self) -> None:
        if not self.production_read_enabled:
            raise PermissionError(
                "Production read blocked. "
                "Set ETRADE_ALLOW_PRODUCTION_READ=YES explicitly."
            )

    def assert_account_allowed(self, account_id_key: str) -> None:
        if self.allowed_account_id_keys:
            if account_id_key not in self.allowed_account_id_keys:
                raise PermissionError(
                    f"Account not in allowlist: {account_id_key}"
                )
