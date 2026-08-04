from __future__ import annotations
import zipfile
from pathlib import Path
from typing import Any

EXCLUDED={".git",".venv","__pycache__",".pytest_cache"}

def create_bundle(root: Path, output: Path) -> dict[str, Any]:
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():
        output.unlink()
    count=0
    with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.resolve()==output.resolve():
                continue
            rel=p.relative_to(root)
            if any(part in EXCLUDED for part in rel.parts):
                continue
            z.write(p,rel.as_posix())
            count+=1
    return {
        "created":output.exists(),
        "path":str(output),
        "file_count":count,
        "size_bytes":output.stat().st_size if output.exists() else 0,
    }
