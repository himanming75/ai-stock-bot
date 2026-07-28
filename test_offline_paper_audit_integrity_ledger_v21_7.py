import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_audit_cert_ledger_v21_5 import sha256_payload
from backtest.offline_paper_audit_integrity_ledger_v21_7 import (
    OfflinePaperAuditIntegrityLedgerV217Policy,
    load_audit_integrity_ledger_result,
    record_offline_paper_audit_integrity_certificate_v21_7,
    save_audit_integrity_ledger_result,
    verify_audit_integrity_ledger_chain,
)
from test_offline_paper_audit_cert_integrity_v21_6 import (
    NOW as V21_6_NOW,
    audit as audit_v21_6,
    create_source as create_v21_5_source,
)


NOW = datetime(2026, 7, 29, 13, 10, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source(now: datetime = V21_6_NOW) -> Any:
    return audit_v21_6(create_v21_5_source(), now=now)


def record(
    source: Any,
    operator: Any = "operator-001",
    text: Any = "RECORD OFFLINE PAPER AUDIT CERTIFICATE INTEGRITY V21.7",
    existing: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        record_offline_paper_audit_integrity_certificate_v21_7,
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
        "V21.7 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source_one = create_source()
    source_before = copy.deepcopy(source_one.to_dict())
    first = record(source_one)
    require(first.result_status == "RECORDED_IN_MEMORY", "첫 Ledger 기록 실패")
    require(first.ledger_entry_recorded, "첫 Entry 기록 상태 오류")
    require(len(first.entries) == 1, "첫 Entry 개수 오류")
    require(source_one.to_dict() == source_before, "V21.6 Source 변경")

    source_two = create_source(V21_6_NOW + timedelta(minutes=1))
    second = record(
        source_two,
        existing=first.entries,
        now=NOW + timedelta(minutes=1),
    )
    require(second.result_status == "RECORDED_IN_MEMORY", "두 번째 기록 실패")
    require(len(second.entries) == 2, "두 번째 Entry 개수 오류")
    require(second.entries[0] == first.entries[0], "기존 Entry 변경")
    require(
        second.entries[1].previous_entry_hash == second.entries[0].entry_hash,
        "Ledger 연결 Hash 오류",
    )
    chain_valid, chain_errors = verify_audit_integrity_ledger_chain(
        second.entries
    )
    require(chain_valid and not chain_errors, "V21.7 Ledger Hash Chain 실패")
    require(
        second.latest_audit_certificate_hash
        == source_two.audit_certificate_hash,
        "V21.6 Certificate Hash 보존 실패",
    )
    require(
        second.latest_audit_certificate_ledger_snapshot_hash
        == source_two.audit_certificate_ledger_snapshot_hash,
        "V21.5 Ledger Snapshot Hash 보존 실패",
    )
    require(
        second.latest_v21_4_audit_certificate_hash
        == source_two.latest_audit_certificate_hash,
        "V21.4 Audit Certificate Hash 보존 실패",
    )
    require(
        second.latest_v21_3_ledger_snapshot_hash
        == source_two.latest_ledger_snapshot_hash,
        "V21.3 Ledger Snapshot Hash 보존 실패",
    )
    require(
        second.latest_v21_2_validation_certificate_hash
        == source_two.latest_validation_certificate_hash,
        "V21.2 Validation Certificate Hash 보존 실패",
    )
    require(
        second.latest_v21_1_order_hash == source_two.latest_order_hash,
        "V21.1 Order Hash 보존 실패",
    )
    require(
        second.latest_v21_0_account_hash == source_two.latest_account_hash,
        "V21.0 Account Hash 보존 실패",
    )
    require_safe(second)

    duplicate = record(
        source_two,
        existing=second.entries,
        now=NOW + timedelta(minutes=2),
    )
    wrong_text = record(source_one, text="IGNORE")
    empty_operator = record(source_one, operator="")
    wrong_operator_policy = OfflinePaperAuditIntegrityLedgerV217Policy(
        broker_api_disabled=False
    )
    unsafe_policy = record(source_one, policy=wrong_operator_policy)
    wrong_type = record(object())
    wrong_existing = record(source_one, existing={"bad": "ledger"})
    backward = record(
        source_one,
        now=datetime.fromisoformat(source_one.certificate.audited_at)
        - timedelta(seconds=1),
    )

    tampered_source = copy.deepcopy(source_one)
    tampered_source.certificate = replace(
        tampered_source.certificate,
        audit_certificate_ledger_snapshot_hash="a" * 64,
    )
    tampered_certificate = record(tampered_source)

    broken_linkage = copy.deepcopy(source_one)
    broken_linkage.audit_certificate_hash = "b" * 64
    broken_source_linkage = record(broken_linkage)

    unsafe_source = copy.deepcopy(source_one)
    unsafe_source.network_accessed = True
    unsafe_source_result = record(unsafe_source)

    tampered_existing_entry = replace(
        second.entries[0],
        latest_v21_1_order_hash="c" * 64,
    )
    tampered_existing = record(
        create_source(V21_6_NOW + timedelta(minutes=2)),
        existing=(tampered_existing_entry, second.entries[1]),
        now=NOW + timedelta(minutes=3),
    )

    duplicate_entry = replace(
        second.entries[1],
        audit_certificate_id=second.entries[0].audit_certificate_id,
        entry_hash="",
    )
    duplicate_entry = replace(
        duplicate_entry,
        entry_hash=sha256_payload(duplicate_entry.payload_without_hash()),
    )
    duplicate_ledger = record(
        create_source(V21_6_NOW + timedelta(minutes=2)),
        existing=(second.entries[0], duplicate_entry),
        now=NOW + timedelta(minutes=3),
    )

    chronology_entry = replace(
        second.entries[1],
        recorded_at=(
            datetime.fromisoformat(second.entries[0].recorded_at)
            - timedelta(seconds=1)
        ).isoformat(),
        entry_hash="",
    )
    chronology_entry = replace(
        chronology_entry,
        entry_hash=sha256_payload(chronology_entry.payload_without_hash()),
    )
    chronology_ledger = record(
        create_source(V21_6_NOW + timedelta(minutes=2)),
        existing=(second.entries[0], chronology_entry),
        now=NOW + timedelta(minutes=3),
    )

    for blocked in (
        duplicate,
        wrong_text,
        empty_operator,
        unsafe_policy,
        wrong_existing,
        backward,
        broken_source_linkage,
        tampered_existing,
        duplicate_ledger,
        chronology_ledger,
    ):
        require(blocked.result_status == "BLOCKED", "위험 입력 미차단")
    for failed in (wrong_type, tampered_certificate, unsafe_source_result):
        require(failed.result_status == "FAILED", "위험 Source 미실패")

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_audit_integrity_ledger_result(
            second, Path(directory)
        )
        require(report_path.exists() and latest_path.exists(), "저장 실패")
        payload = load_audit_integrity_ledger_result(latest_path)
        require(payload["version"] == "V21.7", "저장 Version 오류")
        require(payload["total_ledger_entry_count"] == 2, "저장 Entry 개수 오류")

    checked_results = (
        first,
        second,
        duplicate,
        wrong_text,
        empty_operator,
        unsafe_policy,
        wrong_type,
        wrong_existing,
        backward,
        tampered_certificate,
        broken_source_linkage,
        unsafe_source_result,
        tampered_existing,
        duplicate_ledger,
        chronology_ledger,
    )
    for checked in checked_results:
        require_safe(checked)

    checks = {
        "Version is V21.7": second.version == "V21.7",
        "Default policy is valid": second.policy_checks_passed,
        "Policy is immutable": (
            OfflinePaperAuditIntegrityLedgerV217Policy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe_policy.all_checks_passed,
        "V21.6 audit source passed": second.source_checks_passed,
        "Certificate hash passed": second.certificate_hash_checks_passed,
        "Source linkage passed": second.linkage_checks_passed,
        "First certificate was recorded": first.ledger_entry_recorded,
        "Second certificate was recorded": second.ledger_entry_recorded,
        "Two ledger entries were created": len(second.entries) == 2,
        "Sequences are chronological": second.chronology_checks_passed,
        "Ledger hash chain passed": chain_valid,
        "V21.6 certificate hash was preserved": (
            second.latest_audit_certificate_hash
            == source_two.audit_certificate_hash
        ),
        "V21.5 ledger snapshot hash was preserved": (
            second.latest_audit_certificate_ledger_snapshot_hash
            == source_two.audit_certificate_ledger_snapshot_hash
        ),
        "V21.4 audit certificate hash was preserved": (
            second.latest_v21_4_audit_certificate_hash
            == source_two.latest_audit_certificate_hash
        ),
        "V21.3 ledger snapshot hash was preserved": (
            second.latest_v21_3_ledger_snapshot_hash
            == source_two.latest_ledger_snapshot_hash
        ),
        "V21.2 validation certificate hash was preserved": (
            second.latest_v21_2_validation_certificate_hash
            == source_two.latest_validation_certificate_hash
        ),
        "V21.1 order hash was preserved": (
            second.latest_v21_1_order_hash == source_two.latest_order_hash
        ),
        "V21.0 account hash was preserved": (
            second.latest_v21_0_account_hash == source_two.latest_account_hash
        ),
        "Duplicate certificate was blocked": duplicate.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Empty operator was blocked": empty_operator.result_status == "BLOCKED",
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Wrong existing ledger was blocked": (
            wrong_existing.result_status == "BLOCKED"
        ),
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered certificate failed": (
            tampered_certificate.result_status == "FAILED"
        ),
        "Broken source linkage was blocked": (
            broken_source_linkage.result_status == "BLOCKED"
        ),
        "Unsafe source failed": unsafe_source_result.result_status == "FAILED",
        "Tampered existing ledger was blocked": (
            tampered_existing.result_status == "BLOCKED"
        ),
        "Duplicate ledger ID tampering was blocked": (
            duplicate_ledger.result_status == "BLOCKED"
        ),
        "Ledger chronology tampering was blocked": (
            chronology_ledger.result_status == "BLOCKED"
        ),
        "Result save and load passed": payload["version"] == "V21.7",
        "Funds were not reserved": not second.funds_reserved,
        "Holdings were not reserved": not second.holdings_reserved,
        "Market data API was not called": not second.market_data_api_called,
        "Account API was not called": not second.account_api_called,
        "Network was not accessed": not second.network_accessed,
        "Broker API was not called": not second.broker_api_called,
        "Broker order was not created": not second.broker_order_created,
        "Order was not submitted": not second.order_submitted,
        "Live execution not authorized": not second.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 108)
    print(
        "AI STOCK BOT V21.7 OFFLINE PAPER AUDIT CERTIFICATE "
        "INTEGRITY AUDIT LEDGER TEST"
    )
    print("=" * 108)
    print("V21.7 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V21.7 Validation Check 실패")
    print()
    print(
        "V21.7 offline paper audit certificate integrity audit ledger "
        "test completed successfully."
    )
    print(
        "V21.6 Certificate Hash, V21.5 Ledger Snapshot Hash, Ledger Sequence "
        "및 SHA-256 Hash Chain이 검증되었습니다."
    )
    print(
        "잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
