from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .service import PortfolioContextCertificationService


HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio Context AI / 포트폴리오 컨텍스트 AI</title>
<style>
body{font-family:Arial,sans-serif;margin:24px;background:#f5f7fa;color:#17202a}
.card{background:white;border-radius:10px;padding:16px;margin:12px 0;box-shadow:0 2px 8px #0001}
.safe{background:#e8f8f5;padding:12px;border-radius:8px}
table{width:100%;border-collapse:collapse}
th,td{padding:9px;border-bottom:1px solid #e5e7e9;text-align:left}
</style>
</head>
<body>
<h1>Portfolio Context AI</h1>
<p>포트폴리오 컨텍스트 · Cross-Asset Correlation · Signal Feedback</p>
<div class="safe">Read Only / 읽기 전용 — Broker Write OFF · Allocation OFF · Live Learning OFF</div>
<div id="summary" class="card">Loading / 불러오는 중...</div>
<div id="pairs" class="card"></div>
<script>
fetch('/api/report').then(r=>r.json()).then(data=>{
 const p=data.portfolio_context;
 const f=data.signal_feedback;
 document.getElementById('summary').innerHTML=`
 <h2>Portfolio / 포트폴리오</h2>
 <p>Risk / 위험: ${p.portfolio_risk_level_i18n.en} / ${p.portfolio_risk_level_i18n.ko}</p>
 <p>Diversification / 분산: ${p.diversification_state_i18n.en} / ${p.diversification_state_i18n.ko}</p>
 <p>Average |Correlation|: ${p.average_absolute_correlation.toFixed(3)}</p>
 <p>Feedback / 피드백: ${f.feedback_health_i18n.en} / ${f.feedback_health_i18n.ko}</p>
 <p>Directional Accuracy / 방향 정확도: ${(f.directional_accuracy*100).toFixed(1)}%</p>`;
 const rows=p.pairs.map(x=>`<tr><td>${x.left}</td><td>${x.right}</td><td>${x.correlation.toFixed(3)}</td><td>${x.classification}</td></tr>`).join('');
 document.getElementById('pairs').innerHTML=`<h2>Correlation / 상관관계</h2><table><tr><th>Left</th><th>Right</th><th>Correlation</th><th>Class</th></tr>${rows}</table>`;
});
</script>
</body></html>"""


def run_dashboard(host: str, port: int, output_dir: Path) -> None:
    result = PortfolioContextCertificationService().evaluate(
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
    print("LIVE LEARNING: OFF")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
