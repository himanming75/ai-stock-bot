from __future__ import annotations
from pathlib import Path
import shutil

root=Path(r"C:\stock-bot")
server=root/"web_controller/server.py"
backup=root/"release/personal_web_backtest_route_repair/backup/server.py.bak"
backup.parent.mkdir(parents=True,exist_ok=True)

text=server.read_text(encoding="utf-8")
if not backup.exists():
    shutil.copy2(server,backup)

import_line=(
    "from web_controller.backtest_api import "
    "get_payload as get_backtest,action_payload as run_backtest_action"
)
if import_line not in text:
    marker=(
        "from web_controller.live_approval_api import "
        "get_payload as get_live_approval,refresh_payload,decision_payload"
    )
    if marker not in text:
        raise SystemExit("SERVER_IMPORT_MARKER_NOT_FOUND")
    text=text.replace(marker,marker+"\n"+import_line)

# GET route: handle both unpatched and already-patched states.
if '"/api/backtest":lambda:get_backtest(self.root)' not in text:
    marker='"/api/live-approval":lambda:get_live_approval(self.root)}'
    replacement=(
        '"/api/live-approval":lambda:get_live_approval(self.root),'
        '"/api/backtest":lambda:get_backtest(self.root)}'
    )
    if marker not in text:
        raise SystemExit("GET_ROUTE_MARKER_NOT_FOUND")
    text=text.replace(marker,replacement)

# POST route: actual server uses an if/elif chain.
if 'p=="/api/backtest/action"' not in text:
    marker='elif p=="/api/live-approval/decision":r=decision_payload(self.root,b)'
    replacement=(
        marker+
        '\n        elif p=="/api/backtest/action":'
        'r=run_backtest_action(self.root,b)'
    )
    if marker not in text:
        raise SystemExit("POST_ROUTE_MARKER_NOT_FOUND")
    text=text.replace(marker,replacement)

server.write_text(text,encoding="utf-8")
print("BACKTEST SERVER ROUTE REPAIR: PASS")
