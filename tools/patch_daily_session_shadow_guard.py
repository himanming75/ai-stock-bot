from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "paper_daily_session/runner.py"

text = PATH.read_text(encoding="utf-8-sig")
import_line = (
    "from paper_daily_session.shadow_integration "
    "import DailySessionShadowGuard\n"
)

if import_line not in text:
    marker = "from typing import Any\n"
    if marker not in text:
        raise RuntimeError("IMPORT_MARKER_NOT_FOUND")
    text = text.replace(marker, marker + "\n" + import_line, 1)

old = (
    '                self._status(\n'
    '                    "RUNNING_ONE_CONTROLLED_CYCLE",\n'
    '                    clock=clock,\n'
    '                    today_order_count=order_count,\n'
    '                )\n'
    '                cycle = self._run_order_cycle()\n'
)

new = (
    '                try:\n'
    '                    shadow_guard = DailySessionShadowGuard(\n'
    '                        self.root\n'
    '                    ).evaluate(\n'
    '                        client=client,\n'
    '                        account=account,\n'
    '                        clock=clock,\n'
    '                        today_order_count=order_count,\n'
    '                    )\n'
    '                except Exception as shadow_error:\n'
    '                    shadow_guard = {\n'
    '                        "mode": "SHADOW",\n'
    '                        "enforced": False,\n'
    '                        "action": "SHADOW_UNAVAILABLE",\n'
    '                        "would_allow_order": None,\n'
    '                        "quality_score": None,\n'
    '                        "issue_codes": [\n'
    '                            "SHADOW_EVALUATION_ERROR"\n'
    '                        ],\n'
    '                        "error": str(shadow_error),\n'
    '                    }\n\n'
    '                self._status(\n'
    '                    "RUNNING_ONE_CONTROLLED_CYCLE",\n'
    '                    clock=clock,\n'
    '                    today_order_count=order_count,\n'
    '                    shadow_guard=shadow_guard,\n'
    '                )\n\n'
    '                # Shadow only: existing Paper order path remains unchanged.\n'
    '                cycle = self._run_order_cycle()\n'
)

if old in text:
    text = text.replace(old, new, 1)
elif "shadow_guard = DailySessionShadowGuard(" not in text:
    raise RuntimeError("CONTROLLED_CYCLE_BLOCK_NOT_FOUND")

PATH.write_text(text, encoding="utf-8")
print("PATCH: PASS")
