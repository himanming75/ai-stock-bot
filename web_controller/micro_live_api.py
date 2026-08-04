from pathlib import Path
from controlled_micro_live.engine import evaluate
from controlled_micro_live.dashboard import payload
from controlled_micro_live.kill_switch import set_state

def get_payload(root:Path)->dict:
    return payload(root) or evaluate(root)

def refresh_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root)}

def kill_switch_payload(root:Path,body:dict)->dict:
    value=set_state(root,bool(body.get("enabled",True)),str(body.get("reason","")))
    return {"ok":True,"kill_switch":value,"result":evaluate(root)}
