from __future__ import annotations
from copy import deepcopy
from decimal import Decimal
from typing import Any

from .models import AllocationDecision, OrderCandidate


class PortfolioExposureManager:
    def validate_candidate(
        self,
        *,
        candidate: OrderCandidate,
        runtime_snapshot: dict[str, Any],
        portfolio_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        risk = runtime_snapshot["risk_limits"]
        gross_limit = Decimal(str(risk["maximum_gross_exposure"]))
        symbol_limit = Decimal(str(risk["maximum_symbol_exposure"]))
        gross_used = Decimal(str(portfolio_snapshot.get("gross_exposure", "0")))
        symbol_used = Decimal(str(
            portfolio_snapshot.get("symbol_exposure", {}).get(
                candidate.symbol, "0"
            )
        ))

        projected_gross = gross_used + candidate.notional
        projected_symbol = symbol_used + candidate.notional
        checks = {
            "candidate_submit_flag_off": candidate.submit_allowed is False,
            "gross_exposure_within_limit": projected_gross <= gross_limit,
            "symbol_exposure_within_limit": projected_symbol <= symbol_limit,
            "symbol_allowed": candidate.symbol in runtime_snapshot.get(
                "allowed_symbols", []
            ),
            "order_type_allowed": candidate.order_type in runtime_snapshot.get(
                "allowed_order_types", []
            ),
            "notional_positive": candidate.notional > 0,
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
            "projected_gross_exposure": str(projected_gross),
            "projected_symbol_exposure": str(projected_symbol),
            "actual_portfolio_modified": False,
        }

    def preview_apply(
        self,
        *,
        candidate: OrderCandidate,
        portfolio_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        result = deepcopy(portfolio_snapshot)
        gross = Decimal(str(result.get("gross_exposure", "0")))
        symbols = dict(result.get("symbol_exposure", {}))
        symbol = Decimal(str(symbols.get(candidate.symbol, "0")))
        result["gross_exposure"] = str(gross + candidate.notional)
        symbols[candidate.symbol] = str(symbol + candidate.notional)
        result["symbol_exposure"] = symbols
        result["preview_only"] = True
        result["actual_portfolio_modified"] = False
        return result
