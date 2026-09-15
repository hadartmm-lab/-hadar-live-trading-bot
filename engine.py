from __future__ import annotations
import time
from indicators import supertrend, structure, candle_bias_1h, volume_confirmation, wyckoff_heuristic, rsi_divergence_detail
from advanced_patterns import (
    liquidity_sweep, support_resistance, flag_wedge_pattern,
    market_regime, bos_choch, impulse_fib,
)
from datafeeds import market_df


def _add(points, bucket, reason, checklist, key, state='ok'):
    bucket[0] += points
    if reason:
        bucket[1].append(reason)
    checklist[key] = state


async def analyze_symbol(symbol:str, asset_type:str, vix_bias:str='neutral'):
    dfs={}; sources={}
    for tf in ['1h','4h','12h','1d']:
        dfs[tf], sources[tf] = await market_df(symbol,tf,asset_type)

    L=[0.0,[]]; S=[0.0,[]]
    checklist={}

    # 1) Market state / structure - highest priority
    structs={tf:structure(dfs[tf]) for tf in ['1d','12h','4h']}
    for tf,w in [('12h',14),('4h',11),('1d',8)]:
        st=structs[tf]
        if st=='bullish': _add(w,L,f'{tf} bullish structure +{w}L',checklist,f'{tf}_structure','bullish')
        elif st=='bearish': _add(w,S,f'{tf} bearish structure +{w}S',checklist,f'{tf}_structure','bearish')
        else: checklist[f'{tf}_structure']='range'

    regime12=market_regime(dfs['12h']); regime4=market_regime(dfs['4h'])
    if regime12['regime']=='trend':
        pts=round(8*regime12['strength'],1)
        if regime12['direction']=='bullish': _add(pts,L,f'12h trending regime +{pts}L',checklist,'regime12','bullish trend')
        elif regime12['direction']=='bearish': _add(pts,S,f'12h trending regime +{pts}S',checklist,'regime12','bearish trend')
    else:
        checklist['regime12']=regime12['regime']

    # 2) BOS / CHoCH - structural trigger
    bos12=bos_choch(dfs['12h']); bos4=bos_choch(dfs['4h'])
    for label,bos,maxpts in [('12h',bos12,10),('4h',bos4,7)]:
        if bos['direction']=='bullish':
            pts=round(maxpts*bos['strength'],1); _add(pts,L,f'{label} {bos["event"]} bullish +{pts}L',checklist,f'bos_{label}','bullish')
        elif bos['direction']=='bearish':
            pts=round(maxpts*bos['strength'],1); _add(pts,S,f'{label} {bos["event"]} bearish +{pts}S',checklist,f'bos_{label}','bearish')
        else: checklist[f'bos_{label}']='none'

    # 3) SuperTrend context
    st_dirs={}
    for tf,w in [('12h',8),('4h',6)]:
        _,d=supertrend(dfs[tf],10,3.0); sd='bullish' if int(d.iloc[-1])==1 else 'bearish'; st_dirs[tf]=sd
        if sd=='bullish': _add(w,L,f'{tf} SuperTrend bullish +{w}L',checklist,f'supertrend_{tf}','bullish')
        else: _add(w,S,f'{tf} SuperTrend bearish +{w}S',checklist,f'supertrend_{tf}','bearish')

    # 4) RSI divergences on 4H + 12H
    div4=rsi_divergence_detail(dfs['4h']); div12=rsi_divergence_detail(dfs['12h'])
    if div4['type']=='bullish':
        pts=round(6*div4['strength'],1); _add(pts,L,f'4h bullish RSI divergence +{pts}L',checklist,'rsi_div_4h','bullish')
    elif div4['type']=='bearish':
        pts=round(6*div4['strength'],1); _add(pts,S,f'4h bearish RSI divergence +{pts}S',checklist,'rsi_div_4h','bearish')
    else: checklist['rsi_div_4h']='none'
    if div12['type']=='bullish':
        pts=round(9*div12['strength'],1); _add(pts,L,f'12h bullish RSI divergence +{pts}L',checklist,'rsi_div_12h','bullish')
    elif div12['type']=='bearish':
        pts=round(9*div12['strength'],1); _add(pts,S,f'12h bearish RSI divergence +{pts}S',checklist,'rsi_div_12h','bearish')
    else: checklist['rsi_div_12h']='none'
    div_sync = div4['type'] if div4['type']==div12['type'] and div4['type']!='none' else 'none'
    if div_sync=='bullish': _add(5,L,'4H + 12H RSI divergence synchronized +5L',checklist,'divergence_sync','bullish')
    elif div_sync=='bearish': _add(5,S,'4H + 12H RSI divergence synchronized +5S',checklist,'divergence_sync','bearish')
    else: checklist['divergence_sync']='none'

    # 5) Relevant impulse Fibonacci pullback
    fib=impulse_fib(dfs['12h'])
    if fib.get('status')=='healthy_pullback':
        pts=round(14*(0.75+0.25*fib.get('impulse_quality',0.5)),1)
        if fib['direction']=='bullish': _add(pts,L,f'12h healthy Fib 0.50–0.618 +{pts}L',checklist,'fib','bullish healthy')
        else: _add(pts,S,f'12h healthy Fib 0.50–0.618 +{pts}S',checklist,'fib','bearish healthy')
    elif fib.get('in_zone'):
        checklist['fib']=f"{fib.get('direction')} in zone / unconfirmed"
    else:
        checklist['fib']='not in 0.50–0.618'

    # 6) Wyckoff + range location
    wy=wyckoff_heuristic(dfs['12h'])
    if wy=='accumulation_zone': _add(7,L,'12h lower range / accumulation +7L',checklist,'wyckoff','accumulation')
    elif wy=='distribution_zone': _add(7,S,'12h upper range / distribution +7S',checklist,'wyckoff','distribution')
    elif wy=='markup': _add(5,L,'12h markup +5L',checklist,'wyckoff','markup')
    elif wy=='markdown': _add(5,S,'12h markdown +5S',checklist,'wyckoff','markdown')
    else: checklist['wyckoff']='neutral'

    # 7) Volume confirmation
    vr=volume_confirmation(dfs['4h'])
    if vr>=1.25:
        if structs['4h']=='bullish': _add(5,L,f'4h volume x{vr:.2f} confirms +5L',checklist,'volume','bullish confirmation')
        elif structs['4h']=='bearish': _add(5,S,f'4h volume x{vr:.2f} confirms +5S',checklist,'volume','bearish confirmation')
        else: checklist['volume']=f'high x{vr:.2f} / no direction'
    else: checklist['volume']=f'normal x{vr:.2f}'

    # 8) Liquidity sweep / reclaim
    sweep=liquidity_sweep(dfs['4h'])
    if sweep['type']=='bullish':
        pts=round(8*sweep['strength'],1); _add(pts,L,f'4h bullish liquidity sweep +{pts}L',checklist,'liquidity','bullish sweep')
    elif sweep['type']=='bearish':
        pts=round(8*sweep['strength'],1); _add(pts,S,f'4h bearish liquidity sweep +{pts}S',checklist,'liquidity','bearish sweep')
    else: checklist['liquidity']='none'

    # 9) Support / resistance proximity
    sr=support_resistance(dfs['12h']); price=float(dfs['1h'].close.iloc[-1])
    sup=sr.get('support'); res=sr.get('resistance')
    if sup and sup['touches']>=2 and abs(price-sup['price'])/max(price,1e-9)<.018:
        _add(4,L,f'Near tested 12h support ({sup["touches"]} touches) +4L',checklist,'sr','near support')
    elif res and res['touches']>=2 and abs(res['price']-price)/max(price,1e-9)<.018:
        _add(4,S,f'Near tested 12h resistance ({res["touches"]} touches) +4S',checklist,'sr','near resistance')
    else: checklist['sr']='neutral'

    # 10) Flags / wedges
    pattern=flag_wedge_pattern(dfs['12h'])
    if pattern['pattern'] in ('bull_flag','falling_wedge'):
        pts=round(8*pattern['confidence'],1); _add(pts,L,f'12h {pattern["pattern"]} +{pts}L',checklist,'pattern',pattern['pattern'])
    elif pattern['pattern'] in ('bear_flag','rising_wedge'):
        pts=round(8*pattern['confidence'],1); _add(pts,S,f'12h {pattern["pattern"]} +{pts}S',checklist,'pattern',pattern['pattern'])
    else: checklist['pattern']='none'

    # 11) 1H candles only - no RSI on 1H
    c1=candle_bias_1h(dfs['1h'])
    if c1=='bullish': _add(5,L,'1h candles support LONG +5L',checklist,'candles_1h','bullish')
    elif c1=='bearish': _add(5,S,'1h candles support SHORT +5S',checklist,'candles_1h','bearish')
    else: checklist['candles_1h']='neutral'

    # 12) VIX filter for stocks only
    if asset_type=='stock':
        if vix_bias=='risk_on': _add(7,L,'VIX regime risk-on +7L',checklist,'vix','risk_on')
        elif vix_bias=='risk_off': _add(7,S,'VIX regime risk-off +7S',checklist,'vix','risk_off')
        else: checklist['vix']='neutral'

    # Confluence quality: penalize opposite evidence, reward cross-timeframe alignment.
    rawL, rawS=L[0],S[0]
    dominant='LONG' if rawL>=rawS else 'SHORT'
    opposite=min(rawL,rawS)
    conflict_penalty=opposite*0.42
    adjL=max(0,rawL-conflict_penalty); adjS=max(0,rawS-conflict_penalty)

    # Explicit alignment bonus, not just point stacking.
    bull_align=sum([structs['12h']=='bullish',structs['4h']=='bullish',st_dirs['12h']=='bullish',st_dirs['4h']=='bullish',regime12.get('direction')=='bullish'])
    bear_align=sum([structs['12h']=='bearish',structs['4h']=='bearish',st_dirs['12h']=='bearish',st_dirs['4h']=='bearish',regime12.get('direction')=='bearish'])
    if bull_align>=4: adjL*=1.08
    if bear_align>=4: adjS*=1.08

    max_points=128.0
    lscore=min(100,round(adjL/max_points*100,1)); sscore=min(100,round(adjS/max_points*100,1))
    direction='LONG' if lscore>=sscore else 'SHORT'; score=max(lscore,sscore)
    gap=abs(lscore-sscore)
    if gap<12 or score<45: direction='WAIT'

    # Missing confirmations: explain exactly what is still absent for dominant scenario.
    target='bullish' if (lscore>=sscore) else 'bearish'
    missing=[]
    if checklist.get('12h_structure')!=target: missing.append('12H structure alignment')
    if checklist.get('4h_structure')!=target: missing.append('4H structure alignment')
    if checklist.get('supertrend_12h')!=target: missing.append('12H SuperTrend')
    if checklist.get('fib') not in (f'{target} healthy',): missing.append('Fib 0.50–0.618 healthy pullback')
    if checklist.get('rsi_div_4h')!=target and checklist.get('rsi_div_12h')!=target: missing.append('4H/12H RSI divergence support')
    if checklist.get('bos_4h')!=target and checklist.get('bos_12h')!=target: missing.append('BOS/CHoCH confirmation')
    if checklist.get('candles_1h')!=target: missing.append('1H candle direction')
    if asset_type=='stock' and checklist.get('vix') not in (('risk_on' if target=='bullish' else 'risk_off'),): missing.append('VIX regime alignment')
    missing=missing[:5]

    setup_power = 'ELITE' if score>=90 and gap>=25 else 'STRONG' if score>=82 and gap>=18 else 'BUILDING' if score>=70 else 'WATCH' if score>=60 else 'LOW'

    return {
        'symbol':symbol,'asset_type':asset_type,'direction':direction,'score':score,
        'long_score':lscore,'short_score':sscore,'gap':round(gap,1),'price':price,
        'setup_power':setup_power,'missing_confirmations':missing,'checklist':checklist,
        'one_hour_candles':c1,'fib':fib,'wyckoff':wy,'volume_ratio_4h':round(vr,2),
        'rsi_divergence_4h':div4,'rsi_divergence_12h':div12,'divergence_sync':div_sync,
        'market_regime_12h':regime12,'market_regime_4h':regime4,'bos_12h':bos12,'bos_4h':bos4,
        'liquidity_sweep':sweep,'support_resistance':sr,'pattern':pattern,
        'sources':sources,'data_source':sources.get('1h','-'),
        'reasons':(L[1] if lscore>=sscore else S[1])[-18:],'updated_at':int(time.time())
    }
