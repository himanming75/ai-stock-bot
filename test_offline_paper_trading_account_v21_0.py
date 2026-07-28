import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from test_sandbox_verification_final_report_v20_0 import (
    create_source as create_v20_source,
)
from test_sandbox_verification_final_report_v20_0 import finalize

from backtest.offline_paper_trading_account_v21_0 import (
    OfflinePaperTradingAccountV210Policy,
    create_offline_paper_trading_account_v21_0,
    load_account_result,
    save_account_result,
    verify_offline_paper_account,
)


NOW = datetime(2026, 7, 29, 12, 30, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    return finalize(create_v20_source())


def create_account(
    source: Any,
    operator: Any = "operator-001",
    text: Any = "CREATE IN MEMORY OFFLINE PAPER ACCOUNT V21.0",
    initial_cash: Any = 10_000.0,
    currency: Any = "USD",
    positions: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        create_offline_paper_trading_account_v21_0,
        source,
        operator,
        text,
        initial_cash,
        currency,
        positions,
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
                not result.paper_order_execution_authorized,
                not result.automatic_execution_authorized,
                not result.deposits_authorized,
                not result.withdrawals_authorized,
                result.execution_blocked,
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
        "V21.0 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_source()
    source_before = copy.deepcopy(source.to_dict())
    result = create_account(source)
    require(result.result_status == "CREATED_IN_MEMORY", "Account 생성 실패")
    require(result.account_created, "Account Object 생성 실패")
    require(result.account is not None, "Account 누락")
    require(result.account_mode == "OFFLINE_PAPER", "Account Mode 오류")
    require(result.currency == "USD", "Currency 오류")
    require(result.initial_cash == 10_000.0, "Initial Cash 오류")
    require(result.cash_balance == 10_000.0, "Cash Balance 오류")
    require(result.total_equity == 10_000.0, "Total Equity 오류")
    require(result.total_position_count == 0, "초기 Position 오류")
    require(result.paper_trading_enabled, "Paper Trading 비활성")
    require(
        result.source_v20_report_hash == source.report_hash,
        "V20.0 Report Hash 연결 오류",
    )
    require(source.to_dict() == source_before, "V20.0 Source 변경 감지")
    account_valid, account_errors = verify_offline_paper_account(
        result.account
    )
    require(account_valid and not account_errors, "Account Hash 검증 실패")
    require_safe(result)

    custom = create_account(source, initial_cash=25_000.55)
    require(custom.initial_cash == 25_000.55, "Custom Cash 오류")
    require(custom.total_equity == 25_000.55, "Custom Equity 오류")

    wrong_text = create_account(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "확인 문구 미차단")
    empty_operator = create_account(source, operator="")
    require(empty_operator.result_status == "BLOCKED", "빈 Operator 미차단")
    wrong_currency = create_account(source, currency="KRW")
    require(wrong_currency.result_status == "BLOCKED", "Currency 미차단")
    negative_cash = create_account(source, initial_cash=-1)
    require(negative_cash.result_status == "BLOCKED", "음수 Cash 미차단")
    boolean_cash = create_account(source, initial_cash=True)
    require(boolean_cash.result_status == "BLOCKED", "Boolean Cash 미차단")
    infinite_cash = create_account(source, initial_cash=float("inf"))
    require(infinite_cash.result_status == "BLOCKED", "무한 Cash 미차단")
    excessive_cash = create_account(source, initial_cash=1_000_000.01)
    require(excessive_cash.result_status == "BLOCKED", "초과 Cash 미차단")
    existing_position = create_account(
        source,
        positions=[{"symbol": "AAPL", "quantity": 1}],
    )
    require(
        existing_position.result_status == "BLOCKED",
        "초기 Position 미차단",
    )
    unsafe_policy = OfflinePaperTradingAccountV210Policy(
        broker_api_disabled=False
    )
    unsafe = create_account(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy 미차단")
    wrong_type = create_account(object())
    require(wrong_type.result_status == "FAILED", "잘못된 Source 미실패")
    backward = create_account(
        source,
        now=datetime(2026, 7, 29, 11, 59, tzinfo=timezone.utc),
    )
    require(backward.result_status == "BLOCKED", "역순 시간 미차단")

    tampered_source = copy.deepcopy(source)
    tampered_source.report = replace(
        tampered_source.report,
        final_verification_status="LIVE_READY",
    )
    tampered = create_account(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Source 미실패")

    unsafe_source = copy.deepcopy(source)
    unsafe_source.live_execution_authorized = True
    unsafe_source_result = create_account(unsafe_source)
    require(
        unsafe_source_result.result_status == "FAILED",
        "위험 Source 미실패",
    )

    changed_account = replace(result.account, cash_balance=9_999.0)
    changed_valid, changed_errors = verify_offline_paper_account(
        changed_account
    )
    require(not changed_valid and changed_errors, "Account 변조 미탐지")

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_account_result(
            result,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "저장 실패",
        )
        payload = load_account_result(latest_path)
        require(payload["version"] == "V21.0", "저장 Version 오류")
        require(
            payload["account"]["account_mode"] == "OFFLINE_PAPER",
            "저장 Account Mode 오류",
        )

    for checked in (
        result,
        custom,
        wrong_text,
        empty_operator,
        wrong_currency,
        negative_cash,
        boolean_cash,
        infinite_cash,
        excessive_cash,
        existing_position,
        unsafe,
        wrong_type,
        backward,
        tampered,
        unsafe_source_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V21.0": result.version == "V21.0",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            OfflinePaperTradingAccountV210Policy
            .__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V20.0 final report source passed": result.source_checks_passed,
        "V20.0 report hash linkage passed": (
            result.source_linkage_checks_passed
        ),
        "V20.0 source remained unchanged": (
            source.to_dict() == source_before
        ),
        "Offline paper account was created": result.account_created,
        "Account mode is offline paper": (
            result.account.account_mode == "OFFLINE_PAPER"
        ),
        "Initial cash was recorded": result.initial_cash == 10_000.0,
        "Cash balance equals initial cash": (
            result.cash_balance == result.initial_cash
        ),
        "Total equity equals initial cash": (
            result.total_equity == result.initial_cash
        ),
        "Initial positions are empty": result.total_position_count == 0,
        "Account SHA-256 hash passed": account_valid,
        "Custom initial cash passed": custom.initial_cash == 25_000.55,
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Empty operator was blocked": (
            empty_operator.result_status == "BLOCKED"
        ),
        "Wrong currency was blocked": (
            wrong_currency.result_status == "BLOCKED"
        ),
        "Negative cash was blocked": (
            negative_cash.result_status == "BLOCKED"
        ),
        "Boolean cash was blocked": (
            boolean_cash.result_status == "BLOCKED"
        ),
        "Infinite cash was blocked": (
            infinite_cash.result_status == "BLOCKED"
        ),
        "Excessive cash was blocked": (
            excessive_cash.result_status == "BLOCKED"
        ),
        "Non-empty positions were blocked": (
            existing_position.result_status == "BLOCKED"
        ),
        "Wrong source type failed": wrong_type.result_status == "FAILED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Tampered source failed": tampered.result_status == "FAILED",
        "Unsafe source failed": (
            unsafe_source_result.result_status == "FAILED"
        ),
        "Account tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V21.0",
        "Deposits are not authorized": not result.deposits_authorized,
        "Withdrawals are not authorized": not result.withdrawals_authorized,
        "Market data API was not called": (
            not result.market_data_api_called
        ),
        "Account API was not called": not result.account_api_called,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": (
            not result.live_execution_authorized
        ),
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 108)
    print("AI STOCK BOT V21.0 OFFLINE PAPER TRADING ACCOUNT TEST")
    print("=" * 108)
    print("V21.0 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V21.0 Validation Check 실패")
    print()
    print(
        "V21.0 offline paper trading account test completed successfully."
    )
    print(
        "V20.0 Final Report 연결, 가상 현금·Equity 초기화 및 "
        "Account SHA-256 Hash가 검증되었습니다."
    )
    print(
        "입출금, Broker API, 실제 계좌, Network, 주문 및 "
        "Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
