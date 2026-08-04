from __future__ import annotations
import zipfile
from pathlib import Path
from typing import Any

EXCLUDED = {
    ".git", ".venv", "__pycache__", ".pytest_cache",
    "V105_33_TO_V105_64_FINAL_RELEASE_BUNDLE.zip",
}

def create_bundle(
    root: Path,
    output_path: Path,
) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()
    files = []
    with zipfile.ZipFile(
        output_path,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if any(part in EXCLUDED for part in rel.parts):
                continue
            if path.resolve() == output_path.resolve():
                continue
            archive.write(path, rel.as_posix())
            files.append(rel.as_posix())
    return {
        "created": output_path.exists(),
        "path": str(output_path),
        "file_count": len(files),
        "size_bytes": output_path.stat().st_size if output_path.exists() else 0,
    }
