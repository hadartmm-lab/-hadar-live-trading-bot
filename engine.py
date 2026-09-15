from __future__ import annotations
import time
from indicators import supertrend, structure, candle_bias_1h, fib_retracement_health, volume_confirmation, wyckoff_heuristic
from advanced_patterns import liquidity_sweep, support_resistance, flag_wedge_pattern
from datafeeds import market_df

async def analyze_symbol(symbol:str, asset_type:str, vix_bias:str='neutral'):
    dfs={}
    for tf in ['1h','4h','12h','1d']:
        dfs[tf]=await market_df(symbol,tf,asset_type)

    long=0.0; short=0.0; reasons=[]
    for tf,w in [('12h',14),('4h',11),('1d',8)]:
        s=structure(dfs[tf])
        if s=='bullish': long+=w; reasons.append(f'{tf} structure bullish +{w}L')
        elif s=='bearish': short+=w; reasons.append(f'{tf} structure bearish +{w}S')

    for tf,w in [('12h',9),('4h',7)]:
        _,d=supertrend(dfs[tf],10,3.0)
        if int(d.iloc[-1])==1: long+=w; reasons.append(f'{tf} SuperTrend bullish +{w}L')
        else: short+=w; reasons.append(f'{tf} SuperTrend bearish +{w}S')

    fib=fib_retracement_health(dfs['12h'])
    if fib.get('status')=='healthy_pullback':
        if fib['direction']=='bullish': long+=13; reasons.append('12h healthy Fib 0.50–0.618 + structure +13L')
        else: short+=13; reasons.append('12h healthy Fib 0.50–0.618 + structure +13S')

    wy=wyckoff_heuristic(dfs['12h'])
    if wy=='accumulation_zone': long+=7; reasons.append('12h lower range / accumulation heuristic +7L')
    elif wy=='distribution_zone': short+=7; reasons.append('12h upper range / distribution heuristic +7S')
    elif wy=='markup': long+=5
    elif wy=='markdown': short+=5

    vr=volume_confirmation(dfs['4h'])
    if vr>=1.25:
        st4=structure(dfs['4h'])
        if st4=='bullish': long+=5; reasons.append(f'4h volume x{vr:.2f} confirms +5L')
        elif st4=='bearish': short+=5; reasons.append(f'4h volume x{vr:.2f} confirms +5S')

    sweep=liquidity_sweep(dfs['4h'])
    if sweep['type']=='bullish':
        pts=round(8*sweep['strength'],1); long+=pts; reasons.append(f'4h bullish liquidity sweep/reclaim +{pts}L')
    elif sweep['type']=='bearish':
        pts=round(8*sweep['strength'],1); short+=pts; reasons.append(f'4h bearish liquidity sweep/reclaim +{pts}S')

    sr=support_resistance(dfs['12h'])
    price=float(dfs['1h'].close.iloc[-1])
    sup=sr.get('support'); res=sr.get('resistance')
    if sup and sup['touches']>=2 and abs(price-sup['price'])/max(price,1e-9)<.018:
        long+=4; reasons.append(f'Near tested 12h support ({sup["touches"]} touches) +4L')
    if res and res['touches']>=2 and abs(res['price']-price)/max(price,1e-9)<.018:
        short+=4; reasons.append(f'Near tested 12h resistance ({res["touches"]} touches) +4S')

    pattern=flag_wedge_pattern(dfs['12h'])
    if pattern['pattern'] in ('bull_flag','falling_wedge'):
        pts=round(8*pattern['confidence'],1); long+=pts; reasons.append(f'12h {pattern["pattern"]} +{pts}L')
    elif pattern['pattern'] in ('bear_flag','rising_wedge'):
        pts=round(8*pattern['confidence'],1); short+=pts; reasons.append(f'12h {pattern["pattern"]} +{pts}S')

    c1=candle_bias_1h(dfs['1h'])
    if c1=='bullish': long+=5; reasons.append('1h candles support LONG +5L')
    elif c1=='bearish': short+=5; reasons.append('1h candles support SHORT +5S')

    if asset_type=='stock':
        if vix_bias=='risk_on': long+=7; reasons.append('VIX app risk-on +7L')
        elif vix_bias=='risk_off': short+=7; reasons.append('VIX app risk-off +7S')

    max_points=84.0
    conflict=min(long,short)*0.35
    long=max(0,long-conflict); short=max(0,short-conflict)
    lscore=min(100,round(long/max_points*100,1)); sscore=min(100,round(short/max_points*100,1))
    direction='LONG' if lscore>=sscore else 'SHORT'; score=max(lscore,sscore)
    confidence_gap=abs(lscore-sscore)
    if confidence_gap<12: direction='WAIT'
    return {
        'symbol':symbol,'asset_type':asset_type,'direction':direction,'score':score,
        'long_score':lscore,'short_score':sscore,'gap':round(confidence_gap,1),'price':price,
        'one_hour_candles':c1,'fib':fib,'wyckoff':wy,'volume_ratio_4h':round(vr,2),
        'liquidity_sweep':sweep,'support_resistance':sr,'pattern':pattern,
        'reasons':reasons[-16:],'updated_at':int(time.time())
    }
