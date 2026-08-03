from __future__ import annotations
from typing import Any

def render_markdown(result: dict[str, Any]) -> str:
    metrics = result.get("daily_metrics", {})
    fills = result.get("fill_summary", {})
    positions = result.get("position_summary", {})
    gates = result.get("close_gates", {})
    lines = [
        f'# Daily Paper Close Report — {result.get("close_date")}',
        "",
        f'- State: **{result.get("state")}**',
        f'- Status: **{result.get("status")}**',
        f'- Paper only: **{result.get("paper_only")}**',
        f'- Actual orders submitted: **{result.get("actual_orders_submitted")}**',
        "",
        "## Account",
        "",
        f'- Starting equity: ${metrics.get("starting_equity", 0):,.2f}',
        f'- Ending equity: ${metrics.get("ending_equity", 0):,.2f}',
        f'- Daily PnL: ${metrics.get("daily_pnl", 0):,.2f}',
        f'- Daily return: {metrics.get("daily_return_pct", 0):.4f}%',
        f'- Realized PnL: ${metrics.get("realized_pnl", 0):,.2f}',
        f'- Unrealized PnL: ${metrics.get("unrealized_pnl", 0):,.2f}',
        "",
        "## Fills",
        "",
        f'- Total fills: {fills.get("fill_count", 0)}',
        f'- Full fills: {fills.get("filled_count", 0)}',
        f'- Partial fills: {fills.get("partial_fill_count", 0)}',
        f'- Not filled: {fills.get("not_filled_count", 0)}',
        f'- Gross notional: ${fills.get("gross_notional", 0):,.2f}',
        "",
        "## Positions",
        "",
        f'- Open positions: {positions.get("open_position_count", 0)}',
    ]
    for row in positions.get("positions", []):
        lines.append(
            f'- {row.get("symbol")}: {row.get("quantity")} shares, '
            f'average cost ${row.get("average_cost", 0):,.2f}, '
            f'holding days {row.get("holding_days", 0)}'
        )
    lines += [
        "",
        "## Close Gates",
        "",
        f'- Passed: **{gates.get("passed")}**',
        f'- Failed checks: {", ".join(gates.get("failed", [])) or "None"}',
        "",
        "## Safety",
        "",
        "- Broker write: disabled",
        "- Order submission: disabled",
        "- Live trading: disabled",
        "- External network: disabled",
        "",
    ]
    return "\n".join(lines)
