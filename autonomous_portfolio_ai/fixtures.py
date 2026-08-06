from __future__ import annotations
from decimal import Decimal

from .models import PortfolioCandidate


D = Decimal


CANDIDATES = [
    PortfolioCandidate(
        symbol="NVDA",
        sector="TECH",
        action="BUY",
        confidence=D("0.92"),
        volatility=D("0.38"),
        correlation_group="MEGA_CAP_TECH",
        expected_return=D("0.18"),
        current_weight=D("0.08"),
    ),
    PortfolioCandidate(
        symbol="MSFT",
        sector="TECH",
        action="BUY",
        confidence=D("0.84"),
        volatility=D("0.22"),
        correlation_group="MEGA_CAP_TECH",
        expected_return=D("0.12"),
        current_weight=D("0.07"),
    ),
    PortfolioCandidate(
        symbol="JPM",
        sector="FINANCIALS",
        action="BUY",
        confidence=D("0.74"),
        volatility=D("0.18"),
        correlation_group="BANKS",
        expected_return=D("0.09"),
        current_weight=D("0.05"),
    ),
    PortfolioCandidate(
        symbol="XLE",
        sector="ENERGY",
        action="WAIT",
        confidence=D("0.60"),
        volatility=D("0.30"),
        correlation_group="ENERGY",
        expected_return=D("0.08"),
        current_weight=D("0.04"),
    ),
]
