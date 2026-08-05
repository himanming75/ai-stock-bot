from __future__ import annotations
from copy import deepcopy
CANONICAL_COMPONENTS={
"credential_and_endpoint_policy":{"module":"alpaca_paper_read.config","classification":"CANONICAL","write_capable":False},
"broker_read_adapter":{"module":"alpaca_paper_read.adapter","classification":"CANONICAL","write_capable":False},
"read_http_transport":{"module":"alpaca_paper_read.http_client","classification":"CANONICAL","write_capable":False},
"pre_execution_safety_gateway":{"module":"broker_safe_execution.gateway","classification":"CANONICAL","write_capable":False},
"order_lifecycle_and_fill_observation":{"module":"paper_execution_lifecycle.engine","classification":"CANONICAL","write_capable":False},
"portfolio_sync_and_recovery_planning":{"module":"portfolio_sync_recovery.engine","classification":"CANONICAL","write_capable":False},
"local_execution_authorization":{"module":"execution_authorization","classification":"CANONICAL","write_capable":False},
"local_paper_simulation":{"module":"paper_dispatch_engine","classification":"CANONICAL","write_capable":False},
"local_portfolio_accounting":{"module":"paper_portfolio","classification":"CANONICAL","write_capable":False},
"risk_governor":{"module":"autonomous_risk_governor","classification":"CANONICAL","write_capable":False},
"allocation_engine":{"module":"ai_risk_allocation.allocation_qualification","classification":"CANONICAL","write_capable":False},
}
COMPATIBILITY_COMPONENTS={
"paper_broker_adapter.boundary":{"classification":"COMPATIBILITY","canonical_role":"pre_execution_safety_gateway"},
"paper_broker":{"classification":"COMPATIBILITY","canonical_role":"broker_read_adapter"},
"live_broker_readonly":{"classification":"COMPATIBILITY","canonical_role":"broker_read_adapter"},
"broker_safe_execution.sync":{"classification":"COMPATIBILITY","canonical_role":"portfolio_sync_and_recovery_planning"},
}
DEPRECATED_COMPONENTS={
"direct_imports_of_legacy_broker_modules":{"classification":"DEPRECATED","replacement":"broker_integration.registry","deletion_planned":False},
"multiple_independent_state_roots":{"classification":"DEPRECATED","replacement":"broker_integration.paths.BrokerStatePaths","deletion_planned":False},
"unqualified_broker_write_entrypoints":{"classification":"DEPRECATED","replacement":"P2 canonical execution gateway","deletion_planned":False},
}
def canonical_component(role):
    if role not in CANONICAL_COMPONENTS: raise KeyError(f"UNKNOWN_CANONICAL_BROKER_ROLE:{role}")
    return deepcopy(CANONICAL_COMPONENTS[role])
def consolidation_manifest():
    return {"canonical":deepcopy(CANONICAL_COMPONENTS),"compatibility":deepcopy(COMPATIBILITY_COMPONENTS),"deprecated":deepcopy(DEPRECATED_COMPONENTS),"legacy_files_deleted":[],"broker_write_authorized":False}
