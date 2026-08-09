from __future__ import annotations

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import argparse, json, subprocess

ROOT_DEFAULT=Path(r"C:\stock-bot")

PATHS={
    "v294":Path("runtime/regime_aware_buy_shadow_v2_9_4/latest_runtime_observation_gate_v2_9_4.json"),
    "v30":Path("runtime/paper_2week_validation_v3_0/latest_validation_report.json"),
    "shadow_snapshot":Path("runtime/regime_aware_buy_shadow_v2_7/latest_shadow_snapshot.json"),
    "shadow_ledger":Path("runtime/regime_aware_buy_shadow_v2_7/shadow_candidate_ledger.jsonl"),
    "hook_ledger":Path("runtime/regime_aware_buy_shadow_v2_8_1/hook_ledger.jsonl"),
    "paper_session":Path("runtime/paper_autonomous_daily_session/session_ledger.jsonl"),
}

HTML='''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Stock Bot Operations Dashboard</title>
<style>
body{font-family:Arial,sans-serif;margin:0;background:#111827;color:#e5e7eb}
header{padding:18px 24px;background:#1f2937;display:flex;justify-content:space-between;align-items:center}
h1{font-size:20px;margin:0}.muted{color:#9ca3af;font-size:12px}
main{padding:20px;max-width:1400px;margin:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.card{background:#1f2937;border:1px solid #374151;border-radius:10px;padding:16px}
.card h2{font-size:14px;margin:0 0 10px;color:#93c5fd}
.big{font-size:26px;font-weight:700}.good{color:#86efac}.wait{color:#fde68a}.bad{color:#fca5a5}
table{width:100%;border-collapse:collapse;font-size:13px}
td,th{padding:7px;border-bottom:1px solid #374151;text-align:left}
button{background:#2563eb;color:white;border:0;padding:8px 12px;border-radius:7px;cursor:pointer}
</style>
</head>
<body>
<header><div><h1>AI Stock Bot Operations Dashboard</h1><div class="muted">Read-only local operations view</div></div><button onclick="load()">Refresh</button></header>
<main>
<div class="grid">
<div class="card"><h2>System Health</h2><div id="health" class="big">Loading...</div><div id="git" class="muted"></div></div>
<div class="card"><h2>Runtime Observation Gate</h2><div id="gate" class="big"></div><div id="gateDetail"></div></div>
<div class="card"><h2>Two-Week Paper Validation</h2><div id="validation" class="big"></div><div id="validationDetail"></div></div>
<div class="card"><h2>Paper Session</h2><div id="paper" class="big"></div><div id="paperDetail"></div></div>
<div class="card"><h2>Shadow Candidate</h2><div id="shadow" class="big"></div><div id="shadowDetail"></div></div>
<div class="card"><h2>Safety</h2><div id="safety"></div></div>
</div>
<br>
<div class="card"><h2>Recent Runtime Events</h2><table><thead><tr><th>Time</th><th>Source</th><th>Status / Stage</th></tr></thead><tbody id="events"></tbody></table></div>
</main>
<script>
function cls(status){status=String(status||""); if(status.includes("BLOCKED")||status.includes("FAIL"))return"bad"; if(status.includes("WAIT")||status.includes("ACTIVE"))return"wait"; return"good";}
function setv(id,text,status){let e=document.getElementById(id);e.textContent=text;e.className="big "+cls(status||text);}
async function load(){
 const r=await fetch('/api/status',{cache:'no-store'}); const d=await r.json();
 setv('health',d.health.overall,d.health.overall); document.getElementById('git').textContent=`${d.git.branch} ${d.git.head_short} | origin ${d.git.origin_main_short}`;
 setv('gate',d.runtime_gate.status,d.runtime_gate.status); document.getElementById('gateDetail').textContent=`Hooks ${d.runtime_gate.successful_hooks}/${d.runtime_gate.required_hooks}`;
 setv('validation',d.two_week.status,d.two_week.status); document.getElementById('validationDetail').textContent=`Days ${d.two_week.completed_days}/${d.two_week.required_days} | Remaining ${d.two_week.remaining_days}`;
 setv('paper',d.paper.latest_stage||'NO DATA',d.paper.latest_stage); document.getElementById('paperDetail').textContent=`Ledger records ${d.paper.record_count}`;
 setv('shadow',d.shadow.status,d.shadow.status); document.getElementById('shadowDetail').textContent=`Signals ${d.shadow.signal_count} | Outcomes ${d.shadow.outcome_count}`;
 document.getElementById('safety').innerHTML=`Broker write: <b>${d.safety.broker_write?'YES':'NO'}</b><br>Live order: <b>${d.safety.live_order?'YES':'NO'}</b><br>Production modified by dashboard: <b>NO</b>`;
 document.getElementById('events').innerHTML=d.recent_events.map(x=>`<tr><td>${x.time||''}</td><td>${x.source}</td><td>${x.status||''}</td></tr>`).join('');
}
load(); setInterval(load,15000);
</script>
</body></html>'''

def read_json(path:Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

def read_jsonl(path:Path,limit=None):
    if not path.exists():
        return []
    out=[]
    for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out[-limit:] if limit else out

def git_state(root:Path):
    def run(*args):
        p=subprocess.run(["git",*args],cwd=root,capture_output=True,text=True,check=False)
        return (p.stdout or "").strip()
    head=run("rev-parse","HEAD")
    origin=run("rev-parse","origin/main")
    return {
        "branch":run("branch","--show-current"),
        "head":head,
        "head_short":head[:8],
        "origin_main":origin,
        "origin_main_short":origin[:8],
        "synced":bool(head and origin and head==origin),
    }

def build_status(root:Path):
    v294=read_json(root/PATHS["v294"])
    v30=read_json(root/PATHS["v30"])
    shadow=read_json(root/PATHS["shadow_snapshot"])
    hooks=read_jsonl(root/PATHS["hook_ledger"])
    shadow_rows=read_jsonl(root/PATHS["shadow_ledger"])
    sessions=read_jsonl(root/PATHS["paper_session"])
    git=git_state(root)

    signals=[x for x in shadow_rows if x.get("event_type")=="SHADOW_SIGNAL"]
    outcomes=[x for x in shadow_rows if x.get("event_type")=="SHADOW_OUTCOME"]
    gate_hooks=int(v294.get("successful_hook_count",0) or 0)
    gate_req=int(v294.get("required_successful_hooks",3) or 3)
    vstate=v30.get("validation_state",{}) or {}

    broker_write=any(x.get("broker_write_performed") is True for x in hooks)
    live_order=any(x.get("live_order_submission_performed") is True for x in hooks)
    blocked=any([
        str(v294.get("status","")).startswith("BLOCKED"),
        str(v30.get("status","")).startswith("BLOCKED"),
        broker_write,
        live_order,
        not git["synced"],
    ])
    overall="BLOCKED_ATTENTION_REQUIRED" if blocked else ("WAITING_FOR_RUNTIME" if gate_hooks<gate_req else "HEALTHY")

    events=[]
    for x in hooks[-10:]:
        events.append({"time":x.get("timestamp_utc"),"source":"shadow-hook","status":x.get("status")})
    for x in sessions[-10:]:
        events.append({"time":x.get("timestamp_utc") or x.get("generated_at_utc"),"source":"paper-session","status":x.get("stage")})
    events=events[-15:]

    return {
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "health":{"overall":overall},
        "git":git,
        "runtime_gate":{
            "status":v294.get("status","NO_GATE_REPORT"),
            "successful_hooks":gate_hooks,
            "required_hooks":gate_req,
        },
        "two_week":{
            "status":v30.get("status","NO_V3_REPORT"),
            "completed_days":int(vstate.get("completed_trading_days",0) or 0),
            "required_days":int(vstate.get("required_trading_days",10) or 10),
            "remaining_days":int(vstate.get("remaining_trading_days",10) or 10),
        },
        "paper":{
            "record_count":len(sessions),
            "latest_stage":sessions[-1].get("stage") if sessions else None,
        },
        "shadow":{
            "status":shadow.get("status","NO_SHADOW_SNAPSHOT"),
            "signal_count":len(signals),
            "outcome_count":len(outcomes),
        },
        "safety":{"broker_write":broker_write,"live_order":live_order},
        "recent_events":events,
        "contracts":{
            "read_only":True,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "production_parameter_modified":False,
        },
    }

class Handler(BaseHTTPRequestHandler):
    root=ROOT_DEFAULT
    def log_message(self,fmt,*args):
        pass
    def send_body(self,code,ctype,body:bytes):
        self.send_response(code)
        self.send_header("Content-Type",ctype)
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        p=urlparse(self.path).path
        if p=="/":
            self.send_body(200,"text/html; charset=utf-8",HTML.encode())
        elif p=="/api/status":
            self.send_body(200,"application/json; charset=utf-8",json.dumps(build_status(self.root),indent=2).encode())
        elif p=="/health":
            self.send_body(200,"application/json; charset=utf-8",json.dumps({"status":"PASS","read_only":True}).encode())
        else:
            self.send_body(404,"application/json",b'{"error":"not found"}')

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=str(ROOT_DEFAULT))
    p.add_argument("--host",default="127.0.0.1")
    p.add_argument("--port",type=int,default=8765)
    a=p.parse_args()
    Handler.root=Path(a.root).resolve()
    server=ThreadingHTTPServer((a.host,a.port),Handler)
    print(f"V3.1 dashboard: http://{a.host}:{a.port}")
    print("READ_ONLY: true")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
