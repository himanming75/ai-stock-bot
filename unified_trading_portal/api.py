from __future__ import annotations
from pathlib import Path

from .data import (
    build_detail,
    load_portal_snapshot,
    load_sync_result,
)


class UnifiedPortalDataService:
    def __init__(
        self,
        *,
        portal_path: Path,
        sync_result_path: Path,
    ) -> None:
        self.portal_path = portal_path
        self.sync_result_path = sync_result_path

    def dashboard(self) -> dict:
        portal = load_portal_snapshot(
            self.portal_path
        )
        sync = load_sync_result(
            self.sync_result_path
        )
        detail = build_detail(sync)
        return {
            **portal,
            "detail_counts": {
                "accounts": len(
                    detail["accounts"]
                ),
                "positions": len(
                    detail["positions"]
                ),
                "orders": len(
                    detail["orders"]
                ),
                "quotes": len(
                    detail["quotes"]
                ),
            },
        }

    def accounts(self) -> list[dict]:
        return build_detail(
            load_sync_result(
                self.sync_result_path
            )
        )["accounts"]

    def positions(self) -> list[dict]:
        return build_detail(
            load_sync_result(
                self.sync_result_path
            )
        )["positions"]

    def orders(self) -> list[dict]:
        return build_detail(
            load_sync_result(
                self.sync_result_path
            )
        )["orders"]

    def reconciliation(self) -> dict:
        detail = build_detail(
            load_sync_result(
                self.sync_result_path
            )
        )
        return {
            "issues": detail["issues"],
            "errors": detail["errors"],
            "sources": detail["sources"],
            "partial_success": detail[
                "partial_success"
            ],
        }
