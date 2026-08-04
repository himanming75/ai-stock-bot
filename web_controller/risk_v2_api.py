from pathlib import Path
from risk_engine_v2.engine import evaluate
from risk_engine_v2.dashboard import payload
from risk_engine_v2.kill_switch import set_state

def get_payload(root:Path)->dict:
    return payload(root) or evaluate(root)

def refresh_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root)}

def kill_switch_payload(root:Path,body:dict)->dict:
    value=set_state(root,bool(body.get("enabled",True)),str(body.get("reason","")))
    return {"ok":True,"kill_switch":value,"result":evaluate(root)}
