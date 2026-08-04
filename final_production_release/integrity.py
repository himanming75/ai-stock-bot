from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from final_production_release.io import write_json,sha256_file

TARGETS=[
 "V216_01_TO_V220_64_MANIFEST.json",
 "RUN_V216_01_TO_V220_64.ps1",
 "RUN_V216_01_TO_V220_64_TEST_AND_VERIFY.ps1",
 "INSTALL_AND_SAVE_V216_01_TO_V220_64_ONE_CLICK.ps1",
 "final_production_release/engine.py",
 "release/v216_01_to_v220_64/config/final_production_release_policy.json",
 "release/v216_01_to_v220_64/docs/FINAL_OPERATOR_GUIDE.md",
 "release/v216_01_to_v220_64/rollback/RESTORE_TO_V215.ps1",
]

def build(root:Path)->dict[str,Any]:
    rows=[]
    for rel in TARGETS:
        path=root/rel
        rows.append({
          "path":rel,"present":path.exists(),
          "size_bytes":path.stat().st_size if path.exists() else 0,
          "sha256":sha256_file(path) if path.exists() else None,
        })
    result={
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "file_count":sum(1 for x in rows if x["present"]),
      "all_present":all(x["present"] for x in rows),
      "files":rows,
    }
    write_json(root/"release/v216_01_to_v220_64/actual/final_integrity_manifest.json",result)
    return result
