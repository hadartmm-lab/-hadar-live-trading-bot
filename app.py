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
.block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1180px;}
h1, h2, h3 {letter-spacing: -0.02em;}
.small-note {font-size: 0.9rem; opacity: 0.78;}
.badge {display:inline-block; padding: 0.35rem 0.7rem; border-radius: 999px; font-weight: 700; font-size: 0.85rem; margin-right: 0.4rem; margin-bottom: 0.35rem;}
.badge-green {background:#e9f9ef; color:#177d3f; border:1px solid #bce7ca;}
.badge-red {background:#fdeeee; color:#b42318; border:1px solid #f7c0c0;}
.badge-orange {background:#fff4e5; color:#b54708; border:1px solid #f7d4a4;}
.badge-blue {background:#eef4ff; color:#175cd3; border:1px solid #c7d7fe;}
.badge-gray {background:#f2f4f7; color:#344054; border:1px solid #d0d5dd;}
.card {border:1px solid #e5e7eb; border-radius:18px; padding:1rem 1rem 0.75rem 1rem; margin-bottom:0.9rem; box-shadow: 0 4px 18px rgba(16,24,40,0.04);}
.card.ready {background: linear-gradient(180deg, #f7fff9 0%, #ffffff 100%); border-color:#b7ebc5;}
.card.developing {background: linear-gradient(180deg, #fffaf3 0%, #ffffff 100%); border-color:#f2d7a6;}
.card.watch {background: linear-gradient(180deg, #f7fbff 0%, #ffffff 100%); border-color:#bfd6ff;}
.card.no-trade {background: linear-gradient(180deg, #fcfcfd 0%, #ffffff 100%); border-color:#eaecf0;}
.metric-box {background:#f8fafc; border:1px solid #eaecf0; border-radius:14px; padding:0.8rem; text-align:center;}
.metric-label {font-size:0.82rem; color:#667085; margin-bottom:0.2rem;}
.metric-value {font-size:1.5rem; font-weight:800; color:#101828;}
.reason-box {background:#f8fafc; border-radius:12px; padding:0.8rem 0.9rem; border:1px solid #eaecf0;}
hr.soft {border:none; border-top:1px solid #eaecf0; margin:0.9rem 0;}
[data-testid="stMetricValue"] {font-size: 1.45rem;}
[data-testid="stExpander"] details {border:1px solid #eaecf0; border-radius:12px; background:#fff;}
</style>
""", unsafe_allow_html=True)


def stage_of(r):
    if r.get("direction") in ("WAIT", "ERROR", None):
        return "NO TRADE"
    s=float(r.get("score",0))
    if s>=settings.ready_score: return "READY"
    if s>=settings.developing_score: return "DEVELOPING"
    if s>=settings.watch_score: return "WATCH"
    return "NO TRADE"


def stage_class(stage: str) -> str:
    return {
        'READY': 'ready',
        'DEVELOPING': 'developing',
        'WATCH': 'watch',
        'NO TRADE': 'no-trade'
    }.get(stage, 'no-trade')


def pill(text: str, tone: str='gray') -> str:
    tone_map = {
        'green':'badge-green', 'red':'badge-red', 'orange':'badge-orange',
        'blue':'badge-blue', 'gray':'badge-gray'
    }
    return f'<span class="badge {tone_map.get(tone, "badge-gray")}">{text}</span>'


def fmt_price(x):
    if not isinstance(x,(int,float)) or math.isnan(x):
        return '-'
    if x >= 1000:
        return f'{x:,.2f}'
    if x >= 1:
        return f'{x:,.4f}'
    return f'{x:,.6f}'


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


def render_compact_card(r):
    stage = stage_of(r)
    direction = r.get('direction', '-')
    score = float(r.get('score', 0))
    symbol = r.get('symbol', '-')
    source = r.get('data_source', '-')
    stage_tone = {'READY':'green','DEVELOPING':'orange','WATCH':'blue','NO TRADE':'gray'}[stage]
    dir_tone = 'green' if direction=='LONG' else 'red' if direction=='SHORT' else 'gray'
    asset_emoji = '₿' if r.get('asset_type') == 'crypto' else '📊'
    html = f"""
    <div class='card {stage_class(stage)}'>
      <div style='display:flex;justify-content:space-between;align-items:flex-start;gap:0.8rem;flex-wrap:wrap;'>
        <div>
          <div style='font-size:1.85rem;font-weight:900;color:#101828'>{asset_emoji} {symbol}</div>
          <div style='margin-top:0.25rem'>{pill(stage, stage_tone)} {pill(direction, dir_tone)} {pill(source, 'gray')}</div>
        </div>
        <div style='min-width:160px;'>
          <div class='metric-box'>
            <div class='metric-label'>Score</div>
            <div class='metric-value'>{score:.1f}/100</div>
          </div>
        </div>
      </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
    if 'error' in r:
        st.error(r['error'])
        return

    c1,c2,c3,c4 = st.columns(4)
    c1.metric('Price', fmt_price(r.get('price')))
    c2.metric('1H candles', str(r.get('one_hour_candles','-')).upper())
    fib = r.get('fib',{}) or {}
    c3.metric('Fib zone', fib.get('status','-'))
    pat = r.get('pattern',{}) or {}
    c4.metric('Pattern', pat.get('pattern','-'))

    progress = min(max(score / 100.0, 0.0), 1.0)
    st.progress(progress, text=f"Confidence gap: {r.get('gap','-')} • Long {r.get('long_score','-')} / Short {r.get('short_score','-')}")

    with st.expander('More details'):
        d1, d2 = st.columns(2)
        sw = r.get('liquidity_sweep',{}) or {}
        sr = r.get('support_resistance',{}) or {}
        d1.markdown('**Setup summary**')
        d1.write(f"Fib: {fib.get('status','-')} ({fib.get('direction','-')})")
        d1.write(f"Liquidity sweep: {sw.get('type','-')} | strength {sw.get('strength','-')}")
        d1.write(f"Pattern: {pat.get('pattern','-')} | confidence {pat.get('confidence','-')}")
        d1.write(f"Wyckoff heuristic: {r.get('wyckoff','-')}")
        d1.write(f"4H volume ratio: {r.get('volume_ratio_4h','-')}")

        d2.markdown('**Support / resistance**')
        sup = sr.get('support') or {}
        res = sr.get('resistance') or {}
        d2.write(f"Support: {sup.get('price','-')} | touches {sup.get('touches','-')}")
        d2.write(f"Resistance: {res.get('price','-')} | touches {res.get('touches','-')}")
        sources = r.get('sources', {})
        if sources:
            d2.markdown('**Data sources**')
            for tf in ['1h','4h','12h','1d']:
                d2.write(f"{tf}: {sources.get(tf,'-')}")

        st.markdown("<div class='reason-box'><b>Why this score</b></div>", unsafe_allow_html=True)
        for x in r.get('reasons',[]):
            st.write('•', x)


st.title('Hadar Live Trading Bot')
st.caption('Friendlier dashboard • cleaner view • resilient crypto data fallback • 12H/4H/Daily core • 1H candles only')

header_left, header_mid, header_right = st.columns([2.8, 1.2, 1.2])
with header_left:
    st.markdown("<div class='small-note'>Focused view: show the important parts first, hide heavy details inside expanders.</div>", unsafe_allow_html=True)
with header_mid:
    if st.button('🔄 Scan now', use_container_width=True):
        st.cache_data.clear()
with header_right:
    mode = st.selectbox('Show', ['All', 'Crypto only', 'Stocks only'], index=0)

bucket=int(time.time()//60)
with st.spinner('Scanning market data…'):
    vix, rows, ts = scan_all_cached(bucket)

# Filter mode
if mode == 'Crypto only':
    rows = [r for r in rows if r.get('asset_type') == 'crypto']
elif mode == 'Stocks only':
    rows = [r for r in rows if r.get('asset_type') == 'stock']

# Summary / market regime
st.markdown('### Market regime')
vc1,vc2,vc3,vc4 = st.columns(4)
vc1.metric('VIX bias', str(vix.get('bias','neutral')).upper())
vc2.metric('VIX score', vix.get('score',0))
vc3.metric('VIX', vix.get('vix','-'))
vc4.metric('VIX9D/VIX', vix.get('vix9d_ratio','-'))
st.caption(f"VIX source: {vix.get('source','-')} • 4H divergence: {vix.get('div4h','-')} • 12H divergence: {vix.get('div12h','-')}")

ready=[r for r in rows if stage_of(r)=='READY']
develop=[r for r in rows if stage_of(r)=='DEVELOPING']
watch=[r for r in rows if stage_of(r)=='WATCH']
other=[r for r in rows if stage_of(r)=='NO TRADE']

sum1,sum2,sum3,sum4 = st.columns(4)
sum1.metric('READY', len(ready))
sum2.metric('DEVELOPING', len(develop))
sum3.metric('WATCH', len(watch))
sum4.metric('NO TRADE', len(other))

# Tabs reduce visual overload
labels = [
    f'🟢 READY ({len(ready)})',
    f'🟠 DEVELOPING ({len(develop)})',
    f'🔵 WATCH ({len(watch)})',
    f'⚪ NO TRADE ({len(other)})'
]

tabs = st.tabs(labels)
for tab, grp in zip(tabs, [ready, develop, watch, other]):
    with tab:
        if not grp:
            st.info('Nothing here right now.')
        for r in sorted(grp, key=lambda x: float(x.get('score',0)), reverse=True):
            render_compact_card(r)

st.caption('If one crypto source is blocked, the app tries Binance Vision / alternate Binance endpoints and then Yahoo as fallback. For 24/7 alerts, keep the background alert worker separate from Streamlit.')
