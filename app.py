from __future__ import annotations
import asyncio
import time
import math
import streamlit as st

from config import settings
from engine import analyze_symbol
from vix_engine import analyze_internal_vix

st.set_page_config(page_title="Hadar Live Trading Bot", page_icon="📈", layout="wide")

st.markdown("""
<style>
:root {
  --bg: #f6f8fb;
  --card: #ffffff;
  --text: #101828;
  --muted: #667085;
  --line: #e4e7ec;
  --navy: #0f172a;
  --navy-2: #111b34;
  --green: #12b76a;
  --green-soft: #e8fff3;
  --orange: #f79009;
  --orange-soft: #fff6e8;
  --blue: #2e90fa;
  --blue-soft: #eef7ff;
  --red: #f04438;
  --red-soft: #fff0f0;
  --gray-soft: #f2f4f7;
}
html, body, [data-testid="stAppViewContainer"] {background: var(--bg);}
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1220px;}
h1, h2, h3 {letter-spacing: -0.02em; color: var(--text);} 
.main-title {font-size: 2rem; font-weight: 900; color: #fff; margin: 0;}
.hero {
  background: linear-gradient(135deg, #0f172a 0%, #111b34 45%, #173a6a 100%);
  color: #fff; border-radius: 24px; padding: 1.1rem 1.1rem 1rem 1.1rem;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.18); border: 1px solid rgba(255,255,255,0.08);
  margin-bottom: 1rem;
}
.hero-sub {opacity: 0.82; font-size: 0.95rem; margin-top: 0.2rem;}
.toolbar {
  background: rgba(255,255,255,0.09); border: 1px solid rgba(255,255,255,0.12);
  border-radius: 18px; padding: 0.55rem 0.8rem; margin-top: 0.9rem;
}
.section-title {font-size: 1.08rem; font-weight: 850; color: var(--text); margin-bottom: 0.45rem;}
.muted {font-size: 0.92rem; color: var(--muted);}
.badge {display:inline-block; padding: 0.34rem 0.72rem; border-radius: 999px; font-weight: 800; font-size: 0.80rem; margin-right: 0.35rem; margin-bottom: 0.35rem;}
.b-green {background: var(--green-soft); color: #067647; border:1px solid #b7ebc5;}
.b-red {background: var(--red-soft); color:#b42318; border:1px solid #f8c1bd;}
.b-orange {background: var(--orange-soft); color:#b54708; border:1px solid #f7d6a8;}
.b-blue {background: var(--blue-soft); color:#175cd3; border:1px solid #bfdbfe;}
.b-gray {background: #f2f4f7; color:#344054; border:1px solid #d0d5dd;}
.b-dark {background: rgba(255,255,255,0.08); color:#fff; border:1px solid rgba(255,255,255,0.16);}
.overview-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.75rem;margin:0.65rem 0 0.2rem 0;}
.overview-box {
  background: linear-gradient(180deg, #ffffff 0%, #fbfcfe 100%); border:1px solid var(--line);
  border-radius: 18px; padding: 0.9rem; box-shadow: 0 6px 20px rgba(16,24,40,0.04);
}
.overview-label {font-size:0.8rem; color:var(--muted); margin-bottom:0.15rem;}
.overview-value {font-size:1.55rem; font-weight:900; color:var(--text); line-height:1.15;}
.status-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.65rem; margin:0.8rem 0 1rem 0;}
.status-card {
  background:#fff; border:1px solid var(--line); border-radius:18px; padding:0.75rem 0.7rem;
  text-align:center; box-shadow:0 6px 18px rgba(16,24,40,0.03);
}
.status-name {font-size:0.78rem; color:var(--muted); margin-bottom:0.2rem;}
.status-value {font-size:1.45rem; font-weight:900; color:var(--text);}
.panel {
  background:#fff; border:1px solid var(--line); border-radius:22px; padding:1rem; margin-bottom:1rem;
  box-shadow:0 8px 24px rgba(16,24,40,0.04);
}
.card {
  background:#fff; border:1px solid var(--line); border-radius:22px; padding:1rem; margin-bottom:0.9rem;
  box-shadow:0 10px 22px rgba(16,24,40,0.05);
}
.card.ready {background: linear-gradient(180deg, #f6fff9 0%, #ffffff 100%); border-color:#b7ebc5;}
.card.developing {background: linear-gradient(180deg, #fffaf1 0%, #ffffff 100%); border-color:#f6d39d;}
.card.watch {background: linear-gradient(180deg, #f7fbff 0%, #ffffff 100%); border-color:#c7d7fe;}
.card.no-trade {background: linear-gradient(180deg, #fcfcfd 0%, #ffffff 100%);}
.symbol {font-size:1.55rem; font-weight:900; color:var(--text); line-height:1.1;}
.card-sub {font-size:0.86rem; color:var(--muted);}
.score-circle {
  min-width:88px; height:88px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  background: radial-gradient(circle at 30% 30%, #ffffff 0%, #f4f7fb 60%, #eef2f7 100%);
  border: 1px solid var(--line); box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
  flex-direction:column;
}
.score-number {font-size:1.45rem; font-weight:900; color:var(--text); line-height:1;}
.score-caption {font-size:0.7rem; color:var(--muted); margin-top:0.15rem;}
.info-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.55rem;margin-top:.75rem;}
.info-box {background:#f8fafc;border:1px solid #eaecf0;border-radius:14px;padding:.7rem .75rem;}
.info-title {font-size:.75rem;color:var(--muted);margin-bottom:.18rem;}
.info-value {font-size:1rem;font-weight:800;color:var(--text);line-height:1.2;}
.quality-bar {margin-top:0.75rem;}
.hr-soft {height:1px;background:#eaecf0;border:none;margin:0.8rem 0;}
[data-testid="stMetricValue"] {font-size: 1.4rem;}
[data-testid="stTabs"] button {font-weight:800;}
[data-testid="stExpander"] details {border:1px solid #e5e7eb; border-radius:15px; background:#fff; overflow:hidden;}
[data-testid="stExpander"] details summary {background:#fcfcfd; border-bottom:1px solid #f2f4f7;}
@media (max-width: 900px){
  .status-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
  .info-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
}
</style>
""", unsafe_allow_html=True)


def stage_of(r):
    if r.get("direction") == "ERROR":
        return "ERROR"
    if r.get("direction") in ("WAIT", None):
        return "NO TRADE"
    s=float(r.get("score",0))
    if s>=settings.ready_score: return "READY"
    if s>=settings.developing_score: return "DEVELOPING"
    if s>=settings.watch_score: return "WATCH"
    return "NO TRADE"


def stage_class(stage: str) -> str:
    return {
        'READY': 'ready', 'DEVELOPING': 'developing', 'WATCH': 'watch',
        'NO TRADE': 'no-trade', 'ERROR': 'no-trade'
    }.get(stage, 'no-trade')


def tone(stage_or_dir: str) -> str:
    mapping = {
        'READY':'green', 'DEVELOPING':'orange', 'WATCH':'blue', 'NO TRADE':'gray', 'ERROR':'red',
        'LONG':'green', 'SHORT':'red', 'WAIT':'gray', 'RISK_ON':'green', 'RISK_OFF':'red', 'NEUTRAL':'gray'
    }
    return mapping.get(stage_or_dir, 'gray')


def pill(text: str, tone_name: str='gray', dark=False) -> str:
    cls = {'green':'b-green','red':'b-red','orange':'b-orange','blue':'b-blue','gray':'b-gray'}.get(tone_name, 'b-gray')
    if dark:
        cls = 'b-dark'
    return f'<span class="badge {cls}">{text}</span>'


def fmt_price(x):
    if not isinstance(x,(int,float)) or math.isnan(x):
        return '-'
    if x >= 1000: return f'{x:,.2f}'
    if x >= 1: return f'{x:,.4f}'
    return f'{x:,.6f}'


def signal_label(score: float, direction: str, stage: str) -> str:
    if stage == 'READY' and score >= 90:
        return f'Strong {direction}'
    if stage == 'READY':
        return f'Active {direction}'
    if stage == 'DEVELOPING':
        return f'Building {direction}'
    if stage == 'WATCH':
        return f'Watch {direction}'
    if direction == 'WAIT':
        return 'Mixed / Wait'
    return 'No clear edge'


@st.cache_data(ttl=45, show_spinner=False)
def scan_all_cached(_bucket:int):
    async def run():
        try:
            vix = await asyncio.to_thread(analyze_internal_vix)
        except Exception as e:
            vix = {"bias":"neutral","score":0,"source":"error","error":str(e)}

        async def one(symbol, asset_type):
            try:
                return await asyncio.wait_for(
                    analyze_symbol(symbol, asset_type, vix.get("bias","neutral")),
                    timeout=40,
                )
            except asyncio.TimeoutError:
                return {"symbol":symbol,"asset_type":asset_type,"direction":"ERROR","score":0,"error":"Data source timeout — skipped this scan"}
            except Exception as e:
                return {"symbol":symbol,"asset_type":asset_type,"direction":"ERROR","score":0,"error":str(e)}

        jobs=[one(s,"crypto") for s in settings.crypto_symbols] + [one(s,"stock") for s in settings.stock_symbols]
        rows=list(await asyncio.gather(*jobs))
        return vix, rows, int(time.time())
    return asyncio.run(run())


def render_symbol_card(r):
    stage = stage_of(r)
    direction = r.get('direction', '-')
    score = float(r.get('score', 0))
    symbol = r.get('symbol', '-')
    source = r.get('data_source', '-')
    signal = signal_label(score, direction, stage)
    stage_tone = tone(stage)
    dir_tone = tone(direction)
    asset_type = r.get('asset_type')
    asset_name = 'Crypto' if asset_type == 'crypto' else 'Stock'
    asset_icon = '₿' if asset_type == 'crypto' else '📈'
    html = f"""
    <div class='card {stage_class(stage)}'>
      <div style='display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;'>
        <div style='flex:1;min-width:220px;'>
          <div class='symbol'>{asset_icon} {symbol}</div>
          <div class='card-sub' style='margin-top:0.16rem;'>{signal}</div>
          <div style='margin-top:0.5rem;'>
            {pill(stage, stage_tone)} {pill(direction, dir_tone)} {pill(asset_name, 'gray')} {pill(source, 'gray')}
          </div>
        </div>
        <div class='score-circle'>
          <div class='score-number'>{score:.0f}</div>
          <div class='score-caption'>score</div>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    if 'error' in r:
        st.error(r['error'])
        return

    fib = r.get('fib',{}) or {}
    pat = r.get('pattern',{}) or {}
    info_html = f"""
    <div class='info-grid'>
      <div class='info-box'><div class='info-title'>Price</div><div class='info-value'>{fmt_price(r.get('price'))}</div></div>
      <div class='info-box'><div class='info-title'>1H Candles</div><div class='info-value'>{str(r.get('one_hour_candles','-')).upper()}</div></div>
      <div class='info-box'><div class='info-title'>Fib Zone</div><div class='info-value'>{fib.get('status','-')}</div></div>
      <div class='info-box'><div class='info-title'>Pattern</div><div class='info-value'>{pat.get('pattern','-')}</div></div>
    </div>
    """
    st.markdown(info_html, unsafe_allow_html=True)
    st.progress(min(max(score/100.0,0.0),1.0), text=f"Long {r.get('long_score','-')} • Short {r.get('short_score','-')} • Confidence gap {r.get('gap','-')}")

    with st.expander('More details'):
        left, right = st.columns(2)
        sw = r.get('liquidity_sweep',{}) or {}
        sr = r.get('support_resistance',{}) or {}
        with left:
            st.markdown('**Setup summary**')
            st.write(f"Fib: {fib.get('status','-')} ({fib.get('direction','-')})")
            st.write(f"Liquidity sweep: {sw.get('type','-')} | strength {sw.get('strength','-')}")
            st.write(f"Pattern: {pat.get('pattern','-')} | confidence {pat.get('confidence','-')}")
            st.write(f"Wyckoff heuristic: {r.get('wyckoff','-')}")
            st.write(f"4H volume ratio: {r.get('volume_ratio_4h','-')}")
        with right:
            st.markdown('**Support / resistance**')
            sup = sr.get('support') or {}
            res = sr.get('resistance') or {}
            st.write(f"Support: {sup.get('price','-')} | touches {sup.get('touches','-')}")
            st.write(f"Resistance: {res.get('price','-')} | touches {res.get('touches','-')}")
            sources = r.get('sources', {})
            if sources:
                st.markdown('**Data sources**')
                for tf in ['1h','4h','12h','1d']:
                    st.write(f"{tf}: {sources.get(tf,'-')}")
        st.markdown('**Why this score**')
        for x in r.get('reasons',[]):
            st.write('•', x)


# HERO
st.markdown("""
<div class='hero'>
  <div class='main-title'>Hadar Live Trading Bot</div>
  <div class='hero-sub'>Premium layout • cleaner decision flow • VIX-aware market regime • crypto + stocks dashboard</div>
  <div class='toolbar'>Focus on the strongest opportunities first. Deep details stay hidden until you open them.</div>
</div>
""", unsafe_allow_html=True)

controls_l, controls_m, controls_r = st.columns([1.2, 1.4, 1])
with controls_l:
    mode = st.selectbox('Market', ['All', 'Crypto only', 'Stocks only'], index=0)
with controls_m:
    sort_mode = st.selectbox('Sort', ['Highest score', 'Direction then score', 'Alphabetical'], index=0)
with controls_r:
    if st.button('🔄 Scan now', use_container_width=True):
        st.cache_data.clear()

bucket=int(time.time()//60)
with st.spinner('Scanning market data…'):
    vix, rows, ts = scan_all_cached(bucket)

if mode == 'Crypto only':
    rows = [r for r in rows if r.get('asset_type') == 'crypto']
elif mode == 'Stocks only':
    rows = [r for r in rows if r.get('asset_type') == 'stock']

# categorization
ready=[r for r in rows if stage_of(r)=='READY']
develop=[r for r in rows if stage_of(r)=='DEVELOPING']
watch=[r for r in rows if stage_of(r)=='WATCH']
no_trade=[r for r in rows if stage_of(r)=='NO TRADE']
errors=[r for r in rows if stage_of(r)=='ERROR']
valid=[r for r in rows if stage_of(r)!='ERROR']

def sort_rows(grp):
    if sort_mode == 'Alphabetical':
        return sorted(grp, key=lambda x: x.get('symbol',''))
    if sort_mode == 'Direction then score':
        return sorted(grp, key=lambda x: (x.get('direction',''), -float(x.get('score',0))))
    return sorted(grp, key=lambda x: float(x.get('score',0)), reverse=True)

# overview
bias = str(vix.get('bias','neutral')).upper()
st.markdown("<div class='section-title'>Overview</div>", unsafe_allow_html=True)
left, right = st.columns([1.45, 1])
with left:
    st.markdown(
        f"""
        <div class='panel'>
          <div style='display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;'>
            <div>
              <div class='section-title' style='margin-bottom:.35rem'>Market regime</div>
              <div>{pill('VIX ' + bias, tone(bias))} {pill('Score ' + str(vix.get('score',0)), 'blue')} {pill('VIX ' + str(vix.get('vix','-')), 'gray')} {pill('VIX9D/VIX ' + str(vix.get('vix9d_ratio','-')), 'gray')}</div>
              <div class='muted' style='margin-top:.55rem'>Source: {vix.get('source','-')} • 4H divergence: {vix.get('div4h','-')} • 12H divergence: {vix.get('div12h','-')}</div>
            </div>
            <div class='overview-grid' style='min-width:250px;flex:1;'>
              <div class='overview-box'><div class='overview-label'>Top stage</div><div class='overview-value'>{'READY' if ready else 'DEVELOPING' if develop else 'WATCH' if watch else 'WAIT'}</div></div>
              <div class='overview-box'><div class='overview-label'>Valid symbols</div><div class='overview-value'>{len(valid)}</div></div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )
with right:
    st.markdown(
        f"""
        <div class='status-grid'>
          <div class='status-card'><div class='status-name'>🟢 READY</div><div class='status-value'>{len(ready)}</div></div>
          <div class='status-card'><div class='status-name'>🟠 DEVELOPING</div><div class='status-value'>{len(develop)}</div></div>
          <div class='status-card'><div class='status-name'>🔵 WATCH</div><div class='status-value'>{len(watch)}</div></div>
          <div class='status-card'><div class='status-name'>⚪ NO TRADE</div><div class='status-value'>{len(no_trade)}</div></div>
        </div>
        """, unsafe_allow_html=True
    )
    if errors:
        st.warning(f'{len(errors)} symbols have a data-source error and are separated from trade signals.')

# top opportunities
st.markdown("<div class='section-title'>Top opportunities</div><div class='muted'>The strongest symbols right now, even if they are not fully READY yet.</div>", unsafe_allow_html=True)
top = sort_rows(valid)[:3]
if top:
    for r in top:
        render_symbol_card(r)
else:
    st.info('No valid market data yet.')

# full scan
st.markdown("<div class='section-title'>Full market scan</div><div class='muted'>Use the tabs to keep the view clean. Data errors are separated from NO TRADE.</div>", unsafe_allow_html=True)
labels = [
    f'🟢 READY {len(ready)}',
    f'🟠 DEVELOPING {len(develop)}',
    f'🔵 WATCH {len(watch)}',
    f'⚪ WAIT {len(no_trade)}',
    f'⚠️ ERR {len(errors)}'
]
tabs = st.tabs(labels)
for tab, grp in zip(tabs, [ready, develop, watch, no_trade, errors]):
    with tab:
        ordered = sort_rows(grp)
        if not ordered:
            st.info('Nothing here right now.')
        for r in ordered:
            render_symbol_card(r)

st.caption('Crypto data fallback order: Binance Vision → alternate Binance endpoints → Yahoo. For 24/7 alerts, keep the background alert worker separate from Streamlit.')
