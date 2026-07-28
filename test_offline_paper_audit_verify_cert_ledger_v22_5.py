import ast
import contextlib
import io
import json
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backtest.offline_paper_audit_verify_cert_ledger_v22_5 import (
    CONFIRMATION_TEXT,
    OfflinePaperAuditVerifyCertLedgerV225Policy,
    load_result,
    record_offline_paper_audit_verification_certificate_v22_5,
    save_result,
    verify_ledger_chain,
)
from test_offline_paper_verify_cert_audit_ledger_verify_v22_4 import (
    create_source as create_v22_3_source,
    verify as verify_v22_4,
)


NOW = datetime(2026, 7, 30, 12, 30, tzinfo=timezone.utc)


def silent(function, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source(now=NOW):
    return silent(verify_v22_4, create_v22_3_source(), now=now)


def record(source, entries=(), now=NOW, operator="paper-auditor", text=CONFIRMATION_TEXT):
    return record_offline_paper_audit_verification_certificate_v22_5(
        source,
        operator=operator,
        confirmation_text=text,
        existing_entries=entries,
        now=now,
    )


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def source_has_no_external_calls():
    source_path = (
        Path(__file__).resolve().parent
        / "backtest"
        / "offline_paper_audit_verify_cert_ledger_v22_5.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
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
    source_one = create_source(NOW)
    source_before = source_one.to_dict()
    first = record(source_one, now=NOW + timedelta(minutes=1))
    require(first.all_checks_passed, "첫 번째 V22.5 기록 실패")
    require(source_one.to_dict() == source_before, "V22.4 Source 변경")

    source_two = create_source(NOW + timedelta(minutes=2))
    second = record(
        source_two,
        entries=first.entries,
        now=NOW + timedelta(minutes=3),
    )
    chain_valid, chain_errors = verify_ledger_chain(second.entries)
    require(second.all_checks_passed, "두 번째 V22.5 기록 실패")
    require(chain_valid and not chain_errors, "V22.5 Ledger Hash Chain 실패")

    wrong_confirmation = record(source_two, text="WRONG")
    empty_operator = record(source_two, operator="")
    duplicate = record(
        source_one,
        entries=first.entries,
        now=NOW + timedelta(minutes=4),
    )
    backward = record(
        create_source(NOW + timedelta(minutes=5)),
        entries=second.entries,
        now=NOW,
    )
    wrong_policy = record_offline_paper_audit_verification_certificate_v22_5(
        source_two,
        operator="paper-auditor",
        confirmation_text=CONFIRMATION_TEXT,
        policy=replace(
            OfflinePaperAuditVerifyCertLedgerV225Policy(),
            network_access_disabled=False,
        ),
        now=NOW + timedelta(minutes=6),
    )
    tampered_source = replace(
        source_two,
        verification_certificate_hash="f" * 64,
        certificate=replace(source_two.certificate, certificate_hash="f" * 64),
    )
    unsafe_source = replace(source_two, network_accessed=True)
    tampered_entry = replace(first.entries[0], operator="attacker")
    tampered_ledger = record(
        create_source(NOW + timedelta(minutes=7)),
        entries=(tampered_entry,),
        now=NOW + timedelta(minutes=8),
    )

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_result(second, Path(directory))
        payload = load_result(report_path)
        latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
        save_load_passed = (
            payload["version"] == "V22.5"
            and payload["ledger_snapshot_hash"] == second.ledger_snapshot_hash
            and latest_payload["latest_ledger_entry_hash"] == second.latest_ledger_entry_hash
        )

    checks = {
        "Version is V22.5": second.version == "V22.5",
        "Default policy is valid": first.policy_checks_passed,
        "Policy is immutable": OfflinePaperAuditVerifyCertLedgerV225Policy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not wrong_policy.all_checks_passed,
        "V22.4 verification source passed": second.source_checks_passed,
        "Certificate hash passed": second.certificate_hash_checks_passed,
        "Source linkage passed": second.source_linkage_checks_passed,
        "First certificate was recorded": first.certificate_recorded,
        "Second certificate was recorded": second.certificate_recorded,
        "Two ledger entries were created": second.total_ledger_entry_count == 2,
        "Sequences are chronological": [entry.sequence for entry in second.entries] == [1, 2],
        "Ledger hash chain passed": chain_valid,
        "V22.4 certificate hash was preserved": (
            second.latest_source_verification_certificate_hash
            == source_two.verification_certificate_hash
        ),
        "V22.4 source remained unchanged": source_one.to_dict() == source_before,
        "Duplicate certificate was blocked": not duplicate.all_checks_passed,
        "Wrong confirmation was blocked": not wrong_confirmation.all_checks_passed,
        "Empty operator was blocked": not empty_operator.all_checks_passed,
        "Backward time was blocked": not backward.all_checks_passed,
        "Tampered source failed": not record(tampered_source).all_checks_passed,
        "Unsafe source failed": not record(unsafe_source).all_checks_passed,
        "Ledger tampering detected": not tampered_ledger.all_checks_passed,
        "Result save and load passed": save_load_passed,
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

    print("=" * 78)
    print("AI STOCK BOT V22.5 OFFLINE PAPER AUDIT VERIFICATION CERTIFICATE LEDGER TEST")
    print("=" * 78)
    print("V22.5 VALIDATION CHECKS")
    print("-" * 78)
    for label, passed in checks.items():
        print(f"{label:<52} : {passed}")
    print("=" * 78)
    require(all(checks.values()), "V22.5 Validation Check 실패")
    print()
    print("V22.5 offline paper audit verification certificate ledger test completed successfully.")
    print("V22.4 Certificate Hash, Ledger Sequence 및 SHA-256 Hash Chain이 검증되었습니다.")
    print("잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
