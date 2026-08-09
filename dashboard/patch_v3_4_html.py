
from __future__ import annotations

from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\stock-bot")
    args = parser.parse_args()

    target = Path(args.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if 'id="equityChart"' in text:
        print("V3.4 VISUALIZATION HTML ALREADY PRESENT")
        return 0

    style_marker = "@media(max-width:900px){.two{grid-template-columns:1fr}}"
    css_lines = [
        ".chartbox{height:240px;background:#111820;border:1px solid #30363d;border-radius:8px;padding:8px}",
        ".chartbox svg{width:100%;height:100%;display:block}",
        ".chart-empty{display:flex;align-items:center;justify-content:center;height:100%;color:#8b949e;font-size:12px}",
        ".progress-row{display:grid;grid-template-columns:repeat(10,1fr);gap:6px}",
        ".progress-cell{height:32px;border:1px solid #30363d;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:11px}",
        ".progress-cell.done{background:#1f6f3d}.progress-cell.waiting{background:#21262d}",
        ".alloc-row{display:flex;align-items:center;gap:8px;margin:7px 0}",
        ".alloc-label{width:70px;font-size:12px}",
        ".alloc-track{flex:1;height:12px;background:#21262d;border-radius:8px;overflow:hidden}",
        ".alloc-fill{height:100%;background:#388bfd}",
        ".alloc-pct{width:52px;text-align:right;font-size:11px;color:#8b949e}",
    ]
    css = "\n" + "\n".join(css_lines) + "\n"

    if style_marker not in text:
        raise RuntimeError("style marker not found")
    text = text.replace(style_marker, style_marker + css, 1)

    timeline_marker = '<div class="section">\n<h3>Recent Timeline</h3>'
    visual_lines = [
        '<div class="section">',
        '<h3>Visualization</h3>',
        '<div class="two">',
        '<div><h3>Equity Curve</h3><div id="equityChart" class="chartbox"></div></div>',
        '<div><h3>Daily Realized P/L</h3><div id="pnlChart" class="chartbox"></div></div>',
        '</div>',
        '<div class="two" style="margin-top:12px">',
        '<div><h3>Position Allocation</h3><div id="allocationChart" class="card"></div></div>',
        '<div><h3>10-Day Validation Progress</h3><div id="validationChart" class="card"></div></div>',
        '</div>',
        '<div class="grid" style="margin-top:12px">',
        '<div class="card"><h2>Current Unrealized P/L</h2><div id="vizUnrealized" class="big"></div></div>',
        '<div class="card"><h2>Equity History Points</h2><div id="vizEquityPoints" class="big"></div></div>',
        '<div class="card"><h2>Daily P/L Points</h2><div id="vizPnlPoints" class="big"></div></div>',
        '<div class="card"><h2>Visualization Status</h2><div id="vizStatus" class="note"></div></div>',
        '</div>',
        '</div>',
        '',
    ]
    visual_html = "\n".join(visual_lines)

    if timeline_marker not in text:
        raise RuntimeError("timeline marker not found")
    text = text.replace(timeline_marker, visual_html + timeline_marker, 1)

    load_marker = "async function load(){"
    function_lines = [
        "function lineSvg(points,width=700,height=220){",
        "  if(!points||points.length<2)return '<div class=\"chart-empty\">Not enough historical points yet</div>';",
        "  let vals=points.map(x=>Number(x.value)).filter(Number.isFinite);",
        "  if(vals.length<2)return '<div class=\"chart-empty\">No numeric history yet</div>';",
        "  let lo=Math.min(...vals),hi=Math.max(...vals);",
        "  if(hi===lo){hi=lo+1;}",
        "  let pad=18;",
        "  let coords=vals.map((v,i)=>{let x=pad+(width-pad*2)*(i/(vals.length-1));let y=pad+(height-pad*2)*(1-(v-lo)/(hi-lo));return [x,y];});",
        "  let poly=coords.map(p=>p[0].toFixed(1)+','+p[1].toFixed(1)).join(' ');",
        "  return `<svg viewBox=\"0 0 ${width} ${height}\" preserveAspectRatio=\"none\"><line x1=\"${pad}\" y1=\"${height-pad}\" x2=\"${width-pad}\" y2=\"${height-pad}\" stroke=\"#30363d\"/><polyline fill=\"none\" stroke=\"#58a6ff\" stroke-width=\"3\" points=\"${poly}\"/><text x=\"${pad}\" y=\"14\" fill=\"#8b949e\" font-size=\"10\">${hi.toFixed(2)}</text><text x=\"${pad}\" y=\"${height-3}\" fill=\"#8b949e\" font-size=\"10\">${lo.toFixed(2)}</text></svg>`;",
        "}",
        "function barSvg(points,width=700,height=220){",
        "  if(!points||points.length===0)return '<div class=\"chart-empty\">No realized P/L points yet</div>';",
        "  let vals=points.map(x=>Number(x.value)).filter(Number.isFinite);",
        "  if(vals.length===0)return '<div class=\"chart-empty\">No numeric P/L yet</div>';",
        "  let max=Math.max(1,...vals.map(v=>Math.abs(v))),pad=18,zero=height/2;",
        "  let bw=(width-pad*2)/vals.length;",
        "  let bars=vals.map((v,i)=>{let h=(Math.abs(v)/max)*(height/2-pad);let x=pad+i*bw+2,y=v>=0?zero-h:zero;let fill=v>=0?'#3fb950':'#f85149';return `<rect x=\"${x.toFixed(1)}\" y=\"${y.toFixed(1)}\" width=\"${Math.max(2,bw-4).toFixed(1)}\" height=\"${h.toFixed(1)}\" fill=\"${fill}\"/>`;}).join('');",
        "  return `<svg viewBox=\"0 0 ${width} ${height}\" preserveAspectRatio=\"none\"><line x1=\"${pad}\" y1=\"${zero}\" x2=\"${width-pad}\" y2=\"${zero}\" stroke=\"#8b949e\"/>${bars}</svg>`;",
        "}",
        "function allocationHtml(rows){",
        "  if(!rows||rows.length===0)return '<div class=\"note\">No position market values available</div>';",
        "  return rows.map(x=>`<div class=\"alloc-row\"><div class=\"alloc-label\">${x.symbol}</div><div class=\"alloc-track\"><div class=\"alloc-fill\" style=\"width:${(100*x.weight).toFixed(1)}%\"></div></div><div class=\"alloc-pct\">${(100*x.weight).toFixed(1)}%</div></div>`).join('');",
        "}",
        "function validationHtml(rows){",
        "  if(!rows||rows.length===0)return '<div class=\"note\">Validation slots unavailable</div>';",
        "  return `<div class=\"progress-row\">${rows.map(x=>`<div class=\"progress-cell ${x.completed?'done':'waiting'}\">D${x.day}</div>`).join('')}</div>`;",
        "}",
    ]
    functions = "\n".join(function_lines) + "\n"

    if load_marker not in text:
        raise RuntimeError("load function marker not found")
    text = text.replace(load_marker, functions + load_marker, 1)

    sources_marker = "  document.getElementById('sources').textContent='Runtime sources: '+d.data_sources.join(' | ');"
    viz_lines = [
        "  let v=d.visualization||{};",
        "  document.getElementById('equityChart').innerHTML=lineSvg(v.equity_history||[]);",
        "  document.getElementById('pnlChart').innerHTML=barSvg(v.daily_realized_pnl||[]);",
        "  document.getElementById('allocationChart').innerHTML=allocationHtml(v.position_allocation||[]);",
        "  document.getElementById('validationChart').innerHTML=validationHtml(v.validation_slots||[]);",
        "  setv('vizUnrealized',money(v.summary?.current_unrealized_pnl));",
        "  setv('vizEquityPoints',v.summary?.equity_point_count??0);",
        "  setv('vizPnlPoints',v.summary?.daily_realized_point_count??0);",
        "  document.getElementById('vizStatus').textContent=d.visualization_status||'UNKNOWN';",
    ]
    viz_js = "\n".join(viz_lines) + "\n"

    if sources_marker not in text:
        raise RuntimeError("sources JS marker not found")
    text = text.replace(sources_marker, viz_js + sources_marker, 1)

    text = text.replace(
        "Alpaca Paper · Read-only · V3.3 Health Layer",
        "Alpaca Paper · Read-only · V3.4 Visualization Layer",
        1,
    )

    target.write_text(text, encoding="utf-8")
    print("V3.4 VISUALIZATION HTML PATCH: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
