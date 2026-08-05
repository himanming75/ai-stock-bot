from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IO_PATH = ROOT / "autonomous_risk_governor" / "io.py"

REQUIRED_FUNCTION = """
def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\\n") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\\n")
"""


def main() -> int:
    if not IO_PATH.exists():
        raise FileNotFoundError(f"Missing file: {IO_PATH}")

    content = IO_PATH.read_text(encoding="utf-8-sig")

    if "def append_jsonl(" not in content:
        if "from typing import Any" not in content:
            content = content.replace(
                "from pathlib import Path",
                "from pathlib import Path\nfrom typing import Any",
            )
        if "import json" not in content:
            content = "import json\n" + content

        content = content.rstrip() + "\n\n" + REQUIRED_FUNCTION.strip() + "\n"
        IO_PATH.write_text(content, encoding="utf-8", newline="\n")
        print("append_jsonl added to autonomous_risk_governor/io.py")
    else:
        print("append_jsonl already present; no code change required.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
