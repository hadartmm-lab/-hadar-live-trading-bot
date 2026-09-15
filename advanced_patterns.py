from __future__ import annotations
import numpy as np
import pandas as pd
from indicators import pivots, atr, structure


def _lin_slope(y):
    y=np.asarray(y,dtype=float)
    if len(y)<3: return 0.0
    x=np.arange(len(y),dtype=float)
    return float(np.polyfit(x,y,1)[0])


def liquidity_sweep(df: pd.DataFrame, lookback=40, atr_period=14):
    """Detect stop-hunt style wick through a prior local extreme followed by reclaim.
    Returns the latest bullish/bearish sweep if present. Heuristic, not exchange order-book proof.
    """
    if len(df)<lookback+5: return {'type':'none','strength':0}
    x=df.tail(lookback+1).copy().reset_index(drop=True)
    a=atr(x,atr_period).iloc[-1]
    cur=x.iloc[-1]
    prev=x.iloc[:-1]
    prior_low=float(prev.low.tail(lookback).min())
    prior_high=float(prev.high.tail(lookback).max())
    rng=max(float(a),1e-9)
    body=abs(float(cur.close-cur.open))
    lower_wick=min(float(cur.open),float(cur.close))-float(cur.low)
    upper_wick=float(cur.high)-max(float(cur.open),float(cur.close))
    bull = cur.low < prior_low and cur.close > prior_low and lower_wick > max(body*1.2, .20*rng)
    bear = cur.high > prior_high and cur.close < prior_high and upper_wick > max(body*1.2, .20*rng)
    if bull:
        penetration=(prior_low-float(cur.low))/rng
        return {'type':'bullish','strength':round(min(1.0,.45+penetration*.35+min(lower_wick/rng,.5)),2),
                'level':prior_low,'wick_low':float(cur.low),'reclaim_close':float(cur.close)}
    if bear:
        penetration=(float(cur.high)-prior_high)/rng
        return {'type':'bearish','strength':round(min(1.0,.45+penetration*.35+min(upper_wick/rng,.5)),2),
                'level':prior_high,'wick_high':float(cur.high),'reclaim_close':float(cur.close)}
    return {'type':'none','strength':0}


def support_resistance(df: pd.DataFrame, lookback=180, tolerance_atr=.45):
    """Cluster pivot highs/lows into horizontal S/R zones and score touches."""
    x=df.tail(lookback).copy().reset_index(drop=True)
    if len(x)<30: return {'support':None,'resistance':None,'zones':[]}
    a=float(atr(x,14).iloc[-1]); tol=max(a*tolerance_atr, float(x.close.iloc[-1])*.001)
    hs=pivots(x.high,3,3,'high'); ls=pivots(x.low,3,3,'low')
    pts=[(float(x.high.iloc[i]),'R',i) for i in hs]+[(float(x.low.iloc[i]),'S',i) for i in ls]
    pts.sort(key=lambda z:z[0])
    clusters=[]
    for price,kind,idx in pts:
        placed=False
        for c in clusters:
            if abs(price-c['price'])<=tol:
                n=c['touches']; c['price']=(c['price']*n+price)/(n+1); c['touches']+=1; c['kinds'].append(kind); c['last_idx']=max(c['last_idx'],idx); placed=True; break
        if not placed: clusters.append({'price':price,'touches':1,'kinds':[kind],'last_idx':idx})
    p=float(x.close.iloc[-1])
    zones=[]
    for c in clusters:
        age=max(0,len(x)-1-c['last_idx']); recency=max(0,1-age/max(len(x),1))
        score=c['touches'] + recency
        zones.append({'price':round(c['price'],8),'touches':c['touches'],'score':round(score,2),
                      'role':'support' if c['price']<=p else 'resistance'})
    supports=sorted([z for z in zones if z['price']<=p], key=lambda z:(p-z['price'], -z['score']))
    resist=sorted([z for z in zones if z['price']>p], key=lambda z:(z['price']-p, -z['score']))
    return {'support':supports[0] if supports else None,'resistance':resist[0] if resist else None,
            'zones':sorted(zones,key=lambda z:z['score'],reverse=True)[:8]}


def flag_wedge_pattern(df: pd.DataFrame, lookback=70):
    """Conservative geometric heuristic for bull/bear flags and rising/falling wedges."""
    x=df.tail(lookback).copy().reset_index(drop=True)
    if len(x)<35: return {'pattern':'none','confidence':0}
    # impulse = first ~55%, consolidation = last ~45%
    cut=max(20,int(len(x)*.58)); imp=x.iloc[:cut]; con=x.iloc[cut:]
    imp_move=float(imp.close.iloc[-1]-imp.close.iloc[0]); imp_rng=max(float(imp.high.max()-imp.low.min()),1e-9)
    imp_strength=abs(imp_move)/imp_rng
    hs=pivots(con.high,2,2,'high'); ls=pivots(con.low,2,2,'low')
    if len(hs)<2 or len(ls)<2 or imp_strength<.45: return {'pattern':'none','confidence':0}
    hvals=[float(con.high.iloc[i]) for i in hs[-4:]]; lvals=[float(con.low.iloc[i]) for i in ls[-4:]]
    hslope=_lin_slope(hvals); lslope=_lin_slope(lvals)
    scale=max(float(con.close.mean()),1e-9); hn=hslope/scale; ln=lslope/scale
    bull_imp=imp_move>0; bear_imp=imp_move<0
    pattern='none'; conf=0.0
    # flags: both boundaries drift against impulse, roughly parallel
    if bull_imp and hn<0 and ln<0:
        parallel=1-min(1,abs(hn-ln)/max(abs(hn)+abs(ln),1e-9)); pattern='bull_flag'; conf=.55+.25*parallel+.2*imp_strength
    elif bear_imp and hn>0 and ln>0:
        parallel=1-min(1,abs(hn-ln)/max(abs(hn)+abs(ln),1e-9)); pattern='bear_flag'; conf=.55+.25*parallel+.2*imp_strength
    # wedges: converging boundaries. Rising wedge bearish, falling wedge bullish.
    width_start=float(con.high.iloc[:max(3,len(con)//4)].max()-con.low.iloc[:max(3,len(con)//4)].min())
    width_end=float(con.high.iloc[-max(3,len(con)//4):].max()-con.low.iloc[-max(3,len(con)//4):].min())
    converging=width_end < width_start*.82
    if converging and hn>0 and ln>0 and ln>hn: pattern='rising_wedge'; conf=max(conf,.68)
    if converging and hn<0 and ln<0 and hn<ln: pattern='falling_wedge'; conf=max(conf,.68)
    return {'pattern':pattern,'confidence':round(min(conf,1.0),2),'high_slope':round(hn,6),'low_slope':round(ln,6),
            'impulse':'bullish' if bull_imp else 'bearish'}
