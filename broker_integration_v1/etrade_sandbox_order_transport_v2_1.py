from __future__ import annotations

import json
from urllib.request import Request, urlopen

from .etrade_oauth_signer import oauth_header


class SandboxOrderPolicyError(RuntimeError):
    pass


class ETradeSandboxOrderTransport:
    def __init__(self,consumer_key,consumer_secret,access_token,access_token_secret,network_enabled=False):
        self.consumer_key=consumer_key
        self.consumer_secret=consumer_secret
        self.access_token=access_token
        self.access_token_secret=access_token_secret
        self.base_url="https://apisb.etrade.com/v1"
        self.network_enabled=bool(network_enabled)
        self.calls=[]

    def _assert_sandbox_order_path(self,path):
        if not path.startswith("/accounts/"):
            raise SandboxOrderPolicyError("Only sandbox account order paths are allowed.")
        if not (path.endswith("/orders/preview.json") or path.endswith("/orders/place.json")):
            raise SandboxOrderPolicyError("Only preview/place endpoints are allowed in V2.1.")

    def post_json(self,path,payload):
        self._assert_sandbox_order_path(path)
        if not self.network_enabled:
            raise SandboxOrderPolicyError("Sandbox order network requires explicit opt-in.")

        url=self.base_url+path
        auth=oauth_header(
            "POST",url,
            self.consumer_key,self.consumer_secret,
            token=self.access_token,
            token_secret=self.access_token_secret,
        )
        data=json.dumps(payload,separators=(",",":")).encode("utf-8")
        self.calls.append({"method":"POST","path":path})
        req=Request(
            url,
            data=data,
            headers={
                "Authorization":auth,
                "Accept":"application/json",
                "Content-Type":"application/json",
            },
            method="POST",
        )
        with urlopen(req,timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


class FixtureSandboxOrderTransport:
    def __init__(self,responses):
        self.responses=dict(responses)
        self.calls=[]

    def post_json(self,path,payload):
        self.calls.append({"method":"POST","path":path,"payload":payload})
        if path not in self.responses:
            raise KeyError(path)
        value=self.responses[path]
        return value(payload) if callable(value) else value
