import json
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
PAPER_BASE_URL="https://paper-api.alpaca.markets"
class AlpacaPaperClient:
    def __init__(self,key,secret,base_url=PAPER_BASE_URL):
        if base_url.rstrip("/")!=PAPER_BASE_URL: raise ValueError("LIVE_OR_UNKNOWN_ENDPOINT_REJECTED")
        self.key=key; self.secret=secret; self.base=base_url.rstrip("/")
    def _req(self,m,path,payload=None):
        req=Request(self.base+path,data=json.dumps(payload).encode() if payload is not None else None,method=m,
          headers={"APCA-API-KEY-ID":self.key,"APCA-API-SECRET-KEY":self.secret,"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=20) as r:
                b=r.read().decode(); return json.loads(b) if b else {}
        except HTTPError as e: raise RuntimeError(f"ALPACA_HTTP_{e.code}:{e.read().decode(errors='replace')}") from e
        except URLError as e: raise RuntimeError(f"ALPACA_NETWORK_ERROR:{e.reason}") from e
    def get_clock(self): return self._req("GET","/v2/clock")
    def get_account(self): return self._req("GET","/v2/account")
    def get_orders(self,status="open"): 
        v=self._req("GET",f"/v2/orders?status={status}&limit=100&direction=desc"); return v if isinstance(v,list) else []
    def submit_order(self,payload): return self._req("POST","/v2/orders",payload)
