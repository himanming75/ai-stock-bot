"""Executable validation checks for V24.4."""

from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta
from io import StringIO
import ast
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_audit_trust_v24_4 import (
    VERSION, REQUIRED_CONFIRMATION, AuditTrustV244Policy,
    build_offline_audit_trust_v24_4, detect_trust_cycle,
    load_trust_result, save_trust_result, verify_root_anchor,
    verify_trust_certificate, verify_trust_lineage, verify_trust_node,
)

with redirect_stdout(StringIO()):
    from test_offline_audit_chain_v24_3 import result as source_result

TRUST_TIME = (datetime.fromisoformat(source_result.created_at) + timedelta(seconds=1)).isoformat()


def blocked(callable_) -> bool:
    try:
        callable_()
    except (TypeError, ValueError, PermissionError):
        return True
    return False


result = build_offline_audit_trust_v24_4(
    (source_result,), operator="offline-trust-auditor",
    confirmation=REQUIRED_CONFIRMATION, trust_time=TRUST_TIME,
)

checks = {
    "Version is V24.4": result.version == VERSION,
    "Default policy is valid": result.policy == AuditTrustV244Policy(),
    "Source contracts passed": result.source_contracts_verified,
    "Source certificates passed": result.source_certificates_verified,
    "Source chain links passed": result.source_chain_links_verified,
    "Unique source check passed": result.unique_sources_verified,
    "Root trust anchor passed": result.root_anchor_verified and verify_root_anchor(result.root_anchor),
    "Trust lineage passed": result.lineage_verified and verify_trust_lineage(result.root_anchor, result.nodes),
    "Cycle-free check passed": result.cycle_free_verified and not detect_trust_cycle(result.root_anchor, result.nodes),
    "Chain depth passed": result.chain_depth_verified,
    "Immutable history passed": result.immutable_history_verified,
    "Source safety passed": result.safety_verified,
    "Sources remained unchanged": result.sources_remained_unchanged,
    "Trust score is 100": result.trust_score == 100,
    "One trust node was created": len(result.nodes) == 1,
    "Eleven findings were created": len(result.findings) == 11,
    "Trust certificate created": result.certificate_created,
    "Trust verification completed": result.result_status == "AUDIT_TRUST_VERIFIED",
    "Trust node hash passed": verify_trust_node(result.nodes[0]),
    "Output certificate hash passed": result.certificate is not None and verify_trust_certificate(result.certificate),
    "Wrong confirmation was blocked": blocked(lambda: build_offline_audit_trust_v24_4((source_result,), operator="offline-trust-auditor", confirmation="WRONG", trust_time=TRUST_TIME)),
    "Empty operator was blocked": blocked(lambda: build_offline_audit_trust_v24_4((source_result,), operator="", confirmation=REQUIRED_CONFIRMATION, trust_time=TRUST_TIME)),
    "Wrong source container was blocked": blocked(lambda: build_offline_audit_trust_v24_4([source_result], operator="offline-trust-auditor", confirmation=REQUIRED_CONFIRMATION, trust_time=TRUST_TIME)),
    "Wrong source type was blocked": blocked(lambda: build_offline_audit_trust_v24_4(({},), operator="offline-trust-auditor", confirmation=REQUIRED_CONFIRMATION, trust_time=TRUST_TIME)),
    "Empty source tuple was blocked": blocked(lambda: build_offline_audit_trust_v24_4((), operator="offline-trust-auditor", confirmation=REQUIRED_CONFIRMATION, trust_time=TRUST_TIME)),
    "Backward trust time was blocked": blocked(lambda: build_offline_audit_trust_v24_4((source_result,), operator="offline-trust-auditor", confirmation=REQUIRED_CONFIRMATION, trust_time="2000-01-01T00:00:00+00:00")),
    "Invalid policy was blocked": blocked(lambda: build_offline_audit_trust_v24_4((source_result,), operator="offline-trust-auditor", confirmation=REQUIRED_CONFIRMATION, trust_time=TRUST_TIME, policy=replace(AuditTrustV244Policy(), allow_network=True))),
}

replayed = build_offline_audit_trust_v24_4((source_result, source_result), operator="offline-trust-auditor", confirmation=REQUIRED_CONFIRMATION, trust_time=TRUST_TIME)
checks["Duplicate/replayed source detected"] = not replayed.unique_sources_verified
checks["Replay prevented certificate creation"] = not replayed.certificate_created

unsafe = build_offline_audit_trust_v24_4((replace(source_result, execution_blocked=False),), operator="offline-trust-auditor", confirmation=REQUIRED_CONFIRMATION, trust_time=TRUST_TIME)
checks["Unsafe source detected"] = not unsafe.safety_verified

tampered_anchor = replace(result.root_anchor, operator="attacker")
checks["Root anchor tampering detected"] = not verify_root_anchor(tampered_anchor)

tampered_node = replace(result.nodes[0], source_result_hash="0" * 64)
checks["Trust node tampering detected"] = not verify_trust_node(tampered_node)
checks["Broken lineage detected"] = not verify_trust_lineage(result.root_anchor, (tampered_node,))

cycle_node = replace(result.nodes[0], parent_id=result.nodes[0].node_id)
checks["Trust cycle detected"] = detect_trust_cycle(result.root_anchor, (cycle_node,))

tampered_certificate = replace(result.certificate, operator="attacker")
checks["Output certificate tampering detected"] = not verify_trust_certificate(tampered_certificate)

with TemporaryDirectory() as temp_dir:
    saved_path = Path(temp_dir) / "v24_4_result.json"
    save_trust_result(result, saved_path)
    loaded = load_trust_result(saved_path)
    checks["Result save and load passed"] = loaded == result

source_text = Path("backtest/offline_audit_trust_v24_4.py").read_text(encoding="utf-8")
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
print("AI STOCK BOT V24.4 OFFLINE AUDIT TRUST-CHAIN TEST")
print("=" * 78)
for name, passed in checks.items():
    print(f"{name:<50} : {passed}")
print("=" * 78)
if not checks["All checks passed"]:
    failed = [name for name, passed in checks.items() if not passed]
    raise AssertionError(f"V24.4 checks failed: {failed}")
print()
print("V24.4 offline audit trust-chain test completed successfully.")
print("Root trust, lineage, cycle detection, immutable history, and replay protection were verified.")
print("Market/account/network/broker/order/live execution remained blocked.")
