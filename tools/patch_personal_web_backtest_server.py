from pathlib import Path
import shutil

root=Path(r"C:\stock-bot")
server=root/"web_controller/server.py"
backup=root/"release/personal_web_backtest/backup/server.py.bak"
backup.parent.mkdir(parents=True,exist_ok=True)
text=server.read_text(encoding="utf-8")
if not backup.exists():
    shutil.copy2(server,backup)

import_line="from web_controller.backtest_api import get_payload as get_backtest,action_payload as run_backtest_action"
if import_line not in text:
    marker="from web_controller.live_approval_api import get_payload as get_live_approval,refresh_payload,decision_payload"
    if marker not in text:
        raise SystemExit("SERVER_IMPORT_MARKER_NOT_FOUND")
    text=text.replace(marker,marker+"\n"+import_line)

old='"/api/live-approval":lambda:get_live_approval(self.root)}'
new='"/api/live-approval":lambda:get_live_approval(self.root),"/api/backtest":lambda:get_backtest(self.root)}'
if new not in text:
    if old not in text:
        raise SystemExit("GET_ROUTE_MARKER_NOT_FOUND")
    text=text.replace(old,new)

# Insert POST route before generic/remaining branches by matching live approval decision block.
needle='if p=="/api/live-approval/decision":self._json(200,decision_payload(self.root,body));return'
add=needle+'\n        if p=="/api/backtest/action":self._json(200,run_backtest_action(self.root,body));return'
if 'p=="/api/backtest/action"' not in text:
    if needle not in text:
        raise SystemExit("POST_ROUTE_MARKER_NOT_FOUND")
    text=text.replace(needle,add)

server.write_text(text,encoding="utf-8")
print("SERVER PATCH: PASS")
