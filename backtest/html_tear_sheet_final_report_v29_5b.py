#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, hashlib, html, json, math, os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

VERSION = "29.5B"
GENERATOR_NAME = "HTML Tear Sheet & Final Report Generator"

def _utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _safe_float(value):
    if value is None or isinstance(value, bool): return None
    if isinstance(value, (int,float)):
        v=float(value); return v if math.isfinite(v) else None
    if isinstance(value,str):
        raw=value.strip().replace(',',''); pct=raw.endswith('%')
        if pct: raw=raw[:-1]
        try: v=float(raw)
        except ValueError: return None
        if pct: v/=100.0
        return v if math.isfinite(v) else None
    return None

def _first(mapping,names,default=None):
    if not isinstance(mapping,Mapping): return default
    lower={str(k).lower():v for k,v in mapping.items()}
    for name in names:
        if name in mapping: return mapping[name]
        if name.lower() in lower: return lower[name.lower()]
    return default

def _as_mapping(value): return dict(value) if isinstance(value,Mapping) else {}

def _as_rows(value):
    if isinstance(value,list): return [dict(r) for r in value if isinstance(r,Mapping)]
    if isinstance(value,Mapping):
        rows=[]
        for k,v in value.items():
            if isinstance(v,Mapping):
                row=dict(v); row.setdefault('period',k); rows.append(row)
            else: rows.append({'period':k,'value':v})
        return rows
    return []

def _deep_find(payload,aliases):
    wanted={a.lower() for a in aliases}; queue=[payload]; seen=set()
    while queue:
        cur=queue.pop(0)
        if id(cur) in seen: continue
        seen.add(id(cur))
        if isinstance(cur,Mapping):
            for k,v in cur.items():
                if str(k).lower() in wanted: return v
            queue.extend(cur.values())
        elif isinstance(cur,list): queue.extend(cur)
    return None

def _label(key): return str(key).replace('_',' ').replace('-',' ').strip().title()

def _status_class(value):
    if isinstance(value,bool): return 'good' if value else 'bad'
    t=str(value).strip().upper()
    if t in {'PASS','PASSED','OK','VALID','VERIFIED','SUCCESS','TRUE','GREEN'}: return 'good'
    if t in {'FAIL','FAILED','INVALID','ERROR','FALSE','RED'}: return 'bad'
    if t in {'WARN','WARNING','YELLOW','REVIEW'}: return 'warn'
    return ''

def _format_number(value,key=''):
    if value is None: return '—'
    if isinstance(value,bool): return 'PASS' if value else 'FAIL'
    if isinstance(value,str): return html.escape(value)
    n=_safe_float(value)
    if n is None: return html.escape(str(value))
    lk=key.lower()
    if any(x in lk for x in ('return','drawdown','rate','win_','loss_','exposure')): return f'{n*100:.2f}%'
    if any(x in lk for x in ('capital','equity','pnl','profit','cost','value','cash','notional')): return f'${n:,.2f}'
    if any(x in lk for x in ('sharpe','sortino','calmar','factor','ratio')): return f'{n:.3f}'
    return f'{int(n):,}' if n.is_integer() else f'{n:,.4f}'.rstrip('0').rstrip('.')

def _canonical_points(value,value_aliases):
    out=[]
    if isinstance(value,Mapping):
        for k,v in value.items():
            n=_safe_float(v)
            if n is not None: out.append((str(k),n))
        return out
    if not isinstance(value,list): return out
    for i,item in enumerate(value):
        if isinstance(item,Mapping):
            label=_first(item,['date','timestamp','time','period','index','label'],str(i))
            raw=_first(item,value_aliases)
            if raw is None:
                vals=[v for k,v in item.items() if str(k).lower() not in {'date','timestamp','time','period','index','label'} and _safe_float(v) is not None]
                raw=vals[0] if vals else None
            n=_safe_float(raw)
            if n is not None: out.append((str(label),n))
        else:
            n=_safe_float(item)
            if n is not None: out.append((str(i),n))
    return out

def _line_svg(points,title,percent=False):
    if len(points)<2: return '<div class="empty">Not enough data to draw chart.</div>'
    w,h=900,260; pl,pr,pt,pb=72,24,28,48; cw=w-pl-pr; ch=h-pt-pb
    vals=[v for _,v in points]; lo,hi=min(vals),max(vals)
    if math.isclose(lo,hi): lo-=1; hi+=1
    coords=[]
    for i,(_,v) in enumerate(points):
        x=pl+cw*i/max(1,len(points)-1); y=pt+ch*(hi-v)/(hi-lo); coords.append((x,y))
    path=' '.join(('M' if i==0 else 'L')+f' {x:.2f} {y:.2f}' for i,(x,y) in enumerate(coords))
    area=f'M {coords[0][0]:.2f} {pt+ch:.2f} '+' '.join(f'L {x:.2f} {y:.2f}' for x,y in coords)+f' L {coords[-1][0]:.2f} {pt+ch:.2f} Z'
    grid=[]
    for i in range(5):
        y=pt+ch*i/4; v=hi-(hi-lo)*i/4; txt=f'{v*100:.1f}%' if percent else f'{v:,.2f}'
        grid.append(f'<line x1="{pl}" y1="{y:.2f}" x2="{w-pr}" y2="{y:.2f}" class="grid"/><text x="{pl-10}" y="{y+4:.2f}" text-anchor="end" class="axis">{html.escape(txt)}</text>')
    first=html.escape(points[0][0]); middle=html.escape(points[len(points)//2][0]); last=html.escape(points[-1][0])
    return f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}"><title>{html.escape(title)}</title>{"".join(grid)}<path d="{area}" class="area"/><path d="{path}" class="line"/><text x="{pl}" y="{h-16}" class="axis">{first}</text><text x="{w/2}" y="{h-16}" text-anchor="middle" class="axis">{middle}</text><text x="{w-pr}" y="{h-16}" text-anchor="end" class="axis">{last}</text></svg>'

def _table(rows,max_rows=50):
    if not rows: return '<div class="empty">No records available.</div>'
    cols=[]
    for row in rows[:max_rows]:
        for k in row:
            if k not in cols: cols.append(k)
    body=[]
    for row in rows[:max_rows]:
        body.append('<tr>'+''.join(f'<td class="{_status_class(row.get(c))}">{_format_number(row.get(c),c)}</td>' for c in cols)+'</tr>')
    note=f'<div class="table-note">Showing {max_rows:,} of {len(rows):,} rows.</div>' if len(rows)>max_rows else ''
    return '<div class="table-wrap"><table><thead><tr>'+''.join(f'<th>{html.escape(_label(c))}</th>' for c in cols)+'</tr></thead><tbody>'+''.join(body)+'</tbody></table></div>'+note

def _metric_cards(metrics):
    preferred=['total_return','annualized_return','cagr','sharpe_ratio','sortino_ratio','max_drawdown','calmar_ratio','win_rate','profit_factor','total_trades','ending_equity','net_pnl']
    ordered=[]; used=set()
    for k in preferred:
        if k in metrics: ordered.append((k,metrics[k])); used.add(k)
    ordered.extend((k,v) for k,v in metrics.items() if k not in used and not isinstance(v,(dict,list)))
    ordered=ordered[:16]
    if not ordered: return '<div class="empty">No summary metrics available.</div>'
    return '<div class="metric-grid">'+''.join(f'<div class="metric"><div class="metric-label">{html.escape(_label(k))}</div><div class="metric-value">{_format_number(v,k)}</div></div>' for k,v in ordered)+'</div>'

def _hash_payload(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

@dataclass(frozen=True)
class ReportData:
    title:str; subtitle:str; generated_at:str; source_hash:str; metrics:dict; equity_points:list; drawdown_points:list; monthly_rows:list; trade_rows:list; audit:dict; risk:dict; execution:dict; metadata:dict; notes:list

def normalize_payload(payload,title=None):
    metrics=_as_mapping(_deep_find(payload,['metrics','summary_metrics','performance_summary','summary']))
    if isinstance(metrics.get('metrics'),Mapping): metrics=dict(metrics['metrics'])
    equity=_canonical_points(_deep_find(payload,['equity_curve','portfolio_equity','equity','nav_curve']),['equity','value','nav','portfolio_value','close'])
    drawdown=_canonical_points(_deep_find(payload,['drawdown_curve','drawdowns','underwater','underwater_curve']),['drawdown','value','dd'])
    if not drawdown and equity:
        peak=-math.inf; drawdown=[]
        for label,v in equity:
            peak=max(peak,v); drawdown.append((label,0.0 if peak==0 else v/peak-1.0))
    notes_raw=_deep_find(payload,['notes','warnings','observations','conclusions'])
    notes=[notes_raw] if isinstance(notes_raw,str) else [str(x) for x in notes_raw] if isinstance(notes_raw,list) else []
    return ReportData(title or str(_first(payload,['title','report_title'],'AI Stock Trading Bot')),str(_first(payload,['subtitle','report_subtitle'],f'V{VERSION} Final Tear Sheet')),_utc_now_iso(),_hash_payload(payload),metrics,equity,drawdown,_as_rows(_deep_find(payload,['monthly_returns','monthly_return_table','returns_by_month'])),_as_rows(_deep_find(payload,['trades','trade_log','closed_trades','executions'])),_as_mapping(_deep_find(payload,['audit_certificate','certificate','verification','audit','offline_paper_audit'])),_as_mapping(_deep_find(payload,['risk_controls','risk','limits','guardrails'])),_as_mapping(_deep_find(payload,['execution_statistics','execution_metrics','execution_summary','slippage'])),_as_mapping(_deep_find(payload,['metadata','run_metadata','manifest','provenance'])),notes)

def _kv_section(mapping):
    if not mapping: return '<div class="empty">No data available.</div>'
    rows=[]
    for k,v in mapping.items():
        rendered=f'<pre>{html.escape(json.dumps(v,indent=2,ensure_ascii=False))}</pre>' if isinstance(v,(dict,list)) else _format_number(v,k)
        rows.append(f'<div class="kv-row"><div class="kv-key">{html.escape(_label(k))}</div><div class="kv-value {_status_class(v)}">{rendered}</div></div>')
    return '<div class="kv">'+''.join(rows)+'</div>'

def render_html(data):
    audit_status=_first(data.audit,['status','result','verification_status'],'NOT PROVIDED'); pass_class=_status_class(audit_status)
    notes='<ul>'+''.join(f'<li>{html.escape(n)}</li>' for n in data.notes)+'</ul>' if data.notes else '<div class="empty">No additional notes.</div>'
    css='''
:root{--bg:#f4f6f8;--panel:#fff;--ink:#17212b;--muted:#667085;--line:#d9e0e7;--accent:#2457d6;--accent-soft:#e9efff;--good:#117a4b;--bad:#b42318;--warn:#b54708}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 Arial,sans-serif}.container{max-width:1180px;margin:auto;padding:32px 22px 60px}.hero{background:linear-gradient(135deg,#15233f,#2457d6);color:#fff;border-radius:18px;padding:30px}.hero h1{margin:0 0 6px;font-size:31px}.hero h2{margin:0;font-size:17px;font-weight:500;opacity:.9}.hero-meta{display:flex;flex-wrap:wrap;gap:10px 22px;margin-top:22px;font-size:12px}.badge{border-radius:999px;padding:5px 10px;background:#ffffff29;font-weight:700}.section{margin-top:22px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px}.section h3{margin:0 0 16px;font-size:19px}.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}.metric{border:1px solid var(--line);border-radius:11px;padding:14px;background:#fbfcfe}.metric-label{color:var(--muted);font-size:12px}.metric-value{margin-top:5px;font-size:21px;font-weight:700}.chart{width:100%;height:auto}.grid{stroke:#e7ebf0}.axis{fill:#667085;font-size:11px}.line{fill:none;stroke:var(--accent);stroke-width:3}.area{fill:var(--accent-soft)}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:22px}.kv-row{display:grid;grid-template-columns:minmax(180px,35%) 1fr;gap:18px;padding:10px 0;border-bottom:1px solid var(--line)}.kv-key{color:var(--muted)}.good{color:var(--good);font-weight:700}.bad{color:var(--bad);font-weight:700}.warn{color:var(--warn);font-weight:700}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:10px}table{width:100%;border-collapse:collapse;white-space:nowrap}th,td{padding:9px 11px;border-bottom:1px solid var(--line);text-align:right}th{background:#f8fafc;color:#475467;font-size:12px}th:first-child,td:first-child{text-align:left}.empty,.table-note{color:var(--muted)}pre{white-space:pre-wrap;margin:0;font-size:12px}.footer{color:var(--muted);font-size:11px;margin-top:20px;text-align:center}@media(max-width:760px){.two-col{grid-template-columns:1fr}.kv-row{grid-template-columns:1fr}}@media print{body{background:#fff}.container{max-width:none;padding:0}.hero,.section{break-inside:avoid}}
'''
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(data.title)} — {html.escape(data.subtitle)}</title><style>{css}</style></head><body><div class="container"><header class="hero"><h1>{html.escape(data.title)}</h1><h2>{html.escape(data.subtitle)}</h2><div class="hero-meta"><span class="badge">Generator V{VERSION}</span><span>Generated: {html.escape(data.generated_at)}</span><span>Audit: <strong class="{pass_class}">{html.escape(str(audit_status))}</strong></span><span>Source SHA-256: {data.source_hash[:16]}…</span></div></header><section class="section"><h3>Executive Performance Summary</h3>{_metric_cards(data.metrics)}</section><section class="section"><h3>Equity Curve</h3>{_line_svg(data.equity_points,'Equity Curve')}</section><section class="section"><h3>Drawdown / Underwater Curve</h3>{_line_svg(data.drawdown_points,'Drawdown Curve',True)}</section><div class="two-col"><section class="section"><h3>Audit Certificate &amp; Verification</h3>{_kv_section(data.audit)}</section><section class="section"><h3>Run Metadata / Provenance</h3>{_kv_section(data.metadata)}</section></div><div class="two-col"><section class="section"><h3>Risk Controls</h3>{_kv_section(data.risk)}</section><section class="section"><h3>Execution Statistics</h3>{_kv_section(data.execution)}</section></div><section class="section"><h3>Monthly Returns</h3>{_table(data.monthly_rows,120)}</section><section class="section"><h3>Trade / Execution Detail</h3>{_table(data.trade_rows,100)}</section><section class="section"><h3>Final Notes</h3>{notes}</section><div class="footer">{GENERATOR_NAME} V{VERSION} · Full source SHA-256: {data.source_hash}</div></div></body></html>'''

def generate_report(payload,output_path,title=None):
    output=Path(output_path); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(render_html(normalize_payload(payload,title)),encoding='utf-8',newline='\n'); return output

def load_payload(path):
    p=Path(path)
    if p.suffix.lower()=='.json':
        data=json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(data,Mapping): raise ValueError('Top-level JSON payload must be an object.')
        return dict(data)
    if p.suffix.lower()=='.csv':
        with p.open('r',encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
        return {'title':p.stem,'trades':rows}
    raise ValueError('Unsupported input format. Use .json or .csv')

def main(argv=None):
    ap=argparse.ArgumentParser(description=f'{GENERATOR_NAME} V{VERSION}'); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); ap.add_argument('--title'); ap.add_argument('--manifest-output'); args=ap.parse_args(argv)
    payload=load_payload(args.input); output=generate_report(payload,args.output,args.title); report_hash=hashlib.sha256(output.read_bytes()).hexdigest()
    manifest={'schema_version':'v29.5b.final_report_manifest.1','generator':GENERATOR_NAME,'generator_version':VERSION,'generated_at':_utc_now_iso(),'input_path':os.path.abspath(args.input),'output_path':os.path.abspath(output),'source_payload_sha256':_hash_payload(payload),'html_sha256':report_hash,'html_size_bytes':output.stat().st_size,'status':'PASS'}
    if args.manifest_output:
        mp=Path(args.manifest_output); mp.parent.mkdir(parents=True,exist_ok=True); mp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(manifest,indent=2,sort_keys=True)); return 0

if __name__=='__main__': raise SystemExit(main())
