import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from backtest.paper_broker_adapter_foundation import (
    PaperBrokerAdapterPolicy,
    build_paper_broker_adapter_package,
    load_paper_broker_adapter_result,
    save_paper_broker_adapter_result,
    verify_adapter_package,
)
from test_authorized_paper_run_execution_envelope import (
    VALID_ORDERS,
    create_authorization_source,
)
from backtest.authorized_paper_run_execution_envelope import (
    build_authorized_paper_run_execution_envelope,
)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    authorization = create_authorization_source()
    return silent(
        build_authorized_paper_run_execution_envelope,
        authorization,
        VALID_ORDERS,
        authorization.authorizations[-1].operator,
        "BUILD AUTHORIZED PAPER RUN ENVELOPE",
    )


def build(source: Any, operator: str | None = None, text: str | None = None, policy: Any = None) -> Any:
    actual_operator = operator
    if actual_operator is None:
        actual_operator = source.envelope.operator if source.envelope else "operator"
    return silent(
        build_paper_broker_adapter_package,
        source,
        actual_operator,
        text or "PREPARE PAPER BROKER ADAPTER",
        policy,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    require(not result.paper_execution_authorized, "Paper 실행 권한이 열렸습니다.")
    require(not result.automatic_execution_authorized, "자동 실행 권한이 열렸습니다.")
    require(result.execution_blocked, "Execution 차단이 해제되었습니다.")
    require(not result.network_accessed, "Network가 사용되었습니다.")
    require(not result.account_accessed, "계좌가 조회되었습니다.")
    require(not result.broker_api_called, "Broker API가 호출되었습니다.")
    require(not result.broker_order_created, "Broker Order가 생성되었습니다.")
    require(not result.order_submitted, "주문이 제출되었습니다.")
    require(not result.live_order_created, "Live Order가 생성되었습니다.")
    require(not result.live_execution_authorized, "Live 실행이 허용되었습니다.")


def main() -> None:
    source = create_source()
    prepared = build(source)
    require(prepared.version == "V13.0", "Version이 V13.0이 아닙니다.")
    require(prepared.result_status == "PREPARED", "정상 Package가 준비되지 않았습니다.")
    require(prepared.all_checks_passed, "정상 검사가 실패했습니다.")
    require(prepared.ticket_count == 2, "두 개 Ticket이 생성되지 않았습니다.")
    require(prepared.adapter_package is not None, "Adapter Package가 없습니다.")
    require(
        all(not ticket.transmit for ticket in prepared.adapter_package.tickets),
        "Transmit이 False가 아닙니다.",
    )
    valid, errors = verify_adapter_package(prepared.adapter_package)
    require(valid and not errors, "Package Hash 검사가 실패했습니다.")
    require_safe(prepared)

    wrong_operator = build(source, operator="wrong-operator")
    require(wrong_operator.result_status == "FAILED", "잘못된 Operator가 차단되지 않았습니다.")
    require_safe(wrong_operator)

    wrong_text = build(source, text="CONNECT BROKER")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    require_safe(wrong_text)

    unsafe_policy = PaperBrokerAdapterPolicy(broker_api_disabled=False)
    unsafe = build(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험한 Policy가 차단되지 않았습니다.")
    require_safe(unsafe)

    tampered_source = copy.deepcopy(source)
    require(tampered_source.envelope is not None, "변조 테스트 Source가 없습니다.")
    object.__setattr__(tampered_source.envelope, "operator", "tampered")
    tampered = build(tampered_source, operator="tampered")
    require(tampered.result_status == "FAILED", "Source 변조가 실패 처리되지 않았습니다.")
    require_safe(tampered)

    duplicate_envelope = replace(
        source.envelope,
        orders=(source.envelope.orders[0], source.envelope.orders[0]),
        total_order_count=2,
    )
    duplicate_source = copy.deepcopy(source)
    duplicate_source.envelope = duplicate_envelope
    duplicate = build(duplicate_source)
    require(duplicate.result_status == "FAILED", "중복/변조 Source가 차단되지 않았습니다.")
    require_safe(duplicate)

    tampered_package = replace(prepared.adapter_package, adapter_name="TAMPERED")
    valid, errors = verify_adapter_package(tampered_package)
    require(not valid and bool(errors), "Package 변조가 탐지되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_paper_broker_adapter_result(
            prepared, Path(directory)
        )
        require(report.exists() and latest.exists(), "결과 파일이 저장되지 않았습니다.")
        payload = load_paper_broker_adapter_result(latest)
        require(payload["version"] == "V13.0", "저장 결과 Version이 다릅니다.")

    checks = {
        "Version is V13.0": prepared.version == "V13.0",
        "Default policy is valid": prepared.policy_checks_passed,
        "Policy is immutable": PaperBrokerAdapterPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "Adapter package was prepared": prepared.paper_adapter_prepared,
        "Two broker-neutral tickets were mapped": prepared.ticket_count == 2,
        "All tickets have transmit False": all(
            not ticket.transmit for ticket in prepared.adapter_package.tickets
        ),
        "Package hash passed": prepared.package_hash_checks_passed,
        "Wrong operator was blocked": wrong_operator.result_status == "FAILED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Source tampering failed": tampered.result_status == "FAILED",
        "Duplicate or tampered source failed": duplicate.result_status == "FAILED",
        "Package tampering was detected": not valid,
        "Result save and load passed": payload["version"] == "V13.0",
        "Paper execution remains unauthorized": not prepared.paper_execution_authorized,
        "Automatic execution remains disabled": not prepared.automatic_execution_authorized,
        "Execution remains blocked": prepared.execution_blocked,
        "Network was not accessed": not prepared.network_accessed,
        "Account was not accessed": not prepared.account_accessed,
        "Broker API was not called": not prepared.broker_api_called,
        "Broker order was not created": not prepared.broker_order_created,
        "Order was not submitted": not prepared.order_submitted,
        "Live order was not created": not prepared.live_order_created,
        "Live execution not authorized": not prepared.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V13.0 PAPER BROKER ADAPTER FOUNDATION TEST")
    print("=" * 92)
    print("V13.0 VALIDATION CHECKS")
    print("-" * 92)
    for name, passed in checks.items():
        print(f"{name:<58}: {passed}")
    print("=" * 92)
    require(checks["All checks passed"], "V13.0 Validation Check가 실패했습니다.")
    print()
    print("V13.0 paper broker adapter foundation test completed successfully.")
    print("Broker-neutral Ticket Mapping, SHA-256 Package 및 변조 차단이 검증되었습니다.")
    print("Network, 계좌, Broker API, 실제 주문 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
