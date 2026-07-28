import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_audit_cert_integrity_v21_6 import (
    OfflinePaperAuditCertIntegrityV216Policy,
    audit_offline_paper_audit_cert_ledger_v21_6,
    load_integrity_audit_result,
    save_integrity_audit_result,
    verify_integrity_audit_certificate,
)
from backtest.offline_paper_audit_cert_ledger_v21_5 import sha256_payload
from test_offline_paper_audit_cert_ledger_v21_5 import (
    NOW as V21_5_NOW,
    create_source as create_audit_source,
    record as record_v21_5,
)


NOW = datetime(2026, 7, 29, 12, 50, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    first = record_v21_5(create_audit_source())
    return record_v21_5(
        create_audit_source(),
        existing=first.entries,
        now=V21_5_NOW + timedelta(minutes=1),
    )


def audit(
    source: Any,
    operator: Any = "operator-001",
    text: Any = "AUDIT OFFLINE PAPER AUDIT CERTIFICATE LEDGER V21.5",
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        audit_offline_paper_audit_cert_ledger_v21_6,
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
        "V21.6 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = audit(source)
    require(result.result_status == "AUDITED_IN_MEMORY", "정상 Audit 실패")
    require(result.audit_status == "PASSED", "Audit Status 오류")
    require(result.audited_entry_count == 2, "Audit Entry 개수 오류")
    require(result.certificate is not None, "Audit Certificate 누락")
    require(source.to_dict() == source_before, "V21.5 Source 변경")
    require(not result.ledger_modified, "Ledger Modified 값 오류")
    require(
        all(
            finding.finding_status == "PASSED"
            for finding in result.certificate.findings
        ),
        "Entry Finding 실패",
    )
    require(
        result.latest_audit_certificate_hash
        == source.latest_audit_certificate_hash,
        "V21.4 Audit Certificate Hash 보존 실패",
    )
    require(
        result.latest_ledger_snapshot_hash
        == source.latest_ledger_snapshot_hash,
        "V21.3 Ledger Snapshot Hash 보존 실패",
    )
    require(
        result.latest_validation_certificate_hash
        == source.latest_validation_certificate_hash,
        "V21.2 Certificate Hash 보존 실패",
    )
    require(
        result.latest_order_hash == source.latest_order_hash,
        "V21.1 Order Hash 보존 실패",
    )
    require(
        result.latest_account_hash == source.latest_account_hash,
        "V21.0 Account Hash 보존 실패",
    )
    certificate_valid, certificate_errors = (
        verify_integrity_audit_certificate(result.certificate)
    )
    require(
        certificate_valid and not certificate_errors,
        "V21.6 Audit Certificate Hash 실패",
    )
    require_safe(result)

    wrong_text = audit(source, text="IGNORE")
    wrong_operator = audit(source, operator="operator-999")
    empty_operator = audit(source, operator="")
    unsafe_policy = OfflinePaperAuditCertIntegrityV216Policy(
        broker_api_disabled=False
    )
    unsafe = audit(source, policy=unsafe_policy)
    wrong_type = audit(object())
    backward = audit(
        source,
        now=datetime.fromisoformat(source.entries[-1].recorded_at)
        - timedelta(seconds=1),
    )

    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (
        replace(
            tampered_source.entries[0],
            ledger_snapshot_hash="e" * 64,
        ),
        tampered_source.entries[1],
    )
    tampered = audit(tampered_source)

    duplicate_source = copy.deepcopy(source)
    duplicate_entry = replace(
        duplicate_source.entries[1],
        audit_certificate_id=duplicate_source.entries[0].audit_certificate_id,
        entry_hash="",
    )
    duplicate_entry = replace(
        duplicate_entry,
        entry_hash=sha256_payload(duplicate_entry.payload_without_hash()),
    )
    duplicate_source.entries = (
        duplicate_source.entries[0],
        duplicate_entry,
    )
    duplicate_result = audit(duplicate_source)

    chronology_source = copy.deepcopy(source)
    chronology_entry = replace(
        chronology_source.entries[1],
        recorded_at=(
            datetime.fromisoformat(chronology_source.entries[0].recorded_at)
            - timedelta(seconds=1)
        ).isoformat(),
        entry_hash="",
    )
    chronology_entry = replace(
        chronology_entry,
        entry_hash=sha256_payload(chronology_entry.payload_without_hash()),
    )
    chronology_source.entries = (
        chronology_source.entries[0],
        chronology_entry,
    )
    chronology_result = audit(chronology_source)

    broken_linkage = copy.deepcopy(source)
    broken_linkage.latest_ledger_entry_hash = "f" * 64
    broken = audit(broken_linkage)

    unsafe_source = copy.deepcopy(source)
    unsafe_source.network_accessed = True
    unsafe_source_result = audit(unsafe_source)

    changed_certificate = replace(
        result.certificate,
        audit_certificate_ledger_snapshot_hash="a" * 64,
    )
    changed_valid, changed_errors = verify_integrity_audit_certificate(
        changed_certificate
    )

    for blocked in (
        wrong_text,
        wrong_operator,
        empty_operator,
        unsafe,
        backward,
        broken,
    ):
        require(blocked.result_status == "BLOCKED", "위험 입력 미차단")
    for failed in (
        wrong_type,
        tampered,
        duplicate_result,
        chronology_result,
        unsafe_source_result,
    ):
        require(failed.result_status == "FAILED", "위험 Source 미실패")
    require(
        not changed_valid and changed_errors,
        "Audit Certificate 변조 미탐지",
    )

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_integrity_audit_result(
            result, Path(directory)
        )
        require(report_path.exists() and latest_path.exists(), "저장 실패")
        payload = load_integrity_audit_result(latest_path)
        require(payload["version"] == "V21.6", "저장 Version 오류")
        require(payload["audited_entry_count"] == 2, "저장 Entry 개수 오류")

    for checked in (
        result,
        wrong_text,
        wrong_operator,
        empty_operator,
        unsafe,
        wrong_type,
        backward,
        tampered,
        duplicate_result,
        chronology_result,
        broken,
        unsafe_source_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V21.6": result.version == "V21.6",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            OfflinePaperAuditCertIntegrityV216Policy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V21.5 certificate ledger source passed": result.source_checks_passed,
        "Ledger hash chain passed": result.ledger_hash_chain_checks_passed,
        "Source linkage passed": result.source_linkage_checks_passed,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Audit status check passed": result.audit_status_checks_passed,
        "Entry safety check passed": result.entry_safety_checks_passed,
        "Ledger snapshot hash passed": result.snapshot_hash_checks_passed,
        "V21.5 ledger remained unchanged": source.to_dict() == source_before,
        "Audit certificate hash passed": certificate_valid,
        "Two entry findings passed": len(result.certificate.findings) == 2,
        "V21.4 audit certificate hash was preserved": (
            result.latest_audit_certificate_hash
            == source.latest_audit_certificate_hash
        ),
        "V21.3 ledger snapshot hash was preserved": (
            result.latest_ledger_snapshot_hash
            == source.latest_ledger_snapshot_hash
        ),
        "V21.2 certificate hash was preserved": (
            result.latest_validation_certificate_hash
            == source.latest_validation_certificate_hash
        ),
        "V21.1 order hash was preserved": (
            result.latest_order_hash == source.latest_order_hash
        ),
        "V21.0 account hash was preserved": (
            result.latest_account_hash == source.latest_account_hash
        ),
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Empty operator was blocked": empty_operator.result_status == "BLOCKED",
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered ledger failed": tampered.result_status == "FAILED",
        "Duplicate certificate tampering failed": (
            duplicate_result.result_status == "FAILED"
        ),
        "Ledger chronology tampering failed": (
            chronology_result.result_status == "FAILED"
        ),
        "Broken source linkage was blocked": broken.result_status == "BLOCKED",
        "Unsafe source failed": unsafe_source_result.result_status == "FAILED",
        "Certificate tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V21.6",
        "Funds were not reserved": not result.funds_reserved,
        "Holdings were not reserved": not result.holdings_reserved,
        "Market data API was not called": not result.market_data_api_called,
        "Account API was not called": not result.account_api_called,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Broker order was not created": not result.broker_order_created,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": (
            not result.live_execution_authorized
        ),
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 108)
    print(
        "AI STOCK BOT V21.6 OFFLINE PAPER AUDIT CERTIFICATE LEDGER "
        "INTEGRITY AUDIT TEST"
    )
    print("=" * 108)
    print("V21.6 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V21.6 Validation Check 실패")
    print()
    print(
        "V21.6 offline paper audit certificate ledger integrity audit "
        "test completed successfully."
    )
    print(
        "V21.5 Ledger Hash Chain, 연결 Hash, Entry Findings, 읽기 전용 "
        "Audit 및 V21.6 Certificate Hash가 검증되었습니다."
    )
    print(
        "잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
