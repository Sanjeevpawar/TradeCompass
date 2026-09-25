from math import isfinite
from statistics import mean
from data.candle_models import Candle


def sma(values, period):
    if len(values) < period: return None
    return mean(values[-period:])

def ema(values, period):
    if len(values) < period: return None
    k = 2 / (period + 1)
    value = mean(values[:period])
    for x in values[period:]: value = x * k + value * (1-k)
    return value

def rsi(values, period=14):
    if len(values) <= period: return None
    gains, losses = [], []
    for a,b in zip(values[-period-1:-1], values[-period:]):
        d=b-a; gains.append(max(d,0)); losses.append(max(-d,0))
    ag, al = mean(gains), mean(losses)
    if al == 0: return 100.0
    return 100 - (100/(1 + ag/al))

def atr(candles, period=14):
    if len(candles) <= period: return None
    trs=[]
    for i,c in enumerate(candles):
        if i==0: tr=c.high-c.low
        else:
            prev=candles[i-1].close
            tr=max(c.high-c.low, abs(c.high-prev), abs(c.low-prev))
        trs.append(tr)
    return mean(trs[-period:])

def vwap(candles):
    pv=sum(((c.high+c.low+c.close)/3)*c.volume for c in candles)
    vol=sum(c.volume for c in candles)
    return pv/vol if vol else None

def macd(values, fast=12, slow=26, signal=9):
    if len(values) < slow + signal: return None
    series=[]
    for i in range(slow, len(values)+1):
        window=values[:i]
        series.append(ema(window, fast)-ema(window, slow))
    line=series[-1]
    sig=ema(series, signal)
    return {"line":line, "signal":sig, "histogram":line-sig if sig is not None else None}

def volume_ratio(candles, period=20):
    if len(candles) <= period: return None
    avg=mean(c.volume for c in candles[-period-1:-1])
    return candles[-1].volume/avg if avg else None

def calculate_indicators(candles):
    closes=[c.close for c in candles]
    return {
        "ema_5": ema(closes,5), "ema_20": ema(closes,20), "ema_50": ema(closes,50),
        "sma_100": sma(closes,100), "sma_200": sma(closes,200),
        "rsi_14": rsi(closes,14), "atr_14": atr(candles,14), "vwap": vwap(candles),
        "macd": macd(closes), "volume_ratio": volume_ratio(candles,20),
    }
