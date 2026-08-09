
from pathlib import Path
import argparse

TARGET=Path("broker_integration_v1/integrated_status_v2.py")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if '"place_ledger_v2_1_2": place_ledger' in text:
        print("V2.1.2 STATUS ALREADY PRESENT")
        return 0

    marker='def build_broker_integration_v2_status(repo_root=None):\n'
    repl=(
        'def build_broker_integration_v2_status(repo_root=None):\n'
        '    from .etrade_sandbox_order_status_v2_1_2 import build_etrade_sandbox_order_v2_1_2_status\n'
        '    place_ledger=build_etrade_sandbox_order_v2_1_2_status()\n'
    )
    if marker not in text:
        raise RuntimeError("V2.1.2 STATUS INSERT MARKER NOT FOUND")
    text=text.replace(marker,repl,1)

    marker2='        "contracts":{\n'
    repl2='        "place_ledger_v2_1_2": place_ledger,\n        "contracts":{\n'
    if marker2 not in text:
        raise RuntimeError("V2.1.2 STATUS RETURN MARKER NOT FOUND")
    text=text.replace(marker2,repl2,1)

    target.write_text(text,encoding="utf-8")
    print("V2.1.2 STATUS INTEGRATION: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
