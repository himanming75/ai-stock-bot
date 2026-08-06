from __future__ import annotations
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def http_get(
    *,
    url: str,
    headers: dict[str, str],
    query: dict[str, object] | None = None,
    timeout: int = 20,
) -> dict:
    clean_query = {
        k: v
        for k, v in (query or {}).items()
        if v is not None
    }
    final_url = url
    if clean_query:
        final_url += (
            "&" if "?" in url else "?"
        ) + urlencode(clean_query)
    request = Request(
        final_url,
        headers=headers,
        method="GET",
    )
    started = time.perf_counter()
    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            body = response.read()
            return {
                "status_code": response.status,
                "headers": dict(
                    response.headers.items()
                ),
                "body": body,
                "elapsed_ms": (
                    time.perf_counter() - started
                ) * 1000,
            }
    except HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            errors="replace",
        )
        raise RuntimeError(
            f"ETRADE_HTTP_{exc.code}: {body[:600]}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(
            f"ETRADE_NETWORK_ERROR: {exc.reason}"
        ) from exc


def response_json(result: dict):
    return json.loads(
        result["body"].decode(
            "utf-8",
            errors="replace",
        )
    )
