import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from backtest.paper_broker_session_configuration import (
    PaperBrokerSessionPolicy,
    build_paper_broker_session_configuration,
    load_session_configuration_result,
    save_session_configuration_result,
    verify_session_configuration,
)
from test_paper_broker_adapter_foundation import create_source as create_v129_source
from backtest.paper_broker_adapter_foundation import (
    build_paper_broker_adapter_package,
)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    envelope = create_v129_source()
    return silent(
        build_paper_broker_adapter_package,
        envelope,
        envelope.envelope.operator,
        "PREPARE PAPER BROKER ADAPTER",
    )


def build(
    source: Any,
    operator: str | None = None,
    text: str = "PREPARE PAPER BROKER SESSION CONFIGURATION",
    settings: dict[str, Any] | None = None,
    policy: Any = None,
) -> Any:
    actual_operator = operator or (
        source.adapter_package.operator if source.adapter_package else "operator"
    )
    return silent(
        build_paper_broker_session_configuration,
        source, actual_operator, text, settings, policy,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    checks = (
        not result.paper_session_authorized,
        not result.paper_execution_authorized,
        not result.automatic_execution_authorized,
        result.execution_blocked,
        not result.session_opened,
        not result.network_accessed,
        not result.account_accessed,
        not result.broker_api_called,
        not result.broker_order_created,
        not result.order_submitted,
        not result.live_order_created,
        not result.live_execution_authorized,
    )
    require(all(checks), "Session 또는 Execution 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_source()
    configured = build(source)
    require(configured.result_status == "CONFIGURED", "정상 설정이 생성되지 않았습니다.")
    require(configured.all_checks_passed, "정상 검사가 실패했습니다.")
    require(configured.configuration is not None, "Configuration이 없습니다.")
    valid, errors = verify_session_configuration(configured.configuration)
    require(valid and not errors, "Configuration Hash 검사가 실패했습니다.")
    require_safe(configured)

    wrong_operator = build(source, operator="wrong-operator")
    require(wrong_operator.result_status == "FAILED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = build(source, text="OPEN SESSION")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    secret = build(source, settings={"api_key": "DO-NOT-USE"})
    require(secret.result_status == "BLOCKED", "API Key 입력이 차단되지 않았습니다.")
    live = build(source, settings={"environment": "LIVE"})
    require(live.result_status == "BLOCKED", "LIVE 환경이 차단되지 않았습니다.")
    credential = build(source, settings={"credential_mode": "API_KEY"})
    require(credential.result_status == "BLOCKED", "Credential 사용이 차단되지 않았습니다.")
    connection = build(source, settings={"connection_mode": "CONNECT"})
    require(connection.result_status == "BLOCKED", "Connection 활성화가 차단되지 않았습니다.")
    unsafe_policy = PaperBrokerSessionPolicy(network_access_disabled=False)
    unsafe = build(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험한 Policy가 차단되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(
        tampered_source.adapter_package, "adapter_name", "TAMPERED"
    )
    tampered = build(tampered_source)
    require(tampered.result_status == "FAILED", "Source 변조가 실패 처리되지 않았습니다.")

    tampered_configuration = replace(
        configured.configuration, broker_profile="TAMPERED"
    )
    valid_after_tamper, tamper_errors = verify_session_configuration(
        tampered_configuration
    )
    require(
        not valid_after_tamper and bool(tamper_errors),
        "Configuration 변조가 탐지되지 않았습니다.",
    )

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_session_configuration_result(
            configured, Path(directory)
        )
        require(report.exists() and latest.exists(), "결과가 저장되지 않았습니다.")
        payload = load_session_configuration_result(latest)
        require(payload["version"] == "V13.1", "저장 Version이 다릅니다.")

    for result in (
        configured, wrong_operator, wrong_text, secret, live,
        credential, connection, unsafe, tampered,
    ):
        require_safe(result)

    checks = {
        "Version is V13.1": configured.version == "V13.1",
        "Default policy is valid": configured.policy_checks_passed,
        "Policy is immutable": PaperBrokerSessionPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "Paper session configuration prepared": configured.paper_configuration_prepared,
        "Configuration hash passed": configured.configuration_hash_checks_passed,
        "Wrong operator was blocked": wrong_operator.result_status == "FAILED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "API key input was blocked": secret.result_status == "BLOCKED",
        "LIVE environment was blocked": live.result_status == "BLOCKED",
        "Credential mode was blocked": credential.result_status == "BLOCKED",
        "Connection mode was blocked": connection.result_status == "BLOCKED",
        "Source tampering failed": tampered.result_status == "FAILED",
        "Configuration tampering detected": not valid_after_tamper,
        "Result save and load passed": payload["version"] == "V13.1",
        "Paper session remains unauthorized": not configured.paper_session_authorized,
        "Paper execution remains unauthorized": not configured.paper_execution_authorized,
        "Automatic execution remains disabled": not configured.automatic_execution_authorized,
        "Execution remains blocked": configured.execution_blocked,
        "Session was not opened": not configured.session_opened,
        "Network was not accessed": not configured.network_accessed,
        "Account was not accessed": not configured.account_accessed,
        "Broker API was not called": not configured.broker_api_called,
        "Broker order was not created": not configured.broker_order_created,
        "Order was not submitted": not configured.order_submitted,
        "Live order was not created": not configured.live_order_created,
        "Live execution not authorized": not configured.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V13.1 PAPER BROKER SESSION CONFIGURATION TEST")
    print("=" * 92)
    print("V13.1 VALIDATION CHECKS")
    print("-" * 92)
    for name, passed in checks.items():
        print(f"{name:<58}: {passed}")
    print("=" * 92)
    require(checks["All checks passed"], "V13.1 Validation Check가 실패했습니다.")
    print()
    print("V13.1 paper broker session configuration test completed successfully.")
    print("Paper 전용 설정, Secret 차단, SHA-256 Hash 및 변조 탐지가 검증되었습니다.")
    print("Session, Network, 계좌, Broker API, 주문 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
