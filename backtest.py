from __future__ import annotations
import pandas as pd
from indicators import structure, supertrend, volume_confirmation, wyckoff_heuristic, candle_bias_1h, rsi_divergence_detail, stoch_rsi_signal
from advanced_patterns import liquidity_sweep, flag_wedge_pattern, market_regime, bos_choch, impulse_fib

THRESHOLDS=(55,68,78,90)


def score_snapshot(df12, df4, df1h, df1d, vix_bias='neutral', asset_type='crypto'):
    L=S=0.0
    structs={}
    for tf,df,w in [('12h',df12,12),('4h',df4,10),('1d',df1d,5)]:
        st=structure(df); structs[tf]=st
        if st=='bullish':L+=w
        elif st=='bearish':S+=w
    reg=market_regime(df12)
    if reg['regime']=='trend':
        pts=6*reg['strength']
        if reg['direction']=='bullish':L+=pts
        elif reg['direction']=='bearish':S+=pts
    for df,w in [(df12,5),(df4,4)]:
        _,d=supertrend(df,10,3.0)
        if int(d.iloc[-1])==1:L+=w
        else:S+=w
    for df,maxp in [(df12,7),(df4,6)]:
        b=bos_choch(df)
        if b['direction']=='bullish':L+=maxp*b['strength']
        elif b['direction']=='bearish':S+=maxp*b['strength']
    d4=rsi_divergence_detail(df4); d12=rsi_divergence_detail(df12)
    if d4['type']=='bullish':L+=8*d4['strength']
    elif d4['type']=='bearish':S+=8*d4['strength']
    if d12['type']=='bullish':L+=12*d12['strength']
    elif d12['type']=='bearish':S+=12*d12['strength']
    if d4['type']==d12['type'] and d4['type']!='none':
        if d4['type']=='bullish':L+=4
        else:S+=4
    # RSI momentum / Stoch RSI layer (4H, 12H, Daily bonus)
    moms=[]
    for df,maxp in [(df4,4),(df12,6),(df1d,3)]:
        m=stoch_rsi_signal(df); moms.append(m)
        if m['direction']=='bullish':L+=maxp*m['strength']
        elif m['direction']=='bearish':S+=maxp*m['strength']
    if sum(m['direction']=='bullish' for m in moms)>=2:L+=3
    elif sum(m['direction']=='bearish' for m in moms)>=2:S+=3
    fib=impulse_fib(df12)
    if fib.get('status')=='healthy_pullback':
        pts=9*(.75+.25*fib.get('impulse_quality',.5))
        if fib.get('direction')=='bullish':L+=pts
        elif fib.get('direction')=='bearish':S+=pts
    wy=wyckoff_heuristic(df12)
    if wy=='accumulation_zone':L+=4
    elif wy=='distribution_zone':S+=4
    elif wy=='markup':L+=3
    elif wy=='markdown':S+=3
    vr=volume_confirmation(df4)
    if vr>=1.25:
        if structs['4h']=='bullish':L+=3
        elif structs['4h']=='bearish':S+=3
    sw=liquidity_sweep(df4)
    if sw['type']=='bullish':L+=4*sw['strength']
    elif sw['type']=='bearish':S+=4*sw['strength']
    pat=flag_wedge_pattern(df12)
    if pat['pattern'] in ('bull_flag','falling_wedge'):L+=2*pat['confidence']
    elif pat['pattern'] in ('bear_flag','rising_wedge'):S+=2*pat['confidence']
    c=candle_bias_1h(df1h)
    if c=='bullish':L+=2
    elif c=='bearish':S+=2
    conflictL=L-S*.35; conflictS=S-L*.35
    L=max(0,conflictL); S=max(0,conflictS)
    if asset_type=='stock':
        if vix_bias=='risk_on': L*=1.05; S*=.97
        elif vix_bias=='risk_off': S*=1.05; L*=.97
    ls=min(100,L); ss=min(100,S)
    return ('LONG',ls) if ls>=ss else ('SHORT',ss)


def backtest_frames(df12: pd.DataFrame, df4: pd.DataFrame, df1h: pd.DataFrame, df1d: pd.DataFrame,
                    horizon_12h_bars=4, min_bars=140):
    """Walk-forward calibration test; intended for score calibration, not brokerage-grade P&L."""
    rows=[]
    if len(df12)<min_bars+horizon_12h_bars:return {'summary':{},'trades':0}
    for i in range(min_bars,len(df12)-horizon_12h_bars):
        t=pd.Timestamp(df12.iloc[i].ts)
        s12=df12.iloc[:i+1]; s4=df4[pd.to_datetime(df4.ts)<=t]; s1=df1h[pd.to_datetime(df1h.ts)<=t]; sd=df1d[pd.to_datetime(df1d.ts)<=t]
        if min(len(s4),len(s1),len(sd))<30:continue
        d,score=score_snapshot(s12,s4,s1,sd)
        entry=float(df12.iloc[i].close); exitp=float(df12.iloc[i+horizon_12h_bars].close)
        raw=(exitp-entry)/entry; ret=raw if d=='LONG' else -raw
        rows.append({'ts':str(t),'direction':d,'score':round(score,1),'return_pct':ret*100,'win':ret>0})
    out={}
    for th in THRESHOLDS:
        xs=[r for r in rows if r['score']>=th]
        out[str(th)]={'signals':len(xs),'win_rate':round(100*sum(r['win'] for r in xs)/len(xs),1) if xs else 0,
                      'avg_return_pct':round(sum(r['return_pct'] for r in xs)/len(xs),3) if xs else 0}
    return {'summary':out,'trades':len(rows),'sample':rows[-25:]}
