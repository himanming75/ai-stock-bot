import ast
import contextlib
import copy
import io
import json
import tempfile
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backtest.offline_paper_integrity_cert_ledger_v22_9 import (
    CONFIRMATION_TEXT,
    OfflinePaperIntegrityCertLedgerV229Policy,
    load_result,
    record_offline_paper_integrity_certificate_v22_9,
    save_result,
    sha256_payload,
    verify_ledger_chain,
)
from test_offline_paper_audit_cert_integrity_v22_8 import (
    NOW as V22_8_NOW,
    audit as audit_v22_8,
    create_source as create_v22_7_source,
)


NOW = datetime(2026, 7, 30, 15, 0, tzinfo=timezone.utc)


def create_source(now=V22_8_NOW):
    return audit_v22_8(create_v22_7_source(), now=now)


def record(source, existing=None, operator="paper-auditor", text=CONFIRMATION_TEXT, policy=None, now=NOW):
    with contextlib.redirect_stdout(io.StringIO()):
        return record_offline_paper_integrity_certificate_v22_9(
            source, operator=operator, confirmation_text=text, existing=existing, policy=policy, now=now
        )


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def source_has_no_external_calls():
    path = Path(__file__).resolve().parent / "backtest" / "offline_paper_integrity_cert_ledger_v22_9.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_imports = {"requests", "httpx", "urllib", "socket", "aiohttp", "alpaca_trade_api", "ib_insync", "ccxt"}
    forbidden_calls = {"urlopen", "connect", "request", "get", "post", "submit_order", "place_order", "create_order", "send_order"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(x.name.split(".")[0] in forbidden_imports for x in node.names):
            return False
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in forbidden_imports:
            return False
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name in forbidden_calls:
                return False
    return True


def rehash(entry):
    empty = replace(entry, entry_hash="")
    return replace(empty, entry_hash=sha256_payload(empty.payload_without_hash()))


def main():
    first_source = create_source()
    before = copy.deepcopy(first_source.to_dict())
    first = record(first_source)
    second_source = create_source(V22_8_NOW + timedelta(minutes=5))
    second = record(second_source, existing=first.entries, now=NOW + timedelta(minutes=10))
    valid_chain, chain_errors = verify_ledger_chain(second.entries)
    require(first.result_status == "RECORDED_IN_MEMORY", "첫 Certificate 기록 실패")
    require(second.result_status == "RECORDED_IN_MEMORY", "두 번째 Certificate 기록 실패")
    require(valid_chain and not chain_errors, "V22.9 Hash Chain 실패")

    policy = OfflinePaperIntegrityCertLedgerV229Policy()
    try:
        policy.network_access_disabled = False
        immutable = False
    except (FrozenInstanceError, AttributeError):
        immutable = True

    wrong_policy = record(first_source, policy=replace(policy, broker_api_disabled=False))
    duplicate = record(first_source, existing=first.entries, now=NOW + timedelta(minutes=1))
    wrong_confirmation = record(first_source, text="WRONG")
    empty_operator = record(first_source, operator="")
    wrong_type = record(object())
    wrong_existing = record(first_source, existing={"bad": True})
    backward = record(second_source, existing=first.entries, now=NOW - timedelta(minutes=1))

    tampered_source = copy.deepcopy(first_source)
    tampered_source.certificate = replace(tampered_source.certificate, audit_status="FAILED")
    tampered_certificate = record(tampered_source)
    broken_linkage = copy.deepcopy(first_source)
    broken_linkage.integrity_certificate_hash = "f" * 64
    broken_source = record(broken_linkage)
    unsafe_source = copy.deepcopy(first_source)
    unsafe_source.network_accessed = True
    unsafe = record(unsafe_source)

    changed_first = replace(second.entries[0], operator="attacker")
    changed = (changed_first, second.entries[1])
    changed_valid, _ = verify_ledger_chain(changed)
    tampered_existing = record(
        create_source(V22_8_NOW + timedelta(minutes=10)),
        existing=changed,
        now=NOW + timedelta(minutes=20),
    )

    retention_policy = replace(policy, maximum_ledger_entries=1)
    retained = record(second_source, existing=first.entries, policy=retention_policy, now=NOW + timedelta(minutes=10))
    retained_valid, _ = verify_ledger_chain(retained.entries)

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_result(second, Path(directory))
        loaded = load_result(report)
        latest_loaded = json.loads(latest.read_text(encoding="utf-8"))
        save_load = loaded["version"] == "V22.9" and len(latest_loaded["entries"]) == 2

    checks = {
        "Version is V22.9": second.version == "V22.9",
        "Default policy is valid": second.policy_checks_passed,
        "Policy is immutable": immutable,
        "Invalid policies are blocked": not wrong_policy.all_checks_passed,
        "V22.8 audit source passed": second.source_checks_passed,
        "Integrity certificate hash passed": second.certificate_hash_checks_passed,
        "Source linkage passed": second.linkage_checks_passed,
        "V22.8 source remained unchanged": first_source.to_dict() == before,
        "First certificate was recorded": first.ledger_entry_recorded,
        "Second certificate was recorded": second.ledger_entry_recorded,
        "Two ledger entries were created": len(second.entries) == 2,
        "Sequences are chronological": [x.sequence for x in second.entries] == [1, 2],
        "Integrity certificate ledger hash chain passed": valid_chain,
        "Integrity certificate hash was preserved": (
            first.entries[0].source_integrity_certificate_hash
            == first_source.integrity_certificate_hash
        ),
        "Source ledger snapshot hash was preserved": (
            first.entries[0].source_audit_certificate_ledger_snapshot_hash
            == first_source.source_ledger_snapshot_hash
        ),
        "Duplicate certificate was blocked": not duplicate.all_checks_passed,
        "Wrong confirmation was blocked": not wrong_confirmation.all_checks_passed,
        "Empty operator was blocked": not empty_operator.all_checks_passed,
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Wrong existing ledger was blocked": not wrong_existing.all_checks_passed,
        "Backward time was blocked": not backward.all_checks_passed,
        "Tampered certificate failed": tampered_certificate.result_status == "FAILED",
        "Broken source linkage was blocked": not broken_source.all_checks_passed,
        "Unsafe source failed": not unsafe.all_checks_passed,
        "Ledger tampering detected": not changed_valid,
        "Tampered existing ledger was blocked": not tampered_existing.all_checks_passed,
        "Retention limit rebuilt ledger chain": retained.records_trimmed == 1 and retained_valid,
        "Result save and load passed": save_load,
        "Ledger was not modified": not second.ledger_modified,
        "Funds were not reserved": not second.funds_reserved,
        "Holdings were not reserved": not second.holdings_reserved,
        "Market data API was not called": not second.market_data_api_called,
        "Account API was not called": not second.account_api_called,
        "Network was not accessed": not second.network_accessed,
        "Broker API was not called": not second.broker_api_called,
        "Broker order was not created": not second.broker_order_created,
        "Order was not submitted": not second.order_submitted,
        "Live execution not authorized": not second.live_execution_authorized,
        "External execution calls are absent": source_has_no_external_calls(),
        "All checks passed": second.all_checks_passed,
    }
    print("=" * 82)
    print("AI STOCK BOT V22.9 OFFLINE PAPER INTEGRITY CERTIFICATE LEDGER TEST")
    print("=" * 82)
    print("V22.9 VALIDATION CHECKS")
    print("-" * 82)
    for label, passed in checks.items():
        print(f"{label:<58} : {passed}")
    print("=" * 82)
    require(all(checks.values()), "V22.9 Validation Check 실패")
    print()
    print("V22.9 offline paper integrity certificate ledger test completed successfully.")
    print("V22.8 Integrity Certificate Hash, Source Ledger Snapshot Hash 및 SHA-256 Ledger Chain이 검증되었습니다.")
    print("잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
