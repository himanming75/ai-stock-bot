from pathlib import Path
import argparse
TARGET=Path("dashboard/trade_ledger_normalizer_v3_6.py")
def main():
    p=argparse.ArgumentParser(); p.add_argument("--root",default=r"C:\stock-bot"); a=p.parse_args(); target=Path(a.root)/TARGET; text=target.read_text(encoding="utf-8")
    if "def collect_identifier_values(" in text: print("V3.7 IDENTIFIER NORMALIZATION ALREADY PRESENT"); return 0
    marker="\n\ndef find_numeric_pnl(record):"
    func='''\n\ndef collect_identifier_values(record):\n    wanted={"order_id","client_order_id","trade_id","position_id","parent_order_id","execution_id","fill_id"}\n    result={}\n    for path,key,value in _walk(record):\n        normalized=key.lower()\n        if normalized not in wanted or value is None: continue\n        s=str(value).strip()\n        if s: result.setdefault(normalized,set()).add(s)\n    return {k:sorted(v) for k,v in result.items()}\n'''
    if marker not in text: raise RuntimeError("find_numeric_pnl marker not found")
    text=text.replace(marker,func+marker,1)
    old='''            "pnl_recovered": pnl is not None,\n        },\n    }\n'''; new='''            "pnl_recovered": pnl is not None,\n            "identifiers": collect_identifier_values(record),\n        },\n    }\n'''
    if old not in text: raise RuntimeError("normalization return marker not found")
    target.write_text(text.replace(old,new,1),encoding="utf-8"); print("V3.7 IDENTIFIER NORMALIZATION: PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
