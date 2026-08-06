from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .service import PortfolioOptimizerCertificationService


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio Optimizer / 포트폴리오 최적화</title>
<style>
body{font-family:Arial,sans-serif;margin:24px;background:#f5f7fa;color:#17202a}
.card{background:white;border-radius:10px;padding:16px;margin:12px 0;box-shadow:0 2px 8px #0001}
.safe{background:#e8f8f5;padding:12px;border-radius:8px}
table{width:100%;border-collapse:collapse}
th,td{padding:9px;border-bottom:1px solid #e5e7e9;text-align:left}
</style>
</head>
<body>
<h1>Portfolio Optimizer</h1>
<p>포트폴리오 최적화 · Scenario Stress · Capital Guardrail</p>
<div class="safe">Simulation Only / 시뮬레이션 전용 — Allocation OFF · Broker Write OFF</div>
<div id="weights" class="card">Loading / 불러오는 중...</div>
<div id="stress" class="card"></div>
<script>
fetch('/api/report').then(r=>r.json()).then(data=>{
 const w=Object.entries(data.optimizer.candidate_weights)
  .map(x=>`<tr><td>${x[0]}</td><td>${(x[1]*100).toFixed(2)}%</td></tr>`).join('');
 document.getElementById('weights').innerHTML=`<h2>Candidate Weights / 후보 비중</h2><table>${w}</table>`;
 const s=data.stress_results.map(x=>`<tr><td>${x.scenario_i18n.en} / ${x.scenario_i18n.ko}</td><td>${(x.portfolio_return*100).toFixed(2)}%</td><td>${(x.estimated_drawdown*100).toFixed(2)}%</td></tr>`).join('');
 document.getElementById('stress').innerHTML=`<h2>Stress / 스트레스</h2><table><tr><th>Scenario</th><th>Return</th><th>Drawdown</th></tr>${s}</table><p>Guardrail: ${data.guardrails.status_i18n.en} / ${data.guardrails.status_i18n.ko}</p>`;
});
</script>
</body></html>"""


def run_dashboard(host: str, port: int, output_dir: Path) -> None:
    result = PortfolioOptimizerCertificationService().evaluate(
        output_dir=output_dir
    )
    report = result["report"]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if urlparse(self.path).path == "/api/report":
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
    print("POSITION ALLOCATION: OFF")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
