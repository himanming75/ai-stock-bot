from __future__ import annotations


def risk_events(risk: dict) -> list[dict]:
    events = []
    for alert in risk.get("alerts", []):
        events.append(
            {
                "source": "RISK_MONITOR",
                "code": alert.get("code", "RISK_ALERT"),
                "severity": alert.get("severity", "WARNING"),
                "title": f"Risk alert: {alert.get('code', 'UNKNOWN')}",
                "body": (
                    f"Actual={alert.get('actual')} "
                    f"Limit={alert.get('limit')}"
                ),
                "context": {
                    "risk_level": risk.get("risk_level"),
                    "portfolio_risk_score": risk.get(
                        "portfolio_risk_score"
                    ),
                    "actual": alert.get("actual"),
                    "limit": alert.get("limit"),
                },
            }
        )
    if risk.get("risk_level") == "CRITICAL" and not events:
        events.append(
            {
                "source": "RISK_MONITOR",
                "code": "PORTFOLIO_RISK_CRITICAL",
                "severity": "CRITICAL",
                "title": "Portfolio risk is critical",
                "body": (
                    "The portfolio risk monitor reported CRITICAL."
                ),
                "context": {
                    "portfolio_risk_score": risk.get(
                        "portfolio_risk_score"
                    )
                },
            }
        )
    return events


def health_events(health: dict) -> list[dict]:
    events = []
    for code in health.get("critical_issues", []):
        events.append(
            {
                "source": "SYSTEM_HEALTH",
                "code": code,
                "severity": "CRITICAL",
                "title": f"System health critical: {code}",
                "body": (
                    f"Health score={health.get('health_score')} "
                    f"Status={health.get('status')}"
                ),
                "context": {
                    "health_score": health.get("health_score"),
                    "status": health.get("status"),
                },
            }
        )
    for code in health.get("warnings", []):
        events.append(
            {
                "source": "SYSTEM_HEALTH",
                "code": code,
                "severity": "WARNING",
                "title": f"System health warning: {code}",
                "body": (
                    f"Health score={health.get('health_score')} "
                    f"Status={health.get('status')}"
                ),
                "context": {
                    "health_score": health.get("health_score"),
                    "status": health.get("status"),
                },
            }
        )
    return events


def performance_events(performance: dict) -> list[dict]:
    events = []
    for warning in performance.get("warnings", []):
        events.append(
            {
                "source": "PERFORMANCE_ANALYTICS",
                "code": warning,
                "severity": "INFO",
                "title": f"Performance analytics: {warning}",
                "body": (
                    "Performance analytics completed with a "
                    "data-readiness notice."
                ),
                "context": {
                    "observation_count": performance.get(
                        "observation_count"
                    ),
                    "status": performance.get("status"),
                },
            }
        )
    return events


def controller_events(controller: dict) -> list[dict]:
    events = []
    status = controller.get("status")
    if status and status not in {"PASS", "PASS_WITH_WARNINGS"}:
        events.append(
            {
                "source": "CONTROLLER",
                "code": "CONTROLLER_NOT_PASS",
                "severity": "CRITICAL",
                "title": "Paper automation controller is not PASS",
                "body": f"Controller status={status}",
                "context": {
                    "status": status,
                    "stopped_reason": controller.get(
                        "stopped_reason"
                    ),
                },
            }
        )
    return events
