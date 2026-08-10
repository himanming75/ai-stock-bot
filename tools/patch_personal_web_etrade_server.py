from pathlib import Path
import shutil

root=Path(r"C:\stock-bot")
server=root/"web_controller/server.py"
backup=root/"release/personal_web_etrade/backup/server.py.bak"
backup.parent.mkdir(parents=True,exist_ok=True)
text=server.read_text(encoding="utf-8")
if not backup.exists():
    shutil.copy2(server,backup)

imp="from web_controller.etrade_api import get_payload as get_etrade,action_payload as run_etrade_action"
if imp not in text:
    marker="from web_controller.backtest_api import get_payload as get_backtest,action_payload as run_backtest_action"
    if marker not in text:
        marker="from web_controller.live_approval_api import get_payload as get_live_approval,refresh_payload,decision_payload"
    if marker not in text:
        raise SystemExit("IMPORT_MARKER_NOT_FOUND")
    text=text.replace(marker,marker+"\n"+imp)

if '"/api/etrade":lambda:get_etrade(self.root)' not in text:
    marker='"/api/backtest":lambda:get_backtest(self.root)}'
    if marker in text:
        text=text.replace(marker,'"/api/backtest":lambda:get_backtest(self.root),"/api/etrade":lambda:get_etrade(self.root)}')
    else:
        marker='"/api/live-approval":lambda:get_live_approval(self.root)}'
        if marker not in text:
            raise SystemExit("GET_ROUTE_MARKER_NOT_FOUND")
        text=text.replace(marker,'"/api/live-approval":lambda:get_live_approval(self.root),"/api/etrade":lambda:get_etrade(self.root)}')

if 'p=="/api/etrade/action"' not in text:
    marker='elif p=="/api/backtest/action":r=run_backtest_action(self.root,b)'
    if marker in text:
        text=text.replace(marker,marker+'\n        elif p=="/api/etrade/action":r=run_etrade_action(self.root,b)')
    else:
        marker='elif p=="/api/live-approval/decision":r=decision_payload(self.root,b)'
        if marker not in text:
            raise SystemExit("POST_ROUTE_MARKER_NOT_FOUND")
        text=text.replace(marker,marker+'\n        elif p=="/api/etrade/action":r=run_etrade_action(self.root,b)')

server.write_text(text,encoding="utf-8")
print("ETRADE SERVER PATCH: PASS")
