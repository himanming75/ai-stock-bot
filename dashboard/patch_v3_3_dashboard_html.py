
from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()
    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if 'id="alertSummary"' in text:
        print("V3.3 HTML PATCH ALREADY PRESENT")
        return 0

    marker = '<div class="grid">'
    block = "\n".join([
        '<div class="section">',
        '<h3>Alerts / Health</h3>',
        '<div class="grid">',
        '<div class="card"><h2>Critical</h2><div id="alertCritical" class="big"></div></div>',
        '<div class="card"><h2>Warnings</h2><div id="alertWarning" class="big"></div></div>',
        '<div class="card"><h2>Info</h2><div id="alertInfo" class="big"></div></div>',
        '<div class="card"><h2>Alert Summary</h2><div id="alertSummary" class="note"></div></div>',
        '</div>',
        '</div>',
        '',
    ]) + "\n"

    pos = text.find(marker)
    if pos < 0:
        raise RuntimeError("dashboard grid marker not found")
    text = text[:pos] + block + text[pos:]

    js_marker = "  setv('health',d.health.overall,d.health.overall);"
    js_lines = [
        "  let alerts=[];",
        "  if(String(d.health?.overall||'').includes('BLOCKED')) alerts.push(['CRITICAL','SYSTEM_BLOCKED',d.health.overall]);",
        "  if((d.runtime_gate?.successful_hooks??0)<(d.runtime_gate?.required_hooks??3)) alerts.push(['INFO','RUNTIME_GATE_WAITING',`Hooks ${d.runtime_gate?.successful_hooks??0}/${d.runtime_gate?.required_hooks??3}`]);",
        "  if((d.two_week?.completed_days??0)<(d.two_week?.required_days??10)) alerts.push(['INFO','TWO_WEEK_PROGRESS',`Validation ${d.two_week?.completed_days??0}/${d.two_week?.required_days??10}`]);",
        "  if(d.git?.available===false) alerts.push(['WARNING','GIT_UNAVAILABLE',d.git?.error||'Git unavailable']);",
        "  if(d.git?.synced===false) alerts.push(['WARNING','GIT_NOT_SYNCED','Local HEAD differs from origin/main']);",
        "  let critical=alerts.filter(x=>x[0]==='CRITICAL').length;",
        "  let warning=alerts.filter(x=>x[0]==='WARNING').length;",
        "  let info=alerts.filter(x=>x[0]==='INFO').length;",
        "  setv('alertCritical',critical,critical>0?'FAIL':'PASS');",
        "  setv('alertWarning',warning,warning>0?'WAIT':'PASS');",
        "  setv('alertInfo',info,'WAIT');",
        "  document.getElementById('alertSummary').textContent=alerts.map(x=>x[1]+': '+x[2]).join(' | ')||'No active alerts';",
    ]
    js = "\n".join(js_lines) + "\n"

    if js_marker not in text:
        raise RuntimeError("dashboard JS marker not found")
    text = text.replace(js_marker, js + js_marker, 1)
    text = text.replace(
        "Alpaca Paper · Read-only · V3.2",
        "Alpaca Paper · Read-only · V3.3 Health Layer",
        1,
    )

    target.write_text(text, encoding="utf-8")
    print("V3.3 HTML ALERT PATCH: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
