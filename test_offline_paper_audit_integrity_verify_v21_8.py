import contextlib
import copy
import io
import tempfile
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_audit_cert_ledger_v21_5 import sha256_payload
from backtest.offline_paper_audit_integrity_verify_v21_8 import (
    OfflinePaperAuditIntegrityVerifyV218Policy,
    ledger_snapshot_hash,
    load_audit_integrity_verification_result,
    save_audit_integrity_verification_result,
    verify_offline_paper_audit_integrity_ledger_v21_8,
    verify_verification_certificate,
)
from test_offline_paper_audit_integrity_ledger_v21_7 import (
    NOW as V21_7_NOW,
    create_source as create_v21_6_source,
    record as record_v21_7,
)
from test_offline_paper_audit_cert_integrity_v21_6 import (
    NOW as V21_6_NOW,
)


NOW = datetime(2026, 7, 29, 13, 20, tzinfo=timezone.utc)
CONFIRMATION = "VERIFY OFFLINE PAPER AUDIT INTEGRITY LEDGER V21.8"


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    first_source = create_v21_6_source()
    first = record_v21_7(first_source)
    second_source = create_v21_6_source(V21_6_NOW + timedelta(minutes=1))
    return record_v21_7(
        second_source,
        existing=first.entries,
        now=V21_7_NOW + timedelta(minutes=1),
    )


def verify(
    source: Any,
    operator: Any = "operator-001",
    text: Any = CONFIRMATION,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        verify_offline_paper_audit_integrity_ledger_v21_8,
        source,
        operator,
        text,
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
                not result.ledger_modified,
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
        "V21.8 실행 안전장치가 해제되었습니다.",
    )


def rehash(entry: Any) -> Any:
    entry = replace(entry, entry_hash="")
    return replace(
        entry,
        entry_hash=sha256_payload(entry.payload_without_hash()),
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = verify(source)

    require(result.version == "V21.8", "Version 오류")
    require(result.result_status == "VERIFIED_IN_MEMORY", "검증 상태 오류")
    require(result.verification_status == "PASSED", "Verification Status 오류")
    require(result.verification_completed, "Verification 완료 상태 오류")
    require(result.all_checks_passed, "전체 검증 실패")
    require(result.verified_entry_count == 2, "검증 Entry 개수 오류")
    require(len(result.certificate.findings) == 2, "Finding 개수 오류")
    require(
        all(item.finding_status == "PASSED" for item in result.certificate.findings),
        "Entry Finding 실패",
    )
    require(source.to_dict() == source_before, "V21.7 Source가 변경됨")
    require(
        result.audit_integrity_ledger_snapshot_hash
        == ledger_snapshot_hash(source.entries),
        "V21.7 Ledger Snapshot Hash 오류",
    )
    require(
        result.latest_ledger_entry_hash == source.latest_ledger_entry_hash,
        "V21.7 Latest Ledger Hash 보존 실패",
    )
    require(
        result.latest_audit_certificate_hash
        == source.latest_audit_certificate_hash,
        "V21.6 Audit Certificate Hash 보존 실패",
    )
    require(
        result.latest_audit_certificate_ledger_snapshot_hash
        == source.latest_audit_certificate_ledger_snapshot_hash,
        "V21.5 Ledger Snapshot Hash 보존 실패",
    )
    require(
        result.latest_v21_4_audit_certificate_hash
        == source.latest_v21_4_audit_certificate_hash,
        "V21.4 Audit Certificate Hash 보존 실패",
    )
    require(
        result.latest_v21_3_ledger_snapshot_hash
        == source.latest_v21_3_ledger_snapshot_hash,
        "V21.3 Ledger Snapshot Hash 보존 실패",
    )
    require(
        result.latest_v21_2_validation_certificate_hash
        == source.latest_v21_2_validation_certificate_hash,
        "V21.2 Validation Certificate Hash 보존 실패",
    )
    require(
        result.latest_v21_1_order_hash == source.latest_v21_1_order_hash,
        "V21.1 Order Hash 보존 실패",
    )
    require(
        result.latest_v21_0_account_hash == source.latest_v21_0_account_hash,
        "V21.0 Account Hash 보존 실패",
    )
    certificate_valid, certificate_errors = verify_verification_certificate(
        result.certificate
    )
    require(
        certificate_valid and not certificate_errors,
        "V21.8 Verification Certificate Hash 실패",
    )
    require_safe(result)

    policy = OfflinePaperAuditIntegrityVerifyV218Policy()
    try:
        policy.broker_api_disabled = False
        immutable = False
    except (FrozenInstanceError, AttributeError):
        immutable = True
    require(immutable, "V21.8 Policy가 immutable이 아닙니다.")

    wrong_text = verify(source, text="IGNORE")
    empty_operator = verify(source, operator="")
    wrong_operator = verify(source, operator="operator-999")
    unsafe_policy = verify(
        source,
        policy=OfflinePaperAuditIntegrityVerifyV218Policy(
            network_access_disabled=False
        ),
    )
    wrong_type = verify(object())
    backward = verify(
        source,
        now=datetime.fromisoformat(source.entries[-1].recorded_at)
        - timedelta(seconds=1),
    )

    tampered_entry = replace(
        source.entries[0],
        latest_v21_1_order_hash="a" * 64,
    )
    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (tampered_entry, source.entries[1])
    tampered_ledger = verify(tampered_source)

    duplicate_source = copy.deepcopy(source)
    duplicate_second = rehash(
        replace(
            source.entries[1],
            audit_certificate_id=source.entries[0].audit_certificate_id,
        )
    )
    duplicate_source.entries = (source.entries[0], duplicate_second)
    duplicate_source.latest_ledger_entry_hash = duplicate_second.entry_hash
    duplicate_ledger = verify(duplicate_source)

    chronology_source = copy.deepcopy(source)
    chronology_second = rehash(
        replace(
            source.entries[1],
            recorded_at=(
                datetime.fromisoformat(source.entries[0].recorded_at)
                - timedelta(seconds=1)
            ).isoformat(),
        )
    )
    chronology_source.entries = (source.entries[0], chronology_second)
    chronology_source.latest_ledger_entry_hash = chronology_second.entry_hash
    chronology_ledger = verify(chronology_source)

    broken_linkage = copy.deepcopy(source)
    broken_linkage.latest_audit_certificate_hash = "b" * 64
    broken_source_linkage = verify(broken_linkage)

    unsafe_source = copy.deepcopy(source)
    unsafe_source.network_accessed = True
    unsafe_source_result = verify(unsafe_source)

    failed_results = (
        wrong_text,
        empty_operator,
        wrong_operator,
        unsafe_policy,
        wrong_type,
        backward,
        tampered_ledger,
        duplicate_ledger,
        chronology_ledger,
        broken_source_linkage,
        unsafe_source_result,
    )
    require(
        all(item.result_status in {"BLOCKED", "FAILED"} for item in failed_results),
        "차단/실패 Case가 통과했습니다.",
    )
    for item in failed_results:
        require(not item.all_checks_passed, "실패 Case 전체 통과 오류")
        require(not item.verification_completed, "실패 Case 완료 상태 오류")
        require_safe(item)

    tampered_certificate = replace(
        result.certificate,
        audit_integrity_ledger_snapshot_hash="c" * 64,
    )
    tampered_valid, _ = verify_verification_certificate(tampered_certificate)
    require(not tampered_valid, "변조 Certificate가 검증되었습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_audit_integrity_verification_result(
            result,
            Path(directory),
        )
        require(report_path.exists(), "Report 저장 실패")
        require(latest_path.exists(), "Latest 저장 실패")
        loaded = load_audit_integrity_verification_result(latest_path)
        require(loaded["version"] == "V21.8", "저장 Version 오류")
        require(
            loaded["verification_status"] == "PASSED",
            "저장 Verification Status 오류",
        )
        require(
            loaded["certificate"]["certificate_hash"]
            == result.verification_certificate_hash,
            "저장 Certificate Hash 오류",
        )

    checks = {
        "Version is V21.8": result.version == "V21.8",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": immutable,
        "Invalid policies are blocked": unsafe_policy.result_status == "BLOCKED",
        "V21.7 ledger source passed": result.source_checks_passed,
        "Ledger hash chain passed": result.ledger_hash_chain_checks_passed,
        "Source linkage passed": result.source_linkage_checks_passed,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Audit status check passed": result.audit_status_checks_passed,
        "Entry safety check passed": result.entry_safety_checks_passed,
        "Ledger snapshot hash passed": result.snapshot_hash_checks_passed,
        "V21.7 ledger remained unchanged": result.ledger_unchanged_checks_passed,
        "Verification certificate hash passed": result.certificate_hash_checks_passed,
        "Two entry findings passed": len(result.certificate.findings) == 2,
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Wrong operator was blocked": wrong_operator.result_status == "FAILED",
        "Empty operator was blocked": empty_operator.result_status == "BLOCKED",
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered ledger failed": tampered_ledger.result_status == "FAILED",
        "Duplicate certificate was detected": duplicate_ledger.result_status == "FAILED",
        "Ledger chronology tampering detected": chronology_ledger.result_status == "FAILED",
        "Broken source linkage was blocked": broken_source_linkage.result_status == "FAILED",
        "Unsafe ledger source failed": unsafe_source_result.result_status == "FAILED",
        "Certificate tampering detected": not tampered_valid,
        "Result save and load passed": loaded["version"] == "V21.8",
        "Market data API was not called": not result.market_data_api_called,
        "Account was not accessed": not result.account_api_called,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Broker order was not created": not result.broker_order_created,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
        "All checks passed": result.all_checks_passed,
    }
    width = max(len(label) for label in checks)
    print("=" * 78)
    print("AI STOCK BOT V21.8 OFFLINE PAPER AUDIT INTEGRITY VERIFICATION TEST")
    print("=" * 78)
    print("V21.8 VALIDATION CHECKS")
    print("-" * 78)
    for label, passed in checks.items():
        print(f"{label:<{width}} : {passed}")
    print("=" * 78)
    require(all(checks.values()), "V21.8 표시 검증 중 실패가 있습니다.")
    print()
    print("V21.8 offline paper audit integrity verification test completed successfully.")
    print(
        "V21.7 Ledger Chain, Entry Findings, Snapshot Hash, 읽기 전용 검증 및 "
        "Verification Certificate Hash가 검증되었습니다."
    )
    print(
        "잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
