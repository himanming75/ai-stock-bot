from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .service import MultiTimeframeAICertificationService


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Multi-Timeframe AI / 멀티 타임프레임 AI</title>
<style>
body{font-family:Arial,sans-serif;margin:24px;background:#f5f7fa;color:#17202a}
h1{margin-bottom:4px}.sub{color:#566573;margin-bottom:20px}
.card{background:white;border-radius:10px;padding:16px;margin:12px 0;box-shadow:0 2px 8px #0001}
table{width:100%;border-collapse:collapse;background:white}
th,td{padding:10px;border-bottom:1px solid #e5e7e9;text-align:left;font-size:14px}
.badge{padding:4px 8px;border-radius:12px;background:#eaf2f8;display:inline-block}
.safe{background:#e8f8f5;padding:12px;border-radius:8px;margin:16px 0}
</style>
</head>
<body>
<h1>Multi-Timeframe AI</h1>
<div class="sub">멀티 타임프레임 AI · Market Regime 2.0 · Advanced Confidence</div>
<div class="safe">Analysis Only / 분석 전용 — Broker Write OFF · Order Submission OFF · Live Trading OFF</div>
<div id="app" class="card">Loading / 불러오는 중...</div>
<script>
fetch('/api/report').then(r=>r.json()).then(data=>{
 const rows=data.analyses.map(x=>`<tr>
 <td>${x.rank}</td><td>${x.symbol}</td>
 <td><span class="badge">${x.action_i18n.en} / ${x.action_i18n.ko}</span></td>
 <td>${x.market_regime_2_i18n.en} / ${x.market_regime_2_i18n.ko}</td>
 <td>${(x.probability*100).toFixed(1)}%</td>
 <td>${(x.expected_return*100).toFixed(2)}%</td>
 <td>${(x.expected_risk*100).toFixed(2)}%</td>
 <td>${x.reward_risk.toFixed(2)}</td>
 <td>${(x.confidence_calibration.calibrated_confidence*100).toFixed(1)}%</td>
 </tr>`).join('');
 document.getElementById('app').innerHTML=`<table><thead><tr>
 <th>#</th><th>Symbol / 종목</th><th>Signal / 신호</th>
 <th>Regime / 국면</th><th>Probability / 확률</th>
 <th>Expected Return / 기대수익</th><th>Expected Risk / 기대위험</th>
 <th>R/R</th><th>Confidence / 신뢰도</th>
 </tr></thead><tbody>${rows}</tbody></table>`;
}).catch(e=>{document.getElementById('app').textContent=String(e)});
</script>
</body></html>"""


def run_dashboard(host: str, port: int, output_dir: Path) -> None:
    result = MultiTimeframeAICertificationService().evaluate(
        output_dir=output_dir
    )
    report = result["report"]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/report":
                payload = json.dumps(
                    report,
                    ensure_ascii=False,
                    sort_keys=True,
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            payload = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):
            return

    print(f"DASHBOARD READY: http://{host}:{port}")
    print("BROKER WRITE: OFF")
    print("ORDER SUBMISSION: OFF")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
