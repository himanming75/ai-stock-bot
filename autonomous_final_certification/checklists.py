from __future__ import annotations
from .models import ReadinessCheck, ValidationGate


def platform_readiness_checks() -> list[ReadinessCheck]:
    return [
        ReadinessCheck(
            "MARKET_DATA_PIPELINE",
            "PASS",
            True,
            "Historical and polling modules present",
            "RUN_INTRADAY_LIVE_READ_VALIDATION",
        ),
        ReadinessCheck(
            "AI_ENGINE",
            "PASS",
            True,
            "AI engine structural certification complete",
            "VALIDATE_WITH_FRESH_MARKET_DATA",
        ),
        ReadinessCheck(
            "MULTI_AI_VOTING",
            "PASS",
            True,
            "Weighted voting and veto certification complete",
            "VALIDATE_INTRADAY_CONSISTENCY",
        ),
        ReadinessCheck(
            "PORTFOLIO_AI",
            "PASS",
            True,
            "Target allocation and risk limits certified",
            "VALIDATE_WITH_ACTUAL_ACCOUNT_SNAPSHOT",
        ),
        ReadinessCheck(
            "SELF_LEARNING",
            "PASS",
            False,
            "Learning and explainability certification complete",
            "COLLECT_REAL_PAPER_OUTCOMES",
        ),
        ReadinessCheck(
            "OPERATIONS_HEALTH",
            "PASS",
            True,
            "Dependency guard and emergency stop certified",
            "RUN_LONG_DURATION_TEST",
        ),
        ReadinessCheck(
            "ALPACA_PAPER_CONNECTION",
            "PENDING_INTRADAY_VALIDATION",
            True,
            "Code ready; market-hours validation pending",
            "RUN_WHEN_MARKET_OPEN",
        ),
        ReadinessCheck(
            "ETRADE_CONNECTION",
            "BLOCKED_BY_KEY_ISSUANCE",
            False,
            "Read-only code ready; Consumer Key unavailable",
            "OBTAIN_SANDBOX_CONSUMER_KEY",
        ),
        ReadinessCheck(
            "BROKER_WRITE",
            "DISABLED",
            True,
            "Write routes disabled",
            "KEEP_DISABLED",
        ),
        ReadinessCheck(
            "ORDER_SUBMISSION",
            "DISABLED",
            True,
            "No executable order path enabled",
            "KEEP_DISABLED",
        ),
    ]


def validation_gates() -> list[ValidationGate]:
    return [
        ValidationGate(
            "PAPER_INTRADAY_DATA_FRESHNESS",
            "PENDING",
            True,
            True,
            "Requires open market",
        ),
        ValidationGate(
            "PAPER_MULTI_CYCLE_STABILITY",
            "PENDING",
            True,
            True,
            "Requires long-running market session",
        ),
        ValidationGate(
            "PAPER_END_OF_DAY_SHUTDOWN",
            "PENDING",
            True,
            True,
            "Requires market close observation",
        ),
        ValidationGate(
            "ETRADE_SANDBOX_READ",
            "BLOCKED",
            False,
            True,
            "Sandbox Consumer Key unavailable",
        ),
        ValidationGate(
            "ETRADE_PRODUCTION_READ_ONLY",
            "BLOCKED",
            False,
            True,
            "Production key and OAuth validation unavailable",
        ),
        ValidationGate(
            "LIVE_ORDER_ENABLEMENT",
            "BLOCKED",
            False,
            True,
            "Manual approval and separate future certification required",
        ),
    ]
