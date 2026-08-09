
from __future__ import annotations

from pathlib import Path
import argparse

TARGET = Path("dashboard/operations_dashboard_v3_2.py")

START_MARKER = "def git_state(root: Path):"
END_MARKER = "\n\ndef build_status(root: Path):"

NEW_BLOCK = r'''def discover_git_executable():
    import shutil

    found = shutil.which("git")
    if found:
        return found

    candidates = [
        Path(r"C:\Program Files\Git\cmd\git.exe"),
        Path(r"C:\Program Files\Git\bin\git.exe"),
        Path(r"C:\Program Files (x86)\Git\cmd\git.exe"),
        Path.home() / "AppData" / "Local" / "Programs" / "Git" / "cmd" / "git.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def git_state(root: Path):
    git_exe = discover_git_executable()

    if not git_exe:
        return {
            "branch": "UNKNOWN",
            "head_short": "",
            "origin_main_short": "",
            "synced": True,
            "available": False,
            "error": "GIT_EXECUTABLE_NOT_FOUND",
        }

    def run(*args):
        try:
            process = subprocess.run(
                [git_exe, *args],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
            return (process.stdout or "").strip()
        except Exception:
            return ""

    head = run("rev-parse", "HEAD")
    origin = run("rev-parse", "origin/main")
    branch = run("branch", "--show-current")

    return {
        "branch": branch or "UNKNOWN",
        "head_short": head[:8],
        "origin_main_short": origin[:8],
        "synced": True if not head or not origin else head == origin,
        "available": True,
        "error": None,
    }
'''

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\stock-bot")
    args = parser.parse_args()

    target = Path(args.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if "def discover_git_executable():" in text:
        print("V3.2.1 PATCH ALREADY PRESENT")
        return 0

    start = text.find(START_MARKER)
    if start < 0:
        raise RuntimeError("git_state start marker not found")

    end = text.find(END_MARKER, start)
    if end < 0:
        raise RuntimeError("build_status marker not found")

    repaired = text[:start] + NEW_BLOCK + text[end:]
    target.write_text(repaired, encoding="utf-8")

    print("V3.2.1 GIT DISCOVERY PATCH: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
