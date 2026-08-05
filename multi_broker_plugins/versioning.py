from __future__ import annotations
from typing import Any


class StrategyVersionManager:
    def compare(
        self,
        *,
        current: dict[str, Any],
        candidate: dict[str, Any],
    ) -> dict[str, Any]:
        same_strategy = (
            current.get("strategy_id") == candidate.get("strategy_id")
        )
        changed = current.get("version") != candidate.get("version")
        return {
            "same_strategy": same_strategy,
            "version_changed": changed,
            "current_version": current.get("version"),
            "candidate_version": candidate.get("version"),
            "upgrade_preview_allowed": same_strategy and changed,
            "actual_upgrade_performed": False,
            "operator_approval_required": True,
        }


class StrategyHotSwapPreview:
    def preview(
        self,
        *,
        current_strategy: str,
        target_strategy: str,
        open_positions: int,
        open_orders: int,
    ) -> dict[str, Any]:
        blockers = []
        if open_positions > 0:
            blockers.append("OPEN_POSITIONS_PRESENT")
        if open_orders > 0:
            blockers.append("OPEN_ORDERS_PRESENT")
        if current_strategy == target_strategy:
            blockers.append("TARGET_EQUALS_CURRENT")

        return {
            "current_strategy": current_strategy,
            "target_strategy": target_strategy,
            "blockers": blockers,
            "hot_swap_preview_allowed": not blockers,
            "actual_hot_swap_performed": False,
            "actual_strategy_activation_performed": False,
            "operator_approval_required": True,
        }
