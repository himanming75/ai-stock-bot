"""Executable validation checks for V24.6."""

from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta
from io import StringIO
import ast
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_audit_validity_v24_6 import (
    VERSION,
    REQUIRED_CONFIRMATION,
    AuditValidityV246Policy,
    build_offline_audit_validity_v24_6,
    is_usage_allowed,
    load_validity_result,
    save_validity_result,
    verify_validity_certificate,
    verify_validity_event,
    verify_validity_links,
)

with redirect_stdout(StringIO()):
    from test_offline_audit_revocation_v24_5 import result as source_result

BASE_TIME = datetime.fromisoformat(source_result.created_at)
NOT_BEFORE = (BASE_TIME + timedelta(seconds=1)).isoformat()
EVALUATION_TIME = (BASE_TIME + timedelta(seconds=2)).isoformat()
NOT_AFTER = (BASE_TIME + timedelta(hours=1)).isoformat()


def blocked(callable_) -> bool:
    try:
        callable_()
    except (TypeError, ValueError, PermissionError):
        return True
    return False


result = build_offline_audit_validity_v24_6(
    source_result,
    operator="offline-validity-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    evaluation_time=EVALUATION_TIME,
    not_before=NOT_BEFORE,
    not_after=NOT_AFTER,
)

checks = {
    "Version is V24.6": result.version == VERSION,
    "Default policy is valid": result.policy == AuditValidityV246Policy(),
    "Source contract passed": result.source_contract_verified,
    "Source certificate passed": result.source_certificate_verified,
    "Source revocation links passed": result.source_revocation_links_verified,
    "Source state passed": result.source_state_verified,
    "Validity window passed": result.validity_window_verified,
    "Evaluation time passed": result.evaluation_time_verified,
    "Effective state passed": result.effective_state_verified,
    "Usage policy passed": result.usage_policy_verified,
    "Validity event hash passed": result.event_hash_verified,
    "Source safety passed": result.safety_verified,
    "Source remained unchanged": result.source_remained_unchanged,
    "Effective state is REVOKED": result.effective_state == "REVOKED",
    "Revoked source usage is denied": not result.usage_allowed,
    "Usage helper denies source": not is_usage_allowed(result),
    "Validity score is 100": result.validity_score == 100,
    "Eleven findings were created": len(result.findings) == 11,
    "One validity event was created": len(result.events) == 1,
    "Validity certificate created": result.certificate_created,
    "Validity verification completed": result.result_status == "AUDIT_VALIDITY_VERIFIED",
    "Event verification passed": verify_validity_event(result.events[0]),
    "Event chain verification passed": verify_validity_links(result.events),
    "Output certificate hash passed": result.certificate is not None and verify_validity_certificate(result.certificate),
    "Wrong confirmation was blocked": blocked(lambda: build_offline_audit_validity_v24_6(source_result, operator="auditor", confirmation="WRONG", evaluation_time=EVALUATION_TIME, not_before=NOT_BEFORE, not_after=NOT_AFTER)),
    "Empty operator was blocked": blocked(lambda: build_offline_audit_validity_v24_6(source_result, operator="", confirmation=REQUIRED_CONFIRMATION, evaluation_time=EVALUATION_TIME, not_before=NOT_BEFORE, not_after=NOT_AFTER)),
    "Backward evaluation was blocked": blocked(lambda: build_offline_audit_validity_v24_6(source_result, operator="auditor", confirmation=REQUIRED_CONFIRMATION, evaluation_time="2000-01-01T00:00:00+00:00", not_before=NOT_BEFORE, not_after=NOT_AFTER)),
    "Invalid policy was blocked": blocked(lambda: build_offline_audit_validity_v24_6(source_result, operator="auditor", confirmation=REQUIRED_CONFIRMATION, evaluation_time=EVALUATION_TIME, not_before=NOT_BEFORE, not_after=NOT_AFTER, policy=replace(AuditValidityV246Policy(), allow_network=True))),
}

# ACTIVE source is produced by V24.5 with no revocation events.
from backtest.offline_audit_revocation_v24_5 import build_offline_audit_revocation_v24_5, REQUIRED_CONFIRMATION as V245_CONFIRMATION
with redirect_stdout(StringIO()):
    from test_offline_audit_trust_v24_4 import result as trust_source
active_source = build_offline_audit_revocation_v24_5(
    trust_source,
    (),
    operator="offline-validity-auditor",
    confirmation=V245_CONFIRMATION,
    evaluation_time=(datetime.fromisoformat(trust_source.created_at) + timedelta(seconds=1)).isoformat(),
)
active_base = datetime.fromisoformat(active_source.created_at)
active_result = build_offline_audit_validity_v24_6(
    active_source,
    operator="offline-validity-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    evaluation_time=(active_base + timedelta(seconds=2)).isoformat(),
    not_before=(active_base + timedelta(seconds=1)).isoformat(),
    not_after=(active_base + timedelta(hours=1)).isoformat(),
)
checks["Active source remains ACTIVE"] = active_result.effective_state == "ACTIVE"
checks["Active source usage is allowed"] = is_usage_allowed(active_result)

expired_result = build_offline_audit_validity_v24_6(
    active_source,
    operator="offline-validity-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    evaluation_time=(active_base + timedelta(hours=2)).isoformat(),
    not_before=(active_base + timedelta(seconds=1)).isoformat(),
    not_after=(active_base + timedelta(hours=1)).isoformat(),
)
checks["Expired state detected"] = expired_result.effective_state == "EXPIRED"
checks["Expired usage is denied"] = not is_usage_allowed(expired_result)

future_result = build_offline_audit_validity_v24_6(
    active_source,
    operator="offline-validity-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    evaluation_time=(active_base + timedelta(seconds=2)).isoformat(),
    not_before=(active_base + timedelta(hours=1)).isoformat(),
    not_after=(active_base + timedelta(hours=2)).isoformat(),
)
checks["Not-yet-valid state detected"] = future_result.effective_state == "NOT_YET_VALID"
checks["Future usage is denied"] = not is_usage_allowed(future_result)

invalid_window = build_offline_audit_validity_v24_6(
    active_source,
    operator="offline-validity-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    evaluation_time=(active_base + timedelta(seconds=2)).isoformat(),
    not_before=(active_base + timedelta(hours=2)).isoformat(),
    not_after=(active_base + timedelta(hours=1)).isoformat(),
)
checks["Invalid window detected"] = not invalid_window.validity_window_verified
checks["Invalid window prevented certificate"] = not invalid_window.certificate_created

tampered_event = replace(result.events[0], effective_state="ACTIVE")
checks["Event tampering detected"] = not verify_validity_event(tampered_event)
checks["Broken validity chain detected"] = not verify_validity_links((tampered_event,))

tampered_certificate = replace(result.certificate, operator="attacker")
checks["Output certificate tampering detected"] = not verify_validity_certificate(tampered_certificate)

with TemporaryDirectory() as temp_dir:
    saved_path = Path(temp_dir) / "v24_6_result.json"
    save_validity_result(result, saved_path)
    loaded = load_validity_result(saved_path)
    checks["Result save and load passed"] = loaded == result

source_text = Path("backtest/offline_audit_validity_v24_6.py").read_text(encoding="utf-8")
tree = ast.parse(source_text)
forbidden_roots = {"requests", "urllib", "http", "socket", "websocket", "aiohttp", "alpaca", "ib_insync", "ccxt", "yfinance"}
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
print("AI STOCK BOT V24.6 OFFLINE AUDIT CERTIFICATE VALIDITY TEST")
print("=" * 78)
for name, passed in checks.items():
    print(f"{name:<52} : {passed}")
print("=" * 78)
if not checks["All checks passed"]:
    failed = [name for name, passed in checks.items() if not passed]
    raise AssertionError(f"V24.6 checks failed: {failed}")
print()
print("V24.6 offline audit certificate validity test completed successfully.")
print("Validity windows, expiry, not-yet-valid state, revocation state, and tamper detection were verified.")
print("Market/account/network/broker/order/live execution remained blocked.")
