from __future__ import annotations
import asyncio, time, math, html
import streamlit as st
from config import settings
from engine import analyze_symbol
from vix_engine import analyze_internal_vix

st.set_page_config(page_title='Hadar Alpha Arena', page_icon='⚡', layout='wide')

st.markdown(r"""
<style>
:root{--ink:#101828;--muted:#667085;--line:#e4e7ec;--panel:#fff;--bg:#f4f7fb;--green:#12b76a;--red:#f04438;--amber:#f79009;--blue:#2e90fa;--purple:#7f56d9}
html,body,[data-testid='stAppViewContainer']{background:linear-gradient(180deg,#f2f5fa 0%,#f8fafc 100%)}
.block-container{max-width:1220px;padding-top:.8rem;padding-bottom:2rem}
h1,h2,h3{letter-spacing:-.025em}.muted{color:var(--muted);font-size:.9rem}
.hero{position:relative;overflow:hidden;background:linear-gradient(135deg,#08111f 0%,#10213c 48%,#173f6e 100%);border:1px solid rgba(255,255,255,.1);border-radius:26px;padding:1.15rem 1.2rem;color:white;box-shadow:0 18px 38px rgba(15,23,42,.20);margin-bottom:.9rem}
.hero:after{content:'';position:absolute;width:220px;height:220px;border-radius:50%;right:-70px;top:-90px;background:radial-gradient(circle,rgba(46,144,250,.38),rgba(46,144,250,0) 70%)}
.hero-title{font-size:2rem;font-weight:950;letter-spacing:-.04em;position:relative;z-index:1}.hero-sub{opacity:.82;font-size:.92rem;position:relative;z-index:1}.hero-strip{margin-top:.8rem;display:flex;gap:.45rem;flex-wrap:wrap;position:relative;z-index:1}
.pill{display:inline-block;border-radius:999px;padding:.34rem .66rem;font-size:.76rem;font-weight:850;border:1px solid transparent;margin-right:.25rem;margin-bottom:.25rem}.p-green{background:#e9fbf1;color:#067647;border-color:#b7ebc5}.p-red{background:#fff0ef;color:#b42318;border-color:#f8c1bd}.p-amber{background:#fff6e8;color:#b54708;border-color:#f6d39d}.p-blue{background:#edf6ff;color:#175cd3;border-color:#c7d7fe}.p-purple{background:#f3efff;color:#6941c6;border-color:#d9d0ff}.p-gray{background:#f2f4f7;color:#344054;border-color:#d0d5dd}.p-dark{background:rgba(255,255,255,.10);color:white;border-color:rgba(255,255,255,.16)}
.section{font-size:1.05rem;font-weight:900;color:var(--ink);margin:.7rem 0 .15rem}.panel{background:white;border:1px solid var(--line);border-radius:22px;padding:.95rem;box-shadow:0 8px 24px rgba(16,24,40,.045);margin-bottom:.8rem}
.regime-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.55rem}.mini{background:linear-gradient(180deg,#fff,#fafcff);border:1px solid #eaecf0;border-radius:16px;padding:.7rem}.mini-label{font-size:.72rem;color:var(--muted);margin-bottom:.15rem}.mini-value{font-weight:900;color:var(--ink);font-size:1.03rem}
.status-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.55rem;margin:.55rem 0 .9rem}.status{border-radius:17px;padding:.7rem;text-align:center;border:1px solid var(--line);background:#fff}.status-name{font-size:.72rem;color:var(--muted);font-weight:800}.status-num{font-size:1.45rem;font-weight:950;color:var(--ink)}
.arena-card{background:white;border:1px solid var(--line);border-radius:23px;padding:1rem;margin:.75rem 0;box-shadow:0 10px 24px rgba(16,24,40,.055)}.arena-ready{border-color:#a9e9c0;background:linear-gradient(180deg,#f5fff9,#fff 48%)}.arena-developing{border-color:#f5cf91;background:linear-gradient(180deg,#fff9ef,#fff 48%)}.arena-watch{border-color:#bad7ff;background:linear-gradient(180deg,#f5faff,#fff 48%)}
.symbol-row{display:flex;justify-content:space-between;gap:1rem;align-items:center;flex-wrap:wrap}.symbol{font-size:1.55rem;font-weight:950;color:var(--ink)}.subtitle{font-size:.86rem;color:var(--muted);margin-top:.12rem}.power{min-width:94px;height:94px;border-radius:22px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:linear-gradient(145deg,#0f172a,#183b68);color:white;box-shadow:0 9px 20px rgba(15,23,42,.2)}.power-score{font-size:1.55rem;font-weight:950;line-height:1}.power-label{font-size:.68rem;opacity:.78;margin-top:.2rem}
.quick-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.5rem;margin:.7rem 0}.quick{border:1px solid #eaecf0;background:#f8fafc;border-radius:14px;padding:.65rem}.q-label{font-size:.7rem;color:var(--muted)}.q-value{font-size:.94rem;font-weight:850;color:var(--ink);margin-top:.12rem;overflow-wrap:anywhere}
.quest{margin-top:.65rem;border:1px solid #e7eaf0;border-radius:15px;background:#fbfcfe;padding:.65rem .72rem}.quest-title{font-size:.74rem;font-weight:900;color:#475467;margin-bottom:.35rem}.quest-items{display:flex;gap:.35rem;flex-wrap:wrap}.missing{margin-top:.6rem;background:#fff8ed;border:1px solid #f7d6a8;border-radius:14px;padding:.65rem}.missing-title{font-size:.74rem;font-weight:900;color:#b54708;margin-bottom:.2rem}.missing-text{font-size:.83rem;color:#7a2e0e}
.leader{background:linear-gradient(135deg,#fff,#f7faff);border:1px solid #d6e4ff;border-radius:22px;padding:.9rem;margin-bottom:.75rem}.rank{display:inline-flex;width:28px;height:28px;border-radius:9px;background:#0f172a;color:#fff;align-items:center;justify-content:center;font-size:.77rem;font-weight:900;margin-right:.45rem}
[data-testid='stTabs'] button{font-weight:850;font-size:.82rem}[data-testid='stExpander'] details{border:1px solid #e5e7eb;border-radius:15px;background:#fff;overflow:hidden}[data-testid='stExpander'] details summary{background:#fcfcfd}
@media(max-width:850px){.regime-grid,.status-grid,.quick-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-title{font-size:1.65rem}.power{min-width:80px;height:80px;border-radius:20px}.power-score{font-size:1.3rem}}
</style>
""", unsafe_allow_html=True)


def esc(x): return html.escape(str(x))
def stage_of(r):
    if r.get('direction')=='ERROR': return 'ERROR'
    if r.get('direction') in ('WAIT',None): return 'NO TRADE'
    s=float(r.get('score',0))
    if s>=settings.ready_score:return 'READY'
    if s>=settings.developing_score:return 'DEVELOPING'
    if s>=settings.watch_score:return 'WATCH'
    return 'NO TRADE'
def cls_stage(s):return {'READY':'arena-ready','DEVELOPING':'arena-developing','WATCH':'arena-watch'}.get(s,'')
def tone(x):return {'READY':'green','LONG':'green','RISK_ON':'green','DEVELOPING':'amber','WATCH':'blue','SHORT':'red','RISK_OFF':'red','ERROR':'red','ELITE':'purple','STRONG':'green','BUILDING':'amber','LOW':'gray','NO TRADE':'gray','WAIT':'gray','NEUTRAL':'gray'}.get(str(x).upper(),'gray')
def pill(txt,t=None,dark=False):return f"<span class='pill {'p-dark' if dark else 'p-'+(t or tone(txt))}'>{esc(txt)}</span>"
def fmt_price(x):
    if not isinstance(x,(int,float)) or math.isnan(x):return '-'
    if x>=1000:return f'{x:,.2f}'
    if x>=1:return f'{x:,.4f}'
    return f'{x:,.6f}'
def readable(v): return str(v).replace('_',' ').title()

@st.cache_data(ttl=45,show_spinner=False)
def scan_all_cached(_bucket:int):
    async def run():
        try:vix=await asyncio.to_thread(analyze_internal_vix)
        except Exception as e:vix={'bias':'neutral','score':0,'source':'error','error':str(e)}
        async def one(symbol,asset_type):
            try:return await asyncio.wait_for(analyze_symbol(symbol,asset_type,vix.get('bias','neutral')),timeout=40)
            except asyncio.TimeoutError:return {'symbol':symbol,'asset_type':asset_type,'direction':'ERROR','score':0,'error':'Data source timeout'}
            except Exception as e:return {'symbol':symbol,'asset_type':asset_type,'direction':'ERROR','score':0,'error':str(e)}
        jobs=[one(s,'crypto') for s in settings.crypto_symbols]+[one(s,'stock') for s in settings.stock_symbols]
        return vix,list(await asyncio.gather(*jobs)),int(time.time())
    return asyncio.run(run())


def checklist_pills(r):
    c=r.get('checklist',{})
    keys=[('12H',c.get('12h_structure')),('4H',c.get('4h_structure')),('RSI 4H',c.get('rsi_div_4h')),('RSI 12H',c.get('rsi_div_12h')),('Fib',c.get('fib')),('1H',c.get('candles_1h'))]
    out=[]
    target='bullish' if r.get('long_score',0)>=r.get('short_score',0) else 'bearish'
    for label,val in keys:
        sv=str(val or 'none').lower()
        ok=(target in sv) or (label=='Fib' and 'healthy' in sv)
        out.append(pill(('✓ ' if ok else '• ')+label,'green' if ok else 'gray'))
    return ''.join(out)


def render_card(r,rank=None):
    stage=stage_of(r); direction=r.get('direction','-'); score=float(r.get('score',0)); power=r.get('setup_power','LOW')
    symbol=r.get('symbol','-'); asset='CRYPTO' if r.get('asset_type')=='crypto' else 'STOCK'; icon='₿' if asset=='CRYPTO' else '◆'
    rank_html=f"<span class='rank'>{rank}</span>" if rank else ''
    st.markdown(f"""
    <div class='arena-card {cls_stage(stage)}'>
      <div class='symbol-row'>
        <div style='flex:1;min-width:220px'>
          <div class='symbol'>{rank_html}{icon} {esc(symbol)}</div>
          <div class='subtitle'>{esc(asset)} • {esc(r.get('data_source','-'))}</div>
          <div style='margin-top:.45rem'>{pill(stage)}{pill(direction)}{pill(power)}{pill('Gap '+str(r.get('gap','-')),'gray')}</div>
        </div>
        <div class='power'><div class='power-score'>{score:.0f}</div><div class='power-label'>SETUP POWER</div></div>
      </div>
    </div>""",unsafe_allow_html=True)
    if 'error' in r:
        st.error(r['error']);return
    fib=r.get('fib',{}) or {}; d4=r.get('rsi_divergence_4h',{}) or {}; d12=r.get('rsi_divergence_12h',{}) or {}; bos4=r.get('bos_4h',{}) or {}
    st.markdown(f"""
    <div class='quick-grid'>
      <div class='quick'><div class='q-label'>Price</div><div class='q-value'>{fmt_price(r.get('price'))}</div></div>
      <div class='quick'><div class='q-label'>Market State</div><div class='q-value'>{readable((r.get('market_regime_12h') or {}).get('regime','-'))}</div></div>
      <div class='quick'><div class='q-label'>RSI Divergence</div><div class='q-value'>4H {readable(d4.get('type','none'))} • 12H {readable(d12.get('type','none'))}</div></div>
      <div class='quick'><div class='q-label'>Fib 0.50–0.618</div><div class='q-value'>{readable(fib.get('status','-'))}</div></div>
    </div>
    <div class='quest'><div class='quest-title'>MISSION CHECKLIST</div><div class='quest-items'>{checklist_pills(r)}</div></div>
    """,unsafe_allow_html=True)
    missing=r.get('missing_confirmations',[])
    if missing:
        st.markdown(f"<div class='missing'><div class='missing-title'>NEXT MISSION — what is still missing</div><div class='missing-text'>{esc(' • '.join(missing))}</div></div>",unsafe_allow_html=True)
    st.progress(min(max(score/100,0),1),text=f"LONG {r.get('long_score','-')}  •  SHORT {r.get('short_score','-')}  •  1H candles: {str(r.get('one_hour_candles','-')).upper()}")
    with st.expander('Open tactical details'):
        a,b=st.columns(2)
        with a:
            st.markdown('**Structure & momentum**')
            st.write('12H regime:',r.get('market_regime_12h'))
            st.write('4H regime:',r.get('market_regime_4h'))
            st.write('12H BOS/CHoCH:',r.get('bos_12h'))
            st.write('4H BOS/CHoCH:',r.get('bos_4h'))
            st.write('RSI divergence 12H:',d12)
            st.write('RSI divergence 4H:',d4)
            st.write('Divergence sync:',r.get('divergence_sync'))
        with b:
            st.markdown('**Setup mechanics**')
            st.write('Fib:',fib)
            st.write('Liquidity:',r.get('liquidity_sweep'))
            st.write('Pattern:',r.get('pattern'))
            st.write('Wyckoff:',r.get('wyckoff'))
            st.write('Support / resistance:',r.get('support_resistance'))
            st.write('4H volume ratio:',r.get('volume_ratio_4h'))
        st.markdown('**Why the score**')
        for reason in r.get('reasons',[]):st.write('•',reason)
        st.markdown('**Data sources**')
        for tf,src in (r.get('sources') or {}).items():st.write(f'{tf}: {src}')

# Hero
st.markdown("""
<div class='hero'>
 <div class='hero-title'>⚡ Hadar Alpha Arena</div>
 <div class='hero-sub'>Live decision engine • Game Premium UI • 12H / 4H core • 1H candles only • no 15m</div>
 <div class='hero-strip'><span class='pill p-dark'>VIX Regime</span><span class='pill p-dark'>RSI Divergence 4H + 12H</span><span class='pill p-dark'>BOS / CHoCH</span><span class='pill p-dark'>Smart Fib</span><span class='pill p-dark'>Liquidity</span></div>
</div>
""",unsafe_allow_html=True)

c1,c2,c3=st.columns([1.25,1.35,1])
with c1:mode=st.selectbox('Arena',['All','Crypto only','Stocks only'])
with c2:sort_mode=st.selectbox('Priority',['Highest Setup Power','LONG first','SHORT first','Alphabetical'])
with c3:
    st.write('')
    if st.button('⚡ RUN SCAN',use_container_width=True):st.cache_data.clear()

bucket=int(time.time()//60)
with st.spinner('Reading market structure and building setup scores…'):
    vix,rows,ts=scan_all_cached(bucket)
if mode=='Crypto only':rows=[r for r in rows if r.get('asset_type')=='crypto']
elif mode=='Stocks only':rows=[r for r in rows if r.get('asset_type')=='stock']

ready=[r for r in rows if stage_of(r)=='READY'];develop=[r for r in rows if stage_of(r)=='DEVELOPING'];watch=[r for r in rows if stage_of(r)=='WATCH'];wait=[r for r in rows if stage_of(r)=='NO TRADE'];errors=[r for r in rows if stage_of(r)=='ERROR'];valid=[r for r in rows if stage_of(r)!='ERROR']

def ordered(xs):
    if sort_mode=='Alphabetical':return sorted(xs,key=lambda r:r.get('symbol',''))
    if sort_mode=='LONG first':return sorted(xs,key=lambda r:(r.get('direction')!='LONG',-float(r.get('score',0))))
    if sort_mode=='SHORT first':return sorted(xs,key=lambda r:(r.get('direction')!='SHORT',-float(r.get('score',0))))
    return sorted(xs,key=lambda r:float(r.get('score',0)),reverse=True)

# Command center
st.markdown("<div class='section'>🎮 Command Center</div>",unsafe_allow_html=True)
bias=str(vix.get('bias','neutral')).upper()
leader=ordered(valid)[0] if valid else None
st.markdown(f"""
<div class='panel'>
 <div class='regime-grid'>
   <div class='mini'><div class='mini-label'>VIX REGIME</div><div class='mini-value'>{esc(bias)}</div></div>
   <div class='mini'><div class='mini-label'>VIX SCORE</div><div class='mini-value'>{esc(vix.get('score',0))}</div></div>
   <div class='mini'><div class='mini-label'>TOP TARGET</div><div class='mini-value'>{esc(leader.get('symbol','-') if leader else '-')}</div></div>
   <div class='mini'><div class='mini-label'>TOP POWER</div><div class='mini-value'>{esc(leader.get('setup_power','-') if leader else '-')}</div></div>
 </div>
 <div style='margin-top:.55rem'>{pill('VIX '+bias)}{pill('VIX '+str(vix.get('vix','-')),'gray')}{pill('VIX9D/VIX '+str(vix.get('vix9d_ratio','-')),'gray')}{pill('4H div '+str(vix.get('div4h','-')),'gray')}{pill('12H div '+str(vix.get('div12h','-')),'gray')}</div>
</div>
<div class='status-grid'>
 <div class='status'><div class='status-name'>🟢 READY</div><div class='status-num'>{len(ready)}</div></div>
 <div class='status'><div class='status-name'>🟠 DEVELOPING</div><div class='status-num'>{len(develop)}</div></div>
 <div class='status'><div class='status-name'>🔵 WATCH</div><div class='status-num'>{len(watch)}</div></div>
 <div class='status'><div class='status-name'>⚪ WAIT</div><div class='status-num'>{len(wait)}</div></div>
</div>
""",unsafe_allow_html=True)
if errors:st.warning(f'⚠️ {len(errors)} data errors are separated from trade decisions.')

# Leaderboard
st.markdown("<div class='section'>🏆 Alpha Leaderboard</div><div class='muted'>The 3 closest setups right now. They can appear here before they reach READY.</div>",unsafe_allow_html=True)
for idx,r in enumerate(ordered(valid)[:3],1):render_card(r,idx)
if not valid:st.info('No valid market data yet.')

# Full arena
st.markdown("<div class='section'>🗺️ Full Arena</div><div class='muted'>Open only the stage you want. Deep tactical data stays hidden by default.</div>",unsafe_allow_html=True)
tabs=st.tabs([f'🟢 READY {len(ready)}',f'🟠 DEV {len(develop)}',f'🔵 WATCH {len(watch)}',f'⚪ WAIT {len(wait)}',f'⚠️ ERR {len(errors)}'])
for tab,grp in zip(tabs,[ready,develop,watch,wait,errors]):
    with tab:
        if not grp:st.info('Nothing here right now.')
        for r in ordered(grp):render_card(r)

st.caption('Game Premium v3 • Analysis + alerts decision engine. Scores are analytical signals, not guarantees. Crypto fallback: Binance Vision → alternate Binance endpoints → Yahoo.')
