from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import parse_qsl, quote, urlsplit


def pct(value):
    return quote(str(value), safe="~-._")


def _normalized_url(url):
    p=urlsplit(url)
    scheme=p.scheme.lower()
    host=p.hostname.lower() if p.hostname else ""
    port=p.port
    if port and not ((scheme=="http" and port==80) or (scheme=="https" and port==443)):
        host=f"{host}:{port}"
    path=p.path or "/"
    return f"{scheme}://{host}{path}"


def _normalized_params(url, oauth_params, request_params=None):
    pairs=[]
    pairs.extend(parse_qsl(urlsplit(url).query, keep_blank_values=True))
    pairs.extend((str(k),str(v)) for k,v in (request_params or {}).items())
    pairs.extend((str(k),str(v)) for k,v in oauth_params.items() if k!="oauth_signature")
    pairs.sort(key=lambda kv:(pct(kv[0]),pct(kv[1])))
    return "&".join(f"{pct(k)}={pct(v)}" for k,v in pairs)


def signature_base_string(method, url, oauth_params, request_params=None):
    return "&".join([
        pct(method.upper()),
        pct(_normalized_url(url)),
        pct(_normalized_params(url, oauth_params, request_params)),
    ])


def hmac_sha1_signature(method, url, consumer_secret, token_secret="", oauth_params=None, request_params=None):
    params=dict(oauth_params or {})
    base=signature_base_string(method,url,params,request_params)
    key=f"{pct(consumer_secret)}&{pct(token_secret)}"
    digest=hmac.new(key.encode(),base.encode(),hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def oauth_header(method, url, consumer_key, consumer_secret, token=None, token_secret="", extra_oauth=None, request_params=None, timestamp=None, nonce=None):
    params={
        "oauth_consumer_key":consumer_key,
        "oauth_nonce":nonce or secrets.token_hex(16),
        "oauth_signature_method":"HMAC-SHA1",
        "oauth_timestamp":str(int(timestamp if timestamp is not None else time.time())),
        "oauth_version":"1.0",
    }
    if token:
        params["oauth_token"]=token
    params.update(extra_oauth or {})
    params["oauth_signature"]=hmac_sha1_signature(
        method,url,consumer_secret,token_secret,params,request_params
    )
    body=", ".join(f'{pct(k)}="{pct(v)}"' for k,v in sorted(params.items()))
    return "OAuth "+body


def official_signature_test_vector():
    url="https://api.etrade.com/v1/accounts/list"
    params={
        "oauth_consumer_key":"c5bb4dcb7bd6826c7c4340df3f791188",
        "oauth_nonce":"0bba225a40d1bbac2430aa0c6163ce44",
        "oauth_signature_method":"HMAC-SHA1",
        "oauth_timestamp":"1344885636",
        "oauth_token":"VbiNYl63EejjlKdQM6FeENzcnrLACrZ2JYD6NQROfVI=",
    }
    sig=hmac_sha1_signature(
        "GET",url,
        "7d30246211192cda43ede3abd9b393b9",
        "XCF9RzyQr4UEPloA+WlC06BnTfYC1P0Fwr3GUw/B0Es=",
        params,
    )
    return {
        "signature":sig,
        "expected_urlencoded":"UOnPVdzExTAgHkcGWLLfeTaaMSM%3D",
        "matches":pct(sig)=="UOnPVdzExTAgHkcGWLLfeTaaMSM%3D",
    }
