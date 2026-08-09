from pathlib import Path
import argparse
TARGET=Path("dashboard/trade_analytics_v3_5.py")
def main():
    p=argparse.ArgumentParser(); p.add_argument("--root",default=r"C:\stock-bot"); a=p.parse_args(); target=Path(a.root)/TARGET; text=target.read_text(encoding="utf-8")
    if "ai_stock_bot_cross_ledger_v3_7" in text: print("V3.7 ANALYTICS INTEGRATION ALREADY PRESENT"); return 0
    old='''    rows.sort(key=lambda x: x["time"])\n    return rows, sorted(set(sources))\n'''
    new='''    rows.sort(key=lambda x: x["time"])\n    import importlib.util\n    reconstruction_path = root / "dashboard" / "cross_ledger_trade_reconstruction_v3_7.py"\n    spec = importlib.util.spec_from_file_location("ai_stock_bot_cross_ledger_v3_7", reconstruction_path)\n    if spec is None or spec.loader is None: raise ModuleNotFoundError(str(reconstruction_path))\n    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\n    rows, audit = module.reconstruct_missing_pnl(root, rows)\n    collect_closed_trades.last_reconstruction_audit = audit\n    return rows, sorted(set(sources))\n'''
    if old not in text: raise RuntimeError("collect return marker not found")
    text=text.replace(old,new,1)
    old2='''    recovery_audit = normalizer.build_recovery_audit(trades)\n\n    return {\n'''; new2='''    recovery_audit = normalizer.build_recovery_audit(trades)\n    reconstruction_audit = getattr(collect_closed_trades, "last_reconstruction_audit", {"status":"NOT_RUN"})\n\n    return {\n'''
    if old2 not in text: raise RuntimeError("recovery audit marker not found")
    text=text.replace(old2,new2,1)
    old3='''        "recovery_audit": recovery_audit,\n        "validation": '''; new3='''        "recovery_audit": recovery_audit,\n        "cross_ledger_reconstruction": reconstruction_audit,\n        "validation": '''
    if old3 not in text: raise RuntimeError("analytics return marker not found")
    target.write_text(text.replace(old3,new3,1),encoding="utf-8"); print("V3.7 ANALYTICS INTEGRATION: PASS"); return 0
if __name__=="__main__": raise SystemExit(main())
