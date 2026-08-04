import os
def detect(account):
 p=str(account.get("credential_prefix","")).strip(); k=os.getenv(f"{p}_API_KEY",""); s=os.getenv(f"{p}_SECRET_KEY","")
 return {"credential_prefix":p,"api_key_present":bool(k),"secret_key_present":bool(s),"ready":bool(k and s)}
