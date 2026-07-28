import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_portfolio_settlement import (
    SandboxPortfolioSettlementPolicy,
    load_settlement_result,
    save_settlement_result,
    settle_sandbox_portfolio,
    verify_settlement_entry,
    verify_settlement_ledger,
)
from test_sandbox_fill_reconciliation import (
    create_lifecycle_source,
    reconcile,
)


NOW = datetime(2026, 7, 28, 12, 31, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return reconcile(create_lifecycle_source())


def settle(
    source: Any,
    operator: str | None = None,
    text: str = "SETTLE IN MEMORY SANDBOX PORTFOLIO",
    cash: Any = 10000.0,
    positions: Any = None,
    policy: Any = None,
) -> Any:
    return silent(
        settle_sandbox_portfolio,
        source,
        operator or source.report.operator,
        text,
        cash,
        positions,
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
        not result.account_updated,
        not result.broker_api_called,
        not result.broker_order_created,
        not result.order_submitted,
        not result.live_order_created,
        not result.live_execution_authorized,
    )), "Settlement 실행 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_source()
    result = settle(source)
    require(result.result_status == "SETTLED_IN_MEMORY", "정상 Settlement가 실패했습니다.")
    require(result.order_count == 2, "두 주문이 처리되지 않았습니다.")
    require(result.settled_count == 1, "한 모의 체결이 반영되지 않았습니다.")
    require(result.no_change_count == 1, "한 취소 주문이 보존되지 않았습니다.")
    require(result.final_cash == 8987.50, "Final Cash가 예상과 다릅니다.")
    require(result.final_position_count == 1, "Final Position 수가 다릅니다.")
    require(result.ledger is not None, "Settlement Ledger가 없습니다.")
    position = result.ledger.final_positions[0]
    require(
        position.instrument == "AAPL"
        and position.quantity == 10
        and position.average_cost == 101.25,
        "AAPL 가상 Position이 예상과 다릅니다.",
    )
    valid, errors = verify_settlement_ledger(result.ledger)
    require(valid and not errors, "Settlement Ledger 검사가 실패했습니다.")
    require_safe(result)

    wrong_operator = settle(source, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = settle(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    low_cash = settle(source, cash=100.0)
    require(low_cash.result_status == "BLOCKED", "부족한 가상 Cash가 차단되지 않았습니다.")
    invalid_cash = settle(source, cash=-1)
    require(invalid_cash.result_status == "BLOCKED", "음수 Cash가 차단되지 않았습니다.")
    bad_positions = settle(
        source, positions={"AAPL": {"quantity": -1, "average_cost": 10}}
    )
    require(bad_positions.result_status == "BLOCKED", "잘못된 Position이 차단되지 않았습니다.")
    unsafe_policy = SandboxPortfolioSettlementPolicy(account_access_disabled=False)
    unsafe = settle(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(tampered_source.report.items[0], "observed_fill_price", 1.0)
    tampered = settle(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Source가 실패 처리되지 않았습니다.")

    changed_entry = replace(result.ledger.entries[0], cash_after=9999.0)
    entry_valid, entry_errors = verify_settlement_entry(changed_entry)
    require(not entry_valid and entry_errors, "Settlement Entry 변조가 탐지되지 않았습니다.")
    changed_ledger = replace(result.ledger, final_cash=9999.0)
    ledger_valid, ledger_errors = verify_settlement_ledger(changed_ledger)
    require(not ledger_valid and ledger_errors, "Settlement Ledger 변조가 탐지되지 않았습니다.")
    duplicate_ledger = replace(
        result.ledger,
        entries=(result.ledger.entries[0], result.ledger.entries[0]),
    )
    duplicate_valid, duplicate_errors = verify_settlement_ledger(duplicate_ledger)
    require(not duplicate_valid and duplicate_errors, "중복 Settlement가 차단되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_settlement_result(result, Path(directory))
        require(report.exists() and latest.exists(), "Settlement 결과가 저장되지 않았습니다.")
        payload = load_settlement_result(latest)
        require(payload["version"] == "V14.4", "저장 Version이 다릅니다.")

    for checked in (
        result, wrong_operator, wrong_text, low_cash,
        invalid_cash, bad_positions, unsafe, tampered,
    ):
        require_safe(checked)

    checks = {
        "Version is V14.4": result.version == "V14.4",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": SandboxPortfolioSettlementPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V14.3 reconciliation source passed": result.source_checks_passed,
        "One simulated fill was settled": result.settled_count == 1,
        "One cancellation made no change": result.no_change_count == 1,
        "Final cash is 8987.50": result.final_cash == 8987.50,
        "AAPL quantity is 10": position.quantity == 10,
        "AAPL average cost is 101.25": position.average_cost == 101.25,
        "Settlement ledger hash passed": valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Insufficient virtual cash was blocked": low_cash.result_status == "BLOCKED",
        "Invalid cash was blocked": invalid_cash.result_status == "BLOCKED",
        "Invalid position was blocked": bad_positions.result_status == "BLOCKED",
        "Tampered reconciliation source failed": tampered.result_status == "FAILED",
        "Settlement entry tampering detected": not entry_valid,
        "Settlement ledger tampering detected": not ledger_valid,
        "Duplicate settlement was blocked": not duplicate_valid,
        "Result save and load passed": payload["version"] == "V14.4",
        "Credentials were not used": not result.credentials_used,
        "Account was not accessed": not result.account_accessed,
        "Account was not updated": not result.account_updated,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V14.4 SANDBOX PORTFOLIO SETTLEMENT TEST")
    print("=" * 92)
    print("V14.4 VALIDATION CHECKS")
    print("-" * 92)
    for name, checked in checks.items():
        print(f"{name:<58}: {checked}")
    print("=" * 92)
    require(checks["All checks passed"], "V14.4 Validation Check가 실패했습니다.")
    print()
    print("V14.4 sandbox portfolio settlement test completed successfully.")
    print("모의 Fill이 가상 Cash·Position·평균단가에 안전하게 반영되었습니다.")
    print("계좌, Network, Broker API 및 실제 주문·체결은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
