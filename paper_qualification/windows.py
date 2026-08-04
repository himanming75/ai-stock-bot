from __future__ import annotations
from typing import Any
from paper_qualification.metrics import compute
from paper_qualification.strategies import score,grade

def evaluate(daily:list[dict[str,Any]],trades:list[dict[str,Any]])->dict[str,Any]:
    result={}
    for window in (5,20,60):
        d=daily[-window:]
        dates={str(x.get("session_date",x.get("date",""))) for x in d}
        t=[x for x in trades if not dates or str(x.get("session_date",x.get("date",""))) in dates]
        m=compute(t,d)
        s=score(m)
        result[str(window)]={"metrics":m,"score":s,"grade":grade(s)}
    return result
