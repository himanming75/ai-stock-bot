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

class ControllerHandler(BaseHTTPRequestHandler):
    root=Path.cwd();static_root=Path.cwd()/"web_controller/static"
    def _json(self,status:int,value:object)->None:
        raw=json.dumps(value,indent=2,sort_keys=True).encode("utf-8")
        self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(raw)
    def _body(self)->dict:
        length=int(self.headers.get("Content-Length","0") or 0)
        if length<=0:return {}
        try:return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:return {}
    def do_GET(self)->None:
        path=urlparse(self.path).path
        if path=="/api/dashboard":self._json(200,build_dashboard(self.root));return
        if path=="/api/logs":self._json(200,get_logs(self.root));return
        if path=="/api/strategy-config":self._json(200,get_strategy(self.root));return
        if path=="/api/paper-operations":self._json(200,get_paper(self.root));return
        if path=="/api/operations-manager":self._json(200,get_operations(self.root));return
        file=self.static_root/("index.html" if path in {"/","/index.html"} else path.lstrip("/"))
        try:
            resolved=file.resolve()
            if self.static_root.resolve() not in resolved.parents and resolved!=self.static_root.resolve():
                self._json(403,{"error":"FORBIDDEN"});return
            if not resolved.exists() or not resolved.is_file():
                self._json(404,{"error":"NOT_FOUND"});return
            raw=resolved.read_bytes();mime=mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            self.send_response(200);self.send_header("Content-Type",mime);self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
        except Exception as exc:self._json(500,{"error":str(exc)})
    def do_POST(self)->None:
        path=urlparse(self.path).path;body=self._body()
        if path=="/api/emergency-stop":
            self._json(200,{"ok":True,"emergency_stop":set_emergency(self.root,bool(body.get("enabled",True)),str(body.get("reason","")))});return
        if path=="/api/action":
            r=run_action(self.root,str(body.get("name","")));self._json(200 if r.get("ok") else 409,r);return
        if path=="/api/strategy-config/validate":
            r=validate_payload(body);self._json(200 if r.get("valid") else 400,r);return
        if path=="/api/strategy-config/save":
            r=update_payload(self.root,body);self._json(200 if r.get("ok") else 409,r);return
        if path=="/api/strategy-config/restore":
            r=restore_payload(self.root);self._json(200 if r.get("ok") else 409,r);return
        if path=="/api/paper-operations/action":
            r=run_paper(self.root,body);self._json(200 if r.get("ok") else 409,r);return
        if path=="/api/paper-operations/settings":
            r=save_settings_payload(self.root,body);self._json(200 if r.get("ok") else 409,r);return
        if path=="/api/operations-manager/settings":
            r=save_operations(self.root,body);self._json(200 if r.get("ok") else 409,r);return
        if path=="/api/operations-manager/job":
            r=run_operations(self.root,body);self._json(200 if r.get("ok") else 409,r);return
        if path=="/api/operations-manager/recovery":
            self._json(200,recovery_payload(self.root));return
        self._json(404,{"error":"NOT_FOUND"})
    def log_message(self,format,*args):print("[WEB]",format%args)

def serve(root:Path,host:str="127.0.0.1",port:int=8765)->None:
    handler=type("ConfiguredControllerHandler",(ControllerHandler,),{"root":root,"static_root":root/"web_controller/static"})
    server=ThreadingHTTPServer((host,port),handler)
    print(f"AI Stock Bot Web Controller: http://{host}:{port}");print("Press Ctrl+C to stop.")
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
