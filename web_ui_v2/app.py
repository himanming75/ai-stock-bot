from __future__ import annotations

import argparse
import html
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest_v2.engine import run_backtest
from backtest_v2.io import load_json, parse_input
from explainability_engine.io import load_json as load_explainability_json


ALLOWED_INPUTS = {
    "single_asset_sample": (
        ROOT / "release/v87_01_to_v87_08/input/backtest_sample.json"
    ),
}


def safe_json(path: Path) -> dict:
    try:
        return load_json(path)
    except Exception:
        return {}


def load_ui_state() -> dict:
    backtest = safe_json(
        ROOT / "release/v87_01_to_v87_08/actual/backtest_v2_result.json"
    )
    validation = safe_json(
        ROOT / "release/v87_09_to_v87_16/actual/"
        "walk_forward_stress_validation_result.json"
    )
    multi_asset = safe_json(
        ROOT / "release/v87_17_to_v87_24/actual/"
        "multi_asset_backtest_result.json"
    )
    explainability = load_explainability_json(
        ROOT / "release/v86_25_to_v86_32/actual/"
        "ai_explainability_result.json"
    )
    return {
        "backtest": backtest,
        "validation": validation,
        "multi_asset": multi_asset,
        "explainability": explainability,
        "paper_only": True,
        "read_only_broker": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }


def svg_line(values: list[float], width: int = 900, height: int = 260) -> str:
    if not values:
        return '<div class="empty">No curve data available.</div>'
    minimum = min(values)
    maximum = max(values)
    span = max(maximum - minimum, 1e-9)
    points = []
    for index, value in enumerate(values):
        x = index / max(1, len(values) - 1) * width
        y = height - ((value - minimum) / span * height)
        points.append(f"{x:.2f},{y:.2f}")
    polyline = " ".join(points)
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img">'
        f'<polyline points="{polyline}" fill="none" stroke="currentColor" '
        f'stroke-width="3"/></svg>'
    )


def badge(value) -> str:
    text = str(value)
    upper = text.upper()
    css = "neutral"
    if upper in {"PASS", "TRUE", "READY", "CERTIFIED"} or "VALIDATED" in upper:
        css = "good"
    elif "REVIEW" in upper or "PENDING" in upper or upper == "FALSE":
        css = "warn"
    elif "FAIL" in upper or "BLOCKED" in upper:
        css = "bad"
    return f'<span class="badge {css}">{html.escape(text)}</span>'


def render_home(state: dict, message: str = "") -> str:
    backtest = state.get("backtest", {}).get("backtest", {})
    validation = state.get("validation", {}).get("validation", {})
    multi = state.get("multi_asset", {}).get("multi_asset", {})
    explain = state.get("explainability", {}).get("report", {})

    trades = backtest.get("trades", [])
    trade_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(row.get('entry_time', '')))}</td>"
        f"<td>{html.escape(str(row.get('exit_time', '')))}</td>"
        f"<td>{float(row.get('entry_price', 0)):.4f}</td>"
        f"<td>{float(row.get('exit_price', 0)):.4f}</td>"
        f"<td>{float(row.get('net_pnl', 0)):.2f}</td>"
        f"<td>{float(row.get('return_pct', 0)):.2f}%</td>"
        "</tr>"
        for row in trades[:100]
    ) or '<tr><td colspan="6">No trades available.</td></tr>'

    risks = []
    for section in (
        explain.get("strategy_explanation", {}),
        explain.get("portfolio_explanation", {}),
    ):
        risks.extend(section.get("risk_factors", []))
    risk_html = "".join(
        f'<li><strong>{html.escape(str(row.get("severity", "")))}</strong> '
        f'{html.escape(str(row.get("message", "")))}</li>'
        for row in risks
    ) or "<li>No explainability risk data available.</li>"

    multi_portfolio = multi.get("portfolio", {})
    cards = [
        ("Backtest State", state.get("backtest", {}).get("state", "NOT_AVAILABLE")),
        ("Total Return", f"{float(backtest.get('total_return_pct', 0)):.2f}%"),
        ("Max Drawdown", f"{float(backtest.get('maximum_drawdown_pct', 0)):.2f}%"),
        ("Trades", str(backtest.get("trade_statistics", {}).get("total_trades", 0))),
        ("Robustness", state.get("validation", {}).get("state", "NOT_AVAILABLE")),
        ("Overfit Risk", str(validation.get("overfit", {}).get("overfit_risk_level", "N/A"))),
        ("Multi-Asset", state.get("multi_asset", {}).get("state", "NOT_AVAILABLE")),
        ("Excess Return", f"{float(multi.get('excess_return_pct', 0)):.2f}%"),
    ]
    card_html = "".join(
        f'<section class="card"><small>{html.escape(title)}</small>'
        f'<strong>{html.escape(value)}</strong></section>'
        for title, value in cards
    )

    message_html = (
        f'<div class="notice">{html.escape(message)}</div>' if message else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Stock Bot Web UI v2</title>
<style>
:root {{ color-scheme:dark; font-family:Arial,sans-serif; }}
body {{ margin:0; background:#0b1220; color:#e5e7eb; }}
header {{ padding:20px 28px; background:#111827; border-bottom:1px solid #334155; }}
main {{ max-width:1450px; margin:auto; padding:24px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }}
.card,.panel {{ background:#111827; border:1px solid #334155; border-radius:12px; padding:16px; }}
.panel {{ margin-top:18px; overflow:auto; }}
.card small {{ display:block; color:#94a3b8; margin-bottom:8px; }}
.card strong {{ font-size:21px; }}
button,select {{ padding:10px 14px; border-radius:8px; border:1px solid #475569; }}
button {{ cursor:pointer; font-weight:bold; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:9px; border-bottom:1px solid #334155; text-align:left; }}
svg {{ width:100%; height:260px; color:#93c5fd; }}
.badge {{ padding:4px 8px; border-radius:999px; font-size:12px; }}
.good {{ background:#14532d; color:#bbf7d0; }}
.warn {{ background:#713f12; color:#fef08a; }}
.bad {{ background:#7f1d1d; color:#fecaca; }}
.neutral {{ background:#334155; }}
.notice {{ background:#1e3a8a; padding:12px; border-radius:8px; margin-bottom:16px; }}
.safety {{ color:#93c5fd; }}
a {{ color:#93c5fd; }}
</style>
</head>
<body>
<header>
<h1>AI Stock Bot Web UI v2</h1>
<div class="safety">Localhost only · Paper only · No broker writes · No live trading</div>
</header>
<main>
{message_html}
<div class="grid">{card_html}</div>

<section class="panel">
<h2>Run Local Backtest</h2>
<form method="post" action="/run-backtest">
<select name="input_key">
<option value="single_asset_sample">Single-asset sample</option>
</select>
<button type="submit">Run Backtest</button>
</form>
<p>This action only runs the local historical simulation and rewrites local result JSON.</p>
</section>

<section class="panel">
<h2>Equity Curve</h2>
{svg_line([float(v) for v in backtest.get("equity_curve", [])])}
</section>

<section class="panel">
<h2>Portfolio Equity Curve</h2>
{svg_line([float(v) for v in multi_portfolio.get("equity_curve", [])])}
</section>

<section class="panel">
<h2>Risk Warnings</h2>
<ul>{risk_html}</ul>
</section>

<section class="panel">
<h2>Trade Log</h2>
<table>
<thead><tr><th>Entry</th><th>Exit</th><th>Entry Price</th><th>Exit Price</th><th>Net PnL</th><th>Return</th></tr></thead>
<tbody>{trade_rows}</tbody>
</table>
</section>

<section class="panel">
<h2>Downloads</h2>
<p>
<a href="/download/backtest">Backtest JSON</a> ·
<a href="/download/validation">Validation JSON</a> ·
<a href="/download/multi-asset">Multi-Asset JSON</a> ·
<a href="/download/explainability">Explainability JSON</a>
</p>
</section>
</main>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "AIStockBotWebUIV2/1.0"

    def log_message(self, format, *args):
        return

    def send_bytes(self, body: bytes, content_type: str, status: int = 200, filename: str = ""):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        state = load_ui_state()
        if path in {"/", "/index.html"}:
            self.send_bytes(render_home(state).encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/health":
            self.send_bytes(b'{"status":"ok"}\n', "application/json")
            return
        downloads = {
            "/download/backtest": (
                ROOT / "release/v87_01_to_v87_08/actual/backtest_v2_result.json",
                "backtest_v2_result.json",
            ),
            "/download/validation": (
                ROOT / "release/v87_09_to_v87_16/actual/walk_forward_stress_validation_result.json",
                "walk_forward_stress_validation_result.json",
            ),
            "/download/multi-asset": (
                ROOT / "release/v87_17_to_v87_24/actual/multi_asset_backtest_result.json",
                "multi_asset_backtest_result.json",
            ),
            "/download/explainability": (
                ROOT / "release/v86_25_to_v86_32/actual/ai_explainability_result.json",
                "ai_explainability_result.json",
            ),
        }
        if path in downloads:
            file_path, filename = downloads[path]
            if not file_path.exists():
                self.send_bytes(b"File not found\n", "text/plain", 404)
                return
            self.send_bytes(file_path.read_bytes(), "application/json", 200, filename)
            return
        self.send_bytes(b"Not Found\n", "text/plain", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/run-backtest":
            self.send_bytes(b"Not Found\n", "text/plain", 404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        key = form.get("input_key", [""])[0]
        input_path = ALLOWED_INPUTS.get(key)
        if input_path is None:
            self.send_bytes(b"Invalid input\n", "text/plain", 400)
            return

        payload = load_json(input_path)
        symbol, bars, policy = parse_input(payload)
        result = run_backtest(symbol, bars, policy)

        result_path = ROOT / "release/v87_01_to_v87_08/actual/backtest_v2_result.json"
        current = safe_json(result_path)
        current["backtest"] = result
        current["state"] = "BACKTEST_ENGINE_V2_READY"
        current["status"] = "PASS"
        current["paper_only"] = True
        current["broker_write_enabled"] = False
        current["order_submission_enabled"] = False
        current["live_trading_enabled"] = False
        current["external_network_enabled"] = False
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(current, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        state = load_ui_state()
        self.send_bytes(
            render_home(state, f"Backtest completed for {symbol}.").encode("utf-8"),
            "text/html; charset=utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8601)
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Web UI v2 only permits localhost binding.")

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"WEB_UI_URL=http://{args.host}:{args.port}")
    print("Local paper-only UI. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
