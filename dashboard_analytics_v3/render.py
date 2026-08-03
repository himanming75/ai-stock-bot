from __future__ import annotations
import html
from typing import Any

def esc(value: Any) -> str:
    return html.escape(str(value))

def badge(value: Any) -> str:
    text = str(value)
    upper = text.upper()
    cls = "neutral"
    if upper in {"PASS","TRUE","APPROVED","READY"} or upper.endswith("_READY"):
        cls = "good"
    elif "REVIEW" in upper or "PENDING" in upper or upper == "FALSE":
        cls = "warn"
    elif "FAIL" in upper or "BLOCK" in upper:
        cls = "bad"
    return f'<span class="badge {cls}">{esc(text)}</span>'

def bar(value: float, maximum: float = 100.0) -> str:
    width = max(0.0, min(100.0, value / maximum * 100.0 if maximum else 0.0))
    return f'<div class="bar"><span style="width:{width:.2f}%"></span></div>'

def render(data: dict) -> str:
    strategy_rows = ""
    for row in data.get("strategy_rows", []):
        failures = ", ".join(row.get("failed_checks", [])) or "—"
        strategy_rows += (
            "<tr>"
            f"<td>{esc(row.get('rank',''))}</td>"
            f"<td><strong>{esc(row.get('strategy',''))}</strong></td>"
            f"<td>{float(row.get('return_pct',0)):.2f}%</td>"
            f"<td>{float(row.get('drawdown_pct',0)):.2f}%</td>"
            f"<td>{float(row.get('sharpe',0)):.2f}</td>"
            f"<td>{float(row.get('profit_factor',0)):.2f}</td>"
            f"<td>{float(row.get('excess_return_pct',0)):.2f}%</td>"
            f"<td>{badge(row.get('approved',False))}</td>"
            f"<td>{esc(failures)}</td>"
            "</tr>"
        )
    if not strategy_rows:
        strategy_rows = '<tr><td colspan="9">No strategy ranking data available.</td></tr>'

    allocation_cards = ""
    for item in data.get("allocations", []):
        weight = float(item.get("weight_pct", 0))
        allocation_cards += (
            '<div class="allocation">'
            f'<div><strong>{esc(item.get("strategy",""))}</strong><span>{weight:.2f}%</span></div>'
            f'{bar(weight, 100)}'
            f'<small>Rank {esc(item.get("rank",""))} · Kelly {float(item.get("kelly_fraction",0)):.2f}</small>'
            '</div>'
        )
    if not allocation_cards:
        allocation_cards = "<p>No portfolio allocations available.</p>"

    risk = data.get("portfolio_risk", {})
    risk_checks = "".join(
        f'<li>{badge(passed)} {esc(name)}</li>'
        for name, passed in risk.get("checks", {}).items()
    ) or "<li>No risk checks available.</li>"

    alerts = "".join(
        f'<div class="alert {esc(item.get("level","info"))}"><strong>{esc(item.get("title",""))}</strong><br>{esc(item.get("message",""))}</div>'
        for item in data.get("alerts", [])
    ) or '<div class="alert good">No active alerts.</div>'

    progress = data.get("validation_progress", {})
    cards = [
        ("Strategy State", data.get("strategy_state")),
        ("Portfolio State", data.get("portfolio_state")),
        ("Production Release", data.get("production_release_state")),
        ("Orchestrator", data.get("orchestrator_state")),
        ("Historical Bars", data.get("bar_count", 0)),
        ("Benchmark Return", f'{float(data.get("benchmark_return_pct",0)):.2f}%'),
        ("Approved Strategies", sum(1 for r in data.get("strategy_rows",[]) if r.get("approved"))),
        ("Risk Passed", risk.get("passed", False)),
    ]
    cards_html = "".join(
        f'<section class="metric"><small>{esc(title)}</small><div>{badge(value)}</div></section>'
        for title, value in cards
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Stock Bot Dashboard Analytics v3</title>
<style>
:root{{color-scheme:dark;font-family:Arial,sans-serif}}
body{{margin:0;background:#07111f;color:#e5e7eb}}
header{{padding:22px 28px;background:#0f172a;border-bottom:1px solid #334155}}
main{{max-width:1500px;margin:auto;padding:24px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}}
.metric,.panel{{background:#111827;border:1px solid #334155;border-radius:12px;padding:16px}}
.metric small{{display:block;color:#94a3b8;margin-bottom:10px}}
.panel{{margin-top:18px;overflow:auto}}
.badge{{display:inline-block;padding:5px 9px;border-radius:999px;font-size:12px;max-width:100%;overflow-wrap:anywhere}}
.good{{background:#14532d;color:#bbf7d0}}.warn{{background:#713f12;color:#fef08a}}
.bad{{background:#7f1d1d;color:#fecaca}}.neutral{{background:#334155}}
table{{width:100%;border-collapse:collapse;min-width:1000px}}
th,td{{padding:9px;border-bottom:1px solid #334155;text-align:left;vertical-align:top}}
.bar{{height:9px;background:#334155;border-radius:99px;overflow:hidden;margin:8px 0}}
.bar span{{display:block;height:100%;background:#93c5fd}}
.allocation{{margin:12px 0}}.allocation>div:first-child{{display:flex;justify-content:space-between}}
.alert{{padding:12px;border-radius:8px;margin:8px 0;background:#1e3a8a}}
.alert.warning{{background:#713f12}}.alert.danger{{background:#7f1d1d}}.alert.good{{background:#14532d}}
.progress{{font-size:28px;font-weight:bold}}
a{{color:#93c5fd}}
</style>
</head>
<body>
<header><h1>AI Stock Bot Dashboard Analytics v3</h1>
<div>Localhost only · Paper only · No broker writes · No live trading</div></header>
<main>
<div class="grid">{cards_html}</div>

<section class="panel">
<h2>Final Validation Progress</h2>
<div class="progress">{esc(progress.get("completed_days",0))} / {esc(progress.get("required_days",3))} days</div>
{bar(float(progress.get("percent_complete",0)),100)}
<p>Remaining distinct days: <strong>{esc(progress.get("remaining_days",0))}</strong></p>
</section>

<section class="panel">
<h2>Active Alerts and Gate Failures</h2>
{alerts}
</section>

<section class="panel">
<h2>Strategy Performance and Approval Gates</h2>
<table><thead><tr>
<th>Rank</th><th>Strategy</th><th>Return</th><th>Drawdown</th><th>Sharpe</th>
<th>Profit Factor</th><th>Excess Return</th><th>Approved</th><th>Failed Checks</th>
</tr></thead><tbody>{strategy_rows}</tbody></table>
</section>

<section class="panel">
<h2>Portfolio Allocations</h2>
{allocation_cards}
</section>

<section class="panel">
<h2>Portfolio Risk Gate</h2>
<p>Largest allocation: <strong>{float(risk.get("largest_allocation_pct",0)):.2f}%</strong></p>
<p>Approved strategies: <strong>{esc(risk.get("approved_strategy_count",0))}</strong></p>
<ul>{risk_checks}</ul>
</section>

<section class="panel">
<h2>Data Source</h2>
<p>{esc(data.get("historical_input") or "Not available")}</p>
<p><a href="/api/analytics">Download analytics JSON</a> · <a href="/health">Health</a></p>
</section>
</main></body></html>"""
