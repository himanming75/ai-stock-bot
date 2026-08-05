from __future__ import annotations


def select_channels(
    severity: str,
    policy: dict,
) -> list[str]:
    configured = policy.get(
        "severity_channels", {}
    ).get(severity, ["LOCAL_LOG"])
    enabled = policy.get("channel_enabled", {})
    return [
        channel
        for channel in configured
        if enabled.get(channel, False)
    ]


def delivery_plan(
    event: dict,
    policy: dict,
) -> list[dict]:
    return [
        {
            "channel": channel,
            "enabled": True,
            "delivery_mode": "PREPARE_ONLY",
            "actual_send_performed": False,
            "configuration_required": (
                channel != "LOCAL_LOG"
            ),
        }
        for channel in select_channels(
            event["severity"], policy
        )
    ]
