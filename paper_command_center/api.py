from __future__ import annotations
from .commands import create_command_plan
from .config import CommandCenterPaths
from .status import build_status


class CommandCenterService:
    def __init__(
        self,
        *,
        paths: CommandCenterPaths,
    ) -> None:
        self.paths = paths

    def status(self) -> dict:
        return build_status(self.paths)

    def command_plan(
        self,
        *,
        action: str,
        requested_by: str,
        reason: str,
    ) -> dict:
        return create_command_plan(
            action=action,
            requested_by=requested_by,
            reason=reason,
            output_path=(
                self.paths.command_plan_output
            ),
            audit_path=self.paths.audit_ledger,
        )
