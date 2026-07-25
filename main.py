from datetime import datetime
from typing import Any

from config import SYMBOLS
from portfolio.allocator import (
    PortfolioAllocation,
    build_allocation_candidate,
    create_portfolio_allocation,
    print_portfolio_allocation,
)
from reports.console_report import (
    print_ranking_table,
    print_report_summary,
    print_top_opportunities,
    save_json_report,
)
from reports.html_dashboard import save_html_dashboard
from scanner.stock_scanner import scan_stocks


def print_program_header() -> None:
    """
    프로그램 시작 제목과 설정 정보를 출력합니다.
    """

    print()
    print("=" * 80)
    print("AI STOCK BOT V3.4")
    print("=" * 80)

    print(
        "Started at : "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        "Symbols    : "
        f"{', '.join(SYMBOLS)}"
    )

    print(
        "Total      : "
        f"{len(SYMBOLS)} symbols"
    )

    print("=" * 80)


def validate_symbols(
    symbols: list[str],
) -> list[str]:
    """
    종목 코드를 대문자로 정리하고
    빈 값과 중복 종목을 제거합니다.
    """

    cleaned_symbols: list[str] = []

    for symbol in symbols:
        normalized = (
            str(symbol)
            .upper()
            .strip()
        )

        if not normalized:
            continue

        if normalized not in cleaned_symbols:
            cleaned_symbols.append(
                normalized
            )

    return cleaned_symbols


def build_portfolio_candidates(
    results: list[Any],
    details: dict[str, dict[str, Any]],
) -> list[Any]:
    """
    종목 스캔 결과와 PositionPlan을 연결해
    Portfolio Allocation 후보 목록을 만듭니다.
    """

    candidates = []

    for result in results:
        symbol_details = details.get(
            result.symbol,
            {},
        )

        position_plan = symbol_details.get(
            "position_plan"
        )

        if position_plan is None:
            print(
                f"{result.symbol}: "
                "position plan이 없어 "
                "포트폴리오 후보에서 제외합니다."
            )
            continue

        candidate = build_allocation_candidate(
            result=result,
            position_plan=position_plan,
        )

        candidates.append(
            candidate
        )

    return candidates


def create_allocation_or_none(
    results: list[Any],
    details: dict[str, dict[str, Any]],
) -> PortfolioAllocation | None:
    """
    스캔 결과를 바탕으로 포트폴리오 배분을 생성합니다.

    사용할 후보가 없으면 None을 반환합니다.
    """

    allocation_candidates = (
        build_portfolio_candidates(
            results=results,
            details=details,
        )
    )

    if not allocation_candidates:
        print()
        print("=" * 80)
        print("PORTFOLIO ALLOCATION SKIPPED")
        print("=" * 80)

        print(
            "포트폴리오 배분에 사용할 "
            "PositionPlan이 없습니다."
        )

        return None

    portfolio_allocation = (
        create_portfolio_allocation(
            candidates=allocation_candidates,
        )
    )

    print_portfolio_allocation(
        portfolio_allocation
    )

    return portfolio_allocation


def print_completion_summary(
    report_path: str | None,
    dashboard_path: str | None,
    portfolio_allocation: PortfolioAllocation | None,
) -> None:
    """
    전체 프로그램 완료 결과를 출력합니다.
    """

    print()
    print("=" * 80)
    print("AI STOCK BOT V3.4 COMPLETED")
    print("=" * 80)

    print(
        "Finished at         : "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        "JSON report         : "
        f"{report_path or 'Not created'}"
    )

    print(
        "HTML dashboard      : "
        f"{dashboard_path or 'Not created'}"
    )

    if portfolio_allocation is not None:
        print(
            "Portfolio selected  : "
            f"{portfolio_allocation.selected_count}"
        )

        print(
            "Total allocated     : "
            f"${portfolio_allocation.total_allocated_amount:,.2f}"
        )

        print(
            "Cash reserve        : "
            f"${portfolio_allocation.cash_reserve_amount:,.2f} "
            f"({portfolio_allocation.cash_reserve_percent:.2f}%)"
        )

        print(
            "Total account risk  : "
            f"{portfolio_allocation.total_account_risk_percent:.2f}%"
        )

        print(
            "Expected profit T1  : "
            f"${portfolio_allocation.total_expected_profit_1:,.2f}"
        )

        print(
            "Expected profit T2  : "
            f"${portfolio_allocation.total_expected_profit_2:,.2f}"
        )

        print(
            "Expected loss       : "
            f"${portfolio_allocation.total_expected_loss:,.2f}"
        )

    print("=" * 80)


def main() -> None:
    """
    AI Stock Bot V3.4 실행 순서:

    1. 종목 목록 정리
    2. 여러 종목 스캔
    3. 기술분석
    4. AI 분석
    5. 백테스트
    6. Trade Plan 생성
    7. Position Plan 생성
    8. 종목 순위표 출력
    9. 상위 종목 상세 출력
    10. 포트폴리오 자동 배분
    11. 포트폴리오 포함 JSON 리포트 저장
    12. HTML Dashboard 생성
    13. 실행 결과 요약
    """

    print_program_header()

    symbols = validate_symbols(
        SYMBOLS
    )

    if not symbols:
        print()
        print("분석할 종목이 없습니다.")
        print(
            "config.py의 SYMBOLS 목록을 "
            "확인하세요."
        )
        return

    try:
        # 여러 종목의 기술분석, AI 분석,
        # 백테스트, Trade Plan,
        # Position Plan을 실행합니다.
        results, details = scan_stocks(
            symbols=symbols
        )

        if not results:
            print()
            print("=" * 80)
            print("SCAN FAILED")
            print("=" * 80)

            print(
                "성공적으로 분석된 종목이 없습니다."
            )

            print(
                "인터넷 연결, 종목 코드, API 키를 "
                "확인하세요."
            )

            return

        # 최종점수가 높은 순서의 종목 순위표
        print_ranking_table(
            results=results
        )

        # 상위 종목 상세 출력
        print_top_opportunities(
            results=results
        )

        # Portfolio Allocation 생성 및 출력
        portfolio_allocation = (
            create_allocation_or_none(
                results=results,
                details=details,
            )
        )

        # 종목 분석과 포트폴리오 배분을
        # 하나의 JSON 리포트로 저장합니다.
        report_path = save_json_report(
            results=results,
            details=details,
            portfolio=portfolio_allocation,
        )

        # HTML Dashboard 저장 및 브라우저 열기
        dashboard_path = save_html_dashboard(
            results=results,
            portfolio=portfolio_allocation,
            open_browser=True,
        )

        # 기존 스캔 결과 요약
        print_report_summary(
            results=results,
            report_path=report_path,
        )

        # V3.4 전체 완료 요약
        print_completion_summary(
            report_path=report_path,
            dashboard_path=dashboard_path,
            portfolio_allocation=portfolio_allocation,
        )

    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("PROGRAM CANCELLED")
        print("=" * 80)

        print(
            "사용자가 프로그램 실행을 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 80)
        print("PROGRAM ERROR")
        print("=" * 80)

        print(
            "Error type   : "
            f"{type(error).__name__}"
        )

        print(
            "Error message: "
            f"{error}"
        )

        print()
        print(
            "한 종목의 오류는 스캐너 내부에서 "
            "처리되지만, 전체 프로그램 설정 오류가 "
            "발생하면 이 메시지가 표시됩니다."
        )


if __name__ == "__main__":
    main()