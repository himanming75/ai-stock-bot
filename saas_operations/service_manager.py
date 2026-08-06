from __future__ import annotations


ALLOWED_ACTIONS = {
    "STATUS",
    "RELOAD_CONFIG_DRY_RUN",
}


class SafeServiceManager:
    def request(
        self,
        *,
        service_name: str,
        action: str,
    ) -> dict:
        normalized = action.upper()
        if normalized not in ALLOWED_ACTIONS:
            return {
                "service_name": service_name,
                "action": normalized,
                "status": "BLOCKED",
                "reason": (
                    "DESTRUCTIVE_SERVICE_ACTION_DISABLED"
                ),
                "process_modified": False,
            }

        return {
            "service_name": service_name,
            "action": normalized,
            "status": "PASS",
            "process_modified": False,
        }
