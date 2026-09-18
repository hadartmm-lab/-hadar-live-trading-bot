from __future__ import annotations
import numpy as np
import pandas as pd


def ema(s: pd.Series, span: int):
    return s.ewm(span=span, adjust=False).mean()


def rsi(s: pd.Series, period: int = 14):
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    # Wilder RSI edge cases: no losses => 100, no gains and no losses => 50.
    out = out.mask((dn == 0) & (up > 0), 100.0)
    out = out.mask((dn == 0) & (up == 0), 50.0)
    return out


def atr(df: pd.DataFrame, period: int = 10):
    pc = df['close'].shift(1)
    tr = pd.concat([(df.high-df.low).abs(), (df.high-pc).abs(), (df.low-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()


def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    a = atr(df, period)
    hl2 = (df.high + df.low) / 2
    upper = hl2 + multiplier * a
    lower = hl2 - multiplier * a
    final_u, final_l = upper.copy(), lower.copy()
    direction = pd.Series(index=df.index, dtype='int64')
    st = pd.Series(index=df.index, dtype='float64')
    direction.iloc[0] = 1
    st.iloc[0] = lower.iloc[0]
    for i in range(1, len(df)):
        final_u.iloc[i] = upper.iloc[i] if (upper.iloc[i] < final_u.iloc[i-1] or df.close.iloc[i-1] > final_u.iloc[i-1]) else final_u.iloc[i-1]
        final_l.iloc[i] = lower.iloc[i] if (lower.iloc[i] > final_l.iloc[i-1] or df.close.iloc[i-1] < final_l.iloc[i-1]) else final_l.iloc[i-1]
        if direction.iloc[i-1] == -1 and df.close.iloc[i] > final_u.iloc[i-1]:
            direction.iloc[i] = 1
        elif direction.iloc[i-1] == 1 and df.close.iloc[i] < final_l.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
        st.iloc[i] = final_l.iloc[i] if direction.iloc[i] == 1 else final_u.iloc[i]
    return st, direction


def pivots(series: pd.Series, left=3, right=3, kind='low'):
    vals = series.values
    out = []
    for i in range(left, len(vals)-right):
        win = vals[i-left:i+right+1]
        if kind == 'low' and vals[i] == np.nanmin(win): out.append(i)
        if kind == 'high' and vals[i] == np.nanmax(win): out.append(i)
    return out


def structure(df: pd.DataFrame):
    hs, ls = pivots(df.high, 3, 3, 'high'), pivots(df.low, 3, 3, 'low')
    h = [df.high.iloc[i] for i in hs[-3:]]
    l = [df.low.iloc[i] for i in ls[-3:]]
    if len(h)>=2 and len(l)>=2:
        if h[-1] > h[-2] and l[-1] > l[-2]: return 'bullish'
        if h[-1] < h[-2] and l[-1] < l[-2]: return 'bearish'
    return 'range'


def candle_bias_1h(df: pd.DataFrame, bars=6):
    x = df.tail(bars)
    green = int((x.close > x.open).sum()); red = int((x.close < x.open).sum())
    slope = x.close.iloc[-1] - x.close.iloc[0]
    if green >= 4 and slope > 0: return 'bullish'
    if red >= 4 and slope < 0: return 'bearish'
    return 'neutral'


def fib_retracement_health(df: pd.DataFrame, lookback=120):
    """Auto-detect latest meaningful impulse and 0.50-0.618 retracement zone.
    0.50 is a market convention (not a Fibonacci ratio); 0.618 is Fibonacci.
    """
    x = df.tail(lookback).copy().reset_index(drop=True)
    hs, ls = pivots(x.high, 4, 4, 'high'), pivots(x.low, 4, 4, 'low')
    if not hs or not ls:
        return {'status':'none','direction':'none','in_zone':False}
    last_h, last_l = hs[-1], ls[-1]
    if last_l < last_h:
        # bullish impulse low -> high; retracement downward from high
        low, high = float(x.low.iloc[last_l]), float(x.high.iloc[last_h])
        if high <= low: return {'status':'none','direction':'none','in_zone':False}
        p = float(x.close.iloc[-1]); rng=high-low
        z50 = high - .50*rng; z618 = high - .618*rng
        lo, hi = min(z50,z618), max(z50,z618)
        in_zone = lo <= p <= hi
        healthy = in_zone and structure(x.iloc[max(0,last_l):]) != 'bearish'
        return {'status':'healthy_pullback' if healthy else 'watch','direction':'bullish','in_zone':in_zone,'swing_low':low,'swing_high':high,'zone_low':lo,'zone_high':hi,'price':p}
    else:
        # bearish impulse high -> low; retracement upward
        high, low = float(x.high.iloc[last_h]), float(x.low.iloc[last_l])
        if high <= low: return {'status':'none','direction':'none','in_zone':False}
        p=float(x.close.iloc[-1]); rng=high-low
        z50 = low + .50*rng; z618 = low + .618*rng
        lo, hi = min(z50,z618), max(z50,z618)
        in_zone = lo <= p <= hi
        healthy = in_zone and structure(x.iloc[max(0,last_h):]) != 'bullish'
        return {'status':'healthy_pullback' if healthy else 'watch','direction':'bearish','in_zone':in_zone,'swing_low':low,'swing_high':high,'zone_low':lo,'zone_high':hi,'price':p}


def rsi_divergence(df: pd.DataFrame, period=14):
    rr = rsi(df.close, period)
    lows = pivots(df.low,4,4,'low'); highs=pivots(df.high,4,4,'high')
    if len(lows)>=2:
        a,b=lows[-2],lows[-1]
        if df.low.iloc[b] < df.low.iloc[a] and rr.iloc[b] > rr.iloc[a]: return 'bullish'
    if len(highs)>=2:
        a,b=highs[-2],highs[-1]
        if df.high.iloc[b] > df.high.iloc[a] and rr.iloc[b] < rr.iloc[a]: return 'bearish'
    return 'none'


def volume_confirmation(df: pd.DataFrame):
    v=df.volume
    ratio=float(v.iloc[-1] / max(v.tail(20).mean(),1e-9))
    return ratio


def range_position(df: pd.DataFrame, lookback=60):
    x=df.tail(lookback); lo=float(x.low.min()); hi=float(x.high.max()); p=float(x.close.iloc[-1])
    pos=(p-lo)/(hi-lo) if hi>lo else .5
    return pos,lo,hi


def wyckoff_heuristic(df: pd.DataFrame):
    pos,lo,hi=range_position(df,80)
    vol=volume_confirmation(df)
    st=structure(df)
    # Heuristic only: range location + structure + volume confirmation
    if st=='range' and pos<.25 and vol<1.8: return 'accumulation_zone'
    if st=='range' and pos>.75 and vol<1.8: return 'distribution_zone'
    if st=='bullish' and pos>.55: return 'markup'
    if st=='bearish' and pos<.45: return 'markdown'
    return 'neutral'


def rsi_divergence_detail(df: pd.DataFrame, period=14):
    """Return RSI divergence plus pivot values for UI/scoring."""
    rr=rsi(df.close, period)
    lows=pivots(df.low,4,4,'low'); highs=pivots(df.high,4,4,'high')
    candidates=[]
    if len(lows)>=2:
        a,b=lows[-2],lows[-1]
        if pd.notna(rr.iloc[a]) and pd.notna(rr.iloc[b]):
            price_change=(float(df.low.iloc[b])-float(df.low.iloc[a]))/max(abs(float(df.low.iloc[a])),1e-9)
            rsi_change=float(rr.iloc[b]-rr.iloc[a])
            if price_change<0 and rsi_change>0:
                strength=min(1.0,.45+min(abs(price_change)*8,.25)+min(rsi_change/30,.3))
                candidates.append((b,{'type':'bullish','strength':round(strength,2),'price_a':float(df.low.iloc[a]),'price_b':float(df.low.iloc[b]),'rsi_a':round(float(rr.iloc[a]),1),'rsi_b':round(float(rr.iloc[b]),1)}))
    if len(highs)>=2:
        a,b=highs[-2],highs[-1]
        if pd.notna(rr.iloc[a]) and pd.notna(rr.iloc[b]):
            price_change=(float(df.high.iloc[b])-float(df.high.iloc[a]))/max(abs(float(df.high.iloc[a])),1e-9)
            rsi_change=float(rr.iloc[b]-rr.iloc[a])
            if price_change>0 and rsi_change<0:
                strength=min(1.0,.45+min(abs(price_change)*8,.25)+min(abs(rsi_change)/30,.3))
                candidates.append((b,{'type':'bearish','strength':round(strength,2),'price_a':float(df.high.iloc[a]),'price_b':float(df.high.iloc[b]),'rsi_a':round(float(rr.iloc[a]),1),'rsi_b':round(float(rr.iloc[b]),1)}))
    if not candidates:
        return {'type':'none','strength':0.0}
    return max(candidates,key=lambda z:z[0])[1]


def stoch_rsi_signal(df: pd.DataFrame, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
    """Directional confirmation from the user's second RSI layer.

    Uses regular RSI(14) direction plus Stoch RSI (3,3,14,14). A bullish
    confirmation is strongest when K crosses above D from/through the
    oversold band; bearish is strongest when K crosses below D from/through
    the overbought band. This is intended for 4H/12H/Daily only.
    """
    rr = rsi(df.close, rsi_period)
    lo = rr.rolling(stoch_period).min()
    hi = rr.rolling(stoch_period).max()
    raw = 100 * (rr - lo) / (hi - lo).replace(0, np.nan)
    k = raw.rolling(k_period).mean()
    d = k.rolling(d_period).mean()
    if len(df) < max(rsi_period + stoch_period + k_period + d_period, 35):
        return {'direction':'neutral','strength':0.0,'rsi_direction':'flat','cross':'none','band':'mid'}
    r_now=float(rr.iloc[-1]) if pd.notna(rr.iloc[-1]) else 50.0
    r_prev=float(rr.iloc[-4]) if pd.notna(rr.iloc[-4]) else r_now
    rsi_dir='up' if r_now > r_prev + 0.5 else 'down' if r_now < r_prev - 0.5 else 'flat'
    k0=float(k.iloc[-2]) if pd.notna(k.iloc[-2]) else 50.0
    d0=float(d.iloc[-2]) if pd.notna(d.iloc[-2]) else 50.0
    k1=float(k.iloc[-1]) if pd.notna(k.iloc[-1]) else 50.0
    d1=float(d.iloc[-1]) if pd.notna(d.iloc[-1]) else 50.0
    golden = k0 <= d0 and k1 > d1
    death = k0 >= d0 and k1 < d1
    vals=(k0,d0,k1,d1)
    oversold_touch=min(vals) <= 20
    oversold_near=min(vals) <= 30
    overbought_touch=max(vals) >= 80
    overbought_near=max(vals) >= 70
    # Classify the band in the context of the actual cross direction. This avoids
    # labeling a fast move that touched both extremes as the wrong band.
    if golden:
        band='oversold' if (oversold_touch or oversold_near) else 'mid'
    elif death:
        band='overbought' if (overbought_touch or overbought_near) else 'mid'
    else:
        cur=(k1+d1)/2
        band='oversold' if cur <= 30 else 'overbought' if cur >= 70 else 'mid'
    # Reward a fresh cross in/near the relevant band. Direction without a
    # fresh cross is still useful, but intentionally weaker.
    if golden and band=='oversold' and rsi_dir=='up':
        return {'direction':'bullish','strength':1.0,'rsi_direction':rsi_dir,'cross':'golden','band':band,'rsi':round(r_now,1),'k':round(k1,1),'d':round(d1,1)}
    if death and band=='overbought' and rsi_dir=='down':
        return {'direction':'bearish','strength':1.0,'rsi_direction':rsi_dir,'cross':'death','band':band,'rsi':round(r_now,1),'k':round(k1,1),'d':round(d1,1)}
    if golden and rsi_dir=='up':
        return {'direction':'bullish','strength':0.7,'rsi_direction':rsi_dir,'cross':'golden','band':band,'rsi':round(r_now,1),'k':round(k1,1),'d':round(d1,1)}
    if death and rsi_dir=='down':
        return {'direction':'bearish','strength':0.7,'rsi_direction':rsi_dir,'cross':'death','band':band,'rsi':round(r_now,1),'k':round(k1,1),'d':round(d1,1)}
    if rsi_dir=='up' and k1>d1:
        return {'direction':'bullish','strength':0.4,'rsi_direction':rsi_dir,'cross':'holding_golden','band':band,'rsi':round(r_now,1),'k':round(k1,1),'d':round(d1,1)}
    if rsi_dir=='down' and k1<d1:
        return {'direction':'bearish','strength':0.4,'rsi_direction':rsi_dir,'cross':'holding_death','band':band,'rsi':round(r_now,1),'k':round(k1,1),'d':round(d1,1)}
    return {'direction':'neutral','strength':0.0,'rsi_direction':rsi_dir,'cross':'none','band':band,'rsi':round(r_now,1),'k':round(k1,1),'d':round(d1,1)}
