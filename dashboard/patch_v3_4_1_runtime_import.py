
from __future__ import annotations

from pathlib import Path
import argparse

TARGET = Path("dashboard/operations_dashboard_v3_2.py")

OLD_LINES = [
    "    try:",
    "        from dashboard.visualization_v3_4 import build_visualization",
    "        payload[\"visualization\"] = build_visualization(root, payload)",
    "        payload[\"visualization_status\"] = \"PASS\"",
    "    except Exception as exc:",
]
OLD = "\n".join(OLD_LINES)

NEW_LINES = [
    "    try:",
    "        import importlib.util",
    "",
    "        module_path = root / \"dashboard\" / \"visualization_v3_4.py\"",
    "",
    "        spec = importlib.util.spec_from_file_location(",
    "            \"ai_stock_bot_visualization_v3_4\",",
    "            module_path,",
    "        )",
    "",
    "        if spec is None or spec.loader is None:",
    "            raise ModuleNotFoundError(",
    "                f\"Unable to load visualization module: {module_path}\"",
    "            )",
    "",
    "        module = importlib.util.module_from_spec(spec)",
    "        spec.loader.exec_module(module)",
    "",
    "        payload[\"visualization\"] = module.build_visualization(",
    "            root,",
    "            payload,",
    "        )",
    "        payload[\"visualization_status\"] = \"PASS\"",
    "    except Exception as exc:",
]
NEW = "\n".join(NEW_LINES)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\stock-bot")
    args = parser.parse_args()

    target = Path(args.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if "ai_stock_bot_visualization_v3_4" in text:
        print("V3.4.1 RUNTIME IMPORT REPAIR ALREADY PRESENT")
        return 0

    if OLD not in text:
        raise RuntimeError("V3.4 visualization import block not found")

    target.write_text(
        text.replace(OLD, NEW, 1),
        encoding="utf-8",
    )

    print("V3.4.1 RUNTIME IMPORT REPAIR: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
