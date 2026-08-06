from __future__ import annotations
from .models import ModuleHealth


HEALTHY_MODULES = [
    ModuleHealth(
        "MARKET_DATA",
        "HEALTHY",
        0,
        "Fresh market snapshot available",
    ),
    ModuleHealth(
        "AI_BRAIN",
        "HEALTHY",
        0,
        "Decision engine ready",
    ),
    ModuleHealth(
        "MULTI_AI_VOTING",
        "HEALTHY",
        0,
        "Consensus ready",
    ),
    ModuleHealth(
        "RISK_ENGINE",
        "HEALTHY",
        0,
        "Risk budget normal",
    ),
    ModuleHealth(
        "PORTFOLIO_AI",
        "HEALTHY",
        0,
        "Target portfolio ready",
    ),
    ModuleHealth(
        "BROKER_ADAPTER",
        "DEGRADED",
        1,
        "Read-only adapter available",
    ),
    ModuleHealth(
        "SELF_LEARNING",
        "HEALTHY",
        0,
        "Learning report ready",
    ),
    ModuleHealth(
        "LEDGER",
        "HEALTHY",
        0,
        "Ledger writable",
    ),
]

CRITICAL_MODULES = [
    ModuleHealth(
        "MARKET_DATA",
        "CRITICAL",
        5,
        "Market data unavailable",
    ),
    *[
        item
        for item in HEALTHY_MODULES
        if item.name != "MARKET_DATA"
    ],
]

BLOCKED_MODULES = [
    item
    if item.name != "PORTFOLIO_AI"
    else ModuleHealth(
        "PORTFOLIO_AI",
        "UNHEALTHY",
        3,
        "Allocation failed validation",
    )
    for item in HEALTHY_MODULES
]
