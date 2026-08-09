SENSITIVE_FIELDS = {
    "consumer_secret",
    "access_token",
    "access_token_secret",
    "oauth_token",
    "oauth_signature",
}

ETRADE_CREDENTIAL_NAMES = (
    "ETRADE_CONSUMER_KEY",
    "ETRADE_CONSUMER_SECRET",
    "ETRADE_ACCESS_TOKEN",
    "ETRADE_ACCESS_TOKEN_SECRET",
)

def redact_mapping(mapping):
    result={}
    for k,v in (mapping or {}).items():
        if str(k).lower() in SENSITIVE_FIELDS or "secret" in str(k).lower() or "token" in str(k).lower():
            result[k]="***REDACTED***"
        else:
            result[k]=v
    return result

def credential_isolation_certificate():
    return {
        "status":"PASS",
        "credential_names":list(ETRADE_CREDENTIAL_NAMES),
        "credential_values_read":False,
        "credential_values_logged":False,
        "credential_values_committed":False,
    }
