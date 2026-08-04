import os
def load():
    k=os.getenv("ALPACA_PAPER_API_KEY") or os.getenv("APCA_API_KEY_ID") or ""
    s=os.getenv("ALPACA_PAPER_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY") or ""
    return {"api_key":k,"secret_key":s,"ready":bool(k and s)}
