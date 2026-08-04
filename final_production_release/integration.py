from __future__ import annotations
import importlib.util
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from final_production_release.io import write_json

MODULES=[
 ("web_controller","web_controller/server.py"),
 ("paper_web_ops","paper_web_ops/runner.py"),
 ("production_scheduler","production_scheduler/engine.py"),
 ("portfolio_broker","portfolio_broker/engine.py"),
 ("multi_broker_production","multi_broker_production/engine.py"),
 ("broker_plugins","broker_plugins/engine.py"),
 ("risk_engine_v2","risk_engine_v2/engine.py"),
 ("ai_strategy_ensemble","ai_strategy_ensemble/engine.py"),
]

def evaluate(root:Path)->dict[str,Any]:
    rows=[]
    for name,rel in MODULES:
        path=root/rel
        rows.append({
          "module":name,
          "path":rel,
          "present":path.exists(),
          "python_file":path.suffix==".py",
          "import_spec_available":importlib.util.spec_from_file_location(name,path) is not None if path.exists() else False,
        })
    required_files=[
      "RUN_V141_01_TO_V145_64_WEB_CONTROLLER.ps1",
      "RUN_V186_01_TO_V190_64.ps1",
      "RUN_V191_01_TO_V195_64.ps1",
      "RUN_V206_01_TO_V210_64.ps1",
      "RUN_V211_01_TO_V215_64.ps1",
      "release/v216_01_to_v220_64/rollback/RESTORE_TO_V215.ps1",
      "release/v216_01_to_v220_64/docs/FINAL_OPERATOR_GUIDE.md",
    ]
    file_rows=[{"path":rel,"present":(root/rel).exists()} for rel in required_files]
    result={
      "evaluated_at":datetime.now(timezone.utc).isoformat(),
      "modules":rows,
      "required_files":file_rows,
      "module_count":len(rows),
      "present_module_count":sum(1 for x in rows if x["present"]),
      "all_modules_present":all(x["present"] for x in rows),
      "all_required_files_present":all(x["present"] for x in file_rows),
    }
    write_json(root/"release/v216_01_to_v220_64/actual/final_integration_check.json",result)
    return result
