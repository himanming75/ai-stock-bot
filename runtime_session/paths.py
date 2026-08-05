from pathlib import Path


def actual_dir(root: Path) -> Path:
    return root / "release/r6_runtime_session_manager/actual"


def lock_path(root: Path) -> Path:
    return actual_dir(root) / "session.lock.json"


def active_session_path(root: Path) -> Path:
    return actual_dir(root) / "active_session.json"


def heartbeat_path(root: Path) -> Path:
    return actual_dir(root) / "heartbeat.json"


def checkpoint_path(root: Path) -> Path:
    return actual_dir(root) / "session_checkpoint.json"


def session_ledger_path(root: Path) -> Path:
    return actual_dir(root) / "session_ledger.jsonl"


def stop_marker_path(root: Path) -> Path:
    return actual_dir(root) / "stop_request.json"
