from __future__ import annotations
import pandas as pd
from indicators import structure, supertrend, fib_retracement_health, volume_confirmation, wyckoff_heuristic, candle_bias_1h
from advanced_patterns import liquidity_sweep, support_resistance, flag_wedge_pattern

THRESHOLDS=(60,70,80,90)


def score_snapshot(df12, df4, df1h, df1d, vix_bias='neutral', asset_type='crypto'):
    L=S=0.0
    for df,w in [(df12,14),(df4,11),(df1d,8)]:
        st=structure(df)
        if st=='bullish': L+=w
        elif st=='bearish': S+=w
    for df,w in [(df12,9),(df4,7)]:
        _,d=supertrend(df,10,3.0)
        if int(d.iloc[-1])==1:L+=w
        else:S+=w
    fib=fib_retracement_health(df12)
    if fib.get('status')=='healthy_pullback':
        if fib.get('direction')=='bullish':L+=13
        elif fib.get('direction')=='bearish':S+=13
    wy=wyckoff_heuristic(df12)
    if wy=='accumulation_zone':L+=7
    elif wy=='distribution_zone':S+=7
    sw=liquidity_sweep(df4)
    if sw['type']=='bullish':L+=8*sw['strength']
    elif sw['type']=='bearish':S+=8*sw['strength']
    pat=flag_wedge_pattern(df12)
    if pat['pattern'] in ('bull_flag','falling_wedge'):L+=8*pat['confidence']
    elif pat['pattern'] in ('bear_flag','rising_wedge'):S+=8*pat['confidence']
    c=candle_bias_1h(df1h)
    if c=='bullish':L+=5
    elif c=='bearish':S+=5
    if asset_type=='stock':
        if vix_bias=='risk_on':L+=7
        elif vix_bias=='risk_off':S+=7
    maxp=84.; conflict=min(L,S)*.35; L=max(0,L-conflict); S=max(0,S-conflict)
    ls=min(100,L/maxp*100); ss=min(100,S/maxp*100)
    return ('LONG',ls) if ls>=ss else ('SHORT',ss)


def backtest_frames(df12: pd.DataFrame, df4: pd.DataFrame, df1h: pd.DataFrame, df1d: pd.DataFrame,
                    horizon_12h_bars=4, min_bars=140):
    """Walk-forward score test. Outcome uses 12H close after horizon; no look-ahead in features.
    Intended for calibration, not brokerage-grade P&L simulation.
    """
    rows=[]
    if len(df12)<min_bars+horizon_12h_bars: return {'summary':{},'trades':0}
    for i in range(min_bars, len(df12)-horizon_12h_bars):
        t=pd.Timestamp(df12.iloc[i].ts)
        s12=df12.iloc[:i+1]
        s4=df4[pd.to_datetime(df4.ts)<=t]
        s1=df1h[pd.to_datetime(df1h.ts)<=t]
        sd=df1d[pd.to_datetime(df1d.ts)<=t]
        if min(len(s4),len(s1),len(sd))<30: continue
        d,score=score_snapshot(s12,s4,s1,sd)
        entry=float(df12.iloc[i].close); exitp=float(df12.iloc[i+horizon_12h_bars].close)
        raw=(exitp-entry)/entry
        ret=raw if d=='LONG' else -raw
        rows.append({'ts':str(t),'direction':d,'score':round(score,1),'return_pct':ret*100,'win':ret>0})
    out={}
    for th in THRESHOLDS:
        xs=[r for r in rows if r['score']>=th]
        out[str(th)]={'signals':len(xs),'win_rate':round(100*sum(r['win'] for r in xs)/len(xs),1) if xs else 0,
                      'avg_return_pct':round(sum(r['return_pct'] for r in xs)/len(xs),3) if xs else 0}
    return {'summary':out,'trades':len(rows),'sample':rows[-25:]}
