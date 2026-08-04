from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from web_controller.server import serve
p=argparse.ArgumentParser()
p.add_argument("--host",default="127.0.0.1")
p.add_argument("--port",type=int,default=8765)
a=p.parse_args()
if a.host not in {"127.0.0.1","localhost"}:
    raise SystemExit("External binding is disabled in V141-V145.")
serve(ROOT,a.host,a.port)
