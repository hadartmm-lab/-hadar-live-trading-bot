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


def impulse_fib(df: pd.DataFrame, lookback=220, pivot_left=4, pivot_right=4, min_impulse_atr=2.2):
    """12H smart Fibonacci anchored to the latest meaningful impulse.

    Logic:
    1) Find confirmed swing pivots on the supplied 12H frame.
    2) Identify the latest significant directional leg ("explosion") whose size is
       at least ``min_impulse_atr`` ATR and whose directional efficiency is reasonable.
    3) Keep the START of that impulse fixed and extend the END anchor to the latest
       extreme created in the same direction (latest/highest high for bullish,
       latest/lowest low for bearish). This makes the Fib update as the impulse extends.
    4) Evaluate the current retracement against the 0.50-0.618 zone.

    Fibonacci is an approval layer, not a stand-alone entry trigger.
    """
    if df is None or len(df) < 40:
        return {'status':'none','direction':'none','in_zone':False,'reason':'insufficient_data'}

    x=df.tail(lookback).copy().reset_index(drop=True)
    a_series=atr(x,14).replace([np.inf,-np.inf],np.nan)
    a_now=float(a_series.dropna().iloc[-1]) if a_series.notna().any() else 0.0
    if not np.isfinite(a_now) or a_now <= 0:
        return {'status':'none','direction':'none','in_zone':False,'reason':'invalid_atr'}

    hs=pivots(x.high,pivot_left,pivot_right,'high')
    ls=pivots(x.low,pivot_left,pivot_right,'low')
    points=[(int(i),'H',float(x.high.iloc[i])) for i in hs] + [(int(i),'L',float(x.low.iloc[i])) for i in ls]
    points.sort(key=lambda z:z[0])
    if len(points) < 2:
        return {'status':'none','direction':'none','in_zone':False,'reason':'no_pivots'}

    # Compress consecutive same-type pivots, keeping the more extreme one.
    alt=[]
    for pt in points:
        if not alt or alt[-1][1] != pt[1]:
            alt.append(pt)
        else:
            prev=alt[-1]
            if (pt[1]=='H' and pt[2] >= prev[2]) or (pt[1]=='L' and pt[2] <= prev[2]):
                alt[-1]=pt

    candidates=[]
    for j in range(1,len(alt)):
        p0,p1=alt[j-1],alt[j]
        if p0[1]==p1[1]:
            continue
        direction='bullish' if (p0[1]=='L' and p1[1]=='H') else 'bearish'
        move=abs(p1[2]-p0[2])
        end_atr=float(a_series.iloc[p1[0]]) if p1[0] < len(a_series) and np.isfinite(a_series.iloc[p1[0]]) else a_now
        end_atr=max(end_atr,1e-9)
        atr_mult=move/end_atr
        bars=max(1,p1[0]-p0[0])

        seg=x.iloc[p0[0]:p1[0]+1]
        if len(seg) < 2:
            continue
        path=float(seg.close.diff().abs().sum())
        efficiency=(move/path) if path>1e-9 else 0.0

        # Require a meaningful 12H impulse, while allowing fast and clean moves.
        significant=(atr_mult >= min_impulse_atr and efficiency >= 0.28) or (atr_mult >= 3.0)
        if significant:
            quality=min(1.0, (atr_mult/5.0)*0.65 + min(1.0,efficiency)*0.35)
            candidates.append({
                'start_idx':p0[0], 'pivot_end_idx':p1[0], 'direction':direction,
                'start_price':p0[2], 'pivot_end_price':p1[2], 'atr_mult':atr_mult,
                'efficiency':efficiency, 'quality':quality, 'bars':bars
            })

    if not candidates:
        return {'status':'none','direction':'none','in_zone':False,'reason':'no_significant_impulse'}

    # User rule: use the LAST meaningful explosion, not the biggest historical move.
    imp=max(candidates, key=lambda c:c['pivot_end_idx'])
    s=imp['start_idx']
    direction=imp['direction']

    # Extend the impulse anchor to the latest extreme made after the launch.
    post=x.iloc[s:]
    if direction=='bullish':
        rel=int(np.argmax(post.high.to_numpy()))
        end_idx=s+rel
        low=float(imp['start_price'])
        high=float(x.high.iloc[end_idx])
        # If a later low undercuts the anchor, that impulse is no longer valid.
        invalid_anchor=bool(float(x.low.iloc[s:].min()) < low - 0.05*a_now)
    else:
        rel=int(np.argmin(post.low.to_numpy()))
        end_idx=s+rel
        high=float(imp['start_price'])
        low=float(x.low.iloc[end_idx])
        invalid_anchor=bool(float(x.high.iloc[s:].max()) > high + 0.05*a_now)

    rng=high-low
    if not np.isfinite(rng) or rng <= 0:
        return {'status':'none','direction':'none','in_zone':False,'reason':'invalid_range'}

    p=float(x.close.iloc[-1])
    if direction=='bullish':
        z50=high-.50*rng
        z618=high-.618*rng
        depth=(high-p)/rng
        invalid_price=p < low
        post_extreme=x.iloc[end_idx:]
        structure_ok=(structure(post_extreme)!='bearish') if len(post_extreme)>=5 else True
    else:
        z50=low+.50*rng
        z618=low+.618*rng
        depth=(p-low)/rng
        invalid_price=p > high
        post_extreme=x.iloc[end_idx:]
        structure_ok=(structure(post_extreme)!='bullish') if len(post_extreme)>=5 else True

    lo=min(z50,z618); hi=max(z50,z618)
    in_zone=lo <= p <= hi
    invalid=bool(invalid_anchor or invalid_price)
    healthy=bool(in_zone and not invalid and structure_ok)

    # Distance to the Fib zone in ATR units helps UI/scoring distinguish "near" from irrelevant.
    if p < lo: dist=lo-p
    elif p > hi: dist=p-hi
    else: dist=0.0
    zone_distance_atr=dist/max(a_now,1e-9)

    return {
        'status':'healthy_pullback' if healthy else 'in_zone' if in_zone else 'watch',
        'direction':direction,
        'in_zone':bool(in_zone),
        'invalid':invalid,
        'structure_ok':bool(structure_ok),
        'swing_low':round(low,8),
        'swing_high':round(high,8),
        'impulse_start_idx':int(s),
        'impulse_end_idx':int(end_idx),
        'zone_low':round(lo,8),
        'zone_high':round(hi,8),
        'price':round(p,8),
        'retracement':round(float(depth),3),
        'zone_distance_atr':round(float(zone_distance_atr),2),
        'impulse_atr_mult':round(float(imp['atr_mult']),2),
        'impulse_efficiency':round(float(imp['efficiency']),2),
        'impulse_quality':round(float(imp['quality']),2),
        'anchor_rule':'latest_significant_12h_impulse_to_latest_extreme'
    }
