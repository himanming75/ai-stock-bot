from __future__ import annotations
import statistics

def sma(values, n):
    return sum(values[-n:])/n if len(values) >= n else None

def ema(values, n):
    if not values: return None
    alpha = 2/(n+1); value = values[0]
    for x in values[1:]: value = alpha*x + (1-alpha)*value
    return value

def rsi(values, n=14):
    if len(values) <= n: return None
    d=[b-a for a,b in zip(values[-n-1:], values[-n:])]
    gains=sum(max(x,0) for x in d)/n; losses=sum(max(-x,0) for x in d)/n
    if losses == 0: return 100.0
    return 100-(100/(1+gains/losses))

def signal(name, closes, config):
    if name == "EMA_CROSS":
        f,s=config.get("fast",10),config.get("slow",30)
        if len(closes)<s+1:return "HOLD"
        pf,ps=ema(closes[:-1],f),ema(closes[:-1],s)
        cf,cs=ema(closes,f),ema(closes,s)
        return "BUY" if pf<=ps and cf>cs else "SELL" if pf>=ps and cf<cs else "HOLD"
    if name == "RSI":
        value=rsi(closes,config.get("period",14))
        if value is None:return "HOLD"
        return "BUY" if value<=config.get("oversold",35) else "SELL" if value>=config.get("overbought",65) else "HOLD"
    if name == "MOMENTUM":
        n=config.get("period",15)
        if len(closes)<n+2:return "HOLD"
        current=closes[-1]/closes[-n-1]-1
        previous=closes[-2]/closes[-n-2]-1
        return "BUY" if previous<=0 and current>0 else "SELL" if previous>=0 and current<0 else "HOLD"
    if name == "BOLLINGER":
        n=config.get("period",20); k=config.get("std",2)
        if len(closes)<n:return "HOLD"
        window=closes[-n:]; mid=statistics.mean(window); sd=statistics.pstdev(window)
        return "BUY" if closes[-1]<mid-k*sd else "SELL" if closes[-1]>mid+k*sd else "HOLD"
    if name == "MACD":
        if len(closes)<35:return "HOLD"
        line=ema(closes,12)-ema(closes,26)
        prev=ema(closes[:-1],12)-ema(closes[:-1],26)
        return "BUY" if prev<=0 and line>0 else "SELL" if prev>=0 and line<0 else "HOLD"
    return "HOLD"
