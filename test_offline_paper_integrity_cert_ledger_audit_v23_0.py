import ast
import copy
import json
import tempfile
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backtest.offline_paper_integrity_cert_ledger_audit_v23_0 import (
    CONFIRMATION_TEXT,
    OfflinePaperIntegrityCertLedgerAuditV230Policy,
    audit_offline_paper_integrity_certificate_ledger_v23_0,
    load_result,
    save_result,
    verify_integrity_certificate,
)
from backtest.offline_paper_integrity_cert_ledger_v22_9 import (
    ledger_snapshot_hash,
    sha256_payload,
)
from test_offline_paper_integrity_cert_ledger_v22_9 import (
    NOW as V22_9_NOW,
    create_source as create_v22_8_source,
    record as record_v22_9,
)


NOW = datetime(2026, 7, 30, 15, 30, tzinfo=timezone.utc)


def create_source():
    first = record_v22_9(create_v22_8_source(), now=V22_9_NOW)
    second_source = create_v22_8_source()
    return record_v22_9(
        second_source,
        existing=first.entries,
        now=V22_9_NOW + timedelta(minutes=3),
    )


def audit(source, operator="paper-auditor", text=CONFIRMATION_TEXT, policy=None, now=NOW):
    return audit_offline_paper_integrity_certificate_ledger_v23_0(
        source, operator=operator, confirmation_text=text, policy=policy, now=now
    )


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def rehash(entry):
    empty = replace(entry, entry_hash="")
    return replace(empty, entry_hash=sha256_payload(empty.payload_without_hash()))


def source_has_no_external_calls():
    path = Path(__file__).resolve().parent / "backtest" / (
        "offline_paper_integrity_cert_ledger_audit_v23_0.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_imports = {
        "requests", "httpx", "urllib", "socket", "aiohttp",
        "alpaca_trade_api", "ib_insync", "ccxt",
    }
    forbidden_calls = {
        "urlopen", "connect", "request", "get", "post",
        "submit_order", "place_order", "create_order", "send_order",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] in forbidden_imports for alias in node.names):
                return False
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in forbidden_imports:
                return False
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in forbidden_calls:
                return False
    return True


def main():
    source = create_source()
    before = copy.deepcopy(source.to_dict())
    source_snapshot = ledger_snapshot_hash(source.entries)
    result = audit(source)
    require(result.all_checks_passed, "V23.0 정상 감사 실패")
    require(source.to_dict() == before, "V22.9 Source 변경")
    valid_certificate, certificate_errors = verify_integrity_certificate(result.certificate)
    require(valid_certificate and not certificate_errors, "V23.0 Certificate Hash 실패")

    policy = OfflinePaperIntegrityCertLedgerAuditV230Policy()
    try:
        policy.network_access_disabled = False
        immutable = False
    except (FrozenInstanceError, AttributeError):
        immutable = True

    wrong_confirmation = audit(source, text="WRONG")
    empty_operator = audit(source, operator="")
    wrong_policy = audit(source, policy=replace(policy, broker_api_disabled=False))
    wrong_type = audit(object())
    backward = audit(
        source,
        now=datetime.fromisoformat(source.entries[-1].recorded_at) - timedelta(seconds=1),
    )

    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (
        replace(source.entries[0], operator="attacker"),
        source.entries[1],
    )
    tampered_ledger = audit(tampered_source)

    duplicate_source = copy.deepcopy(source)
    duplicate_second = rehash(replace(
        source.entries[1],
        source_integrity_certificate_id=source.entries[0].source_integrity_certificate_id,
    ))
    duplicate_source.entries = (source.entries[0], duplicate_second)
    duplicate_source.latest_ledger_entry_hash = duplicate_second.entry_hash
    duplicate = audit(duplicate_source)

    unsafe_source = copy.deepcopy(source)
    unsafe_first = rehash(replace(source.entries[0], network_accessed=True))
    unsafe_second = rehash(replace(source.entries[1], previous_entry_hash=unsafe_first.entry_hash))
    unsafe_source.entries = (unsafe_first, unsafe_second)
    unsafe_source.latest_ledger_entry_hash = unsafe_second.entry_hash
    unsafe = audit(unsafe_source)

    broken_link_source = copy.deepcopy(source)
    broken_first = rehash(replace(
        source.entries[0],
        source_integrity_certificate_hash="short",
    ))
    broken_second = rehash(replace(
        source.entries[1],
        previous_entry_hash=broken_first.entry_hash,
    ))
    broken_link_source.entries = (broken_first, broken_second)
    broken_link_source.latest_ledger_entry_hash = broken_second.entry_hash
    broken_link = audit(broken_link_source)

    tampered_certificate = replace(result.certificate, audit_status="FAILED")
    tampered_valid, _ = verify_integrity_certificate(tampered_certificate)

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_result(result, Path(directory))
        loaded = load_result(report)
        latest_loaded = json.loads(latest.read_text(encoding="utf-8"))
        save_load = (
            loaded["version"] == "V23.0"
            and latest_loaded["integrity_certificate_hash"]
            == result.integrity_certificate_hash
        )

    checks = {
        "Version is V23.0": result.version == "V23.0",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": immutable,
        "Invalid policies are blocked": not wrong_policy.all_checks_passed,
        "V22.9 ledger source passed": result.source_checks_passed,
        "Ledger hash chain passed": result.ledger_hash_chain_checks_passed,
        "Snapshot hash passed": result.source_ledger_snapshot_hash == source_snapshot,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Source linkage check passed": result.source_linkage_checks_passed,
        "Entry safety check passed": result.entry_safety_checks_passed,
        "V22.9 ledger remained unchanged": source.to_dict() == before,
        "Integrity certificate hash passed": valid_certificate,
        "Two entry findings passed": len(result.certificate.findings) == 2,
        "Wrong confirmation was blocked": not wrong_confirmation.all_checks_passed,
        "Empty operator was blocked": not empty_operator.all_checks_passed,
        "Wrong source type failed": not wrong_type.all_checks_passed,
        "Backward time was blocked": not backward.all_checks_passed,
        "Tampered ledger failed": not tampered_ledger.all_checks_passed,
        "Duplicate certificate was detected": not duplicate.all_checks_passed,
        "Unsafe ledger source failed": not unsafe.all_checks_passed,
        "Broken source linkage failed": not broken_link.all_checks_passed,
        "Certificate tampering detected": not tampered_valid,
        "Result save and load passed": save_load,
        "Ledger was not modified": not result.ledger_modified,
        "Funds were not reserved": not result.funds_reserved,
        "Holdings were not reserved": not result.holdings_reserved,
        "Market data API was not called": not result.market_data_api_called,
        "Account API was not called": not result.account_api_called,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Broker order was not created": not result.broker_order_created,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
        "External execution calls are absent": source_has_no_external_calls(),
        "All checks passed": result.all_checks_passed,
    }
    print("=" * 78)
    print("AI STOCK BOT V23.0 OFFLINE PAPER INTEGRITY CERTIFICATE LEDGER AUDIT TEST")
    print("=" * 78)
    print("V23.0 VALIDATION CHECKS")
    print("-" * 78)
    for label, passed in checks.items():
        print(f"{label:<54} : {passed}")
    print("=" * 78)
    require(all(checks.values()), "V23.0 Validation Check 실패")
    print()
    print("V23.0 offline paper integrity certificate ledger audit test completed successfully.")
    print("V22.9 Ledger Chain, Snapshot Hash, Source Linkage 및 Integrity Certificate Hash가 검증되었습니다.")
    print("잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
