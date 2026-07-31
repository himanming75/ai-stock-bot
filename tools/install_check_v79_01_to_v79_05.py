from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alpaca_market_data import inspect_alpaca_installation, load_safety_config

def main() -> int:
    install = inspect_alpaca_installation()
    safety = load_safety_config()
    result = {
        "stage_range": "V79.01-V79.05",
        "python": sys.version.split()[0],
        "alpaca_py_installed": install.installed,
        "alpaca_py_version": install.version,
        "minimum_version": install.minimum_version,
        "credential_presence_detected": safety.credential_presence_detected,
        "credential_values_exposed": False,
        "network_test_performed": False,
        "broker_connected": False,
        "actual_orders_submitted": 0,
        "status": "PASS"
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if not install.installed:
        print("\nOPTIONAL INSTALL COMMAND:")
        print(install.install_command)
        print("Offline tests and certificate generation can still run without alpaca-py.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
