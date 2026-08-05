from __future__ import annotations
from pathlib import Path
import subprocess
from typing import Any


class RepositoryReleaseAuditor:
    def audit(self, root: Path) -> dict[str, Any]:
        required = [
            "broker_integration/actual_validation.py",
            "release/p1_actual_environment_qualification/actual/"
            "p1_actual_environment_certificate.json",
            "release/r16_to_r20_realtime_paper_ops/actual/"
            "r16_to_r20_result.json",
            "IMPORT_R3_CREDENTIAL_ENVIRONMENT.ps1",
        ]
        required_state = {
            item: (root / item).exists() for item in required
        }

        git_available = False
        branch = ""
        status_lines = []
        try:
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
            status_lines = subprocess.run(
                ["git", "status", "--short"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.splitlines()
            git_available = True
        except Exception:
            pass

        return {
            "stage": "REPOSITORY_RELEASE_AUDIT",
            "required_files": required_state,
            "required_files_present": all(required_state.values()),
            "git_available": git_available,
            "git_branch": branch,
            "working_tree_clean": git_available and not status_lines,
            "working_tree_change_count": len(status_lines),
            "working_tree_changes": status_lines[:100],
            "repository_modified": False,
        }
