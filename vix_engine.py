from __future__ import annotations
import time, yfinance as yf, pandas as pd
from indicators import ema, rsi_divergence

_external={'bias':'neutral','score':0.0,'source':'internal','updated_at':0}

def set_external(bias:str, score:float=0.0):
    global _external
    _external={'bias':bias,'score':score,'source':'external_vix_app','updated_at':int(time.time())}
    return _external

def get_external(): return _external

def _dl(sym, period='60d', interval='1h'):
    x=yf.download(sym,period=period,interval=interval,auto_adjust=False,progress=False,threads=False)
    if x.empty: raise RuntimeError(sym)
    if isinstance(x.columns,pd.MultiIndex): x.columns=x.columns.get_level_values(0)
    x=x.reset_index().rename(columns={'Datetime':'ts','Date':'ts','Open':'open','High':'high','Low':'low','Close':'close','Volume':'volume'})
    return x[['ts','open','high','low','close','volume']].dropna()

def _resample(df,rule):
    return df.set_index('ts').resample(rule).agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna().reset_index()

def analyze_internal_vix():
    # Internal fallback inspired by the user's VIX app. External app signal, when fresh, takes priority.
    if _external['source']=='external_vix_app' and time.time()-_external['updated_at'] < 6*3600:
        return _external
    v=_dl('^VIX'); v9=_dl('^VIX9D')
    v12=_resample(v,'12h'); v4=_resample(v,'4h')
    close=v12.close; e9=ema(close,9); e26=ema(close,26)
    score=0.0; reasons=[]
    if close.iloc[-1]>e9.iloc[-1]: score+=1.2; reasons.append('VIX above EMA9')
    else: score-=1.0
    if e9.iloc[-1]>e26.iloc[-1]: score+=1.0; reasons.append('VIX EMA9 > EMA26')
    else: score-=1.0
    ratio=float(v9.close.iloc[-1]/v.close.iloc[-1])
    if ratio>1.03: score+=1.4; reasons.append('VIX9D > VIX by >3%')
    elif ratio<0.97: score-=1.1
    d4=rsi_divergence(v4); d12=rsi_divergence(v12)
    # Bullish VIX divergence = equities risk-off; bearish = risk-on.
    if d4=='bullish': score+=.45
    elif d4=='bearish': score-=.45
    if d12=='bullish': score+=.75
    elif d12=='bearish': score-=.75
    if d4==d12 and d4!='none': score += .35 if d4=='bullish' else -.35
    bias='risk_off' if score>=1.3 else 'risk_on' if score<=-1.3 else 'neutral'
    return {'bias':bias,'score':round(score,2),'source':'internal_vix','reasons':reasons,'vix':round(float(v.close.iloc[-1]),2),'vix9d_ratio':round(ratio,3),'div4h':d4,'div12h':d12,'updated_at':int(time.time())}
