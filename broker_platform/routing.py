from __future__ import annotations
from decimal import Decimal
import hashlib
import json
from typing import Any

from .adapters import BrokerAdapterRegistry
from .gates import evaluate_account_gate
from .models import AccountDefinition, RoutedOrderPreview


class MultiAccountRouter:
    def __init__(
        self,
        *,
        registry: BrokerAdapterRegistry,
    ) -> None:
        self.registry = registry

    @staticmethod
    def _route_id(value: dict[str, Any]) -> str:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
        return "r13-" + hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24]

    def route_candidate(
        self,
        *,
        root,
        candidate: dict[str, Any],
        accounts: list[AccountDefinition],
    ) -> dict[str, Any]:
        routes = []

        for account in accounts:
            blockers: list[str] = []
            validation = account.validate()
            if not validation["valid"]:
                blockers.extend(validation["failed"])
            if not account.enabled:
                blockers.append("ACCOUNT_DISABLED")
            if account.broker_mode != candidate.get("broker_mode"):
                blockers.append("BROKER_MODE_MISMATCH")

            adapter = self.registry.get(account.broker_id)
            capability_result = adapter.validate_offline_candidate(
                candidate
            )
            if not capability_result["valid"]:
                blockers.extend(capability_result["failed"])

            gate = evaluate_account_gate(
                root,
                broker_mode=account.broker_mode,
            )
            if not gate["routing_preview_allowed"]:
                blockers.extend(gate["failed"])

            requested = Decimal(str(candidate.get("notional", "0")))
            weighted = (
                requested * account.allocation_weight
            ).quantize(Decimal("0.01"))
            routed = min(weighted, account.maximum_account_notional)

            if routed <= 0:
                blockers.append("ROUTED_NOTIONAL_ZERO")

            route_allowed = not blockers
            if not route_allowed:
                routed = Decimal("0")

            raw = {
                "candidate_id": candidate.get("candidate_id"),
                "account_id": account.account_id,
                "broker_id": account.broker_id,
                "routed_notional": str(routed),
            }
            route = RoutedOrderPreview(
                route_id=self._route_id(raw),
                candidate_id=str(candidate.get("candidate_id", "")),
                account_id=account.account_id,
                broker_id=account.broker_id,
                broker_mode=account.broker_mode,
                symbol=str(candidate.get("symbol", "")),
                side=str(candidate.get("side", "")),
                order_type=str(candidate.get("order_type", "")),
                time_in_force=str(
                    candidate.get("time_in_force", "")
                ),
                requested_notional=requested,
                routed_notional=routed,
                route_allowed=route_allowed,
                submit_allowed=False,
                blockers=tuple(sorted(set(blockers))),
            )
            routes.append({
                **route.as_json(),
                "account_validation": validation,
                "adapter_validation": capability_result,
                "gate": gate,
            })

        return {
            "candidate_id": candidate.get("candidate_id"),
            "route_count": len(routes),
            "allowed_route_count": sum(
                1 for route in routes if route["route_allowed"]
            ),
            "routes": routes,
            "actual_broker_submission_allowed": False,
            "actual_network_used": False,
            "actual_write_used": False,
        }
