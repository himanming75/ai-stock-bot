
from __future__ import annotations

from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")

REPLACEMENTS = [
    ("AI Stock Bot Unified Operations Dashboard", "AI Stock Bot Unified Operations Dashboard / 통합 운영 대시보드"),
    ("Alpaca Paper · Read-only · V3.5 Trade Analytics", "Alpaca Paper · Read-only / 읽기 전용 · V3.9 Canonical Performance / 정식 성과 데이터"),
    (">Refresh<", ">Refresh / 새로고침<"),
    (">Alerts / Health<", ">Alerts / Health · 알림 / 상태<"),
    (">Critical<", ">Critical / 긴급<"),
    (">Warnings<", ">Warnings / 경고<"),
    (">Info<", ">Info / 정보<"),
    (">Alert Summary<", ">Alert Summary / 알림 요약<"),
    (">System Health<", ">System Health / 시스템 상태<"),
    (">Runtime Gate<", ">Runtime Gate / 실행 검증 게이트<"),
    (">2-Week Validation<", ">2-Week Validation / 2주 검증<"),
    (">Account Equity<", ">Account Equity / 계좌 평가금액<"),
    (">Positions<", ">Positions / 보유 포지션<"),
    (">Open Orders<", ">Open Orders / 미체결 주문<"),
    (">Validation Closed Trades<", ">Validation Closed Trades / 검증 종료 거래<"),
    ("Current 10-day validation only", "Current 10-day validation only / 현재 10일 검증만"),
    (">Historical Closed Trades<", ">Historical Closed Trades / 누적 종료 거래<"),
    ("All saved Paper history", "All saved Paper history / 저장된 전체 페이퍼 기록"),
    (">Current Positions<", ">Current Positions / 현재 보유 포지션<"),
    (">Open / Recent Orders<", ">Open / Recent Orders · 미체결 / 최근 주문<"),
    (">Performance<", ">Performance / 성과<"),
    (">Historical Realized P/L<", ">Historical Realized P/L / 누적 실현손익<"),
    (">Win Rate<", ">Win Rate / 승률<"),
    (">Profit Factor<", ">Profit Factor / 수익 팩터<"),
    (">Shadow Signals / Outcomes<", ">Shadow Signals / Outcomes · 섀도 신호 / 결과<"),
    (">Visualization<", ">Visualization / 시각화<"),
    (">Equity Curve<", ">Equity Curve / 계좌자산 곡선<"),
    (">Daily Realized P/L<", ">Daily Realized P/L / 일별 실현손익<"),
    (">Position Allocation<", ">Position Allocation / 포지션 비중<"),
    (">10-Day Validation Progress<", ">10-Day Validation Progress / 10일 검증 진행<"),
    (">Current Unrealized P/L<", ">Current Unrealized P/L / 현재 미실현손익<"),
    (">Equity History Points<", ">Equity History Points / 자산 기록 수<"),
    (">Daily P/L Points<", ">Daily P/L Points / 일별 손익 기록 수<"),
    (">Visualization Status<", ">Visualization Status / 시각화 상태<"),
    (">Historical Performance & Trade Analytics<", ">Historical Performance & Trade Analytics / 누적 성과 및 거래 분석<"),
    (">Numeric Trades<", ">Numeric Trades / 손익 계산 거래<"),
    (">Net Realized P/L<", ">Net Realized P/L / 순실현손익<"),
    (">Average Trade<", ">Average Trade / 거래당 평균손익<"),
    (">Average Win<", ">Average Win / 평균 수익<"),
    (">Average Loss<", ">Average Loss / 평균 손실<"),
    (">Max Realized Drawdown<", ">Max Realized Drawdown / 최대 실현 낙폭<"),
    (">Cumulative Realized P/L<", ">Cumulative Realized P/L / 누적 실현손익<"),
    (">Historical vs Validation<", ">Historical vs Validation / 누적 vs 검증기간<"),
    (">By Symbol<", ">By Symbol / 종목별<"),
    (">By Exit Reason<", ">By Exit Reason / 청산 사유별<"),
    (">Recent Timeline<", ">Recent Timeline / 최근 거래 흐름<"),
    (">Symbol<", ">Symbol / 종목<"),
    (">Qty<", ">Qty / 수량<"),
    (">Avg Entry<", ">Avg Entry / 평균 진입가<"),
    (">Market Value<", ">Market Value / 평가금액<"),
    (">Unrealized P/L<", ">Unrealized P/L / 미실현손익<"),
    (">Time<", ">Time / 시간<"),
    (">Side<", ">Side / 매수·매도<"),
    (">Status<", ">Status / 상태<"),
    (">Scope<", ">Scope / 구분<"),
    (">Trades<", ">Trades / 거래수<"),
    (">Net P/L<", ">Net P/L / 순손익<"),
    (">PF<", ">PF / 수익팩터<"),
    (">Reason<", ">Reason / 사유<"),
    (">Event<", ">Event / 이벤트<"),
    (">P/L<", ">P/L / 손익<"),
    ("Not enough historical points yet", "Not enough historical points yet / 아직 기록이 부족합니다"),
    ("No realized P/L points yet", "No realized P/L points yet / 아직 실현손익 기록이 없습니다"),
    ("No numeric P/L yet", "No numeric P/L yet / 아직 숫자 손익 데이터가 없습니다"),
    ("No position market values available", "No position market values available / 포지션 평가금액 데이터가 없습니다"),
    ("Validation slots unavailable", "Validation slots unavailable / 검증 진행 데이터가 없습니다"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\stock-bot")
    args = parser.parse_args()

    target = Path(args.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if "V3.9 Canonical Performance / 정식 성과 데이터" in text:
        print("V3.9 BILINGUAL UI ALREADY PRESENT")
        return 0

    applied = 0
    for old, new in REPLACEMENTS:
        if old in text:
            text = text.replace(old, new)
            applied += 1

    if applied < 35:
        raise RuntimeError(
            f"V3.9 bilingual replacement coverage too low: {applied}"
        )

    target.write_text(text, encoding="utf-8")
    print(f"V3.9 BILINGUAL UI: PASS ({applied} replacements)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
