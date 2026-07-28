import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_risk_decision_ledger import (
    SandboxRiskDecisionLedgerPolicy,
    load_ledger_result,
    record_sandbox_risk_decision,
    save_ledger_result,
    verify_ledger_chain,
)
from test_sandbox_risk_decision_gate import apply_gate, create_source as create_risk_source


NOW = datetime(2026, 7, 28, 13, 50, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return apply_gate(create_risk_source())


def record(
    source: Any,
    operator: str | None = None,
    text: str = "RECORD IN MEMORY SANDBOX RISK DECISION",
    existing: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    actual = operator or source.decision.operator
    return silent(
        record_sandbox_risk_decision,
        source, actual, text, existing, policy, now,
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
        not result.market_data_api_called,
        not result.network_accessed,
        not result.account_accessed,
        not result.broker_api_called,
        not result.broker_order_created,
        not result.order_submitted,
        not result.live_order_created,
        not result.live_execution_authorized,
    )), "V14.9 실행 안전장치가 해제되었습니다.")


def main() -> None:
    first_source = create_source()
    first = record(first_source)
    require(first.result_status == "RECORDED_IN_MEMORY", "첫 Ledger 기록이 실패했습니다.")
    require(first.total_entry_count == 1, "첫 Ledger Entry 개수가 다릅니다.")
    require(first.entries[0].sequence == 1, "Genesis Sequence가 다릅니다.")
    require_safe(first)

    second_time = NOW + timedelta(minutes=1)
    second_source = create_source()
    second = record(second_source, existing=first.entries, now=second_time)
    require(second.result_status == "RECORDED_IN_MEMORY", "두 번째 Ledger 기록이 실패했습니다.")
    require(second.total_entry_count == 2, "두 Ledger Entry가 생성되지 않았습니다.")
    valid_chain, chain_errors = verify_ledger_chain(second.entries)
    require(valid_chain and not chain_errors, "Ledger Hash Chain이 실패했습니다.")

    duplicate = record(first_source, existing=first.entries, now=second_time)
    require(duplicate.result_status == "BLOCKED", "중복 Decision이 차단되지 않았습니다.")
    wrong_operator = record(first_source, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = record(first_source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    unsafe_policy = SandboxRiskDecisionLedgerPolicy(order_submission_disabled=False)
    unsafe = record(first_source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")
    backward = record(
        second_source, existing=first.entries,
        now=NOW - timedelta(seconds=1),
    )
    require(backward.result_status == "BLOCKED", "역순 시간이 차단되지 않았습니다.")

    changed_entry = replace(second.entries[0], gate_action="BLOCK")
    changed_entries = (changed_entry, second.entries[1])
    changed_valid, changed_errors = verify_ledger_chain(changed_entries)
    require(not changed_valid and changed_errors, "Ledger 변조가 탐지되지 않았습니다.")
    unsafe_existing = record(
        create_source(), existing=changed_entries, now=second_time + timedelta(minutes=1)
    )
    require(unsafe_existing.result_status == "BLOCKED", "변조 Ledger가 차단되지 않았습니다.")
    tampered_source = copy.deepcopy(first_source)
    object.__setattr__(tampered_source.decision, "gate_action", "BLOCK")
    tampered = record(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Source가 실패 처리되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_ledger_result(second, Path(directory))
        require(report.exists() and latest.exists(), "V14.9 결과가 저장되지 않았습니다.")
        payload = load_ledger_result(latest)
        require(payload["version"] == "V14.9", "저장 Version이 다릅니다.")

    for checked in (
        first, second, duplicate, wrong_operator, wrong_text,
        unsafe, backward, unsafe_existing, tampered,
    ):
        require_safe(checked)

    checks = {
        "Version is V14.9": second.version == "V14.9",
        "Default policy is valid": second.policy_checks_passed,
        "Policy is immutable": SandboxRiskDecisionLedgerPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V14.8 gate source passed": second.source_checks_passed,
        "First decision was recorded": first.ledger_entry_recorded,
        "Second decision was recorded": second.ledger_entry_recorded,
        "Two ledger entries were created": second.total_entry_count == 2,
        "Sequences are chronological": [x.sequence for x in second.entries] == [1, 2],
        "SHA-256 hash chain passed": valid_chain,
        "Duplicate decision was blocked": duplicate.result_status == "BLOCKED",
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Ledger tampering detected": not changed_valid,
        "Unsafe existing ledger was blocked": unsafe_existing.result_status == "BLOCKED",
        "Tampered gate source failed": tampered.result_status == "FAILED",
        "Result save and load passed": payload["version"] == "V14.9",
        "Broker API was not called": not second.broker_api_called,
        "Order was not submitted": not second.order_submitted,
        "Live execution not authorized": not second.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V14.9 SANDBOX RISK DECISION LEDGER TEST")
    print("=" * 92)
    print("V14.9 VALIDATION CHECKS")
    print("-" * 92)
    for name, passed in checks.items():
        print(f"{name:<58}: {passed}")
    print("=" * 92)
    require(checks["All checks passed"], "V14.9 Validation Check가 실패했습니다.")
    print()
    print("V14.9 sandbox risk decision ledger test completed successfully.")
    print("Gate 결정 누적, Sequence, SHA-256 Hash Chain, 중복·역순·변조 차단이 검증되었습니다.")
    print("Broker API, 실제 주문 제출 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
