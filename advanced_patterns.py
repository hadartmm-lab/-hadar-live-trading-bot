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


def market_regime(df: pd.DataFrame, lookback=90):
    """Classify market state as trend/range/transition using swing structure + EMA slope + compression."""
    from indicators import ema
    x=df.tail(lookback).copy().reset_index(drop=True)
    if len(x)<35:
        return {'regime':'unknown','direction':'neutral','strength':0.0}
    st=structure(x)
    e20=ema(x.close,20); e50=ema(x.close,50)
    slope20=float(e20.iloc[-1]-e20.iloc[-8])/max(abs(float(x.close.iloc[-1])),1e-9)
    spread=abs(float(e20.iloc[-1]-e50.iloc[-1]))/max(abs(float(x.close.iloc[-1])),1e-9)
    a=float(atr(x,14).iloc[-1]); price=max(abs(float(x.close.iloc[-1])),1e-9)
    volnorm=a/price
    pos=(float(x.close.iloc[-1])-float(x.low.tail(50).min()))/max(float(x.high.tail(50).max()-x.low.tail(50).min()),1e-9)
    if st in ('bullish','bearish') and (abs(slope20)>0.002 or spread>0.006):
        strength=min(1.0, .45+abs(slope20)*40+spread*15)
        return {'regime':'trend','direction':st,'strength':round(strength,2),'range_position':round(pos,2)}
    if st=='range' and spread<0.008 and abs(slope20)<0.003:
        strength=min(1.0,.55+max(0,.008-spread)*20)
        return {'regime':'range','direction':'neutral','strength':round(strength,2),'range_position':round(pos,2)}
    direction='bullish' if slope20>0 else 'bearish' if slope20<0 else 'neutral'
    return {'regime':'transition','direction':direction,'strength':round(min(1.0,.35+volnorm*12),2),'range_position':round(pos,2)}


def bos_choch(df: pd.DataFrame, lookback=120):
    """Heuristic BOS/CHoCH from recent confirmed swing highs/lows and current close."""
    x=df.tail(lookback).copy().reset_index(drop=True)
    hs=pivots(x.high,3,3,'high'); ls=pivots(x.low,3,3,'low')
    if len(hs)<2 or len(ls)<2:
        return {'event':'none','direction':'none','level':None,'strength':0.0}
    prev_h=float(x.high.iloc[hs[-1]])
    prev_l=float(x.low.iloc[ls[-1]])
    close=float(x.close.iloc[-1])
    st_before=structure(x.iloc[:-1]) if len(x)>20 else 'range'
    a=max(float(atr(x,14).iloc[-1]),1e-9)
    if close>prev_h:
        event='BOS' if st_before=='bullish' else 'CHoCH'
        strength=min(1.0,.5+(close-prev_h)/a*.25)
        return {'event':event,'direction':'bullish','level':prev_h,'strength':round(strength,2)}
    if close<prev_l:
        event='BOS' if st_before=='bearish' else 'CHoCH'
        strength=min(1.0,.5+(prev_l-close)/a*.25)
        return {'event':event,'direction':'bearish','level':prev_l,'strength':round(strength,2)}
    return {'event':'none','direction':'none','level':None,'strength':0.0}


def impulse_fib(df: pd.DataFrame, lookback=180):
    """Select the latest relevant impulse from alternating pivots, then evaluate 0.50-0.618 pullback."""
    x=df.tail(lookback).copy().reset_index(drop=True)
    hs=pivots(x.high,4,4,'high'); ls=pivots(x.low,4,4,'low')
    points=[]
    for i in hs: points.append((i,'H',float(x.high.iloc[i])))
    for i in ls: points.append((i,'L',float(x.low.iloc[i])))
    points.sort(key=lambda z:z[0])
    if len(points)<3:
        return {'status':'none','direction':'none','in_zone':False}
    # Latest completed impulse ending at a confirmed pivot, favor larger moves relative to ATR.
    a=max(float(atr(x,14).iloc[-1]),1e-9)
    candidates=[]
    for j in range(1,len(points)):
        p0,p1=points[j-1],points[j]
        if p0[1]==p1[1]:
            continue
        move=abs(p1[2]-p0[2])
        bars=max(1,p1[0]-p0[0])
        quality=(move/a) * min(1.5, bars/8)
        candidates.append((p1[0],quality,p0,p1))
    if not candidates:
        return {'status':'none','direction':'none','in_zone':False}
    # Last meaningful impulse: among recent 5 choose quality-aware latest.
    recent=candidates[-5:]
    _,quality,p0,p1=max(recent,key=lambda c:(c[0] + min(c[1],10)*1.5))
    if p0[1]=='L' and p1[1]=='H':
        direction='bullish'; low=p0[2]; high=p1[2]; end_idx=p1[0]
        rng=high-low
        z50=high-.50*rng; z618=high-.618*rng
        p=float(x.close.iloc[-1]); lo=min(z50,z618); hi=max(z50,z618)
        in_zone=lo<=p<=hi
        invalid=p<low
        post=x.iloc[end_idx:]
        healthy=in_zone and not invalid and structure(post)!='bearish'
    else:
        direction='bearish'; high=p0[2]; low=p1[2]; end_idx=p1[0]
        rng=high-low
        z50=low+.50*rng; z618=low+.618*rng
        p=float(x.close.iloc[-1]); lo=min(z50,z618); hi=max(z50,z618)
        in_zone=lo<=p<=hi
        invalid=p>high
        post=x.iloc[end_idx:]
        healthy=in_zone and not invalid and structure(post)!='bullish'
    depth=((high-p)/rng if direction=='bullish' else (p-low)/rng) if rng>0 else 0
    return {
        'status':'healthy_pullback' if healthy else 'in_zone' if in_zone else 'watch',
        'direction':direction,'in_zone':in_zone,'invalid':invalid,
        'swing_low':round(low,8),'swing_high':round(high,8),
        'zone_low':round(lo,8),'zone_high':round(hi,8),'price':round(p,8),
        'retracement':round(depth,3),'impulse_quality':round(min(1.0,quality/8),2)
    }
