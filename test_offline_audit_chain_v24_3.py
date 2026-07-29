"""Executable validation checks for V24.3."""

from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta
from io import StringIO
import ast
from pathlib import Path
from tempfile import TemporaryDirectory

from backtest.offline_audit_chain_v24_3 import (
    VERSION,
    REQUIRED_CONFIRMATION,
    AuditChainV243Policy,
    build_offline_audit_chain_v24_3,
    load_chain_result,
    save_chain_result,
    verify_chain_certificate,
    verify_chain_entry,
    verify_chain_links,
)


with redirect_stdout(StringIO()):
    from test_offline_paper_audit_cert_verify_v24_2 import result as source_result


CHAIN_TIME = (
    datetime.fromisoformat(source_result.created_at) + timedelta(seconds=1)
).isoformat()


def blocked(callable_) -> bool:
    try:
        callable_()
    except (TypeError, ValueError, PermissionError):
        return True
    return False


result = build_offline_audit_chain_v24_3(
    (source_result,),
    operator="offline-chain-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    chain_time=CHAIN_TIME,
)

checks = {
    "Version is V24.3": result.version == VERSION,
    "Default policy is valid": result.policy == AuditChainV243Policy(),
    "Source contracts passed": result.source_contracts_verified,
    "Source certificate hashes passed": result.source_certificate_hashes_verified,
    "Source findings hashes passed": result.source_findings_hashes_verified,
    "Source identities passed": result.source_result_identities_verified,
    "Unique source check passed": result.unique_sources_verified,
    "Chronological order passed": result.chronological_order_verified,
    "Chain linkage passed": result.chain_linkage_verified,
    "Source safety passed": result.safety_verified,
    "Sources remained unchanged": result.sources_remained_unchanged,
    "One chain entry was created": len(result.entries) == 1,
    "Nine findings were created": len(result.findings) == 9,
    "Chain certificate created": result.certificate_created,
    "Chain verification completed": result.result_status == "AUDIT_CHAIN_VERIFIED",
    "Chain entry hash passed": verify_chain_entry(result.entries[0]),
    "Complete chain passed": verify_chain_links(result.entries),
    "Output certificate hash passed": result.certificate is not None
    and verify_chain_certificate(result.certificate),
    "Wrong confirmation was blocked": blocked(
        lambda: build_offline_audit_chain_v24_3(
            (source_result,),
            operator="offline-chain-auditor",
            confirmation="WRONG",
            chain_time=CHAIN_TIME,
        )
    ),
    "Empty operator was blocked": blocked(
        lambda: build_offline_audit_chain_v24_3(
            (source_result,),
            operator="",
            confirmation=REQUIRED_CONFIRMATION,
            chain_time=CHAIN_TIME,
        )
    ),
    "Wrong source container was blocked": blocked(
        lambda: build_offline_audit_chain_v24_3(
            [source_result],
            operator="offline-chain-auditor",
            confirmation=REQUIRED_CONFIRMATION,
            chain_time=CHAIN_TIME,
        )
    ),
    "Wrong source type was blocked": blocked(
        lambda: build_offline_audit_chain_v24_3(
            ({},),
            operator="offline-chain-auditor",
            confirmation=REQUIRED_CONFIRMATION,
            chain_time=CHAIN_TIME,
        )
    ),
    "Empty source tuple was blocked": blocked(
        lambda: build_offline_audit_chain_v24_3(
            (),
            operator="offline-chain-auditor",
            confirmation=REQUIRED_CONFIRMATION,
            chain_time=CHAIN_TIME,
        )
    ),
    "Backward chain time was blocked": blocked(
        lambda: build_offline_audit_chain_v24_3(
            (source_result,),
            operator="offline-chain-auditor",
            confirmation=REQUIRED_CONFIRMATION,
            chain_time="2000-01-01T00:00:00+00:00",
        )
    ),
    "Invalid policy was blocked": blocked(
        lambda: build_offline_audit_chain_v24_3(
            (source_result,),
            operator="offline-chain-auditor",
            confirmation=REQUIRED_CONFIRMATION,
            chain_time=CHAIN_TIME,
            policy=replace(AuditChainV243Policy(), allow_network=True),
        )
    ),
}

replayed_result = build_offline_audit_chain_v24_3(
    (source_result, source_result),
    operator="offline-chain-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    chain_time=CHAIN_TIME,
)
checks["Duplicate/replayed source detected"] = not replayed_result.unique_sources_verified
checks["Replay prevented certificate creation"] = not replayed_result.certificate_created

unsafe_result = build_offline_audit_chain_v24_3(
    (replace(source_result, execution_blocked=False),),
    operator="offline-chain-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    chain_time=CHAIN_TIME,
)
checks["Unsafe source detected"] = not unsafe_result.safety_verified

identity_result = build_offline_audit_chain_v24_3(
    (replace(source_result, verification_result_id="0" * 64),),
    operator="offline-chain-auditor",
    confirmation=REQUIRED_CONFIRMATION,
    chain_time=CHAIN_TIME,
)
checks["Tampered source identity detected"] = (
    not identity_result.source_result_identities_verified
)

tampered_entry = replace(result.entries[0], source_result_hash="0" * 64)
checks["Tampered chain entry detected"] = not verify_chain_entry(tampered_entry)
checks["Broken chain detected"] = not verify_chain_links((tampered_entry,))

tampered_certificate = replace(result.certificate, operator="attacker")
checks["Output certificate tampering detected"] = not verify_chain_certificate(
    tampered_certificate
)

with TemporaryDirectory() as temp_dir:
    saved_path = Path(temp_dir) / "v24_3_result.json"
    save_chain_result(result, saved_path)
    loaded = load_chain_result(saved_path)
    checks["Result save and load passed"] = loaded == result

source_text = Path("backtest/offline_audit_chain_v24_3.py").read_text(
    encoding="utf-8"
)
tree = ast.parse(source_text)
forbidden_roots = {
    "requests",
    "urllib",
    "http",
    "socket",
    "websocket",
    "aiohttp",
    "alpaca",
    "ib_insync",
    "ccxt",
    "yfinance",
}
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])
checks["Forbidden network/broker imports are absent"] = not (
    imports & forbidden_roots
)

checks.update(
    {
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
    }
)
checks["All checks passed"] = all(checks.values())

print("=" * 78)
print("AI STOCK BOT V24.3 OFFLINE AUDIT CERTIFICATE HASH-CHAIN TEST")
print("=" * 78)
for name, passed in checks.items():
    print(f"{name:<50} : {passed}")
print("=" * 78)

if not checks["All checks passed"]:
    failed = [name for name, passed in checks.items() if not passed]
    raise AssertionError(f"V24.3 checks failed: {failed}")

print()
print("V24.3 offline audit certificate hash-chain test completed successfully.")
print("V24.2 contracts, hashes, identities, replay protection, and chain linkage were verified.")
print("Market/account/network/broker/order/live execution remained blocked.")
