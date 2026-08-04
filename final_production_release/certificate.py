from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from final_production_release.io import write_json

def build(root:Path,inventory:dict[str,Any],integration:dict[str,Any],integrity:dict[str,Any],checks:dict[str,bool])->dict[str,Any]:
    final_ready=all(checks.values())
    certificate={
      "certificate_type":"AI_STOCK_BOT_V220_FINAL_PRODUCTION_CERTIFICATE",
      "issued_at":datetime.now(timezone.utc).isoformat(),
      "release_stage":"V220.64",
      "final_release_ready":final_ready,
      "development_integration_complete":final_ready,
      "paper_operations_supported":True,
      "live_trading_automatically_enabled":False,
      "manual_live_activation_required":True,
      "present_stage_count":inventory["present_stage_count"],
      "expected_stage_count":inventory["expected_stage_count"],
      "integration_modules_present":integration["present_module_count"],
      "integrity_all_present":integrity["all_present"],
      "broker_write_enabled":False,
      "live_submission_enabled":False,
      "automatic_order_submission_enabled":False,
      "actual_live_orders_submitted":inventory["total_actual_live_orders_submitted"],
      "checks":checks,
    }
    write_json(root/"release/v216_01_to_v220_64/actual/v220_final_certificate.json",certificate)
    return certificate
