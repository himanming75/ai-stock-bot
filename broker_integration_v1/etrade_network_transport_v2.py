from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .etrade_oauth_signer import oauth_header


class ReadOnlyNetworkPolicyError(RuntimeError):
    pass


class ETradeOAuthReadOnlyTransport:
    def __init__(self,consumer_key,consumer_secret,access_token,access_token_secret,base_url,network_enabled=False):
        self.consumer_key=consumer_key
        self.consumer_secret=consumer_secret
        self.access_token=access_token
        self.access_token_secret=access_token_secret
        self.base_url=base_url.rstrip("/")
        self.network_enabled=bool(network_enabled)
        self.calls=[]

    def _assert_readonly(self,method,path):
        if method.upper()!="GET":
            raise ReadOnlyNetworkPolicyError("Only GET is permitted by E*TRADE V2 read-only transport.")
        allowed=(
            "/accounts/list",
            "/accounts/list.json",
            "/accounts/",
        )
        if not any(path.startswith(x) for x in allowed):
            raise ReadOnlyNetworkPolicyError(f"Path not allowed by read-only policy: {path}")

    def get_json(self,path,params=None):
        self._assert_readonly("GET",path)
        if not self.network_enabled:
            raise ReadOnlyNetworkPolicyError("Network is disabled. Explicit read-only opt-in is required.")
        params=dict(params or {})
        url=self.base_url+path
        full=url+("?" + urlencode(params) if params else "")
        header=oauth_header(
            "GET",full,self.consumer_key,self.consumer_secret,
            token=self.access_token,token_secret=self.access_token_secret,
        )
        self.calls.append({"method":"GET","path":path})
        req=Request(full,headers={"Authorization":header,"Accept":"application/json"},method="GET")
        with urlopen(req,timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
