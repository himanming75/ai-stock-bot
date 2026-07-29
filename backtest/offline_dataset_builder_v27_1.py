
from dataclasses import dataclass
from hashlib import sha256
import json

VERSION="27.1"

@dataclass(frozen=True)
class Sample:
    features: tuple[float,...]
    label: int

def build_dataset(rows):
    if not rows: raise ValueError("empty")
    samples=[Sample(tuple(r["features"]), int(r["label"])) for r in rows]
    payload=[{"f":list(s.features),"l":s.label} for s in samples]
    h=sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    return {"version":VERSION,"samples":samples,"hash":h}

def verify(ds):
    payload=[{"f":list(s.features),"l":s.label} for s in ds["samples"]]
    return sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()==ds["hash"]

MARKET_DATA_API_CALLED=False
ACCOUNT_API_CALLED=False
NETWORK_ACCESSED=False
BROKER_API_CALLED=False
BROKER_ORDER_CREATED=False
ORDER_SUBMITTED=False
LIVE_EXECUTION_AUTHORIZED=False
FUNDS_RESERVED=False
HOLDINGS_RESERVED=False
