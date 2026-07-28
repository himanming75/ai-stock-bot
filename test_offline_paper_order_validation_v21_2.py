import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_order_model_v21_1 import (
    sha256_payload as order_sha256_payload,
)
from backtest.offline_paper_order_validation_v21_2 import (
    OfflinePaperOrderValidationV212Policy,
    load_validation_result,
    save_validation_result,
    validate_offline_paper_order_v21_2,
    verify_validation_certificate,
)
from test_offline_paper_order_model_v21_1 import (
    create_account_source,
    create_order,
)


NOW = datetime(2026, 7, 29, 12, 32, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return create_order(create_account_source())


def validate(
    source: Any,
    operator: Any = "operator-001",
    text: Any = "VALIDATE OFFLINE PAPER ORDER DRAFT V21.2",
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        validate_offline_paper_order_v21_2,
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
        "V21.2 실행 안전장치가 해제되었습니다.",
    )


def rehash_order(order: Any, **changes: Any) -> Any:
    changed = replace(order, **changes, order_hash="")
    return replace(
        changed,
        order_hash=order_sha256_payload(changed.payload_without_hash()),
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    order_before = copy.deepcopy(source.order.to_dict())

    result = validate(source)
    require(
        result.result_status == "VALIDATED_IN_MEMORY",
        "Order Validation 실패",
    )
    require(result.order_validated, "Order Validated 표시 누락")
    require(
        result.validation_certificate_created,
        "Validation Certificate 생성 실패",
    )
    require(result.certificate is not None, "Certificate 누락")
    require(
        result.source_order_hash == source.order.order_hash,
        "V21.1 Order Hash 연결 오류",
    )
    require(
        result.source_account_hash == source.source_account_hash,
        "V21.0 Account Hash 연결 오류",
    )
    require(source.to_dict() == source_before, "V21.1 Source 변경 감지")
    require(source.order.to_dict() == order_before, "Order Draft 변경 감지")
    certificate_valid, certificate_errors = verify_validation_certificate(
        result.certificate
    )
    require(
        certificate_valid and not certificate_errors,
        "Certificate Hash 검증 실패",
    )
    require_safe(result)

    limit_source = create_order(
        create_account_source(),
        symbol="MSFT",
        order_type="LIMIT",
        quantity=2,
        reference_price=260.0,
        limit_price=250.0,
    )
    limit_result = validate(limit_source)
    require(
        limit_result.result_status == "VALIDATED_IN_MEMORY",
        "LIMIT Order Validation 실패",
    )
    require(
        limit_result.certificate.estimated_notional == 500.0,
        "LIMIT Notional Validation 오류",
    )

    wrong_text = validate(source, text="IGNORE")
    empty_operator = validate(source, operator="")
    wrong_operator = validate(source, operator="operator-999")
    backward = validate(
        source,
        now=datetime(2026, 7, 29, 12, 30, tzinfo=timezone.utc),
    )
    unsafe_policy = OfflinePaperOrderValidationV212Policy(
        broker_api_disabled=False
    )
    unsafe = validate(source, policy=unsafe_policy)
    wrong_source = validate(object())

    tampered_order_source = copy.deepcopy(source)
    tampered_order_source.order = replace(
        tampered_order_source.order,
        estimated_notional=999.0,
    )
    tampered_order = validate(tampered_order_source)

    broken_result_linkage_source = copy.deepcopy(source)
    broken_result_linkage_source.order_hash = "0" * 64
    broken_result_linkage = validate(broken_result_linkage_source)

    broken_account_linkage_source = copy.deepcopy(source)
    broken_account_linkage_source.order = rehash_order(
        broken_account_linkage_source.order,
        account_hash="f" * 64,
    )
    broken_account_linkage_source.order_hash = (
        broken_account_linkage_source.order.order_hash
    )
    broken_account_linkage = validate(broken_account_linkage_source)

    bad_notional_source = copy.deepcopy(source)
    bad_notional_source.order = rehash_order(
        bad_notional_source.order,
        estimated_notional=999.0,
    )
    bad_notional_source.order_hash = bad_notional_source.order.order_hash
    bad_notional_source.estimated_notional = 999.0
    bad_notional = validate(bad_notional_source)

    insufficient_resource_source = copy.deepcopy(source)
    insufficient_resource_source.order = rehash_order(
        insufficient_resource_source.order,
        cash_balance_snapshot=500.0,
    )
    insufficient_resource_source.order_hash = (
        insufficient_resource_source.order.order_hash
    )
    insufficient_resource = validate(insufficient_resource_source)

    unsafe_source = copy.deepcopy(source)
    unsafe_source.network_accessed = True
    unsafe_source_result = validate(unsafe_source)

    incomplete_source = copy.deepcopy(source)
    incomplete_source.order_draft_created = False
    incomplete_source_result = validate(incomplete_source)

    blocked_results = (
        wrong_text,
        empty_operator,
        wrong_operator,
        backward,
        unsafe,
    )
    for blocked in blocked_results:
        require(blocked.result_status == "BLOCKED", "위험 입력 미차단")
    failed_results = (
        wrong_source,
        tampered_order,
        broken_result_linkage,
        broken_account_linkage,
        bad_notional,
        insufficient_resource,
        unsafe_source_result,
        incomplete_source_result,
    )
    for failed in failed_results:
        require(failed.result_status == "FAILED", "위험 Source 미실패")

    changed_certificate = replace(
        result.certificate,
        estimated_notional=999.0,
    )
    changed_valid, changed_errors = verify_validation_certificate(
        changed_certificate
    )
    require(not changed_valid and changed_errors, "Certificate 변조 미탐지")

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_validation_result(
            result,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "Validation Result 저장 실패",
        )
        payload = load_validation_result(latest_path)
        require(payload["version"] == "V21.2", "저장 Version 오류")
        require(
            payload["certificate"]["certificate_status"]
            == "VALIDATED_IN_MEMORY",
            "저장 Certificate Status 오류",
        )

    for checked in (
        result,
        limit_result,
        *blocked_results,
        *failed_results,
    ):
        require_safe(checked)

    checks = {
        "Version is V21.2": result.version == "V21.2",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            OfflinePaperOrderValidationV212Policy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V21.1 order source passed": result.source_checks_passed,
        "V21.1 order hash passed": result.order_hash_checks_passed,
        "V21.0 account hash linkage passed": (
            result.account_linkage_checks_passed
        ),
        "Result and order linkage passed": (
            result.result_order_linkage_checks_passed
        ),
        "Estimated notional recalculation passed": (
            result.notional_checks_passed
        ),
        "Paper resource check passed": result.resource_checks_passed,
        "Chronology check passed": result.chronology_checks_passed,
        "V21.1 source remained unchanged": source.to_dict() == source_before,
        "Order draft remained unchanged": (
            source.order.to_dict() == order_before
        ),
        "Validation certificate was created": (
            result.validation_certificate_created
        ),
        "Certificate SHA-256 hash passed": certificate_valid,
        "Market order validation passed": result.order_validated,
        "Limit order validation passed": limit_result.order_validated,
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
        "Wrong source type failed": wrong_source.result_status == "FAILED",
        "Tampered order failed": tampered_order.result_status == "FAILED",
        "Broken result linkage failed": (
            broken_result_linkage.result_status == "FAILED"
        ),
        "Broken account linkage failed": (
            broken_account_linkage.result_status == "FAILED"
        ),
        "Bad notional failed": bad_notional.result_status == "FAILED",
        "Insufficient paper resource failed": (
            insufficient_resource.result_status == "FAILED"
        ),
        "Unsafe source failed": (
            unsafe_source_result.result_status == "FAILED"
        ),
        "Incomplete source failed": (
            incomplete_source_result.result_status == "FAILED"
        ),
        "Certificate tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V21.2",
        "Funds were not reserved": not result.funds_reserved,
        "Holdings were not reserved": not result.holdings_reserved,
        "Market data API was not called": (
            not result.market_data_api_called
        ),
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
    print("AI STOCK BOT V21.2 OFFLINE PAPER ORDER VALIDATION TEST")
    print("=" * 108)
    print("V21.2 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V21.2 Validation Check 실패")
    print()
    print("V21.2 offline paper order validation test completed successfully.")
    print(
        "V21.1 주문·계좌 연결, 예상금액·가상자원 재검증 및 "
        "Validation Certificate SHA-256 Hash가 검증되었습니다."
    )
    print(
        "잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, "
        "실제 주문 및 Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
