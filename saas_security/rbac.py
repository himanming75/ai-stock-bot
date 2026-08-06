from __future__ import annotations


ROLE_PERMISSIONS = {
    "OWNER": {
        "workspace.read",
        "workspace.manage",
        "members.manage",
        "security.manage",
        "tokens.manage",
        "audit.read",
        "admin.read",
        "admin.manage",
    },
    "ADMIN": {
        "workspace.read",
        "members.manage",
        "security.manage",
        "tokens.manage",
        "audit.read",
        "admin.read",
    },
    "TRADER": {
        "workspace.read",
        "tokens.manage",
        "audit.read",
    },
    "VIEWER": {
        "workspace.read",
        "audit.read",
    },
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(
        role,
        set(),
    )
