
from pathlib import Path
import argparse

TARGET=Path("broker_integration_v1/integrated_status.py")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if '"v2_etrade_readonly_oauth": v2' in text:
        print("BROKER V2 STATUS ALREADY PRESENT")
        return 0

    text=text.replace(
        "def build_broker_integration_v1_status():",
        "def build_broker_integration_v1_status(repo_root=None):",
        1,
    )

    marker="def build_broker_integration_v1_status(repo_root=None):\n    return {\n"
    replacement=(
        "def build_broker_integration_v1_status(repo_root=None):\n"
        "    from .integrated_status_v2 import build_broker_integration_v2_status\n"
        "    v2=build_broker_integration_v2_status(repo_root)\n"
        "    return {\n"
    )
    if marker not in text:
        raise RuntimeError("BROKER V2 STATUS INSERT MARKER NOT FOUND")
    text=text.replace(marker,replacement,1)

    marker2='        "contracts":{\n'
    replacement2='        "v2_etrade_readonly_oauth": v2,\n        "contracts":{\n'
    if marker2 not in text:
        raise RuntimeError("BROKER V2 STATUS RETURN MARKER NOT FOUND")
    text=text.replace(marker2,replacement2,1)

    target.write_text(text,encoding="utf-8")
    print("BROKER INTEGRATION V2 STATUS: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
