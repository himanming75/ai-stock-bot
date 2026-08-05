from __future__ import annotations

import os
import shutil
from pathlib import Path


def disk_health(path: Path) -> dict:
    total, used, free = shutil.disk_usage(path)
    used_percent = (used / total * 100) if total else 0.0
    return {
        "path": str(path),
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "used_percent": used_percent,
    }


def repository_size(path: Path) -> dict:
    total = 0
    file_count = 0
    largest = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        try:
            size = item.stat().st_size
        except OSError:
            continue
        file_count += 1
        total += size
        largest.append((size, str(item.relative_to(path))))
    largest.sort(reverse=True)
    return {
        "file_count": file_count,
        "total_bytes": total,
        "largest_files": [
            {"path": name, "size_bytes": size}
            for size, name in largest[:20]
        ],
        "files_over_100mb": [
            {"path": name, "size_bytes": size}
            for size, name in largest
            if size > 100 * 1024 * 1024
        ][:20],
    }
