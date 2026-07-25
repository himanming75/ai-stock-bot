import html
import json
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from ai.schemas import StockScanResult
from config import OUTPUT_DIR
from portfolio.allocator import PortfolioAllocation


def escape_text(value: Any) -> str:
    """
    HTML에 안전하게 문자열을 표시합니다.
    """

    return html.escape(
        str(value)
    )


def signal_class(signal: str) -> str:
    """
    BUY, HOLD, SELL에 맞는 CSS 클래스를 반환합니다.
    """

    normalized = (
        str(signal)
        .upper()
        .strip()
    )

    if normalized == "BUY":
        return "signal-buy"

    if normalized == "SELL":
        return "signal-sell"

    return "signal-hold"


def risk_class(risk_level: str) -> str:
    """
    위험도에 맞는 CSS 클래스를 반환합니다.
    """

    normalized = (
        str(risk_level)
        .upper()
        .strip()
    )

    if normalized == "LOW":
        return "risk-low"

    if normalized == "HIGH":
        return "risk-high"

    return "risk-medium"


def plan_class(plan_status: str) -> str:
    """
    Trade Plan 상태에 맞는 CSS 클래스를 반환합니다.
    """

    normalized = (
        str(plan_status)
        .upper()
        .strip()
    )

    if normalized == "ATTRACTIVE":
        return "plan-attractive"

    if normalized == "WATCH":
        return "plan-watch"

    if normalized == "AVOID":
        return "plan-avoid"

    return "plan-weak"


def build_summary_cards(
    portfolio: PortfolioAllocation | None,
    results: list[StockScanResult],
) -> str:
    """
    대시보드 상단의 요약 카드 HTML을 만듭니다.
    """

    if portfolio is None:
        account_size = 0.0
        allocated = 0.0
        cash = 0.0
        risk = 0.0
        profit_2 = 0.0
    else:
        account_size = portfolio.account_size
        allocated = portfolio.total_allocated_amount
        cash = portfolio.cash_reserve_amount
        risk = portfolio.total_account_risk_percent
        profit_2 = portfolio.total_expected_profit_2

    top_symbol = (
        results[0].symbol
        if results
        else "-"
    )

    top_score = (
        results[0].final_score
        if results
        else 0.0
    )

    cards = [
        (
            "Account Size",
            f"${account_size:,.2f}",
            "Total configured account value",
        ),
        (
            "Allocated",
            f"${allocated:,.2f}",
            "Capital assigned to selected stocks",
        ),
        (
            "Cash Reserve",
            f"${cash:,.2f}",
            "Capital remaining in cash",
        ),
        (
            "Portfolio Risk",
            f"{risk:.2f}%",
            "Expected loss if all stop losses trigger",
        ),
        (
            "Expected Profit T2",
            f"${profit_2:,.2f}",
            "Potential profit at second targets",
        ),
        (
            "Top Ranked",
            f"{top_symbol} {top_score:.2f}",
            "Highest final score",
        ),
    ]

    card_html = []

    for title, value, subtitle in cards:
        card_html.append(
            f"""
            <div class="summary-card">
                <div class="summary-title">
                    {escape_text(title)}
                </div>
                <div class="summary-value">
                    {escape_text(value)}
                </div>
                <div class="summary-subtitle">
                    {escape_text(subtitle)}
                </div>
            </div>
            """
        )

    return "\n".join(
        card_html
    )


def build_ranking_rows(
    results: list[StockScanResult],
) -> str:
    """
    종목 순위표 HTML을 만듭니다.
    """

    rows = []

    for rank, result in enumerate(
        results,
        start=1,
    ):
        rows.append(
            f"""
            <tr>
                <td>{rank}</td>
                <td class="symbol-cell">
                    {escape_text(result.symbol)}
                </td>
                <td>${result.close:,.2f}</td>
                <td>{result.final_score:.2f}</td>
                <td>{result.technical_score}</td>

                <td>
                    <span class="badge {signal_class(result.technical_signal)}">
                        {escape_text(result.technical_signal)}
                    </span>
                </td>

                <td>
                    <span class="badge {signal_class(result.ai_signal)}">
                        {escape_text(result.ai_signal)}
                    </span>
                </td>

                <td>{result.ai_confidence}%</td>

                <td>
                    <span class="badge {risk_class(result.risk_level)}">
                        {escape_text(result.risk_level)}
                    </span>
                </td>

                <td>{result.backtest_return:.2f}%</td>
                <td>{result.max_drawdown:.2f}%</td>

                <td>
                    <span class="badge {plan_class(result.plan_status)}">
                        {escape_text(result.plan_status)}
                    </span>
                </td>

                <td>
                    ${result.entry_low:,.2f}
                    -
                    ${result.entry_high:,.2f}
                </td>

                <td>${result.stop_loss:,.2f}</td>
                <td>${result.target_2:,.2f}</td>
                <td>{result.risk_reward_2:.2f}</td>
            </tr>
            """
        )

    return "\n".join(
        rows
    )


def build_opportunity_cards(
    results: list[StockScanResult],
    top_count: int = 5,
) -> str:
    """
    상위 종목별 상세 카드 HTML을 만듭니다.
    """

    cards = []

    for rank, result in enumerate(
        results[:top_count],
        start=1,
    ):
        cards.append(
            f"""
            <div class="stock-card">
                <div class="stock-card-header">
                    <div>
                        <span class="stock-rank">#{rank}</span>
                        <span class="stock-symbol">
                            {escape_text(result.symbol)}
                        </span>
                    </div>

                    <span class="score-pill">
                        {result.final_score:.2f}/100
                    </span>
                </div>

                <div class="stock-grid">
                    <div>
                        <span>Current Price</span>
                        <strong>${result.close:,.2f}</strong>
                    </div>

                    <div>
                        <span>Technical Signal</span>
                        <strong class="{signal_class(result.technical_signal)} text-badge">
                            {escape_text(result.technical_signal)}
                        </strong>
                    </div>

                    <div>
                        <span>AI Signal</span>
                        <strong class="{signal_class(result.ai_signal)} text-badge">
                            {escape_text(result.ai_signal)}
                        </strong>
                    </div>

                    <div>
                        <span>AI Confidence</span>
                        <strong>{result.ai_confidence}%</strong>
                    </div>

                    <div>
                        <span>Entry Zone</span>
                        <strong>
                            ${result.entry_low:,.2f}
                            -
                            ${result.entry_high:,.2f}
                        </strong>
                    </div>

                    <div>
                        <span>Stop Loss</span>
                        <strong>${result.stop_loss:,.2f}</strong>
                    </div>

                    <div>
                        <span>Target 1</span>
                        <strong>${result.target_1:,.2f}</strong>
                    </div>

                    <div>
                        <span>Target 2</span>
                        <strong>${result.target_2:,.2f}</strong>
                    </div>

                    <div>
                        <span>Risk/Reward 2</span>
                        <strong>{result.risk_reward_2:.2f}</strong>
                    </div>

                    <div>
                        <span>Holding Period</span>
                        <strong>
                            {escape_text(result.holding_period)}
                        </strong>
                    </div>
                </div>

                <div class="summary-box">
                    <strong>AI Summary</strong>
                    <p>
                        {escape_text(result.summary)}
                    </p>
                </div>
            </div>
            """
        )

    return "\n".join(
        cards
    )


def build_allocation_rows(
    portfolio: PortfolioAllocation | None,
) -> str:
    """
    포트폴리오 자금 배분 표 HTML을 만듭니다.
    """

    if portfolio is None:
        return """
        <tr>
            <td colspan="10">
                Portfolio allocation was not generated.
            </td>
        </tr>
        """

    rows = []

    for allocation in portfolio.allocations:
        rows.append(
            f"""
            <tr>
                <td>{allocation.rank}</td>
                <td class="symbol-cell">
                    {escape_text(allocation.symbol)}
                </td>
                <td>{allocation.allocation_score:.2f}</td>
                <td>{allocation.shares}</td>
                <td>${allocation.allocated_amount:,.2f}</td>
                <td>{allocation.allocation_percent:.2f}%</td>
                <td>${allocation.reference_entry:,.2f}</td>
                <td>${allocation.expected_loss_amount:,.2f}</td>
                <td>${allocation.expected_profit_2:,.2f}</td>
                <td>
                    {escape_text(allocation.allocation_status)}
                </td>
            </tr>
            """
        )

    return "\n".join(
        rows
    )


def build_rejected_symbols(
    portfolio: PortfolioAllocation | None,
) -> str:
    """
    제외된 종목 목록 HTML을 만듭니다.
    """

    if (
        portfolio is None
        or not portfolio.rejected_symbols
    ):
        return """
        <div class="empty-message">
            No rejected symbols.
        </div>
        """

    items = []

    for rejected in portfolio.rejected_symbols:
        items.append(
            f"""
            <div class="rejected-item">
                <strong>
                    {escape_text(rejected.get("symbol", ""))}
                </strong>
                <span>
                    {escape_text(rejected.get("reason", ""))}
                </span>
            </div>
            """
        )

    return "\n".join(
        items
    )


def build_dashboard_html(
    results: list[StockScanResult],
    portfolio: PortfolioAllocation | None,
) -> str:
    """
    전체 HTML 문서를 생성합니다.
    """

    generated_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    summary_cards = build_summary_cards(
        portfolio=portfolio,
        results=results,
    )

    ranking_rows = build_ranking_rows(
        results=results
    )

    opportunity_cards = build_opportunity_cards(
        results=results
    )

    allocation_rows = build_allocation_rows(
        portfolio=portfolio
    )

    rejected_symbols = build_rejected_symbols(
        portfolio=portfolio
    )

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>AI Stock Bot V3.3 Dashboard</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background: #0b1220;
            color: #e5e7eb;
            font-family:
                Arial,
                Helvetica,
                sans-serif;
        }}

        .container {{
            width: min(1600px, 96%);
            margin: 0 auto;
            padding: 30px 0 60px;
        }}

        .header {{
            padding: 28px;
            border-radius: 18px;
            background:
                linear-gradient(
                    135deg,
                    #111827,
                    #1f2937
                );
            margin-bottom: 24px;
            border: 1px solid #334155;
        }}

        .header h1 {{
            margin: 0 0 8px;
            font-size: 32px;
        }}

        .header p {{
            margin: 4px 0;
            color: #94a3b8;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns:
                repeat(
                    auto-fit,
                    minmax(210px, 1fr)
                );
            gap: 16px;
            margin-bottom: 26px;
        }}

        .summary-card {{
            background: #111827;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 20px;
        }}

        .summary-title {{
            color: #94a3b8;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        .summary-value {{
            font-size: 28px;
            font-weight: 700;
            margin: 10px 0;
        }}

        .summary-subtitle {{
            color: #64748b;
            font-size: 13px;
        }}

        .section {{
            background: #111827;
            border: 1px solid #334155;
            border-radius: 18px;
            padding: 22px;
            margin-bottom: 24px;
        }}

        .section h2 {{
            margin-top: 0;
            font-size: 22px;
        }}

        .table-wrapper {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 1200px;
        }}

        th,
        td {{
            padding: 12px 10px;
            border-bottom: 1px solid #253044;
            text-align: right;
            white-space: nowrap;
        }}

        th {{
            color: #94a3b8;
            font-size: 12px;
            text-transform: uppercase;
        }}

        th:first-child,
        td:first-child,
        th:nth-child(2),
        td:nth-child(2) {{
            text-align: left;
        }}

        .symbol-cell {{
            font-weight: 700;
            color: #f8fafc;
        }}

        .badge {{
            display: inline-block;
            padding: 5px 9px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
        }}

        .signal-buy {{
            background: rgba(34, 197, 94, 0.18);
            color: #4ade80;
        }}

        .signal-hold {{
            background: rgba(234, 179, 8, 0.18);
            color: #facc15;
        }}

        .signal-sell {{
            background: rgba(239, 68, 68, 0.18);
            color: #f87171;
        }}

        .risk-low {{
            background: rgba(34, 197, 94, 0.18);
            color: #4ade80;
        }}

        .risk-medium {{
            background: rgba(234, 179, 8, 0.18);
            color: #facc15;
        }}

        .risk-high {{
            background: rgba(239, 68, 68, 0.18);
            color: #f87171;
        }}

        .plan-attractive {{
            background: rgba(34, 197, 94, 0.18);
            color: #4ade80;
        }}

        .plan-watch {{
            background: rgba(59, 130, 246, 0.18);
            color: #60a5fa;
        }}

        .plan-weak {{
            background: rgba(234, 179, 8, 0.18);
            color: #facc15;
        }}

        .plan-avoid {{
            background: rgba(239, 68, 68, 0.18);
            color: #f87171;
        }}

        .opportunity-grid {{
            display: grid;
            grid-template-columns:
                repeat(
                    auto-fit,
                    minmax(330px, 1fr)
                );
            gap: 18px;
        }}

        .stock-card {{
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 20px;
        }}

        .stock-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
        }}

        .stock-rank {{
            color: #64748b;
            margin-right: 8px;
        }}

        .stock-symbol {{
            font-size: 24px;
            font-weight: 700;
        }}

        .score-pill {{
            background: #2563eb;
            color: white;
            padding: 8px 12px;
            border-radius: 999px;
            font-weight: 700;
        }}

        .stock-grid {{
            display: grid;
            grid-template-columns:
                repeat(
                    2,
                    minmax(0, 1fr)
                );
            gap: 12px;
        }}

        .stock-grid div {{
            background: #111827;
            border-radius: 10px;
            padding: 12px;
        }}

        .stock-grid span {{
            display: block;
            color: #94a3b8;
            font-size: 12px;
            margin-bottom: 6px;
        }}

        .stock-grid strong {{
            font-size: 15px;
        }}

        .text-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 999px;
        }}

        .summary-box {{
            margin-top: 16px;
            padding: 14px;
            background: #111827;
            border-radius: 10px;
        }}

        .summary-box p {{
            color: #cbd5e1;
            line-height: 1.6;
        }}

        .rejected-item {{
            display: flex;
            gap: 14px;
            padding: 12px 0;
            border-bottom: 1px solid #253044;
        }}

        .rejected-item strong {{
            min-width: 80px;
            color: #f87171;
        }}

        .rejected-item span {{
            color: #cbd5e1;
        }}

        .empty-message {{
            color: #64748b;
        }}

        .footer {{
            color: #64748b;
            text-align: center;
            padding-top: 20px;
            font-size: 13px;
        }}

        @media (max-width: 700px) {{
            .stock-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>

<body>
    <div class="container">

        <div class="header">
            <h1>AI Stock Bot V3.3 Dashboard</h1>
            <p>
                Generated at:
                {escape_text(generated_at)}
            </p>
            <p>
                This dashboard is a technical and
                risk-management model, not investment advice.
            </p>
        </div>

        <div class="summary-grid">
            {summary_cards}
        </div>

        <div class="section">
            <h2>Stock Ranking</h2>

            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Symbol</th>
                            <th>Close</th>
                            <th>Final</th>
                            <th>Tech</th>
                            <th>Tech Signal</th>
                            <th>AI Signal</th>
                            <th>Confidence</th>
                            <th>Risk</th>
                            <th>Return</th>
                            <th>Drawdown</th>
                            <th>Plan</th>
                            <th>Entry</th>
                            <th>Stop</th>
                            <th>Target 2</th>
                            <th>R/R</th>
                        </tr>
                    </thead>

                    <tbody>
                        {ranking_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <h2>Top Opportunities</h2>

            <div class="opportunity-grid">
                {opportunity_cards}
            </div>
        </div>

        <div class="section">
            <h2>Portfolio Allocation</h2>

            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Symbol</th>
                            <th>Score</th>
                            <th>Shares</th>
                            <th>Amount</th>
                            <th>Weight</th>
                            <th>Entry</th>
                            <th>Risk</th>
                            <th>Profit T2</th>
                            <th>Status</th>
                        </tr>
                    </thead>

                    <tbody>
                        {allocation_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <h2>Rejected Symbols</h2>
            {rejected_symbols}
        </div>

        <div class="footer">
            AI Stock Bot V3.3 —
            technical analysis, forecasting,
            position sizing and portfolio allocation.
        </div>

    </div>
</body>
</html>
""".strip()


def save_html_dashboard(
    results: list[StockScanResult],
    portfolio: PortfolioAllocation | None,
    filename: str = "dashboard.html",
    open_browser: bool = True,
) -> str:
    """
    HTML 대시보드를 저장하고 선택적으로 브라우저에서 엽니다.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        OUTPUT_DIR / filename
    )

    dashboard_html = build_dashboard_html(
        results=results,
        portfolio=portfolio,
    )

    output_path.write_text(
        dashboard_html,
        encoding="utf-8",
    )

    print()
    print(
        f"HTML dashboard saved: "
        f"{output_path}"
    )

    if open_browser:
        try:
            webbrowser.open(
                output_path.resolve().as_uri()
            )
        except Exception as error:
            print(
                "Dashboard browser open failed: "
                f"{error}"
            )

    return str(
        output_path
    )