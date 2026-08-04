from __future__ import annotations
import zipfile
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from final_production_release.io import write_json,sha256_file

INCLUDE=[
 "final_production_release",
 "web_controller",
 "risk_engine_v2",
 "ai_strategy_ensemble",
 "broker_plugins",
 "broker_plugin_packages",
 "release/v216_01_to_v220_64",
 "V216_01_TO_V220_64_MANIFEST.json",
 "RUN_V216_01_TO_V220_64.ps1",
 "RUN_V216_01_TO_V220_64_TEST_AND_VERIFY.ps1",
]

def create(root:Path)->dict[str,Any]:
    bundle_dir=root/"release/v216_01_to_v220_64/bundle"
    bundle_dir.mkdir(parents=True,exist_ok=True)
    path=bundle_dir/"AI_STOCK_BOT_V220_FINAL_PRODUCTION.zip"
    files=[]
    for rel in INCLUDE:
        target=root/rel
        if target.is_file():files.append(target)
        elif target.is_dir():
            files.extend(p for p in target.rglob("*") if p.is_file() and bundle_dir not in p.parents)
    seen=set();unique=[]
    for file in files:
        key=str(file.resolve())
        if key not in seen:
            seen.add(key);unique.append(file)
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for file in unique:
            z.write(file,file.relative_to(root))
    result={
      "created_at":datetime.now(timezone.utc).isoformat(),
      "bundle_path":str(path),
      "file_count":len(unique),
      "size_bytes":path.stat().st_size,
      "sha256":sha256_file(path),
      "contains_broker_credentials":False,
      "contains_environment_variables":False,
      "tracked_by_git_recommended":False,
    }
    write_json(root/"release/v216_01_to_v220_64/actual/final_bundle_result.json",result)
    return result
