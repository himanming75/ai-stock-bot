import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.paper_broker_sandbox_adapter import (
    PaperBrokerSandboxAdapterPolicy,
    load_sandbox_adapter_result,
    prepare_paper_broker_sandbox,
    save_sandbox_adapter_result,
    verify_handshake,
    verify_response,
)
from test_paper_submission_final_control import (
    control,
    create_sources,
)


NOW = datetime(2026, 7, 28, 12, 5, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    reconciliation, release, ledger = create_sources(
        datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
    )
    return control(
        reconciliation,
        release,
        ledger,
        now=datetime(2026, 7, 28, 12, 1, tzinfo=timezone.utc),
    )


def prepare(
    source: Any,
    operator: str | None = None,
    text: str = "PREPARE OFFLINE PAPER BROKER SANDBOX",
    handshakes: Any = None,
    responses: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    actual = operator or source.controls[-1].operator
    return silent(
        prepare_paper_broker_sandbox,
        source,
        actual,
        text,
        handshakes,
        responses,
        policy,
        now,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    require(all((
        not result.paper_execution_authorized,
        not result.automatic_execution_authorized,
        result.execution_blocked,
        not result.credentials_used,
        not result.dns_lookup_performed,
        not result.socket_created,
        not result.http_request_sent,
        not result.network_accessed,
        not result.account_accessed,
        not result.broker_api_called,
        not result.broker_order_created,
        not result.order_submitted,
        not result.live_order_created,
        not result.live_execution_authorized,
    )), "Sandbox 실행 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_source()
    ready = prepare(source)
    require(ready.result_status == "SANDBOX_READY", "정상 Sandbox 준비가 실패했습니다.")
    require(ready.sandbox_session_ready, "Sandbox Session이 준비되지 않았습니다.")
    require(len(ready.handshakes) == 1, "Handshake가 생성되지 않았습니다.")
    require(len(ready.responses) == 1, "Response가 생성되지 않았습니다.")
    handshake_valid, handshake_errors = verify_handshake(
        ready.handshakes[0]
    )
    response_valid, time_valid, response_errors = verify_response(
        ready.responses[0], NOW
    )
    require(
        handshake_valid and not handshake_errors,
        "Handshake 검사가 실패했습니다.",
    )
    require(
        response_valid and time_valid and not response_errors,
        "Sandbox Response 검사가 실패했습니다.",
    )
    require_safe(ready)

    wrong_operator = prepare(source, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = prepare(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    duplicate = prepare(
        source,
        handshakes=ready.handshakes,
        responses=ready.responses,
    )
    require(duplicate.result_status == "BLOCKED", "중복 Session이 차단되지 않았습니다.")

    unsafe_policy = PaperBrokerSandboxAdapterPolicy(
        network_access_disabled=False
    )
    unsafe = prepare(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(
        tampered_source.controls[-1],
        "controlled_item_count",
        99,
    )
    tampered = prepare(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Final Control이 실패 처리되지 않았습니다.")

    changed_handshake = replace(
        ready.handshakes[0],
        item_count=99,
    )
    changed_handshake_valid, changed_handshake_errors = verify_handshake(
        changed_handshake
    )
    require(
        not changed_handshake_valid and changed_handshake_errors,
        "Handshake 변조가 탐지되지 않았습니다.",
    )

    changed_response = replace(
        ready.responses[0],
        sandbox_status="CONNECTED",
    )
    changed_response_valid, _, changed_response_errors = verify_response(
        changed_response, NOW
    )
    require(
        not changed_response_valid and changed_response_errors,
        "Response 변조가 탐지되지 않았습니다.",
    )

    unsafe_history = prepare(
        create_source(),
        handshakes=(changed_handshake,),
        responses=ready.responses,
    )
    require(
        unsafe_history.result_status == "BLOCKED",
        "변조 Existing Session이 차단되지 않았습니다.",
    )

    expired_valid, expired_time, expired_errors = verify_response(
        ready.responses[0],
        NOW + timedelta(minutes=16),
    )
    require(
        not expired_valid and not expired_time and expired_errors,
        "만료 Sandbox Session이 차단되지 않았습니다.",
    )

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_sandbox_adapter_result(
            ready, Path(directory)
        )
        require(report.exists() and latest.exists(), "Sandbox 결과가 저장되지 않았습니다.")
        payload = load_sandbox_adapter_result(latest)
        require(payload["version"] == "V14.0", "저장 Version이 다릅니다.")

    for result in (
        ready,
        wrong_operator,
        wrong_text,
        duplicate,
        unsafe,
        tampered,
        unsafe_history,
    ):
        require_safe(result)

    checks = {
        "Version is V14.0": ready.version == "V14.0",
        "Default policy is valid": ready.policy_checks_passed,
        "Policy is immutable": PaperBrokerSandboxAdapterPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V13.9 final control was validated": ready.source_checks_passed,
        "Offline handshake was created": handshake_valid,
        "Sandbox response was created": response_valid,
        "Sandbox session is ready": ready.sandbox_session_ready,
        "Session expiration was calculated": time_valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Duplicate session was blocked": duplicate.result_status == "BLOCKED",
        "Tampered final control failed": tampered.result_status == "FAILED",
        "Handshake tampering detected": not changed_handshake_valid,
        "Response tampering detected": not changed_response_valid,
        "Unsafe existing session was blocked": unsafe_history.result_status == "BLOCKED",
        "Expired session was blocked": not expired_valid,
        "Result save and load passed": payload["version"] == "V14.0",
        "Credentials were not used": not ready.credentials_used,
        "DNS lookup was not performed": not ready.dns_lookup_performed,
        "Socket was not created": not ready.socket_created,
        "HTTP request was not sent": not ready.http_request_sent,
        "Network was not accessed": not ready.network_accessed,
        "Broker API was not called": not ready.broker_api_called,
        "Order was not submitted": not ready.order_submitted,
        "Live execution not authorized": not ready.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V14.0 PAPER BROKER SANDBOX ADAPTER TEST")
    print("=" * 92)
    print("V14.0 VALIDATION CHECKS")
    print("-" * 92)
    for name, result in checks.items():
        print(f"{name:<58}: {result}")
    print("=" * 92)
    require(checks["All checks passed"], "V14.0 Validation Check가 실패했습니다.")
    print()
    print("V14.0 paper broker sandbox adapter test completed successfully.")
    print("V13.9 연결, Offline Handshake·Response, 만료·중복·변조 차단이 검증되었습니다.")
    print("Credentials, DNS, Socket, HTTP, Broker API 및 실제 주문은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
