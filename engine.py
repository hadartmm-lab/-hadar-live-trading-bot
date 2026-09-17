from __future__ import annotations
import time
from indicators import supertrend, structure, candle_bias_1h, volume_confirmation, wyckoff_heuristic, rsi_divergence_detail, stoch_rsi_signal
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
    for tf,w in [('12h',12),('4h',10),('1d',5)]:
        st=structs[tf]
        if st=='bullish': _add(w,L,f'{tf} bullish structure +{w}L',checklist,f'{tf}_structure','bullish')
        elif st=='bearish': _add(w,S,f'{tf} bearish structure +{w}S',checklist,f'{tf}_structure','bearish')
        else: checklist[f'{tf}_structure']='range'

    regime12=market_regime(dfs['12h']); regime4=market_regime(dfs['4h'])
    if regime12['regime']=='trend':
        pts=round(6*regime12['strength'],1)
        if regime12['direction']=='bullish': _add(pts,L,f'12h trending regime +{pts}L',checklist,'regime12','bullish trend')
        elif regime12['direction']=='bearish': _add(pts,S,f'12h trending regime +{pts}S',checklist,'regime12','bearish trend')
    else:
        checklist['regime12']=regime12['regime']

    # 2) BOS / CHoCH - structural trigger
    bos12=bos_choch(dfs['12h']); bos4=bos_choch(dfs['4h'])
    for label,bos,maxpts in [('12h',bos12,7),('4h',bos4,6)]:
        if bos['direction']=='bullish':
            pts=round(maxpts*bos['strength'],1); _add(pts,L,f'{label} {bos["event"]} bullish +{pts}L',checklist,f'bos_{label}','bullish')
        elif bos['direction']=='bearish':
            pts=round(maxpts*bos['strength'],1); _add(pts,S,f'{label} {bos["event"]} bearish +{pts}S',checklist,f'bos_{label}','bearish')
        else: checklist[f'bos_{label}']='none'

    # 3) SuperTrend context
    st_dirs={}
    for tf,w in [('12h',5),('4h',4)]:
        _,d=supertrend(dfs[tf],10,3.0); sd='bullish' if int(d.iloc[-1])==1 else 'bearish'; st_dirs[tf]=sd
        if sd=='bullish': _add(w,L,f'{tf} SuperTrend bullish +{w}L',checklist,f'supertrend_{tf}','bullish')
        else: _add(w,S,f'{tf} SuperTrend bearish +{w}S',checklist,f'supertrend_{tf}','bearish')

    # 4) RSI divergences on 4H + 12H
    div4=rsi_divergence_detail(dfs['4h']); div12=rsi_divergence_detail(dfs['12h'])
    if div4['type']=='bullish':
        pts=round(8*div4['strength'],1); _add(pts,L,f'4h bullish RSI divergence +{pts}L',checklist,'rsi_div_4h','bullish')
    elif div4['type']=='bearish':
        pts=round(8*div4['strength'],1); _add(pts,S,f'4h bearish RSI divergence +{pts}S',checklist,'rsi_div_4h','bearish')
    else: checklist['rsi_div_4h']='none'
    if div12['type']=='bullish':
        pts=round(12*div12['strength'],1); _add(pts,L,f'12h bullish RSI divergence +{pts}L',checklist,'rsi_div_12h','bullish')
    elif div12['type']=='bearish':
        pts=round(12*div12['strength'],1); _add(pts,S,f'12h bearish RSI divergence +{pts}S',checklist,'rsi_div_12h','bearish')
    else: checklist['rsi_div_12h']='none'
    div_sync = div4['type'] if div4['type']==div12['type'] and div4['type']!='none' else 'none'
    if div_sync=='bullish': _add(4,L,'4H + 12H RSI divergence synchronized +4L',checklist,'divergence_sync','bullish')
    elif div_sync=='bearish': _add(4,S,'4H + 12H RSI divergence synchronized +4S',checklist,'divergence_sync','bearish')
    else: checklist['divergence_sync']='none'

    # 5) Second RSI / momentum layer: RSI direction + Stoch RSI Golden/Death Cross.
    # 12H is intentionally stronger; Daily is a bonus. Two aligned timeframes get a confluence bonus.
    rsi_momentum={}
    for tf,maxpts in [('4h',4),('12h',6),('1d',3)]:
        sig=stoch_rsi_signal(dfs[tf]); rsi_momentum[tf]=sig
        if sig['direction']=='bullish':
            pts=round(maxpts*sig['strength'],1)
            _add(pts,L,f'{tf} RSI momentum {sig.get("cross")} / {sig.get("band")} +{pts}L',checklist,f'rsi_momentum_{tf}',f'bullish {sig.get("cross")} {sig.get("band")}')
        elif sig['direction']=='bearish':
            pts=round(maxpts*sig['strength'],1)
            _add(pts,S,f'{tf} RSI momentum {sig.get("cross")} / {sig.get("band")} +{pts}S',checklist,f'rsi_momentum_{tf}',f'bearish {sig.get("cross")} {sig.get("band")}')
        else:
            checklist[f'rsi_momentum_{tf}']=f'neutral {sig.get("rsi_direction")} {sig.get("band")}'
    bull_rsi_tfs=sum(rsi_momentum[tf]['direction']=='bullish' for tf in ('4h','12h','1d'))
    bear_rsi_tfs=sum(rsi_momentum[tf]['direction']=='bearish' for tf in ('4h','12h','1d'))
    if bull_rsi_tfs>=2: _add(3,L,'RSI momentum aligned on 2+ timeframes +3L',checklist,'rsi_momentum_sync','bullish')
    elif bear_rsi_tfs>=2: _add(3,S,'RSI momentum aligned on 2+ timeframes +3S',checklist,'rsi_momentum_sync','bearish')
    else: checklist['rsi_momentum_sync']='none'

    # 6) Relevant impulse Fibonacci pullback
    fib=impulse_fib(dfs['12h'])
    if fib.get('status')=='healthy_pullback':
        pts=round(9*(0.75+0.25*fib.get('impulse_quality',0.5)),1)
        if fib['direction']=='bullish': _add(pts,L,f'12h healthy Fib 0.50–0.618 +{pts}L',checklist,'fib','bullish healthy')
        else: _add(pts,S,f'12h healthy Fib 0.50–0.618 +{pts}S',checklist,'fib','bearish healthy')
    elif fib.get('in_zone'):
        checklist['fib']=f"{fib.get('direction')} in zone / unconfirmed"
    else:
        checklist['fib']='not in 0.50–0.618'

    # 7) Wyckoff + range location
    wy=wyckoff_heuristic(dfs['12h'])
    if wy=='accumulation_zone': _add(4,L,'12h lower range / accumulation +4L',checklist,'wyckoff','accumulation')
    elif wy=='distribution_zone': _add(4,S,'12h upper range / distribution +4S',checklist,'wyckoff','distribution')
    elif wy=='markup': _add(3,L,'12h markup +3L',checklist,'wyckoff','markup')
    elif wy=='markdown': _add(3,S,'12h markdown +3S',checklist,'wyckoff','markdown')
    else: checklist['wyckoff']='neutral'

    # 8) Volume confirmation
    vr=volume_confirmation(dfs['4h'])
    if vr>=1.25:
        if structs['4h']=='bullish': _add(3,L,f'4h volume x{vr:.2f} confirms +3L',checklist,'volume','bullish confirmation')
        elif structs['4h']=='bearish': _add(3,S,f'4h volume x{vr:.2f} confirms +3S',checklist,'volume','bearish confirmation')
        else: checklist['volume']=f'high x{vr:.2f} / no direction'
    else: checklist['volume']=f'normal x{vr:.2f}'

    # 9) Liquidity sweep / reclaim
    sweep=liquidity_sweep(dfs['4h'])
    if sweep['type']=='bullish':
        pts=round(4*sweep['strength'],1); _add(pts,L,f'4h bullish liquidity sweep +{pts}L',checklist,'liquidity','bullish sweep')
    elif sweep['type']=='bearish':
        pts=round(4*sweep['strength'],1); _add(pts,S,f'4h bearish liquidity sweep +{pts}S',checklist,'liquidity','bearish sweep')
    else: checklist['liquidity']='none'

    # 10) Support / resistance proximity
    sr=support_resistance(dfs['12h']); price=float(dfs['1h'].close.iloc[-1])
    sup=sr.get('support'); res=sr.get('resistance')
    if sup and sup['touches']>=2 and abs(price-sup['price'])/max(price,1e-9)<.018:
        _add(2,L,f'Near tested 12h support ({sup["touches"]} touches) +2L',checklist,'sr','near support')
    elif res and res['touches']>=2 and abs(res['price']-price)/max(price,1e-9)<.018:
        _add(2,S,f'Near tested 12h resistance ({res["touches"]} touches) +2S',checklist,'sr','near resistance')
    else: checklist['sr']='neutral'

    # 11) Flags / wedges
    pattern=flag_wedge_pattern(dfs['12h'])
    if pattern['pattern'] in ('bull_flag','falling_wedge'):
        pts=round(2*pattern['confidence'],1); _add(pts,L,f'12h {pattern["pattern"]} +{pts}L',checklist,'pattern',pattern['pattern'])
    elif pattern['pattern'] in ('bear_flag','rising_wedge'):
        pts=round(2*pattern['confidence'],1); _add(pts,S,f'12h {pattern["pattern"]} +{pts}S',checklist,'pattern',pattern['pattern'])
    else: checklist['pattern']='none'

    # 12) 1H candles only - no RSI on 1H
    c1=candle_bias_1h(dfs['1h'])
    if c1=='bullish': _add(2,L,'1h candles support LONG +2L',checklist,'candles_1h','bullish')
    elif c1=='bearish': _add(2,S,'1h candles support SHORT +2S',checklist,'candles_1h','bearish')
    else: checklist['candles_1h']='neutral'

    # 13) VIX filter for stocks only
    if asset_type=='stock':
        if vix_bias=='risk_on': _add(0,L,'VIX regime risk-on (modifier)',checklist,'vix','risk_on')
        elif vix_bias=='risk_off': _add(0,S,'VIX regime risk-off (modifier)',checklist,'vix','risk_off')
        else: checklist['vix']='neutral'

    # v3.2 scoring: 100-point transparent scale + conflict/gating.
    # The weights above now add to ~100 for crypto, which makes the score easier to interpret.
    rawL, rawS = L[0], S[0]

    # Opposite evidence should reduce conviction instead of being silently ignored.
    # A 35% conflict haircut is enough to punish mixed charts without destroying early setups.
    adjL=max(0.0, rawL - rawS*0.35)
    adjS=max(0.0, rawS - rawL*0.35)

    # Reward genuine multi-timeframe agreement, but cap the effect to avoid score inflation.
    bull_align=sum([structs['12h']=='bullish',structs['4h']=='bullish',st_dirs['12h']=='bullish',st_dirs['4h']=='bullish',regime12.get('direction')=='bullish'])
    bear_align=sum([structs['12h']=='bearish',structs['4h']=='bearish',st_dirs['12h']=='bearish',st_dirs['4h']=='bearish',regime12.get('direction')=='bearish'])
    if bull_align>=4: adjL += 3
    if bear_align>=4: adjS += 3

    # VIX is a modifier for stocks, not extra points on top of the 100-point scale.
    if asset_type=='stock':
        if vix_bias=='risk_on':
            adjL*=1.05; adjS*=0.97
        elif vix_bias=='risk_off':
            adjS*=1.05; adjL*=0.97

    lscore=min(100,round(adjL,1)); sscore=min(100,round(adjS,1))
    gap=round(abs(lscore-sscore),1)
    dominant='LONG' if lscore>=sscore else 'SHORT'
    target='bullish' if dominant=='LONG' else 'bearish'

    # Bias is always visible, even when there is no entry yet.
    # Very small score gaps are intentionally called NEUTRAL.
    bias = dominant if gap>=7 and max(lscore,sscore)>=35 else 'NEUTRAL'
    score=max(lscore,sscore)

    # Entry gates: score alone cannot produce READY.
    core_alignment = (checklist.get('12h_structure')==target and checklist.get('4h_structure')==target)
    daily_not_opposite = checklist.get('1d_structure') in (target, 'range')
    divergence_ok = (checklist.get('rsi_div_4h')==target or checklist.get('rsi_div_12h')==target)
    rsi_momentum_ok = (sum((rsi_momentum[tf].get('direction')==target) for tf in ('4h','12h','1d')) >= 2)
    trigger_flags = [
        checklist.get('bos_4h')==target or checklist.get('bos_12h')==target,
        divergence_ok,
        rsi_momentum_ok,
        checklist.get('fib')==f'{target} healthy',
        target in str(checklist.get('liquidity','')).lower(),
        (target=='bullish' and checklist.get('pattern') in ('bull_flag','falling_wedge')) or
        (target=='bearish' and checklist.get('pattern') in ('bear_flag','rising_wedge')),
    ]
    trigger_count=sum(bool(x) for x in trigger_flags)

    # Stage is deliberately stricter than the score: READY needs direction, structure and triggers.
    if bias!='NEUTRAL' and score>=78 and gap>=18 and core_alignment and daily_not_opposite and trigger_count>=2:
        stage='READY'
    elif bias!='NEUTRAL' and score>=68 and gap>=14 and core_alignment and trigger_count>=1:
        stage='DEVELOPING'
    elif bias!='NEUTRAL' and score>=55 and gap>=10:
        stage='WATCH'
    else:
        stage='NO TRADE'

    # Keep direction backward-compatible for alerts, while bias remains visible in the UI.
    direction = bias if stage!='NO TRADE' else 'WAIT'

    # Missing confirmations: show the shortest path from current bias to a valid setup.
    missing=[]
    if checklist.get('12h_structure')!=target: missing.append('12H structure alignment')
    if checklist.get('4h_structure')!=target: missing.append('4H structure alignment')
    if not daily_not_opposite: missing.append('Daily trend not opposite')
    if checklist.get('supertrend_12h')!=target: missing.append('12H SuperTrend')
    if checklist.get('fib') != f'{target} healthy': missing.append('Fib 0.50–0.618 healthy pullback')
    if not divergence_ok: missing.append('4H/12H RSI divergence support')
    if not rsi_momentum_ok: missing.append('RSI momentum: 2 of 4H/12H/Daily aligned')
    if not trigger_flags[0]: missing.append('BOS/CHoCH confirmation')
    if checklist.get('candles_1h')!=target: missing.append('1H candle direction')
    if asset_type=='stock' and checklist.get('vix') not in (('risk_on' if target=='bullish' else 'risk_off'),): missing.append('VIX regime alignment')
    missing=missing[:5]

    confidence = ('HIGH' if stage=='READY' and score>=85 and gap>=25 else
                  'MEDIUM' if stage in ('READY','DEVELOPING') else
                  'LOW' if bias!='NEUTRAL' else 'NEUTRAL')
    setup_power = 'ELITE' if score>=90 and gap>=25 and core_alignment else 'STRONG' if score>=78 and gap>=18 else 'BUILDING' if score>=68 else 'WATCH' if score>=55 else 'LOW'
    return {
        'symbol':symbol,'asset_type':asset_type,'direction':direction,'bias':bias,'stage':stage,'confidence':confidence,'score':score,
        'long_score':lscore,'short_score':sscore,'gap':gap,'price':price,
        'setup_power':setup_power,'trigger_count':trigger_count,'core_alignment':core_alignment,'missing_confirmations':missing,'checklist':checklist,
        'one_hour_candles':c1,'fib':fib,'wyckoff':wy,'volume_ratio_4h':round(vr,2),
        'rsi_divergence_4h':div4,'rsi_divergence_12h':div12,'divergence_sync':div_sync,'rsi_momentum':rsi_momentum,
        'market_regime_12h':regime12,'market_regime_4h':regime4,'bos_12h':bos12,'bos_4h':bos4,
        'liquidity_sweep':sweep,'support_resistance':sr,'pattern':pattern,
        'sources':sources,'data_source':sources.get('1h','-'),
        'reasons':(L[1] if lscore>=sscore else S[1])[-18:],'updated_at':int(time.time())
    }
