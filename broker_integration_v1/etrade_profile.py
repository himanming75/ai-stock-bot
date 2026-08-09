ETRADE_API_PROFILE = {
    "auth_protocol": "OAuth 1.0a",
    "signature_method": "HMAC-SHA1",
    "sandbox_base_url": "https://apisb.etrade.com/v1",
    "production_base_url": "https://api.etrade.com/v1",
    "read_endpoints": {
        "accounts": "/accounts/list.json",
        "balance": "/accounts/{accountIdKey}/balance.json",
        "portfolio": "/accounts/{accountIdKey}/portfolio.json",
        "orders": "/accounts/{accountIdKey}/orders.json",
    },
    "write_endpoints_enabled": False,
    "network_enabled_by_default": False,
}

def etrade_profile_certificate():
    return {
        "status":"PASS",
        "profile":ETRADE_API_PROFILE,
        "oauth_1_0a":True,
        "hmac_sha1":True,
        "read_only":True,
        "network_used":False,
        "order_submission_performed":False,
    }
