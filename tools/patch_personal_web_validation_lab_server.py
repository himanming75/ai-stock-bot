from pathlib import Path
import shutil

root=Path(r"C:\stock-bot")
server=root/"web_controller/server.py"
backup=root/"release/personal_web_validation_accelerator/backup/server.py.bak"
backup.parent.mkdir(parents=True,exist_ok=True)
text=server.read_text(encoding="utf-8")
if not backup.exists():
    shutil.copy2(server,backup)

imp="from web_controller.validation_lab_api import get_payload as get_validation_lab,action_payload as run_validation_lab_action"
if imp not in text:
    markers=[
        "from web_controller.etrade_api import get_payload as get_etrade,action_payload as run_etrade_action",
        "from web_controller.backtest_api import get_payload as get_backtest,action_payload as run_backtest_action",
        "from web_controller.live_approval_api import get_payload as get_live_approval,refresh_payload,decision_payload",
    ]
    marker=next((m for m in markers if m in text),None)
    if not marker:
        raise SystemExit("IMPORT_MARKER_NOT_FOUND")
    text=text.replace(marker,marker+"\n"+imp)

if '"/api/validation-lab":lambda:get_validation_lab(self.root)' not in text:
    markers=[
        ('"/api/etrade":lambda:get_etrade(self.root)}',
         '"/api/etrade":lambda:get_etrade(self.root),"/api/validation-lab":lambda:get_validation_lab(self.root)}'),
        ('"/api/backtest":lambda:get_backtest(self.root)}',
         '"/api/backtest":lambda:get_backtest(self.root),"/api/validation-lab":lambda:get_validation_lab(self.root)}'),
    ]
    done=False
    for old,new in markers:
        if old in text:
            text=text.replace(old,new)
            done=True
            break
    if not done:
        raise SystemExit("GET_ROUTE_MARKER_NOT_FOUND")

if 'p=="/api/validation-lab/action"' not in text:
    markers=[
        'elif p=="/api/etrade/action":r=run_etrade_action(self.root,b)',
        'elif p=="/api/backtest/action":r=run_backtest_action(self.root,b)',
        'elif p=="/api/live-approval/decision":r=decision_payload(self.root,b)',
    ]
    marker=next((m for m in markers if m in text),None)
    if not marker:
        raise SystemExit("POST_ROUTE_MARKER_NOT_FOUND")
    text=text.replace(marker,marker+'\n        elif p=="/api/validation-lab/action":r=run_validation_lab_action(self.root,b)')

server.write_text(text,encoding="utf-8")
print("VALIDATION LAB SERVER PATCH: PASS")
