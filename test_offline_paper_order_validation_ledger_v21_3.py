import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_order_validation_ledger_v21_3 import (
    OfflinePaperOrderValidationLedgerV213Policy,
    load_validation_ledger_result,
    record_offline_paper_order_validation_v21_3,
    save_validation_ledger_result,
    verify_validation_ledger_chain,
)
from test_offline_paper_order_validation_v21_2 import (
    create_source as create_order_source,
    validate,
)


NOW = datetime(2026, 7, 29, 12, 35, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return validate(
        create_order_source(),
        now=datetime(2026, 7, 29, 12, 32, tzinfo=timezone.utc),
    )


def record(
    source: Any,
    operator: Any = "operator-001",
    text: Any = "RECORD OFFLINE PAPER ORDER VALIDATION V21.3",
    existing: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        record_offline_paper_order_validation_v21_3,
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
        "V21.3 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    first_source = create_source()
    first_source_before = copy.deepcopy(first_source.to_dict())
    first = record(first_source)
    require(first.result_status == "RECORDED_IN_MEMORY", "첫 기록 실패")
    require(first.total_ledger_entry_count == 1, "첫 Entry 개수 오류")
    require(
        first.entries[0].validation_certificate_hash
        == first_source.certificate_hash,
        "V21.2 Certificate Hash 보존 실패",
    )
    require(
        first.entries[0].source_order_hash == first_source.source_order_hash,
        "V21.1 Order Hash 보존 실패",
    )
    require(
        first.entries[0].source_account_hash
        == first_source.source_account_hash,
        "V21.0 Account Hash 보존 실패",
    )
    require(
        first_source.to_dict() == first_source_before,
        "V21.2 Source 변경 감지",
    )
    require_safe(first)

    second_source = create_source()
    second = record(
        second_source,
        existing=first.entries,
        now=NOW + timedelta(minutes=1),
    )
    require(
        second.result_status == "RECORDED_IN_MEMORY",
        "두 번째 기록 실패",
    )
    require(second.total_ledger_entry_count == 2, "두 Entry 생성 실패")
    require(
        [entry.sequence for entry in second.entries] == [1, 2],
        "Ledger Sequence 오류",
    )
    valid_chain, chain_errors = verify_validation_ledger_chain(second.entries)
    require(valid_chain and not chain_errors, "Validation Ledger Chain 실패")

    retention_policy = OfflinePaperOrderValidationLedgerV213Policy(
        maximum_ledger_entries=1
    )
    retained_first = record(first_source, policy=retention_policy)
    retained_second = record(
        create_source(),
        existing=retained_first.entries,
        policy=retention_policy,
        now=NOW + timedelta(minutes=1),
    )
    retained_valid, retained_errors = verify_validation_ledger_chain(
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
    wrong_operator = record(first_source, operator="operator-999")
    unsafe_policy = OfflinePaperOrderValidationLedgerV213Policy(
        broker_api_disabled=False
    )
    unsafe = record(first_source, policy=unsafe_policy)
    wrong_type = record(object())
    wrong_existing = record(first_source, existing={"invalid": True})
    backward = record(
        second_source,
        existing=first.entries,
        now=NOW - timedelta(minutes=4),
    )

    tampered_source = copy.deepcopy(first_source)
    tampered_source.certificate = replace(
        tampered_source.certificate,
        estimated_notional=999.0,
    )
    tampered = record(tampered_source)

    broken_linkage_source = copy.deepcopy(first_source)
    broken_linkage_source.certificate_hash = "f" * 64
    broken_linkage = record(broken_linkage_source)

    changed_entry = replace(
        second.entries[0],
        estimated_notional=999.0,
    )
    changed_entries = (changed_entry, second.entries[1])
    changed_valid, changed_errors = verify_validation_ledger_chain(
        changed_entries
    )
    require(
        not changed_valid and changed_errors,
        "Validation Ledger 변조 미탐지",
    )
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
        wrong_operator,
        unsafe,
        wrong_existing,
        backward,
        broken_linkage,
        tampered_existing,
    ):
        require(blocked.result_status == "BLOCKED", "위험 입력 미차단")
    for failed in (wrong_type, tampered, unsafe_source_result):
        require(failed.result_status == "FAILED", "위험 Source 미실패")

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_validation_ledger_result(
            second,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "Validation Ledger Result 저장 실패",
        )
        payload = load_validation_ledger_result(latest_path)
        require(payload["version"] == "V21.3", "저장 Version 오류")
        require(len(payload["entries"]) == 2, "저장 Entry 개수 오류")

    for checked in (
        first,
        second,
        retained_first,
        retained_second,
        duplicate,
        wrong_text,
        empty_operator,
        wrong_operator,
        unsafe,
        wrong_type,
        wrong_existing,
        backward,
        tampered,
        broken_linkage,
        tampered_existing,
        unsafe_source_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V21.3": second.version == "V21.3",
        "Default policy is valid": second.policy_checks_passed,
        "Policy is immutable": (
            OfflinePaperOrderValidationLedgerV213Policy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V21.2 validation source passed": second.source_checks_passed,
        "Certificate hash passed": second.certificate_hash_checks_passed,
        "Source linkage passed": second.linkage_checks_passed,
        "V21.2 source remained unchanged": (
            first_source.to_dict() == first_source_before
        ),
        "First validation was recorded": first.ledger_entry_recorded,
        "Second validation was recorded": second.ledger_entry_recorded,
        "Two ledger entries were created": (
            second.total_ledger_entry_count == 2
        ),
        "Sequences are chronological": (
            [entry.sequence for entry in second.entries] == [1, 2]
        ),
        "Validation ledger hash chain passed": valid_chain,
        "Retention limit rebuilt ledger chain": retained_valid,
        "V21.2 certificate hash was preserved": (
            first.entries[0].validation_certificate_hash
            == first_source.certificate_hash
        ),
        "V21.1 order hash was preserved": (
            first.entries[0].source_order_hash
            == first_source.source_order_hash
        ),
        "V21.0 account hash was preserved": (
            first.entries[0].source_account_hash
            == first_source.source_account_hash
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
        "Wrong operator was blocked": (
            wrong_operator.result_status == "BLOCKED"
        ),
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Wrong existing ledger was blocked": (
            wrong_existing.result_status == "BLOCKED"
        ),
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered certificate failed": tampered.result_status == "FAILED",
        "Broken source linkage was blocked": (
            broken_linkage.result_status == "BLOCKED"
        ),
        "Ledger tampering detected": not changed_valid,
        "Tampered existing ledger was blocked": (
            tampered_existing.result_status == "BLOCKED"
        ),
        "Unsafe source failed": (
            unsafe_source_result.result_status == "FAILED"
        ),
        "Result save and load passed": payload["version"] == "V21.3",
        "Funds were not reserved": not second.funds_reserved,
        "Holdings were not reserved": not second.holdings_reserved,
        "Market data API was not called": (
            not second.market_data_api_called
        ),
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
    print(
        "AI STOCK BOT V21.3 OFFLINE PAPER ORDER VALIDATION LEDGER TEST"
    )
    print("=" * 108)
    print("V21.3 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V21.3 Validation Check 실패")
    print()
    print(
        "V21.3 offline paper order validation ledger test completed successfully."
    )
    print(
        "V21.2 Certificate Hash, V21.1 Order Hash, V21.0 Account Hash 보존 및 "
        "SHA-256 Ledger Chain이 검증되었습니다."
    )
    print(
        "잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, 실제 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
