import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_order_ledger_audit_v21_4 import (
    OfflinePaperOrderLedgerAuditV214Policy,
    audit_offline_paper_order_ledger_v21_4,
    load_ledger_audit_result,
    save_ledger_audit_result,
    verify_audit_certificate,
)
from test_offline_paper_order_validation_ledger_v21_3 import (
    create_source as create_validation_source,
    record,
)


NOW = datetime(2026, 7, 29, 12, 40, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    first = record(create_validation_source())
    return record(
        create_validation_source(),
        existing=first.entries,
        now=datetime(2026, 7, 29, 12, 36, tzinfo=timezone.utc),
    )


def audit(
    source: Any,
    operator: Any = "operator-001",
    text: Any = "AUDIT OFFLINE PAPER ORDER VALIDATION LEDGER V21.4",
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        audit_offline_paper_order_ledger_v21_4,
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
        "V21.4 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = audit(source)
    require(result.version == "V21.4", "V21.4 Version 오류")
    require(result.result_status == "AUDITED_IN_MEMORY", "Ledger 감사 실패")
    require(result.audit_completed, "Audit 완료 상태 오류")
    require(result.audited_entry_count == 2, "감사 Entry 개수 오류")
    require(not result.ledger_modified, "Ledger 변경 상태 오류")
    require(source.to_dict() == source_before, "V21.3 Source 변경 감지")
    require(result.certificate is not None, "Audit Certificate 미생성")
    certificate_valid, certificate_errors = verify_audit_certificate(
        result.certificate
    )
    require(
        certificate_valid and not certificate_errors,
        "Audit Certificate Hash 실패",
    )
    require(
        len(result.certificate.findings) == 2
        and all(
            finding.finding_status == "PASSED"
            for finding in result.certificate.findings
        ),
        "Entry Finding 실패",
    )
    latest = source.entries[-1]
    require(
        result.latest_validation_certificate_hash
        == latest.validation_certificate_hash,
        "V21.2 Certificate Hash 보존 실패",
    )
    require(
        result.latest_order_hash == latest.source_order_hash,
        "V21.1 Order Hash 보존 실패",
    )
    require(
        result.latest_account_hash == latest.source_account_hash,
        "V21.0 Account Hash 보존 실패",
    )
    require_safe(result)

    wrong_text = audit(source, text="IGNORE")
    empty_operator = audit(source, operator="")
    wrong_operator = audit(source, operator="operator-999")
    unsafe_policy = OfflinePaperOrderLedgerAuditV214Policy(
        network_access_disabled=False
    )
    unsafe = audit(source, policy=unsafe_policy)
    backward = audit(source, now=NOW - timedelta(minutes=10))
    wrong_type = audit(object())

    tampered_source = copy.deepcopy(source)
    tampered_source.entries = (
        replace(tampered_source.entries[0], estimated_notional=999.0),
        tampered_source.entries[1],
    )
    tampered = audit(tampered_source)

    broken_linkage_source = copy.deepcopy(source)
    broken_linkage_source.latest_ledger_entry_hash = "f" * 64
    broken_linkage = audit(broken_linkage_source)

    unsafe_source = copy.deepcopy(source)
    unsafe_source.network_accessed = True
    unsafe_source_result = audit(unsafe_source)

    tampered_certificate = replace(
        result.certificate,
        latest_order_hash="f" * 64,
    )
    tampered_certificate_valid, tampered_certificate_errors = (
        verify_audit_certificate(tampered_certificate)
    )

    for blocked in (
        wrong_text,
        empty_operator,
        wrong_operator,
        unsafe,
        backward,
        broken_linkage,
    ):
        require(blocked.result_status == "BLOCKED", "위험 입력 미차단")
    for failed in (wrong_type, tampered, unsafe_source_result):
        require(failed.result_status == "FAILED", "위험 Source 미실패")
    require(
        not tampered_certificate_valid and tampered_certificate_errors,
        "Audit Certificate 변조 미탐지",
    )

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_ledger_audit_result(
            result,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "Audit Result 저장 실패",
        )
        payload = load_ledger_audit_result(latest_path)
        require(payload["version"] == "V21.4", "저장 Version 오류")
        require(
            payload["certificate"]["audit_status"] == "PASSED",
            "저장 Certificate 오류",
        )

    for checked in (
        result,
        wrong_text,
        empty_operator,
        wrong_operator,
        unsafe,
        backward,
        wrong_type,
        tampered,
        broken_linkage,
        unsafe_source_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V21.4": result.version == "V21.4",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            OfflinePaperOrderLedgerAuditV214Policy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V21.3 ledger source passed": result.source_checks_passed,
        "Ledger hash chain passed": (
            result.ledger_hash_chain_checks_passed
        ),
        "Source linkage passed": result.source_linkage_checks_passed,
        "Duplicate check passed": result.duplicate_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "Entry safety check passed": result.entry_safety_checks_passed,
        "Ledger snapshot hash passed": result.snapshot_hash_checks_passed,
        "V21.3 ledger remained unchanged": source.to_dict() == source_before,
        "Audit certificate hash passed": certificate_valid,
        "Two entry findings passed": (
            len(result.certificate.findings) == 2
        ),
        "V21.2 certificate hash was preserved": (
            result.latest_validation_certificate_hash
            == latest.validation_certificate_hash
        ),
        "V21.1 order hash was preserved": (
            result.latest_order_hash == latest.source_order_hash
        ),
        "V21.0 account hash was preserved": (
            result.latest_account_hash == latest.source_account_hash
        ),
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Empty operator was blocked": (
            empty_operator.result_status == "BLOCKED"
        ),
        "Wrong operator was blocked": (
            wrong_operator.result_status == "BLOCKED"
        ),
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Tampered ledger failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": (
            broken_linkage.result_status == "BLOCKED"
        ),
        "Unsafe source failed": unsafe_source_result.result_status == "FAILED",
        "Certificate tampering detected": not tampered_certificate_valid,
        "Result save and load passed": payload["version"] == "V21.4",
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
    print("AI STOCK BOT V21.4 OFFLINE PAPER ORDER LEDGER AUDIT TEST")
    print("=" * 108)
    print("V21.4 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V21.4 Validation Check 실패")
    print()
    print(
        "V21.4 offline paper order ledger audit test completed successfully."
    )
    print(
        "V21.3 Ledger Chain, Entry Findings, Snapshot Hash, 읽기 전용 감사 및 "
        "Audit Certificate Hash가 검증되었습니다."
    )
    print(
        "잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
