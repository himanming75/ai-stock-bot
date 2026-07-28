import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_order_lifecycle_tracker import (
    SandboxOrderLifecyclePolicy,
    load_lifecycle_result,
    save_lifecycle_result,
    track_sandbox_order_lifecycle,
    verify_lifecycle,
    verify_lifecycle_batch,
)
from test_sandbox_paper_order_dispatcher import (
    create_chain,
    dispatch,
)


NOW = datetime(2026, 7, 28, 12, 11, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    translation, final_control, adapter = create_chain()
    return dispatch(adapter, final_control, translation)


def make_plan(source: Any) -> tuple[dict[str, str], dict[str, float]]:
    ids = [item.client_order_id for item in source.batch.requests]
    terminal_states = {
        ids[0]: "FILLED_SIMULATED",
        ids[1]: "CANCELLED_SIMULATED",
    }
    fill_prices = {ids[0]: 101.25}
    return terminal_states, fill_prices


def track(
    source: Any,
    operator: str | None = None,
    text: str = "TRACK IN MEMORY SANDBOX ORDER LIFECYCLE",
    terminal_states: Any = None,
    fill_prices: Any = None,
    policy: Any = None,
) -> Any:
    states, prices = make_plan(source)
    return silent(
        track_sandbox_order_lifecycle,
        source,
        operator or source.batch.operator,
        text,
        terminal_states if terminal_states is not None else states,
        fill_prices if fill_prices is not None else prices,
        policy,
        NOW,
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
    )), "Lifecycle 실행 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_source()
    tracked = track(source)
    require(
        tracked.result_status == "TRACKED_IN_MEMORY",
        "정상 Lifecycle 추적이 실패했습니다.",
    )
    require(tracked.order_count == 2, "두 주문이 추적되지 않았습니다.")
    require(tracked.filled_count == 1, "모의 체결 수가 다릅니다.")
    require(tracked.cancelled_count == 1, "모의 취소 수가 다릅니다.")
    require(tracked.event_count == 6, "Lifecycle Event 수가 다릅니다.")
    require(tracked.batch is not None, "Lifecycle Batch가 없습니다.")
    valid, errors = verify_lifecycle_batch(tracked.batch)
    require(valid and not errors, "Lifecycle Batch 검사가 실패했습니다.")
    require_safe(tracked)

    wrong_operator = track(source, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = track(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")

    states, prices = make_plan(source)
    missing_states = dict(states)
    missing_states.pop(next(iter(missing_states)))
    missing = track(
        source, terminal_states=missing_states, fill_prices={}
    )
    require(missing.result_status == "BLOCKED", "누락 Terminal State가 차단되지 않았습니다.")

    invalid_states = dict(states)
    invalid_states[next(iter(invalid_states))] = "LIVE_FILLED"
    invalid = track(
        source, terminal_states=invalid_states, fill_prices=prices
    )
    require(invalid.result_status == "BLOCKED", "위험 Terminal State가 차단되지 않았습니다.")

    unsafe_policy = SandboxOrderLifecyclePolicy(
        broker_api_disabled=False
    )
    unsafe = track(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(
        tampered_source.batch.receipts[0],
        "submitted",
        True,
    )
    tampered = track(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Dispatch Source가 실패 처리되지 않았습니다.")

    changed_event = replace(
        tracked.batch.lifecycles[0].events[1],
        current_state="LIVE_ACKNOWLEDGED",
    )
    changed_lifecycle = replace(
        tracked.batch.lifecycles[0],
        events=(
            tracked.batch.lifecycles[0].events[0],
            changed_event,
            tracked.batch.lifecycles[0].events[2],
        ),
    )
    changed_valid, changed_errors = verify_lifecycle(changed_lifecycle)
    require(
        not changed_valid and changed_errors,
        "Lifecycle Event 변조가 탐지되지 않았습니다.",
    )

    changed_batch = replace(
        tracked.batch,
        filled_count=2,
    )
    batch_valid, batch_errors = verify_lifecycle_batch(changed_batch)
    require(
        not batch_valid and batch_errors,
        "Lifecycle Batch 변조가 탐지되지 않았습니다.",
    )

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_lifecycle_result(
            tracked, Path(directory)
        )
        require(report.exists() and latest.exists(), "Lifecycle 결과가 저장되지 않았습니다.")
        payload = load_lifecycle_result(latest)
        require(payload["version"] == "V14.2", "저장 Version이 다릅니다.")

    for result in (
        tracked,
        wrong_operator,
        wrong_text,
        missing,
        invalid,
        unsafe,
        tampered,
    ):
        require_safe(result)

    checks = {
        "Version is V14.2": tracked.version == "V14.2",
        "Default policy is valid": tracked.policy_checks_passed,
        "Policy is immutable": SandboxOrderLifecyclePolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V14.1 dispatch source passed": tracked.source_checks_passed,
        "Two lifecycles were created": tracked.order_count == 2,
        "Six events were created": tracked.event_count == 6,
        "One order was simulated filled": tracked.filled_count == 1,
        "One order was simulated cancelled": tracked.cancelled_count == 1,
        "Event hash chains passed": tracked.event_hash_checks_passed,
        "Lifecycle batch hash passed": valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Missing terminal state was blocked": missing.result_status == "BLOCKED",
        "Invalid terminal state was blocked": invalid.result_status == "BLOCKED",
        "Tampered dispatch source failed": tampered.result_status == "FAILED",
        "Lifecycle event tampering detected": not changed_valid,
        "Lifecycle batch tampering detected": not batch_valid,
        "Result save and load passed": payload["version"] == "V14.2",
        "Credentials were not used": not tracked.credentials_used,
        "DNS lookup was not performed": not tracked.dns_lookup_performed,
        "Socket was not created": not tracked.socket_created,
        "HTTP request was not sent": not tracked.http_request_sent,
        "Network was not accessed": not tracked.network_accessed,
        "Broker API was not called": not tracked.broker_api_called,
        "Order was not submitted": not tracked.order_submitted,
        "Live execution not authorized": not tracked.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V14.2 SANDBOX ORDER LIFECYCLE TRACKER TEST")
    print("=" * 92)
    print("V14.2 VALIDATION CHECKS")
    print("-" * 92)
    for name, result in checks.items():
        print(f"{name:<58}: {result}")
    print("=" * 92)
    require(checks["All checks passed"], "V14.2 Validation Check가 실패했습니다.")
    print()
    print("V14.2 sandbox order lifecycle tracker test completed successfully.")
    print("Queued·Acknowledged·Filled/Cancelled 모의 전이와 Hash Chain이 검증되었습니다.")
    print("Credentials, Network, Broker API 및 실제 주문·체결은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
