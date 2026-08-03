from __future__ import annotations

import html
import json
from typing import Any


def badge(value: Any) -> str:
    text = str(value)
    normalized = text.upper()
    css = "neutral"
    if normalized in {"PASS", "TRUE", "READY", "APPROVED"}:
        css = "good"
    elif "PENDING" in normalized or normalized in {"FALSE", "NOT_AVAILABLE"}:
        css = "warn"
    elif normalized in {"BLOCKED", "FAIL"} or "ATTENTION" in normalized:
        css = "bad"
    return f'<span class="badge {css}">{html.escape(text)}</span>'


def render_html(state: dict[str, Any]) -> str:
    rows = []
    for item in state["sources"].values():
        rows.append(
            "<tr>"
            f"<td>{html.escape(item['name'])}</td>"
            f"<td>{badge(item['state'])}</td>"
            f"<td>{badge(item['status'])}</td>"
            f"<td>{html.escape(str(item['stage_range']))}</td>"
            f"<td>{html.escape(str(item['next_phase']))}</td>"
            f"<td>{int(item['blocking_issue_count'])}</td>"
            "</tr>"
        )

    summary = state["summary"]
    cards = [
        ("Sources", f"{state['available_source_count']}/{state['total_source_count']}"),
        ("Validation Days", str(summary["validation_completed_days"])),
        ("Remaining Days", str(summary["validation_remaining_days"])),
        ("Stability Score", str(summary["stability_score"])),
        ("Performance Score", str(summary["performance_score"])),
        ("Risk Gate", str(summary["risk_gate_passed"])),
        ("Production Ready", str(summary["production_ready"])),
        ("Blocking Issues", str(state["blocking_issue_count"])),
    ]
    card_html = "".join(
        f'<section class="card"><small>{html.escape(title)}</small>'
        f'<strong>{html.escape(value)}</strong></section>'
        for title, value in cards
    )

    safety = (
        "No safety violations detected."
        if not state["safety_violations"]
        else ", ".join(state["safety_violations"])
    )

    raw = html.escape(json.dumps(state, indent=2, sort_keys=True))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="15">
<title>AI Stock Bot Dashboard v2</title>
<style>
:root {{ color-scheme: dark; font-family: Arial, sans-serif; }}
body {{ margin:0; background:#0b1220; color:#e5e7eb; }}
header {{ padding:22px 28px; background:#111827; border-bottom:1px solid #334155; }}
main {{ padding:24px; max-width:1400px; margin:auto; }}
h1 {{ margin:0 0 8px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; }}
.card {{ background:#111827; border:1px solid #334155; border-radius:12px; padding:16px; }}
.card small {{ display:block; color:#94a3b8; margin-bottom:8px; }}
.card strong {{ font-size:25px; }}
.panel {{ background:#111827; border:1px solid #334155; border-radius:12px; padding:18px; margin-top:18px; overflow:auto; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:10px; border-bottom:1px solid #334155; text-align:left; }}
.badge {{ padding:4px 8px; border-radius:999px; font-size:12px; }}
.good {{ background:#14532d; color:#bbf7d0; }}
.warn {{ background:#713f12; color:#fef08a; }}
.bad {{ background:#7f1d1d; color:#fecaca; }}
.neutral {{ background:#334155; color:#e2e8f0; }}
pre {{ font-size:12px; white-space:pre-wrap; }}
.notice {{ color:#93c5fd; }}
</style>
</head>
<body>
<header>
<h1>AI Stock Bot Dashboard v2</h1>
<div>State: {badge(state['dashboard_state'])} &nbsp; Read-only local dashboard</div>
</header>
<main>
<div class="grid">{card_html}</div>
<section class="panel">
<h2>Safety Boundary</h2>
<p class="notice">{html.escape(safety)}</p>
<p>Paper only: {badge(state['paper_only'])} &nbsp;
Broker write: {badge(state['broker_write_enabled'])} &nbsp;
Live trading: {badge(state['live_trading_enabled'])} &nbsp;
External network: {badge(state['external_network_enabled'])}</p>
</section>
<section class="panel">
<h2>Runtime States</h2>
<table>
<thead><tr><th>Source</th><th>State</th><th>Status</th><th>Stage</th><th>Next phase</th><th>Blocking</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
</section>
<section class="panel">
<details><summary>Raw dashboard state</summary><pre>{raw}</pre></details>
</section>
</main>
</body>
</html>"""
