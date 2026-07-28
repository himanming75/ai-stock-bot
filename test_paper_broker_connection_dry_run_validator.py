import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from backtest.paper_broker_connection_dry_run_validator import (
    PaperConnectionDryRunPolicy,
    load_connection_dry_run_result,
    save_connection_dry_run_result,
    validate_paper_broker_connection_dry_run,
    verify_dry_run_certificate,
)
from backtest.paper_broker_session_configuration import (
    build_paper_broker_session_configuration,
)
from test_paper_broker_session_configuration import create_source as create_v130_source


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    adapter = create_v130_source()
    return silent(
        build_paper_broker_session_configuration,
        adapter,
        adapter.adapter_package.operator,
        "PREPARE PAPER BROKER SESSION CONFIGURATION",
    )


def build(
    source: Any,
    operator: str | None = None,
    text: str = "VALIDATE PAPER CONNECTION WITHOUT CONNECTING",
    policy: Any = None,
) -> Any:
    actual_operator = operator or (
        source.configuration.operator if source.configuration else "operator"
    )
    return silent(
        validate_paper_broker_connection_dry_run,
        source, actual_operator, text, policy,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    values = (
        not result.connection_authorized,
        not result.paper_session_authorized,
        not result.paper_execution_authorized,
        not result.automatic_execution_authorized,
        result.execution_blocked,
        not result.dns_lookup_performed,
        not result.socket_created,
        not result.http_request_sent,
        not result.network_accessed,
        not result.account_accessed,
        not result.session_opened,
        not result.broker_api_called,
        not result.broker_order_created,
        not result.order_submitted,
        not result.live_order_created,
        not result.live_execution_authorized,
    )
    require(all(values), "Connection 또는 Execution 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_source()
    validated = build(source)
    require(validated.version == "V13.2", "Version이 V13.2가 아닙니다.")
    require(validated.result_status == "VALIDATED", "Dry-Run 검증이 실패했습니다.")
    require(validated.all_checks_passed, "정상 검사가 실패했습니다.")
    require(validated.check_count == 10, "10개 Dry-Run Check가 생성되지 않았습니다.")
    require(validated.passed_check_count == 10, "모든 Dry-Run Check가 통과하지 못했습니다.")
    require(validated.certificate is not None, "Certificate가 없습니다.")
    valid, errors = verify_dry_run_certificate(validated.certificate)
    require(valid and not errors, "Certificate Hash 검사가 실패했습니다.")
    require_safe(validated)

    wrong_operator = build(source, operator="wrong-operator")
    require(wrong_operator.result_status == "FAILED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = build(source, text="CONNECT NOW")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    unsafe_policy = PaperConnectionDryRunPolicy(socket_creation_disabled=False)
    unsafe = build(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험한 Policy가 차단되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(tampered_source.configuration, "environment", "LIVE")
    tampered = build(tampered_source)
    require(tampered.result_status == "FAILED", "Source 변조가 실패 처리되지 않았습니다.")

    zero_ticket_source = copy.deepcopy(source)
    object.__setattr__(zero_ticket_source.configuration, "ticket_count", 0)
    zero_ticket = build(zero_ticket_source)
    require(zero_ticket.result_status == "FAILED", "Ticket 변조가 차단되지 않았습니다.")

    tampered_certificate = replace(
        validated.certificate, broker_profile="TAMPERED"
    )
    valid_after_tamper, tamper_errors = verify_dry_run_certificate(
        tampered_certificate
    )
    require(
        not valid_after_tamper and bool(tamper_errors),
        "Certificate 변조가 탐지되지 않았습니다.",
    )

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_connection_dry_run_result(
            validated, Path(directory)
        )
        require(report.exists() and latest.exists(), "결과가 저장되지 않았습니다.")
        payload = load_connection_dry_run_result(latest)
        require(payload["version"] == "V13.2", "저장 Version이 다릅니다.")

    for result in (
        validated, wrong_operator, wrong_text, unsafe, tampered, zero_ticket
    ):
        require_safe(result)

    checks = {
        "Version is V13.2": validated.version == "V13.2",
        "Default policy is valid": validated.policy_checks_passed,
        "Policy is immutable": PaperConnectionDryRunPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "Connection dry-run was validated": validated.connection_dry_run_validated,
        "Ten dry-run checks were created": validated.check_count == 10,
        "All ten dry-run checks passed": validated.passed_check_count == 10,
        "Certificate hash passed": validated.certificate_hash_checks_passed,
        "Wrong operator was blocked": wrong_operator.result_status == "FAILED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Source tampering failed": tampered.result_status == "FAILED",
        "Ticket count tampering failed": zero_ticket.result_status == "FAILED",
        "Certificate tampering detected": not valid_after_tamper,
        "Result save and load passed": payload["version"] == "V13.2",
        "Connection remains unauthorized": not validated.connection_authorized,
        "DNS lookup was not performed": not validated.dns_lookup_performed,
        "Socket was not created": not validated.socket_created,
        "HTTP request was not sent": not validated.http_request_sent,
        "Network was not accessed": not validated.network_accessed,
        "Account was not accessed": not validated.account_accessed,
        "Session was not opened": not validated.session_opened,
        "Broker API was not called": not validated.broker_api_called,
        "Broker order was not created": not validated.broker_order_created,
        "Order was not submitted": not validated.order_submitted,
        "Live order was not created": not validated.live_order_created,
        "Live execution not authorized": not validated.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V13.2 PAPER BROKER CONNECTION DRY-RUN VALIDATOR TEST")
    print("=" * 92)
    print("V13.2 VALIDATION CHECKS")
    print("-" * 92)
    for name, passed in checks.items():
        print(f"{name:<58}: {passed}")
    print("=" * 92)
    require(checks["All checks passed"], "V13.2 Validation Check가 실패했습니다.")
    print()
    print("V13.2 paper broker connection dry-run validator test completed successfully.")
    print("10개 비연결 검사, SHA-256 Certificate 및 변조 차단이 검증되었습니다.")
    print("DNS, Socket, HTTP, Network, 계좌, Broker API 및 주문은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
