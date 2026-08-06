from __future__ import annotations
from pathlib import Path


ALLOWED_LOG_SUFFIXES = {
    ".log",
    ".jsonl",
    ".txt",
}


def list_logs(
    root: Path,
    *,
    limit: int = 200,
) -> list[dict]:
    if not root.exists():
        return []
    items = []
    for path in root.rglob("*"):
        if (
            path.is_file()
            and path.suffix.lower()
            in ALLOWED_LOG_SUFFIXES
        ):
            stat = path.stat()
            items.append({
                "path": str(path),
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
            })
    items.sort(
        key=lambda item: item["modified_at"],
        reverse=True,
    )
    return items[:limit]


def tail_log(
    path: Path,
    *,
    lines: int = 100,
    max_bytes: int = 256_000,
) -> dict:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() not in ALLOWED_LOG_SUFFIXES:
        raise PermissionError("LOG_TYPE_NOT_ALLOWED")
    data = path.read_bytes()
    if len(data) > max_bytes:
        data = data[-max_bytes:]
    text = data.decode(
        "utf-8",
        errors="replace",
    )
    return {
        "path": str(path),
        "lines": text.splitlines()[-lines:],
        "truncated": path.stat().st_size > len(data),
    }
