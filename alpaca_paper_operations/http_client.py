from __future__ import annotations
import json, time
from typing import Any
from urllib import request,error

class HttpResult:
    def __init__(
        self,
        status_code: int,
        data: Any,
        headers: dict[str,str],
    ) -> None:
        self.status_code=status_code
        self.data=data
        self.headers=headers

def request_json(
    method: str,
    url: str,
    headers: dict[str,str],
    payload: dict[str,Any] | None = None,
    timeout_seconds: float = 20.0,
    retry_count: int = 2,
) -> HttpResult:
    body=None
    if payload is not None:
        body=json.dumps(payload).encode("utf-8")
    last_error=None
    for attempt in range(retry_count+1):
        req=request.Request(url,data=body,headers=headers,method=method)
        try:
            with request.urlopen(req,timeout=timeout_seconds) as response:
                raw=response.read().decode("utf-8")
                data=json.loads(raw) if raw else {}
                return HttpResult(
                    int(response.status),
                    data,
                    dict(response.headers.items()),
                )
        except error.HTTPError as exc:
            raw=exc.read().decode("utf-8",errors="replace")
            try:
                data=json.loads(raw)
            except Exception:
                data={"message":raw}
            if exc.code==429 and attempt<retry_count:
                time.sleep(min(2**attempt,5))
                continue
            return HttpResult(int(exc.code),data,dict(exc.headers.items()))
        except Exception as exc:
            last_error=exc
            if attempt<retry_count:
                time.sleep(min(2**attempt,5))
                continue
    raise RuntimeError(f"HTTP REQUEST FAILED: {last_error}")
