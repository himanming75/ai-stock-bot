import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.sandbox_portfolio_valuation_refresh import (
    SandboxPortfolioValuationPolicy,
    load_valuation_result,
    refresh_sandbox_portfolio_valuation,
    save_valuation_result,
    verify_position_valuation,
    verify_valuation_snapshot,
)
from test_sandbox_portfolio_settlement import create_source, settle


NOW = datetime(2026, 7, 28, 12, 41, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_settlement_source() -> Any:
    return settle(create_source())


def refresh(
    source: Any,
    operator: str | None = None,
    text: str = "REFRESH IN MEMORY SANDBOX PORTFOLIO VALUATION",
    prices: Any = None,
    policy: Any = None,
) -> Any:
    return silent(
        refresh_sandbox_portfolio_valuation,
        source,
        operator or source.ledger.operator,
        text,
        {"AAPL": 110.0} if prices is None else prices,
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
        not result.market_data_api_called,
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
    )), "Valuation 실행 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_settlement_source()
    result = refresh(source)
    require(result.result_status == "VALUED_IN_MEMORY", "정상 Valuation이 실패했습니다.")
    require(result.position_count == 1, "Position 하나가 평가되지 않았습니다.")
    require(result.cash_balance == 8987.50, "Cash Balance가 다릅니다.")
    require(result.total_cost_basis == 1012.50, "Cost Basis가 다릅니다.")
    require(result.total_market_value == 1100.00, "Market Value가 다릅니다.")
    require(result.total_unrealized_profit_loss == 87.50, "Unrealized P/L이 다릅니다.")
    require(result.total_equity == 10087.50, "Total Equity가 다릅니다.")
    require(result.total_profit_loss == 87.50, "Total P/L이 다릅니다.")
    require(result.total_return_percent == 0.875, "Total Return이 다릅니다.")
    require(result.snapshot is not None, "Valuation Snapshot이 없습니다.")
    valid, errors = verify_valuation_snapshot(result.snapshot)
    require(valid and not errors, "Valuation Snapshot 검사가 실패했습니다.")
    require_safe(result)

    wrong_operator = refresh(source, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = refresh(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    missing_price = refresh(source, prices={})
    require(missing_price.result_status == "BLOCKED", "누락 Price가 차단되지 않았습니다.")
    extra_price = refresh(source, prices={"AAPL": 110.0, "MSFT": 450.0})
    require(extra_price.result_status == "BLOCKED", "추가 Price가 차단되지 않았습니다.")
    invalid_price = refresh(source, prices={"AAPL": -1})
    require(invalid_price.result_status == "BLOCKED", "음수 Price가 차단되지 않았습니다.")
    unsafe_policy = SandboxPortfolioValuationPolicy(market_data_api_disabled=False)
    unsafe = refresh(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(tampered_source.ledger, "final_cash", 9999.0)
    tampered = refresh(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Settlement Source가 실패 처리되지 않았습니다.")

    changed_valuation = replace(
        result.snapshot.valuations[0], market_value=9999.0
    )
    valuation_valid, valuation_errors = verify_position_valuation(changed_valuation)
    require(not valuation_valid and valuation_errors, "Position Valuation 변조가 탐지되지 않았습니다.")
    changed_snapshot = replace(result.snapshot, total_equity=9999.0)
    snapshot_valid, snapshot_errors = verify_valuation_snapshot(changed_snapshot)
    require(not snapshot_valid and snapshot_errors, "Valuation Snapshot 변조가 탐지되지 않았습니다.")
    duplicate_snapshot = replace(
        result.snapshot,
        position_count=2,
        valuations=(
            result.snapshot.valuations[0],
            result.snapshot.valuations[0],
        ),
    )
    duplicate_valid, duplicate_errors = verify_valuation_snapshot(duplicate_snapshot)
    require(not duplicate_valid and duplicate_errors, "중복 Position Valuation이 차단되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_valuation_result(result, Path(directory))
        require(report.exists() and latest.exists(), "Valuation 결과가 저장되지 않았습니다.")
        payload = load_valuation_result(latest)
        require(payload["version"] == "V14.5", "저장 Version이 다릅니다.")

    for checked in (
        result, wrong_operator, wrong_text, missing_price,
        extra_price, invalid_price, unsafe, tampered,
    ):
        require_safe(checked)

    checks = {
        "Version is V14.5": result.version == "V14.5",
        "Default policy is valid": result.policy_checks_passed,
        "Policy is immutable": SandboxPortfolioValuationPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V14.4 settlement source passed": result.source_checks_passed,
        "AAPL simulated price is 110.00": result.snapshot.valuations[0].simulated_current_price == 110.0,
        "Market value is 1100.00": result.total_market_value == 1100.0,
        "Unrealized profit is 87.50": result.total_unrealized_profit_loss == 87.5,
        "Total equity is 10087.50": result.total_equity == 10087.5,
        "Total return is 0.875 percent": result.total_return_percent == 0.875,
        "Valuation snapshot hash passed": valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Missing price was blocked": missing_price.result_status == "BLOCKED",
        "Extra price was blocked": extra_price.result_status == "BLOCKED",
        "Invalid price was blocked": invalid_price.result_status == "BLOCKED",
        "Tampered settlement source failed": tampered.result_status == "FAILED",
        "Position valuation tampering detected": not valuation_valid,
        "Valuation snapshot tampering detected": not snapshot_valid,
        "Duplicate valuation was blocked": not duplicate_valid,
        "Result save and load passed": payload["version"] == "V14.5",
        "Market data API was not called": not result.market_data_api_called,
        "Account was not accessed": not result.account_accessed,
        "Network was not accessed": not result.network_accessed,
        "Broker API was not called": not result.broker_api_called,
        "Order was not submitted": not result.order_submitted,
        "Live execution not authorized": not result.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V14.5 SANDBOX PORTFOLIO VALUATION REFRESH TEST")
    print("=" * 92)
    print("V14.5 VALIDATION CHECKS")
    print("-" * 92)
    for name, checked in checks.items():
        print(f"{name:<58}: {checked}")
    print("=" * 92)
    require(checks["All checks passed"], "V14.5 Validation Check가 실패했습니다.")
    print()
    print("V14.5 sandbox portfolio valuation refresh test completed successfully.")
    print("가상 현재가로 Market Value, 미실현 손익 및 Total Equity가 계산되었습니다.")
    print("시세 API, 계좌, Network, Broker API 및 실제 주문은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
