from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Any


def validate_environment(root: Path) -> dict[str, Any]:
    version = sys.version_info
    checks = {
        "project_root_exists": root.exists(),
        "git_directory_exists": (root / ".git").exists(),
        "python_supported": version.major == 3 and version.minor >= 10,
        "release_directory_exists": (root / "release").exists(),
        "tools_directory_exists": (root / "tools").exists(),
        "dashboard_directory_exists": (root / "dashboard_v2").exists(),
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
    }
