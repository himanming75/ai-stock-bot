
from pathlib import Path
import argparse

TARGET=Path("dashboard/operations_dashboard_v3_2.py")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    new='            build_broker_integration_v1_status(root)\n        )\n'
    if new in text:
        print("BROKER V2 SERVER ROOT PASS-THROUGH ALREADY PRESENT")
        return 0

    old='            build_broker_integration_v1_status()\n        )\n'
    if old not in text:
        raise RuntimeError("BROKER V2 SERVER PASS-THROUGH MARKER NOT FOUND")

    target.write_text(text.replace(old,new,1),encoding="utf-8")
    print("BROKER V2 SERVER ROOT PASS-THROUGH: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
