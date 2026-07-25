from datetime import datetime

from config import SYMBOLS
from reports.console_report import (
    print_ranking_table,
    print_report_summary,
    print_top_opportunities,
    save_json_report,
)
from scanner.stock_scanner import scan_stocks


def print_program_header() -> None:
    """
    프로그램 시작 제목과 설정 정보를 출력합니다.
    """

    print()
    print("=" * 80)
    print("AI STOCK BOT V2")
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


def main() -> None:
    """
    AI Stock Bot v2 실행 순서:

    1. 종목 목록 정리
    2. 여러 종목 스캔
    3. 최종 순위표 출력
    4. 상위 종목 상세 출력
    5. JSON 리포트 저장
    6. 실행 결과 요약
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
        # 백테스트, 차트 생성을 실행합니다.
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

        # 최종점수가 높은 순서의 순위표
        print_ranking_table(
            results=results
        )

        # 상위 종목의 상세 설명
        print_top_opportunities(
            results=results
        )

        # JSON 보고서 저장
        report_path = save_json_report(
            results=results,
            details=details,
        )

        # 프로그램 종료 요약
        print_report_summary(
            results=results,
            report_path=report_path,
        )

        print()
        print(
            "Finished at: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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