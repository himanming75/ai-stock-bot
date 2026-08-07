from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import csv, json, re, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

REJECT_TOKENS=(
    "fixture","fixtures","scenario","scenarios","example","examples",
    "demo","sample","synthetic","mock","testdata","test_data"
)
DATA_HINTS=("historical","bars","ohlcv","market_data","market-data","alpaca")
GOOD_PROV_KEYS=(
    "actual_external_network_used","network_requests_executed","network_calls_made",
    "actual_network_used","credentials_used","broker_read_performed"
)
ROW_KEYS={
    "symbol":("symbol","ticker"),
    "timestamp":("timestamp","time","datetime","date","t"),
    "open":("open","o"),
    "high":("high","h"),
    "low":("low","l"),
    "close":("close","c"),
    "volume":("volume","v"),
}

def first(row,keys):
    for k in keys:
        if isinstance(row,dict) and row.get(k) not in (None,""):
            return row.get(k)
    return None

def normalize_row(row):
    if not isinstance(row,dict):
        return None
    out={k:first(row,ks) for k,ks in ROW_KEYS.items()}
    if any(out[k] in (None,"") for k in ("symbol","timestamp","open","high","low","close","volume")):
        return None
    try:
        for k in ("open","high","low","close","volume"):
            float(out[k])
    except Exception:
        return None
    out["symbol"]=str(out["symbol"]).upper()
    out["timestamp"]=str(out["timestamp"])
    return out

def read_rows(path:Path,limit=100000):
    rows=[]
    ext=path.suffix.lower()
    try:
        if ext==".jsonl":
            for line in path.read_text(encoding="utf-8-sig",errors="replace").splitlines():
                if not line.strip(): continue
                try:
                    x=json.loads(line)
                except Exception:
                    continue
                if isinstance(x,dict):
                    n=normalize_row(x)
                    if n: rows.append(n)
                if len(rows)>=limit: break
        elif ext==".csv":
            with path.open("r",encoding="utf-8-sig",errors="replace",newline="") as h:
                for x in csv.DictReader(h):
                    n=normalize_row(x)
                    if n: rows.append(n)
                    if len(rows)>=limit: break
        elif ext==".json":
            x=json.loads(path.read_text(encoding="utf-8-sig",errors="replace"))
            candidates=[]
            if isinstance(x,list):
                candidates=x
            elif isinstance(x,dict):
                for key in ("rows","bars","data","records","historical_bars"):
                    if isinstance(x.get(key),list):
                        candidates=x[key]
                        break
            for r in candidates[:limit]:
                n=normalize_row(r)
                if n: rows.append(n)
    except Exception:
        return []
    return rows

def json_objects_near(path:Path):
    objs=[]
    for parent in [path.parent, path.parent.parent]:
        if not parent.exists(): continue
        for p in parent.glob("*.json"):
            if p==path or p.stat().st_size>5_000_000:
                continue
            try:
                x=json.loads(p.read_text(encoding="utf-8-sig",errors="replace"))
                if isinstance(x,dict):
                    objs.append((p,x))
            except Exception:
                pass
    return objs

def provenance(path:Path):
    evidence=[]
    network_positive=False
    credential_positive=False
    explicitly_offline=False

    for p,obj in json_objects_near(path):
        text=json.dumps(obj,default=str).lower()
        if '"network_allowed": false' in text or '"environment": "offline"' in text:
            explicitly_offline=True

        for key in GOOD_PROV_KEYS:
            if key in obj:
                val=obj.get(key)
                evidence.append({"file":str(p),"key":key,"value":val})
                if key in ("actual_external_network_used","actual_network_used","broker_read_performed") and val is True:
                    network_positive=True
                if key in ("network_requests_executed","network_calls_made"):
                    try:
                        if int(val)>0: network_positive=True
                    except Exception:
                        pass
                if key=="credentials_used" and val is True:
                    credential_positive=True

        # nested search, bounded by metadata file size
        for key in GOOD_PROV_KEYS:
            pat=re.compile(r'"'+re.escape(key)+r'"\s*:\s*(true|false|\d+)',re.I)
            for m in pat.finditer(text):
                raw=m.group(1).lower()
                val=True if raw=="true" else False if raw=="false" else int(raw)
                evidence.append({"file":str(p),"key":key,"value":val})
                if key in ("actual_external_network_used","actual_network_used","broker_read_performed") and val is True:
                    network_positive=True
                if key in ("network_requests_executed","network_calls_made") and isinstance(val,int) and val>0:
                    network_positive=True
                if key=="credentials_used" and val is True:
                    credential_positive=True

    return {
        "network_positive":network_positive,
        "credential_positive":credential_positive,
        "explicitly_offline":explicitly_offline,
        "evidence":evidence[:100],
    }

def candidate_files(root:Path):
    result=[]
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel=str(p.relative_to(root)).replace("\\","/")
        low=rel.lower()
        if any(x in low for x in (".git/",".venv/","archive/","__pycache__/")):
            continue
        if p.suffix.lower() not in {".json",".jsonl",".csv"}:
            continue
        if not any(h in low for h in DATA_HINTS):
            continue
        result.append(p)
    return result

def build(root:Path):
    root=Path(root).resolve()
    findings=[]
    trusted=[]

    for p in candidate_files(root):
        rel=str(p.relative_to(root)).replace("\\","/")
        low=rel.lower()
        rejected_name=any(tok in low for tok in REJECT_TOKENS)
        rows=read_rows(p)
        if len(rows)<20:
            continue
        symbols=sorted({r["symbol"] for r in rows})
        timestamps={r["timestamp"] for r in rows}
        prov=provenance(p)

        # Strict rule: genuine dataset requires explicit positive network/read provenance,
        # must not be fixture/scenario/etc, and must not be explicitly offline.
        trust=(
            not rejected_name
            and len(rows)>=200
            and len(timestamps)>=50
            and prov["network_positive"]
            and not prov["explicitly_offline"]
        )

        item={
            "path":rel,
            "row_count":len(rows),
            "symbol_count":len(symbols),
            "symbols":symbols[:50],
            "timestamp_count":len(timestamps),
            "name_rejected":rejected_name,
            "provenance":prov,
            "trusted_real_historical_dataset":trust,
        }
        findings.append(item)
        if trust:
            trusted.append(item)

    findings.sort(key=lambda x:(x["trusted_real_historical_dataset"],x["row_count"]),reverse=True)
    trusted.sort(key=lambda x:x["row_count"],reverse=True)

    engine=root/"backtest/offline_multi_asset_v26_1.py"
    engine_text=engine.read_text(encoding="utf-8-sig",errors="replace") if engine.exists() else ""
    engine_contract={
        "exists":engine.exists(),
        "offline_only_claim":("no network access" in engine_text.lower()),
        "broker_free_claim":("no broker/account apis" in engine_text.lower()),
        "run_function_present":("def run_multi_asset_backtest" in engine_text),
        "trade_realized_pnl_present":("realized_pnl" in engine_text),
        "safe_for_historical_replay_adapter": all([
            engine.exists(),
            "def run_multi_asset_backtest" in engine_text,
            "realized_pnl" in engine_text,
            "no network access" in engine_text.lower(),
        ]),
    }

    out=root/"runtime/real_historical_dataset_replay_gate"
    out.mkdir(parents=True,exist_ok=True)

    report={
        "stage":"REAL_HISTORICAL_DATASET_PROVENANCE_AND_REPLAY_GATE_V1",
        "status":"PASS",
        "mode":"READ_ONLY_DATASET_DISCOVERY",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "candidate_dataset_count":len(findings),
        "trusted_dataset_count":len(trusted),
        "trusted_datasets":trusted[:20],
        "top_dataset_candidates":findings[:50],
        "existing_replay_engine":engine_contract,
        "known_rejections":{
            "v77_46_to_v77_50":"REJECT_SYNTHETIC_GENERATED_BARS",
            "v79_06_to_v79_10":"REJECT_FIXTURE_TRANSPORT",
            "v79_21_to_v79_25":"REJECT_FIXTURE_SOURCE",
        },
        "next_state":(
            "READY_TO_EXECUTE_EXISTING_OFFLINE_MULTI_ASSET_ON_REAL_HISTORY"
            if trusted and engine_contract["safe_for_historical_replay_adapter"]
            else "NEEDS_ACTUAL_HISTORICAL_DATA_INGESTION"
        ),
        "contracts":{
            "dataset_files_modified":False,
            "candidate_replay_executed":False,
            "paper_task_modified":False,
            "broker_write_performed":False,
            "order_submission_performed":False,
            "new_backtest_engine_created":False,
            "new_strategy_created":False,
            "live_auto_enable":False,
        },
    }

    (out/"latest_real_historical_replay_gate.json").write_text(
        json.dumps(report,indent=2,default=str),encoding="utf-8"
    )
    return report

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    args=p.parse_args()
    print(json.dumps(build(Path(args.root)),indent=2,default=str))
