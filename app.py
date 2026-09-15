from __future__ import annotations
import asyncio
import time
import streamlit as st

from config import settings
from engine import analyze_symbol
from vix_engine import analyze_internal_vix

st.set_page_config(page_title="Hadar Live Trading Bot", page_icon="📈", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:1.4rem;max-width:1500px}
[data-testid="stMetricValue"]{font-size:1.55rem}
.small{opacity:.75;font-size:.9rem}
</style>
""", unsafe_allow_html=True)

st.title("Hadar Live Trading Decision Engine")
st.caption("Analysis + alerts dashboard • 12H/4H/Daily core • 1H candles only • no 15m")

@st.cache_data(ttl=45, show_spinner=False)
def scan_all_cached(_bucket:int):
    async def run():
        try:
            vix = await asyncio.to_thread(analyze_internal_vix)
        except Exception as e:
            vix = {"bias":"neutral","score":0,"source":"error","error":str(e)}

        rows=[]
        for symbol in settings.crypto_symbols:
            try:
                r=await analyze_symbol(symbol,"crypto",vix.get("bias","neutral"))
                rows.append(r)
            except Exception as e:
                rows.append({"symbol":symbol,"asset_type":"crypto","direction":"ERROR","score":0,"error":str(e)})
        for symbol in settings.stock_symbols:
            try:
                r=await analyze_symbol(symbol,"stock",vix.get("bias","neutral"))
                rows.append(r)
            except Exception as e:
                rows.append({"symbol":symbol,"asset_type":"stock","direction":"ERROR","score":0,"error":str(e)})
        return vix, rows, int(time.time())
    return asyncio.run(run())

def stage_of(r):
    if r.get("direction") in ("WAIT","ERROR",None): return "NO TRADE"
    s=float(r.get("score",0))
    if s>=settings.ready_score: return "READY"
    if s>=settings.developing_score: return "DEVELOPING"
    if s>=settings.watch_score: return "WATCH"
    return "NO TRADE"

def render_card(r):
    stage=stage_of(r)
    direction=r.get("direction","-")
    score=r.get("score",0)
    symbol=r.get("symbol","-")
    price=r.get("price","-")
    with st.container(border=True):
        c1,c2,c3,c4=st.columns([1.3,1,1,1.2])
        c1.subheader(symbol)
        c2.metric("Direction", direction)
        c3.metric("Score", f"{score}/100")
        c4.metric("Stage", stage)
        if "error" in r:
            st.error(r["error"])
            return
        a,b,c,d=st.columns(4)
        a.metric("Price", f"{price:,.4f}" if isinstance(price,(int,float)) else price)
        a.caption(f"1H candles: {r.get('one_hour_candles','-')}")
        fib=r.get("fib",{}) or {}
        b.metric("Fib", fib.get("status","-"))
        b.caption(f"Direction: {fib.get('direction','-')}")
        sw=r.get("liquidity_sweep",{}) or {}
        c.metric("Liquidity sweep", sw.get("type","-"))
        c.caption(f"Strength: {sw.get('strength','-')}")
        pat=r.get("pattern",{}) or {}
        d.metric("Pattern", pat.get("pattern","-"))
        d.caption(f"Confidence: {pat.get('confidence','-')}")
        with st.expander("Why this score"):
            for x in r.get("reasons",[]): st.write("•",x)

left,right=st.columns([3,1])
with right:
    if st.button("🔄 Scan now", use_container_width=True):
        st.cache_data.clear()

bucket=int(time.time()//60)
with st.spinner("Scanning market data…"):
    vix, rows, ts = scan_all_cached(bucket)

with left:
    st.subheader("Market regime")
vc1,vc2,vc3,vc4=st.columns(4)
vc1.metric("VIX bias", str(vix.get("bias","neutral")).upper())
vc2.metric("VIX score", vix.get("score",0))
vc3.metric("VIX", vix.get("vix","-"))
vc4.metric("VIX9D/VIX", vix.get("vix9d_ratio","-"))
st.caption(f"VIX source: {vix.get('source','-')} • 4H divergence: {vix.get('div4h','-')} • 12H divergence: {vix.get('div12h','-')}")

st.divider()
ready=[r for r in rows if stage_of(r)=="READY"]
develop=[r for r in rows if stage_of(r)=="DEVELOPING"]
watch=[r for r in rows if stage_of(r)=="WATCH"]
other=[r for r in rows if stage_of(r)=="NO TRADE"]

for title,grp in [("🟢 READY",ready),("🟠 DEVELOPING",develop),("🟡 WATCH",watch),("⚪ NO TRADE / WAIT",other)]:
    if grp:
        st.header(title)
        for r in sorted(grp,key=lambda x:float(x.get("score",0)), reverse=True):
            render_card(r)

st.caption("Dashboard refreshes its cached scan about once per minute when the page is active. Streamlit Community Cloud is not a 24/7 always-on alert server; for continuous background alerts deploy the FastAPI worker separately.")
