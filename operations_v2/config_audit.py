from __future__ import annotations
from typing import Any


class ConfigurationDiffAuditor:
    def compare(
        self,
        *,
        baseline: dict[str, Any],
        current: dict[str, Any],
        protected_keys: set[str],
    ) -> dict[str, Any]:
        changes = []
        all_keys = sorted(set(baseline) | set(current))
        protected_change_count = 0

        for key in all_keys:
            old = baseline.get(key)
            new = current.get(key)
            if old == new:
                continue
            protected = key in protected_keys
            if protected:
                protected_change_count += 1
            changes.append({
                "key": key,
                "baseline": old,
                "current": new,
                "protected": protected,
            })

        return {
            "change_count": len(changes),
            "protected_change_count": protected_change_count,
            "changes": changes,
            "safe": protected_change_count == 0,
            "actual_configuration_modified": False,
        }
