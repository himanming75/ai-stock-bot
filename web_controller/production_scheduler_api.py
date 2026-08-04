from pathlib import Path
from production_scheduler.engine import evaluate
from production_scheduler.dashboard import payload
from production_scheduler.jobs import run

def get_payload(root:Path)->dict:
    return payload(root) or evaluate(root)

def refresh_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root)}

def run_job_payload(root:Path,body:dict)->dict:
    return run(root,str(body.get("job","")))
