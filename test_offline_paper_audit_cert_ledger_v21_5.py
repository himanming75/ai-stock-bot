import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_audit_cert_ledger_v21_5 import (
    OfflinePaperAuditCertLedgerV215Policy,
    load_audit_cert_ledger_result,
    record_offline_paper_audit_certificate_v21_5,
    save_audit_cert_ledger_result,
    verify_audit_cert_ledger_chain,
)
from test_offline_paper_order_ledger_audit_v21_4 import (
    audit as audit_v21_4,
    create_source as create_ledger_source,
)


NOW = datetime(2026, 7, 29, 12, 45, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return audit_v21_4(create_ledger_source())


def record(
    source: Any,
    operator: Any = "operator-001",
    text: Any = "RECORD OFFLINE PAPER LEDGER AUDIT CERTIFICATE V21.5",
    existing: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        record_offline_paper_audit_certificate_v21_5,
        source,
        operator,
        text,
        existing,
        policy,
        now,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    require(
        all(
            (
                not result.funds_reserved,
                not result.holdings_reserved,
                not result.paper_order_execution_authorized,
                not result.automatic_execution_authorized,
                result.execution_blocked,
                not result.transmit,
                not result.credentials_used,
                not result.market_data_api_called,
                not result.account_api_called,
                not result.network_accessed,
                not result.broker_api_called,
                not result.broker_order_created,
                not result.order_submitted,
                not result.live_order_created,
                not result.live_execution_authorized,
            )
        ),
        "V21.5 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    first_source = create_source()
    first_source_before = copy.deepcopy(first_source.to_dict())
    first = record(first_source)
    require(first.result_status == "RECORDED_IN_MEMORY", "첫 기록 실패")
    require(first.total_ledger_entry_count == 1, "첫 Entry 개수 오류")
    require(
        first.entries[0].audit_certificate_hash
        == first_source.audit_certificate_hash,
        "V21.4 Audit Certificate Hash 보존 실패",
    )
    require(
        first.entries[0].ledger_snapshot_hash
        == first_source.ledger_snapshot_hash,
        "V21.3 Ledger Snapshot Hash 보존 실패",
    )
    require(
        first.entries[0].latest_validation_certificate_hash
        == first_source.latest_validation_certificate_hash,
        "V21.2 Certificate Hash 보존 실패",
    )
    require(
        first.entries[0].latest_order_hash
        == first_source.latest_order_hash,
        "V21.1 Order Hash 보존 실패",
    )
    require(
        first.entries[0].latest_account_hash
        == first_source.latest_account_hash,
        "V21.0 Account Hash 보존 실패",
    )
    require(
        first_source.to_dict() == first_source_before,
        "V21.4 Source 변경 감지",
    )
    require_safe(first)

    second_source = create_source()
    second = record(
        second_source,
        existing=first.entries,
        now=NOW + timedelta(minutes=1),
    )
    require(second.result_status == "RECORDED_IN_MEMORY", "두 번째 기록 실패")
    require(second.total_ledger_entry_count == 2, "두 Entry 생성 실패")
    valid_chain, chain_errors = verify_audit_cert_ledger_chain(second.entries)
    require(valid_chain and not chain_errors, "Audit Certificate Ledger Chain 실패")

    retention_policy = OfflinePaperAuditCertLedgerV215Policy(
        maximum_ledger_entries=1
    )
    retained_first = record(first_source, policy=retention_policy)
    retained_second = record(
        create_source(),
        existing=retained_first.entries,
        policy=retention_policy,
        now=NOW + timedelta(minutes=1),
    )
    retained_valid, retained_errors = verify_audit_cert_ledger_chain(
        retained_second.entries
    )
    require(
        retained_second.result_status == "RECORDED_IN_MEMORY"
        and retained_second.total_ledger_entry_count == 1
        and retained_second.records_trimmed == 1
        and retained_valid
        and not retained_errors,
        "Ledger 보관 한도 재구성 실패",
    )

    duplicate = record(
        first_source,
        existing=first.entries,
        now=NOW + timedelta(minutes=1),
    )
    wrong_text = record(first_source, text="IGNORE")
    empty_operator = record(first_source, operator="")
    unsafe_policy = OfflinePaperAuditCertLedgerV215Policy(
        broker_api_disabled=False
    )
    unsafe = record(first_source, policy=unsafe_policy)
    wrong_type = record(object())
    wrong_existing = record(first_source, existing={"invalid": True})
    backward = record(
        second_source,
        existing=first.entries,
        now=NOW - timedelta(minutes=10),
    )

    tampered_source = copy.deepcopy(first_source)
    tampered_source.certificate = replace(
        tampered_source.certificate,
        audit_status="FAILED",
    )
    tampered = record(tampered_source)

    broken_source = copy.deepcopy(first_source)
    broken_source.audit_certificate_hash = "f" * 64
    broken = record(broken_source)

    changed_entry = replace(
        second.entries[0],
        ledger_snapshot_hash="e" * 64,
    )
    changed_entries = (changed_entry, second.entries[1])
    changed_valid, changed_errors = verify_audit_cert_ledger_chain(
        changed_entries
    )
    require(not changed_valid and changed_errors, "Ledger 변조 미탐지")
    tampered_existing = record(
        create_source(),
        existing=changed_entries,
        now=NOW + timedelta(minutes=2),
    )

    unsafe_source = copy.deepcopy(first_source)
    unsafe_source.network_accessed = True
    unsafe_source_result = record(unsafe_source)

    for blocked in (
        duplicate,
        wrong_text,
        empty_operator,
        unsafe,
        wrong_existing,
        backward,
        broken,
        tampered_existing,
    ):
        require(blocked.result_status == "BLOCKED", "위험 입력 미차단")
    for failed in (wrong_type, tampered, unsafe_source_result):
        require(failed.result_status == "FAILED", "위험 Source 미실패")

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_audit_cert_ledger_result(
            second,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "Audit Certificate Ledger 저장 실패",
        )
        payload = load_audit_cert_ledger_result(latest_path)
        require(payload["version"] == "V21.5", "저장 Version 오류")
        require(len(payload["entries"]) == 2, "저장 Entry 개수 오류")

    for checked in (
        first,
        second,
        retained_first,
        retained_second,
        duplicate,
        wrong_text,
        empty_operator,
        unsafe,
        wrong_type,
        wrong_existing,
        backward,
        tampered,
        broken,
        tampered_existing,
        unsafe_source_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V21.5": second.version == "V21.5",
        "Default policy is valid": second.policy_checks_passed,
        "Policy is immutable": (
            OfflinePaperAuditCertLedgerV215Policy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V21.4 audit source passed": second.source_checks_passed,
        "Audit certificate hash passed": (
            second.certificate_hash_checks_passed
        ),
        "Source linkage passed": second.linkage_checks_passed,
        "V21.4 source remained unchanged": (
            first_source.to_dict() == first_source_before
        ),
        "First certificate was recorded": first.ledger_entry_recorded,
        "Second certificate was recorded": second.ledger_entry_recorded,
        "Two ledger entries were created": (
            second.total_ledger_entry_count == 2
        ),
        "Sequences are chronological": (
            [entry.sequence for entry in second.entries] == [1, 2]
        ),
        "Audit certificate ledger hash chain passed": valid_chain,
        "Retention limit rebuilt ledger chain": retained_valid,
        "V21.4 audit certificate hash was preserved": (
            first.entries[0].audit_certificate_hash
            == first_source.audit_certificate_hash
        ),
        "V21.3 ledger snapshot hash was preserved": (
            first.entries[0].ledger_snapshot_hash
            == first_source.ledger_snapshot_hash
        ),
        "V21.2 certificate hash was preserved": (
            first.entries[0].latest_validation_certificate_hash
            == first_source.latest_validation_certificate_hash
        ),
        "V21.1 order hash was preserved": (
            first.entries[0].latest_order_hash
            == first_source.latest_order_hash
        ),
        "V21.0 account hash was preserved": (
            first.entries[0].latest_account_hash
            == first_source.latest_account_hash
        ),
        "Duplicate certificate was blocked": (
            duplicate.result_status == "BLOCKED"
        ),
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Empty operator was blocked": (
            empty_operator.result_status == "BLOCKED"
        ),
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Wrong existing ledger was blocked": (
            wrong_existing.result_status == "BLOCKED"
        ),
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered certificate failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": broken.result_status == "BLOCKED",
        "Ledger tampering detected": not changed_valid,
        "Tampered existing ledger was blocked": (
            tampered_existing.result_status == "BLOCKED"
        ),
        "Unsafe source failed": unsafe_source_result.result_status == "FAILED",
        "Result save and load passed": payload["version"] == "V21.5",
        "Funds were not reserved": not second.funds_reserved,
        "Holdings were not reserved": not second.holdings_reserved,
        "Market data API was not called": not second.market_data_api_called,
        "Account API was not called": not second.account_api_called,
        "Network was not accessed": not second.network_accessed,
        "Broker API was not called": not second.broker_api_called,
        "Broker order was not created": not second.broker_order_created,
        "Order was not submitted": not second.order_submitted,
        "Live execution not authorized": (
            not second.live_execution_authorized
        ),
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 108)
    print("AI STOCK BOT V21.5 OFFLINE PAPER AUDIT CERTIFICATE LEDGER TEST")
    print("=" * 108)
    print("V21.5 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V21.5 Validation Check 실패")
    print()
    print(
        "V21.5 offline paper audit certificate ledger test completed successfully."
    )
    print(
        "V21.4 Audit Certificate Hash, V21.3 Ledger Snapshot Hash, V21.2 "
        "Certificate Hash, V21.1 Order Hash 및 V21.0 Account Hash가 보존되었습니다."
    )
    print(
        "잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
