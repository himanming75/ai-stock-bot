from __future__ import annotations

from urllib.parse import parse_qs, quote, urlencode
from urllib.request import Request, urlopen

from .etrade_oauth_profile_v2 import ETRADE_OAUTH_PROFILE
from .etrade_oauth_signer import oauth_header


class OAuthNetworkDisabled(RuntimeError):
    pass


def _read_form_response(response):
    raw=response.read().decode("utf-8")
    return {k:v[0] for k,v in parse_qs(raw,keep_blank_values=True).items()}


class ETradeOAuthFlow:
    def __init__(self,consumer_key,consumer_secret,network_enabled=False,callback="oob"):
        self.consumer_key=consumer_key
        self.consumer_secret=consumer_secret
        self.network_enabled=bool(network_enabled)
        self.callback=callback or "oob"

    def _get_form(self,url,token=None,token_secret="",extra_oauth=None):
        if not self.network_enabled:
            raise OAuthNetworkDisabled("OAuth network calls require explicit opt-in.")
        header=oauth_header(
            "GET",url,self.consumer_key,self.consumer_secret,
            token=token,token_secret=token_secret,extra_oauth=extra_oauth,
        )
        req=Request(url,headers={"Authorization":header},method="GET")
        with urlopen(req,timeout=30) as response:
            return _read_form_response(response)

    def request_token(self):
        return self._get_form(
            ETRADE_OAUTH_PROFILE["request_token_url"],
            extra_oauth={"oauth_callback":self.callback},
        )

    def authorization_url(self,request_token):
        q=urlencode({"key":self.consumer_key,"token":request_token})
        return ETRADE_OAUTH_PROFILE["authorize_url"]+"?"+q

    def access_token(self,request_token,request_token_secret,verifier):
        return self._get_form(
            ETRADE_OAUTH_PROFILE["access_token_url"],
            token=request_token,
            token_secret=request_token_secret,
            extra_oauth={"oauth_verifier":verifier},
        )

    def renew(self,access_token,access_token_secret):
        return self._get_form(
            ETRADE_OAUTH_PROFILE["renew_access_token_url"],
            token=access_token,
            token_secret=access_token_secret,
        )

    def revoke(self,access_token,access_token_secret):
        return self._get_form(
            ETRADE_OAUTH_PROFILE["revoke_access_token_url"],
            token=access_token,
            token_secret=access_token_secret,
        )
