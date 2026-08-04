from __future__ import annotations
import json,mimetypes
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from web_controller.state import build_dashboard,get_logs,set_emergency
from web_controller.actions import run_action
from web_controller.strategy_api import get_payload as get_strategy,update_payload,validate_payload,restore_payload
from web_controller.paper_api import get_payload as get_paper,run_payload as run_paper,save_settings_payload
from web_controller.operations_api import get_payload as get_operations,save_payload as save_operations,run_payload as run_operations,recovery_payload
from web_controller.qualification_api import get_payload as get_qualification,run_payload as run_qualification

class ControllerHandler(BaseHTTPRequestHandler):
    root=Path.cwd();static_root=Path.cwd()/"web_controller/static"
    def _json(self,status,value):
        raw=json.dumps(value,indent=2,sort_keys=True).encode()
        self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(raw)
    def _body(self):
        n=int(self.headers.get("Content-Length","0") or 0)
        try:return json.loads(self.rfile.read(n).decode()) if n else {}
        except Exception:return {}
    def do_GET(self):
        p=urlparse(self.path).path
        routes={"/api/dashboard":lambda:build_dashboard(self.root),"/api/logs":lambda:get_logs(self.root),"/api/strategy-config":lambda:get_strategy(self.root),"/api/paper-operations":lambda:get_paper(self.root),"/api/operations-manager":lambda:get_operations(self.root),"/api/qualification":lambda:get_qualification(self.root)}
        if p in routes:self._json(200,routes[p]());return
        file=self.static_root/("index.html" if p in {"/","/index.html"} else p.lstrip("/"))
        if not file.exists():self._json(404,{"error":"NOT_FOUND"});return
        raw=file.read_bytes();self.send_response(200);self.send_header("Content-Type",mimetypes.guess_type(str(file))[0] or "application/octet-stream");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        p=urlparse(self.path).path;b=self._body()
        if p=="/api/emergency-stop":r={"ok":True,"emergency_stop":set_emergency(self.root,bool(b.get("enabled",True)),str(b.get("reason","")))}
        elif p=="/api/action":r=run_action(self.root,str(b.get("name","")))
        elif p=="/api/strategy-config/validate":r=validate_payload(b)
        elif p=="/api/strategy-config/save":r=update_payload(self.root,b)
        elif p=="/api/strategy-config/restore":r=restore_payload(self.root)
        elif p=="/api/paper-operations/action":r=run_paper(self.root,b)
        elif p=="/api/paper-operations/settings":r=save_settings_payload(self.root,b)
        elif p=="/api/operations-manager/settings":r=save_operations(self.root,b)
        elif p=="/api/operations-manager/job":r=run_operations(self.root,b)
        elif p=="/api/operations-manager/recovery":r=recovery_payload(self.root)
        elif p=="/api/qualification/run":r=run_qualification(self.root)
        else:self._json(404,{"error":"NOT_FOUND"});return
        self._json(200 if r.get("ok",True) else 409,r)
    def log_message(self,format,*args):print("[WEB]",format%args)

def serve(root:Path,host="127.0.0.1",port=8765):
    handler=type("ConfiguredControllerHandler",(ControllerHandler,),{"root":root,"static_root":root/"web_controller/static"})
    server=ThreadingHTTPServer((host,port),handler);print(f"AI Stock Bot Web Controller: http://{host}:{port}");print("Press Ctrl+C to stop.")
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
