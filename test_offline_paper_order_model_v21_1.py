import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_order_model_v21_1 import (
    OfflinePaperOrderV211Policy,
    create_offline_paper_order_v21_1,
    load_order_result,
    save_order_result,
    verify_offline_paper_order,
)
from test_offline_paper_trading_account_v21_0 import (
    create_account,
    create_source,
)


NOW = datetime(2026, 7, 29, 12, 31, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_account_source() -> Any:
    return create_account(create_source())


def create_order(
    source: Any,
    operator: Any = "operator-001",
    text: Any = "CREATE OFFLINE PAPER ORDER DRAFT V21.1",
    symbol: Any = "AAPL",
    side: Any = "BUY",
    order_type: Any = "MARKET",
    quantity: Any = 10,
    reference_price: Any = 100.0,
    limit_price: Any = None,
    currency: Any = "USD",
    time_in_force: Any = "DAY",
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    return silent(
        create_offline_paper_order_v21_1,
        source,
        operator,
        text,
        symbol,
        side,
        order_type,
        quantity,
        reference_price,
        limit_price,
        currency,
        time_in_force,
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
                not result.funds_reserved,
                not result.holdings_reserved,
                not result.paper_order_execution_authorized,
                not result.automatic_execution_authorized,
                result.execution_blocked,
                not result.transmit,
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
        "V21.1 실행 안전장치가 해제되었습니다.",
    )


def main() -> None:
    source = create_account_source()
    source_before = copy.deepcopy(source.to_dict())
    account_before = copy.deepcopy(source.account.to_dict())

    result = create_order(source)
    require(result.result_status == "DRAFTED_IN_MEMORY", "Order 초안 생성 실패")
    require(result.order_draft_created, "Order Draft 생성 표시 누락")
    require(result.order is not None, "Order Object 누락")
    require(result.order.order_mode == "OFFLINE_PAPER_DRAFT", "Order Mode 오류")
    require(result.order.order_status == "DRAFTED_IN_MEMORY", "Order Status 오류")
    require(result.symbol == "AAPL", "Symbol 오류")
    require(result.side == "BUY", "Side 오류")
    require(result.order_type == "MARKET", "Order Type 오류")
    require(result.quantity == 10.0, "Quantity 오류")
    require(result.estimated_notional == 1_000.0, "Estimated Notional 오류")
    require(
        result.source_account_hash == source.account.account_hash,
        "V21.0 Account Hash 연결 오류",
    )
    require(source.to_dict() == source_before, "V21.0 Source 변경 감지")
    require(source.account.to_dict() == account_before, "Account 변경 감지")
    order_valid, order_errors = verify_offline_paper_order(result.order)
    require(order_valid and not order_errors, "Order Hash 검증 실패")
    require_safe(result)

    limit_order = create_order(
        source,
        symbol="MSFT",
        order_type="LIMIT",
        quantity=2,
        reference_price=260.0,
        limit_price=250.0,
    )
    require(limit_order.result_status == "DRAFTED_IN_MEMORY", "LIMIT Order 실패")
    require(limit_order.estimated_notional == 500.0, "LIMIT Notional 오류")
    require(limit_order.order.limit_price == 250.0, "Limit Price 오류")

    fractional = create_order(
        source,
        symbol="NVDA",
        quantity=0.25,
        reference_price=120.0,
    )
    require(fractional.estimated_notional == 30.0, "Fractional Order 오류")

    wrong_text = create_order(source, text="IGNORE")
    empty_operator = create_order(source, operator="")
    wrong_operator = create_order(source, operator="operator-999")
    bad_symbol = create_order(source, symbol="aapl")
    bad_symbol_chars = create_order(source, symbol="AAPL!")
    wrong_side = create_order(source, side="HOLD")
    sell_without_position = create_order(source, side="SELL", quantity=1)
    wrong_type = create_order(source, order_type="STOP")
    zero_quantity = create_order(source, quantity=0)
    boolean_quantity = create_order(source, quantity=True)
    infinite_quantity = create_order(source, quantity=float("inf"))
    excessive_quantity = create_order(source, quantity=1_000_000.01)
    missing_market_price = create_order(source, reference_price=None)
    market_with_limit = create_order(source, limit_price=99.0)
    missing_limit_price = create_order(
        source,
        order_type="LIMIT",
        reference_price=100.0,
        limit_price=None,
    )
    negative_limit_price = create_order(
        source,
        order_type="LIMIT",
        reference_price=100.0,
        limit_price=-1,
    )
    excessive_notional = create_order(
        source,
        quantity=101,
        reference_price=100.0,
    )
    wrong_currency = create_order(source, currency="KRW")
    wrong_time_in_force = create_order(source, time_in_force="GTC")
    backward = create_order(
        source,
        now=datetime(2026, 7, 29, 12, 29, tzinfo=timezone.utc),
    )
    unsafe_policy = OfflinePaperOrderV211Policy(
        broker_api_disabled=False
    )
    unsafe = create_order(source, policy=unsafe_policy)
    wrong_source = create_order(object())

    tampered_source = copy.deepcopy(source)
    tampered_source.account = replace(
        tampered_source.account,
        cash_balance=9_999.0,
    )
    tampered = create_order(tampered_source)
    unsafe_source = copy.deepcopy(source)
    unsafe_source.live_execution_authorized = True
    unsafe_source_result = create_order(unsafe_source)

    blocked_results = (
        wrong_text,
        empty_operator,
        wrong_operator,
        bad_symbol,
        bad_symbol_chars,
        wrong_side,
        sell_without_position,
        wrong_type,
        zero_quantity,
        boolean_quantity,
        infinite_quantity,
        excessive_quantity,
        missing_market_price,
        market_with_limit,
        missing_limit_price,
        negative_limit_price,
        excessive_notional,
        wrong_currency,
        wrong_time_in_force,
        backward,
        unsafe,
    )
    for blocked in blocked_results:
        require(blocked.result_status == "BLOCKED", "위험 입력 미차단")
    require(wrong_source.result_status == "FAILED", "잘못된 Source 미실패")
    require(tampered.result_status == "FAILED", "변조 Account 미실패")
    require(
        unsafe_source_result.result_status == "FAILED",
        "위험 Source 미실패",
    )

    changed_order = replace(result.order, estimated_notional=999.0)
    changed_valid, changed_errors = verify_offline_paper_order(changed_order)
    require(not changed_valid and changed_errors, "Order 변조 미탐지")

    with tempfile.TemporaryDirectory() as directory:
        report_path, latest_path = save_order_result(
            result,
            Path(directory),
        )
        require(
            report_path.exists() and latest_path.exists(),
            "Order Result 저장 실패",
        )
        payload = load_order_result(latest_path)
        require(payload["version"] == "V21.1", "저장 Version 오류")
        require(
            payload["order"]["order_mode"] == "OFFLINE_PAPER_DRAFT",
            "저장 Order Mode 오류",
        )

    for checked in (
        result,
        limit_order,
        fractional,
        *blocked_results,
        wrong_source,
        tampered,
        unsafe_source_result,
    ):
        require_safe(checked)

    checks = {
        "Version is V21.1": result.version == "V21.1",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": (
            OfflinePaperOrderV211Policy.__dataclass_params__.frozen
        ),
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V21.0 offline account source passed": result.source_checks_passed,
        "V21.0 account hash linkage passed": (
            result.source_linkage_checks_passed
        ),
        "V21.0 source remained unchanged": source.to_dict() == source_before,
        "Account balance remained unchanged": (
            source.account.to_dict() == account_before
        ),
        "Market buy order draft was created": result.order_draft_created,
        "Limit buy order draft was created": (
            limit_order.order_draft_created
        ),
        "Fractional quantity passed": fractional.quantity == 0.25,
        "Estimated notional passed": result.estimated_notional == 1_000.0,
        "Order SHA-256 hash passed": order_valid,
        "Wrong confirmation was blocked": (
            wrong_text.result_status == "BLOCKED"
        ),
        "Empty operator was blocked": (
            empty_operator.result_status == "BLOCKED"
        ),
        "Wrong operator was blocked": (
            wrong_operator.result_status == "BLOCKED"
        ),
        "Invalid symbols were blocked": (
            bad_symbol.result_status == "BLOCKED"
            and bad_symbol_chars.result_status == "BLOCKED"
        ),
        "Wrong side was blocked": wrong_side.result_status == "BLOCKED",
        "Short sell was blocked": (
            sell_without_position.result_status == "BLOCKED"
        ),
        "Wrong order type was blocked": (
            wrong_type.result_status == "BLOCKED"
        ),
        "Invalid quantities were blocked": all(
            item.result_status == "BLOCKED"
            for item in (
                zero_quantity,
                boolean_quantity,
                infinite_quantity,
                excessive_quantity,
            )
        ),
        "Invalid market prices were blocked": (
            missing_market_price.result_status == "BLOCKED"
            and market_with_limit.result_status == "BLOCKED"
        ),
        "Invalid limit prices were blocked": (
            missing_limit_price.result_status == "BLOCKED"
            and negative_limit_price.result_status == "BLOCKED"
        ),
        "Insufficient paper cash was blocked": (
            excessive_notional.result_status == "BLOCKED"
        ),
        "Wrong currency was blocked": (
            wrong_currency.result_status == "BLOCKED"
        ),
        "Wrong time in force was blocked": (
            wrong_time_in_force.result_status == "BLOCKED"
        ),
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Wrong source type failed": wrong_source.result_status == "FAILED",
        "Tampered account failed": tampered.result_status == "FAILED",
        "Unsafe source failed": (
            unsafe_source_result.result_status == "FAILED"
        ),
        "Order tampering detected": not changed_valid,
        "Result save and load passed": payload["version"] == "V21.1",
        "Funds were not reserved": not result.funds_reserved,
        "Holdings were not reserved": not result.holdings_reserved,
        "Market data API was not called": (
            not result.market_data_api_called
        ),
        "Account API was not called": not result.account_api_called,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Broker order was not created": not result.broker_order_created,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": (
            not result.live_execution_authorized
        ),
    }
    checks["All checks passed"] = all(checks.values())

    print("=" * 108)
    print("AI STOCK BOT V21.1 OFFLINE PAPER ORDER MODEL TEST")
    print("=" * 108)
    print("V21.1 VALIDATION CHECKS")
    print("-" * 108)
    for name, passed in checks.items():
        print(f"{name:<74}: {passed}")
    print("=" * 108)
    require(checks["All checks passed"], "V21.1 Validation Check 실패")
    print()
    print("V21.1 offline paper order model test completed successfully.")
    print(
        "V21.0 가상계좌 연결, MARKET·LIMIT 매수 초안, 예상금액 및 "
        "Order SHA-256 Hash가 검증되었습니다."
    )
    print(
        "잔액·보유수량 변경, 시세·계좌 API, Network, Broker 주문, "
        "실제 주문 및 Live Execution은 호출되지 않았습니다."
    )


if __name__ == "__main__":
    main()
