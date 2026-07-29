"""Executable validation checks for V24.5."""

from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta
from io import StringIO
import ast
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_audit_revocation_v24_5 import (
    VERSION,
    REQUIRED_CONFIRMATION,
    AuditRevocationV245Policy,
    RevocationRequestV245,
    build_offline_audit_revocation_v24_5,
    is_certificate_blocked,
    load_revocation_result,
    save_revocation_result,
    verify_revocation_certificate,
    verify_revocation_event,
    verify_revocation_links,
    verify_state_transitions,
)

with redirect_stdout(StringIO()):
    from test_offline_audit_trust_v24_4 import result as source_result

BASE_TIME = datetime.fromisoformat(source_result.created_at)
REQUEST_TIME = (BASE_TIME + timedelta(seconds=1)).isoformat()
EVALUATION_TIME = (BASE_TIME + timedelta(seconds=2)).isoformat()


def blocked(callable_) -> bool:
    try:
        callable_()
    except (TypeError, ValueError, PermissionError):
        return True
    return False


revoke_request = RevocationRequestV245(
    action="REVOKE",
    reason_code="OPERATOR_REQUEST",
    requested_at=REQUEST_TIME,
    operator="offline-revocation-auditor",
    note="Offline test revocation",
)

result = build_offline_audit_revocation_v24_5(
    source_result,
    (revoke_request,),
    operator="offline-revocation-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    evaluation_time=EVALUATION_TIME,
)

checks = {
    "Version is V24.5": result.version == VERSION,
    "Default policy is valid": result.policy == AuditRevocationV245Policy(),
    "Source contract passed": result.source_contract_verified,
    "Source root anchor passed": result.source_root_anchor_verified,
    "Source lineage passed": result.source_lineage_verified,
    "Source certificate passed": result.source_certificate_verified,
    "Request contracts passed": result.request_contracts_verified,
    "Reason codes passed": result.reason_codes_verified,
    "Event times passed": result.event_times_verified,
    "Unique event check passed": result.unique_events_verified,
    "Event links passed": result.event_links_verified,
    "State transitions passed": result.state_transitions_verified,
    "Revocation list passed": result.revocation_list_verified,
    "Source safety passed": result.safety_verified,
    "Source remained unchanged": result.source_remained_unchanged,
    "Certificate state is REVOKED": result.effective_certificate_state == "REVOKED",
    "Revoked certificate is blocked": is_certificate_blocked(result),
    "Revocation score is 100": result.revocation_score == 100,
    "One revocation event was created": len(result.events) == 1,
    "Thirteen findings were created": len(result.findings) == 13,
    "Revocation certificate created": result.certificate_created,
    "Revocation verification completed": result.result_status == "AUDIT_REVOCATION_VERIFIED",
    "Event hash passed": verify_revocation_event(result.events[0]),
    "Event chain passed": verify_revocation_links(result.events),
    "Transition verification passed": verify_state_transitions(result.events),
    "Output certificate hash passed": result.certificate is not None and verify_revocation_certificate(result.certificate),
    "Wrong confirmation was blocked": blocked(lambda: build_offline_audit_revocation_v24_5(source_result, (), operator="auditor", confirmation="WRONG", evaluation_time=EVALUATION_TIME)),
    "Empty operator was blocked": blocked(lambda: build_offline_audit_revocation_v24_5(source_result, (), operator="", confirmation=REQUIRED_CONFIRMATION, evaluation_time=EVALUATION_TIME)),
    "Wrong request container was blocked": blocked(lambda: build_offline_audit_revocation_v24_5(source_result, [], operator="auditor", confirmation=REQUIRED_CONFIRMATION, evaluation_time=EVALUATION_TIME)),
    "Wrong request type was blocked": blocked(lambda: build_offline_audit_revocation_v24_5(source_result, ({},), operator="auditor", confirmation=REQUIRED_CONFIRMATION, evaluation_time=EVALUATION_TIME)),
    "Backward evaluation time was blocked": blocked(lambda: build_offline_audit_revocation_v24_5(source_result, (), operator="auditor", confirmation=REQUIRED_CONFIRMATION, evaluation_time="2000-01-01T00:00:00+00:00")),
    "Invalid policy was blocked": blocked(lambda: build_offline_audit_revocation_v24_5(source_result, (), operator="auditor", confirmation=REQUIRED_CONFIRMATION, evaluation_time=EVALUATION_TIME, policy=replace(AuditRevocationV245Policy(), allow_network=True))),
}

reinstate_request = RevocationRequestV245(
    action="REINSTATE",
    reason_code="REINSTATEMENT_APPROVED",
    requested_at=(BASE_TIME + timedelta(seconds=2)).isoformat(),
    operator="offline-revocation-auditor",
    note="Approved offline reinstatement",
)
reinstate_result = build_offline_audit_revocation_v24_5(
    source_result,
    (revoke_request, reinstate_request),
    operator="offline-revocation-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    evaluation_time=(BASE_TIME + timedelta(seconds=3)).isoformat(),
)
checks["Reinstatement restored ACTIVE state"] = reinstate_result.effective_certificate_state == "ACTIVE"
checks["Reinstated certificate is not blocked"] = not is_certificate_blocked(reinstate_result)
checks["Reinstatement chain verified"] = reinstate_result.certificate_created

invalid_reinstate = build_offline_audit_revocation_v24_5(
    source_result,
    (reinstate_request,),
    operator="offline-revocation-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    evaluation_time=(BASE_TIME + timedelta(seconds=3)).isoformat(),
)
checks["Invalid direct reinstatement detected"] = not invalid_reinstate.state_transitions_verified
checks["Invalid transition prevented certificate"] = not invalid_reinstate.certificate_created

bad_reason = replace(revoke_request, reason_code="UNKNOWN_REASON")
bad_reason_result = build_offline_audit_revocation_v24_5(
    source_result,
    (bad_reason,),
    operator="offline-revocation-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    evaluation_time=EVALUATION_TIME,
)
checks["Unknown reason code detected"] = not bad_reason_result.reason_codes_verified
checks["Unknown reason prevented certificate"] = not bad_reason_result.certificate_created

tampered_event = replace(result.events[0], reason_code="KEY_COMPROMISE")
checks["Event tampering detected"] = not verify_revocation_event(tampered_event)
checks["Broken event chain detected"] = not verify_revocation_links((tampered_event,))

tampered_certificate = replace(result.certificate, operator="attacker")
checks["Output certificate tampering detected"] = not verify_revocation_certificate(tampered_certificate)

with TemporaryDirectory() as temp_dir:
    saved_path = Path(temp_dir) / "v24_5_result.json"
    save_revocation_result(result, saved_path)
    loaded = load_revocation_result(saved_path)
    checks["Result save and load passed"] = loaded == result

source_text = Path("backtest/offline_audit_revocation_v24_5.py").read_text(encoding="utf-8")
tree = ast.parse(source_text)
forbidden_roots = {
    "requests", "urllib", "http", "socket", "websocket", "aiohttp",
    "alpaca", "ib_insync", "ccxt", "yfinance",
}
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])
checks["Forbidden network/broker imports are absent"] = not (imports & forbidden_roots)

checks.update({
    "Market data API was not called": not result.market_data_api_called,
    "Account API was not called": not result.account_api_called,
    "Network was not accessed": not result.network_accessed,
    "Broker API was not called": not result.broker_api_called,
    "Broker order was not created": not result.broker_order_created,
    "Order was not submitted": not result.order_submitted,
    "Live execution not authorized": not result.live_execution_authorized,
    "Execution remains blocked": result.execution_blocked,
    "Funds were not reserved": not result.funds_reserved,
    "Holdings were not reserved": not result.holdings_reserved,
})
checks["All checks passed"] = all(checks.values())

print("=" * 78)
print("AI STOCK BOT V24.5 OFFLINE AUDIT CERTIFICATE REVOCATION TEST")
print("=" * 78)
for name, passed in checks.items():
    print(f"{name:<52} : {passed}")
print("=" * 78)
if not checks["All checks passed"]:
    failed = [name for name, passed in checks.items() if not passed]
    raise AssertionError(f"V24.5 checks failed: {failed}")
print()
print("V24.5 offline audit certificate revocation test completed successfully.")
print("Revocation, reinstatement, linked events, reason validation, and tamper detection were verified.")
print("Market/account/network/broker/order/live execution remained blocked.")
