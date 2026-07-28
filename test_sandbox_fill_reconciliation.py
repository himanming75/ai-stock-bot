import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_fill_reconciliation import (
    SandboxFillReconciliationPolicy,
    load_reconciliation_result,
    reconcile_sandbox_fills,
    save_reconciliation_result,
    verify_reconciliation_item,
    verify_reconciliation_report,
)
from test_sandbox_order_lifecycle_tracker import create_source, track


NOW = datetime(2026, 7, 28, 12, 21, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_lifecycle_source() -> Any:
    return track(create_source())


def reconcile(
    source: Any,
    operator: str | None = None,
    text: str = "RECONCILE IN MEMORY SANDBOX FILLS",
    policy: Any = None,
) -> Any:
    return silent(
        reconcile_sandbox_fills,
        source,
        operator or source.batch.operator,
        text,
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
    )), "Reconciliation 실행 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_lifecycle_source()
    result = reconcile(source)
    require(
        result.result_status == "RECONCILED_IN_MEMORY",
        "정상 Fill Reconciliation이 실패했습니다.",
    )
    require(result.order_count == 2, "두 주문이 대조되지 않았습니다.")
    require(result.reconciled_count == 2, "Reconciled Count가 다릅니다.")
    require(result.filled_count == 1, "모의 체결 수가 다릅니다.")
    require(result.cancelled_count == 1, "모의 취소 수가 다릅니다.")
    require(result.mismatch_count == 0, "정상 Source에 Mismatch가 있습니다.")
    require(result.report is not None, "Reconciliation Report가 없습니다.")
    valid, errors = verify_reconciliation_report(result.report)
    require(valid and not errors, "Reconciliation Report 검사가 실패했습니다.")
    require_safe(result)

    wrong_operator = reconcile(source, operator="wrong")
    require(
        wrong_operator.result_status == "BLOCKED",
        "잘못된 Operator가 차단되지 않았습니다.",
    )
    wrong_text = reconcile(source, text="IGNORE")
    require(
        wrong_text.result_status == "BLOCKED",
        "잘못된 확인 문구가 차단되지 않았습니다.",
    )

    unsafe_policy = SandboxFillReconciliationPolicy(
        broker_api_disabled=False
    )
    unsafe = reconcile(source, policy=unsafe_policy)
    require(
        not unsafe.all_checks_passed,
        "위험 Policy가 차단되지 않았습니다.",
    )

    tampered_source = copy.deepcopy(source)
    object.__setattr__(
        tampered_source.batch.lifecycles[0],
        "filled_quantity",
        0,
    )
    tampered = reconcile(tampered_source)
    require(
        tampered.result_status == "FAILED",
        "변조 Lifecycle Source가 실패 처리되지 않았습니다.",
    )

    changed_item = replace(
        result.report.items[0],
        calculated_quantity=result.report.items[0].calculated_quantity + 1,
    )
    item_valid, item_errors = verify_reconciliation_item(changed_item)
    require(
        not item_valid and item_errors,
        "Reconciliation Item 변조가 탐지되지 않았습니다.",
    )

    changed_price = replace(
        result.report.items[0],
        observed_fill_price=999.99,
    )
    price_valid, price_errors = verify_reconciliation_item(changed_price)
    require(
        not price_valid and price_errors,
        "모의 체결 가격 변조가 탐지되지 않았습니다.",
    )

    changed_report = replace(
        result.report,
        reconciled_count=1,
    )
    report_valid, report_errors = verify_reconciliation_report(
        changed_report
    )
    require(
        not report_valid and report_errors,
        "Reconciliation Report 변조가 탐지되지 않았습니다.",
    )

    duplicate_report = replace(
        result.report,
        items=(
            result.report.items[0],
            result.report.items[0],
        ),
    )
    duplicate_valid, duplicate_errors = verify_reconciliation_report(
        duplicate_report
    )
    require(
        not duplicate_valid and duplicate_errors,
        "중복 Reconciliation Item이 차단되지 않았습니다.",
    )

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_reconciliation_result(
            result, Path(directory)
        )
        require(
            report.exists() and latest.exists(),
            "Reconciliation 결과가 저장되지 않았습니다.",
        )
        payload = load_reconciliation_result(latest)
        require(payload["version"] == "V14.3", "저장 Version이 다릅니다.")

    for checked in (
        result,
        wrong_operator,
        wrong_text,
        unsafe,
        tampered,
    ):
        require_safe(checked)

    checks = {
        "Version is V14.3": result.version == "V14.3",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": SandboxFillReconciliationPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V14.2 lifecycle source passed": result.source_checks_passed,
        "Two orders were reconciled": result.order_count == 2,
        "One simulated fill was reconciled": result.filled_count == 1,
        "One simulated cancellation was reconciled": result.cancelled_count == 1,
        "All quantities matched": result.quantity_checks_passed,
        "All terminal states matched": result.state_checks_passed,
        "All simulated prices matched": result.price_checks_passed,
        "Source identities were linked": result.identity_checks_passed,
        "Reconciliation report hash passed": valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Tampered lifecycle source failed": tampered.result_status == "FAILED",
        "Reconciliation item tampering detected": not item_valid,
        "Simulated price tampering detected": not price_valid,
        "Reconciliation report tampering detected": not report_valid,
        "Duplicate reconciliation was blocked": not duplicate_valid,
        "Result save and load passed": payload["version"] == "V14.3",
        "Credentials were not used": not result.credentials_used,
        "DNS lookup was not performed": not result.dns_lookup_performed,
        "Socket was not created": not result.socket_created,
        "HTTP request was not sent": not result.http_request_sent,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V14.3 SANDBOX FILL RECONCILIATION TEST")
    print("=" * 92)
    print("V14.3 VALIDATION CHECKS")
    print("-" * 92)
    for name, checked in checks.items():
        print(f"{name:<58}: {checked}")
    print("=" * 92)
    require(
        checks["All checks passed"],
        "V14.3 Validation Check가 실패했습니다.",
    )
    print()
    print("V14.3 sandbox fill reconciliation test completed successfully.")
    print("모의 체결·취소의 수량, 가격, 상태 및 Source Hash 연결이 검증되었습니다.")
    print("Credentials, Network, Broker API 및 실제 주문·체결은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
