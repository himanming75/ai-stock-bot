from __future__ import annotations
from .models import AccountProfile


class AccountRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, AccountProfile] = {}

    def register(self, profile: AccountProfile) -> None:
        if not profile.account_key:
            raise ValueError("account_key is required")
        if profile.account_key in self._profiles:
            raise ValueError(
                f"Duplicate account_key: {profile.account_key}"
            )
        self._profiles[profile.account_key] = profile

    def get(self, account_key: str) -> AccountProfile:
        if account_key not in self._profiles:
            raise KeyError(
                f"Unknown account_key: {account_key}"
            )
        return self._profiles[account_key]

    def all(self) -> list[AccountProfile]:
        return sorted(
            self._profiles.values(),
            key=lambda item: (
                item.broker,
                item.environment,
                item.account_key,
            ),
        )

    def by_role(self, role: str) -> list[AccountProfile]:
        target = role.upper()
        return [
            item
            for item in self.all()
            if item.role.upper() == target
        ]

    def replace(self, profile: AccountProfile) -> None:
        if profile.account_key not in self._profiles:
            raise KeyError(
                f"Unknown account_key: {profile.account_key}"
            )
        self._profiles[profile.account_key] = profile
