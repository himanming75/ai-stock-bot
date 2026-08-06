from __future__ import annotations


ROLE_PERMISSIONS = {
    "OWNER": {
        "workspace.read",
        "workspace.manage",
        "members.manage",
        "strategy.manage",
        "risk.manage",
        "broker.manage",
        "audit.read",
    },
    "ADMIN": {
        "workspace.read",
        "members.manage",
        "strategy.manage",
        "risk.manage",
        "broker.manage",
        "audit.read",
    },
    "TRADER": {
        "workspace.read",
        "strategy.manage",
        "risk.manage",
        "audit.read",
    },
    "VIEWER": {
        "workspace.read",
        "audit.read",
    },
}


def has_permission(
    role: str,
    permission: str,
) -> bool:
    return permission in ROLE_PERMISSIONS.get(
        role,
        set(),
    )
