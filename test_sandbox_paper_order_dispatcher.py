import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_paper_order_dispatcher import (
    SandboxPaperOrderDispatcherPolicy,
    dispatch_sandbox_paper_orders,
    load_dispatch_result,
    save_dispatch_result,
    verify_dispatch_batch,
)
from test_paper_broker_sandbox_adapter import prepare
from test_paper_submission_final_control import control
from test_paper_submission_reconciliation import build, create_sources
from test_paper_submission_release_gate import issue
from test_paper_submission_release_ledger import record


RELEASE_TIME = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
CONTROL_TIME = datetime(2026, 7, 28, 12, 1, tzinfo=timezone.utc)
ADAPTER_TIME = datetime(2026, 7, 28, 12, 5, tzinfo=timezone.utc)
NOW = datetime(2026, 7, 28, 12, 10, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_chain() -> tuple[Any, Any, Any]:
    translation, submission = create_sources()
    reconciliation = build(translation, submission)
    release = issue(reconciliation, now=RELEASE_TIME)
    ledger = record(release, now=RELEASE_TIME)
    final_control = control(
        reconciliation, release, ledger, now=CONTROL_TIME
    )
    adapter = prepare(final_control, now=ADAPTER_TIME)
    return translation, final_control, adapter


def dispatch(
    adapter: Any,
    final_control: Any,
    translation: Any,
    operator: str | None = None,
    text: str = "DISPATCH ORDERS TO IN MEMORY PAPER SANDBOX",
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    actual = operator or translation.batch.operator
    return silent(
        dispatch_sandbox_paper_orders,
        adapter,
        final_control,
        translation,
        actual,
        text,
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
    )), "Dispatcher 실행 안전장치가 해제되었습니다.")


def main() -> None:
    translation, final_control, adapter = create_chain()
    dispatched = dispatch(adapter, final_control, translation)
    require(
        dispatched.result_status == "DISPATCHED_IN_MEMORY",
        "정상 In-Memory Dispatch가 실패했습니다.",
    )
    require(dispatched.request_count == 2, "두 Request가 생성되지 않았습니다.")
    require(dispatched.receipt_count == 2, "두 Receipt가 생성되지 않았습니다.")
    require(dispatched.batch is not None, "Dispatch Batch가 없습니다.")
    valid, errors = verify_dispatch_batch(dispatched.batch)
    require(valid and not errors, "Dispatch Batch 검사가 실패했습니다.")
    require_safe(dispatched)

    wrong_operator = dispatch(
        adapter, final_control, translation, operator="wrong"
    )
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = dispatch(
        adapter, final_control, translation, text="IGNORE"
    )
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")

    unsafe_policy = SandboxPaperOrderDispatcherPolicy(
        order_submission_disabled=False
    )
    unsafe = dispatch(
        adapter, final_control, translation, policy=unsafe_policy
    )
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    other_translation, other_control, other_adapter = create_chain()
    mismatch = dispatch(adapter, final_control, other_translation)
    require(mismatch.result_status == "BLOCKED", "불일치 Translation이 차단되지 않았습니다.")

    tampered_adapter = copy.deepcopy(adapter)
    object.__setattr__(
        tampered_adapter.responses[-1],
        "sandbox_status",
        "CONNECTED",
    )
    tampered_source = dispatch(
        tampered_adapter, final_control, translation
    )
    require(tampered_source.result_status == "FAILED", "변조 Adapter가 실패 처리되지 않았습니다.")

    changed_request = replace(
        dispatched.batch.requests[0],
        quantity=999,
    )
    changed_batch = replace(
        dispatched.batch,
        requests=(changed_request, *dispatched.batch.requests[1:]),
    )
    changed_valid, changed_errors = verify_dispatch_batch(changed_batch)
    require(
        not changed_valid and changed_errors,
        "Dispatch Request 변조가 탐지되지 않았습니다.",
    )

    changed_receipt = replace(
        dispatched.batch.receipts[0],
        submitted=True,
    )
    receipt_batch = replace(
        dispatched.batch,
        receipts=(changed_receipt, *dispatched.batch.receipts[1:]),
    )
    receipt_valid, receipt_errors = verify_dispatch_batch(receipt_batch)
    require(
        not receipt_valid and receipt_errors,
        "Dispatch Receipt 변조가 탐지되지 않았습니다.",
    )

    expired = dispatch(
        adapter,
        final_control,
        translation,
        now=datetime(2026, 7, 28, 12, 21, tzinfo=timezone.utc),
    )
    require(expired.result_status == "FAILED", "만료 Sandbox Session이 실패 처리되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_dispatch_result(
            dispatched, Path(directory)
        )
        require(report.exists() and latest.exists(), "Dispatch 결과가 저장되지 않았습니다.")
        payload = load_dispatch_result(latest)
        require(payload["version"] == "V14.1", "저장 Version이 다릅니다.")

    for result in (
        dispatched,
        wrong_operator,
        wrong_text,
        unsafe,
        mismatch,
        tampered_source,
        expired,
    ):
        require_safe(result)

    checks = {
        "Version is V14.1": dispatched.version == "V14.1",
        "Default policy is valid": dispatched.policy_checks_passed,
        "Policy is immutable": SandboxPaperOrderDispatcherPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V14.0 sandbox adapter passed": dispatched.adapter_checks_passed,
        "V13.9 final control passed": dispatched.control_checks_passed,
        "V13.4 translation passed": dispatched.translation_checks_passed,
        "All source links passed": dispatched.linkage_checks_passed,
        "Two requests were created": dispatched.request_count == 2,
        "Two receipts were created": dispatched.receipt_count == 2,
        "Dispatch batch hash passed": valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Mismatched translation was blocked": mismatch.result_status == "BLOCKED",
        "Tampered adapter failed": tampered_source.result_status == "FAILED",
        "Request tampering detected": not changed_valid,
        "Receipt tampering detected": not receipt_valid,
        "Expired sandbox session failed": expired.result_status == "FAILED",
        "Result save and load passed": payload["version"] == "V14.1",
        "Credentials were not used": not dispatched.credentials_used,
        "DNS lookup was not performed": not dispatched.dns_lookup_performed,
        "Socket was not created": not dispatched.socket_created,
        "HTTP request was not sent": not dispatched.http_request_sent,
        "Network was not accessed": not dispatched.network_accessed,
        "Broker API was not called": not dispatched.broker_api_called,
        "Order was not submitted": not dispatched.order_submitted,
        "Live execution not authorized": not dispatched.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V14.1 SANDBOX PAPER ORDER DISPATCHER TEST")
    print("=" * 92)
    print("V14.1 VALIDATION CHECKS")
    print("-" * 92)
    for name, result in checks.items():
        print(f"{name:<58}: {result}")
    print("=" * 92)
    require(checks["All checks passed"], "V14.1 Validation Check가 실패했습니다.")
    print()
    print("V14.1 sandbox paper order dispatcher test completed successfully.")
    print("V13.4·V13.9·V14.0 연결, In-Memory Dispatch 및 변조 차단이 검증되었습니다.")
    print("Credentials, DNS, Socket, HTTP, Broker API 및 실제 주문은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
