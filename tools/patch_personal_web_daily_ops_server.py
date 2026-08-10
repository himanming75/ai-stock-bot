from pathlib import Path
import shutil
root=Path(r"C:\stock-bot")
server=root/"web_controller/server.py"
backup=root/"release/personal_web_daily_operations_center/backup/server.py.bak"
backup.parent.mkdir(parents=True,exist_ok=True)
text=server.read_text(encoding="utf-8")
if not backup.exists():
    shutil.copy2(server,backup)

imp="from web_controller.daily_ops_api import get_payload as get_daily_ops,action_payload as run_daily_ops_action"
if imp not in text:
    marker="from web_controller.validation_lab_api import get_payload as get_validation_lab,action_payload as run_validation_lab_action"
    if marker not in text:
        raise SystemExit("IMPORT_MARKER_NOT_FOUND")
    text=text.replace(marker,marker+"\n"+imp)

if '"/api/daily-ops":lambda:get_daily_ops(self.root)' not in text:
    marker='"/api/validation-lab":lambda:get_validation_lab(self.root)}'
    if marker not in text:
        raise SystemExit("GET_ROUTE_MARKER_NOT_FOUND")
    text=text.replace(marker,'"/api/validation-lab":lambda:get_validation_lab(self.root),"/api/daily-ops":lambda:get_daily_ops(self.root)}')

if 'p=="/api/daily-ops/action"' not in text:
    marker='elif p=="/api/validation-lab/action":r=run_validation_lab_action(self.root,b)'
    if marker not in text:
        raise SystemExit("POST_ROUTE_MARKER_NOT_FOUND")
    text=text.replace(marker,marker+'\n        elif p=="/api/daily-ops/action":r=run_daily_ops_action(self.root,b)')

server.write_text(text,encoding="utf-8")
print("DAILY OPS SERVER PATCH: PASS")
