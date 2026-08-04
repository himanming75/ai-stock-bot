from pathlib import Path
from final_production_release.engine import evaluate
from final_production_release.dashboard import payload
from final_production_release.bundle import create

def get_payload(root:Path)->dict:
    return payload(root) or evaluate(root,create_release_bundle=False)

def refresh_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root,create_release_bundle=False)}

def build_bundle_payload(root:Path)->dict:
    return {"ok":True,"bundle":create(root)}
