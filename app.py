from __future__ import annotations
import asyncio, time, math, html
import streamlit as st
from config import settings
from engine import analyze_symbol
from vix_engine import analyze_internal_vix

st.set_page_config(page_title='Hadar Alpha Arena', page_icon='⚡', layout='wide')

st.markdown(r"""
<style>
:root{
  --ink:#101828;--muted:#667085;--line:#e4e7ec;--panel:#ffffff;--bg:#f3f6fb;
  --green:#12b76a;--green-soft:#eafaf1;--red:#f04438;--red-soft:#fff0ef;
  --amber:#f79009;--amber-soft:#fff6e8;--blue:#2e90fa;--blue-soft:#eef6ff;
  --purple:#7f56d9;--purple-soft:#f4efff;--gray-soft:#f2f4f7;
}
html,body,[data-testid='stAppViewContainer']{background:linear-gradient(180deg,#eff4fa 0%,#f8fafc 100%)}
.block-container{max-width:1240px;padding-top:1.25rem;padding-bottom:2rem}
h1,h2,h3{letter-spacing:-.025em}.muted{color:var(--muted);font-size:.92rem}
.hero{position:relative;overflow:hidden;background:linear-gradient(135deg,#08111f 0%,#10213c 42%,#163f6d 100%);border:1px solid rgba(255,255,255,.10);border-radius:28px;padding:1.25rem 1.2rem;color:#fff;box-shadow:0 20px 40px rgba(15,23,42,.20);margin-bottom:1rem}
.hero:before{content:'';position:absolute;inset:auto -70px -90px auto;width:240px;height:240px;border-radius:50%;background:radial-gradient(circle,rgba(46,144,250,.35),rgba(46,144,250,0) 70%)}
.hero-title{font-size:2rem;font-weight:950;letter-spacing:-.04em;position:relative;z-index:1}.hero-sub{opacity:.84;font-size:.95rem;position:relative;z-index:1;max-width:900px}
.hero-strip{margin-top:.9rem;display:flex;gap:.45rem;flex-wrap:wrap;position:relative;z-index:1}
.pill{display:inline-block;border-radius:999px;padding:.34rem .7rem;font-size:.77rem;font-weight:850;border:1px solid transparent;margin-right:.25rem;margin-bottom:.25rem}
.p-green{background:var(--green-soft);color:#067647;border-color:#b7ebc5}.p-red{background:var(--red-soft);color:#b42318;border-color:#f8c1bd}.p-amber{background:var(--amber-soft);color:#b54708;border-color:#f6d39d}.p-blue{background:var(--blue-soft);color:#175cd3;border-color:#c7d7fe}.p-purple{background:var(--purple-soft);color:#6941c6;border-color:#d9d0ff}.p-gray{background:#f2f4f7;color:#344054;border-color:#d0d5dd}.p-dark{background:rgba(255,255,255,.10);color:white;border-color:rgba(255,255,255,.16)}
.section{font-size:1.08rem;font-weight:950;color:var(--ink);margin:.85rem 0 .2rem}.subsection{font-size:.9rem;color:var(--muted);margin-bottom:.55rem}
.panel{background:#fff;border:1px solid var(--line);border-radius:24px;padding:1rem;box-shadow:0 10px 26px rgba(16,24,40,.05);margin-bottom:.85rem}
.command-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:.85rem;align-items:stretch}
.command-left,.command-right{height:100%}
.metric-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.6rem}
.metric{background:linear-gradient(180deg,#fff,#fafcff);border:1px solid #eaecf0;border-radius:18px;padding:.8rem .85rem}
.metric-label{font-size:.73rem;color:var(--muted);margin-bottom:.12rem;letter-spacing:.02em}.metric-value{font-size:1.1rem;font-weight:950;color:var(--ink);line-height:1.2}
.top-target{background:linear-gradient(135deg,#0f172a 0%,#173a69 100%);color:#fff;border-radius:22px;padding:.95rem 1rem;display:flex;justify-content:space-between;gap:.8rem;align-items:flex-start;box-shadow:0 12px 24px rgba(15,23,42,.16)}
.top-title{font-size:.73rem;opacity:.76;margin-bottom:.14rem}.top-symbol{font-size:1.3rem;font-weight:950;line-height:1.08}.top-sub{font-size:.82rem;opacity:.84;margin-top:.18rem}.top-score{min-width:86px;height:86px;border-radius:22px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.12);display:flex;flex-direction:column;align-items:center;justify-content:center}.top-score-num{font-size:1.45rem;font-weight:950;line-height:1}.top-score-lab{font-size:.68rem;opacity:.75}
.status-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.6rem;margin-top:.75rem}.status{border-radius:18px;padding:.72rem;text-align:center;border:1px solid var(--line);background:#fff;box-shadow:0 6px 14px rgba(16,24,40,.03)}.status-name{font-size:.72rem;color:var(--muted);font-weight:800}.status-num{font-size:1.4rem;font-weight:950;color:var(--ink)}
.arena-card{background:#fff;border:1px solid var(--line);border-radius:24px;padding:1rem;margin:.75rem 0;box-shadow:0 12px 24px rgba(16,24,40,.055)}.arena-ready{border-color:#a9e9c0;background:linear-gradient(180deg,#f5fff9,#fff 44%)}.arena-developing{border-color:#f5cf91;background:linear-gradient(180deg,#fff9ef,#fff 44%)}.arena-watch{border-color:#bad7ff;background:linear-gradient(180deg,#f5faff,#fff 44%)}.arena-wait{border-color:#e5e7eb;background:linear-gradient(180deg,#fbfcfd,#fff 44%)}
.card-head{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap}.symbol-wrap{flex:1;min-width:210px}.symbol{font-size:1.58rem;font-weight:950;color:var(--ink);display:flex;align-items:center;gap:.45rem;flex-wrap:wrap}.rank{display:inline-flex;width:30px;height:30px;border-radius:10px;background:#0f172a;color:#fff;align-items:center;justify-content:center;font-size:.8rem;font-weight:900}.subtitle{font-size:.86rem;color:var(--muted);margin-top:.18rem}
.verdict{margin-top:.4rem;font-size:.92rem;font-weight:900;color:var(--ink)}
.power{min-width:92px;height:92px;border-radius:24px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff;box-shadow:0 10px 22px rgba(15,23,42,.16)}.power-elite{background:linear-gradient(145deg,#5a2bbd,#8b5cf6)}.power-strong{background:linear-gradient(145deg,#067647,#12b76a)}.power-building{background:linear-gradient(145deg,#b54708,#f79009)}.power-watch{background:linear-gradient(145deg,#175cd3,#2e90fa)}.power-low{background:linear-gradient(145deg,#667085,#98a2b3)}.power-score{font-size:1.55rem;font-weight:950;line-height:1}.power-label{font-size:.68rem;opacity:.82;margin-top:.18rem}
.summary-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.55rem;margin:.8rem 0}.summary{border:1px solid #eaecf0;background:#f8fafc;border-radius:16px;padding:.72rem}.s-label{font-size:.72rem;color:var(--muted)}.s-value{font-size:.98rem;font-weight:900;color:var(--ink);margin-top:.14rem;overflow-wrap:anywhere}
.quest{margin-top:.6rem;border:1px solid #e7eaf0;border-radius:16px;background:#fbfcfe;padding:.7rem .75rem}.quest-title{font-size:.74rem;font-weight:950;color:#475467;margin-bottom:.4rem}.quest-items{display:flex;gap:.38rem;flex-wrap:wrap}
.verdict-box{margin-top:.6rem;background:linear-gradient(180deg,#f8fbff,#fff);border:1px solid #d6e4ff;border-radius:16px;padding:.7rem .78rem}.verdict-title{font-size:.74rem;font-weight:950;color:#175cd3;margin-bottom:.18rem}.verdict-text{font-size:.95rem;color:#0f172a;font-weight:900}
.missing{margin-top:.6rem;background:#fff8ed;border:1px solid #f7d6a8;border-radius:16px;padding:.7rem .78rem}.missing-title{font-size:.74rem;font-weight:950;color:#b54708;margin-bottom:.18rem}.missing-text{font-size:.84rem;color:#7a2e0e}
.info-note{font-size:.82rem;color:var(--muted)}
[data-testid='stTabs'] button{font-weight:850;font-size:.83rem}[data-testid='stExpander'] details{border:1px solid #e5e7eb;border-radius:16px;background:#fff;overflow:hidden}[data-testid='stExpander'] details summary{background:#fcfcfd}
@media(max-width:900px){.command-grid{grid-template-columns:1fr}.metric-grid,.summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.status-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-title{font-size:1.68rem}.power{min-width:82px;height:82px;border-radius:22px}.power-score{font-size:1.28rem}}
</style>
""", unsafe_allow_html=True)


def esc(x):
    return html.escape(str(x))


def stage_of(r):
    if r.get('direction') == 'ERROR':
        return 'ERROR'
    if r.get('direction') in ('WAIT', None):
        return 'NO TRADE'
    s = float(r.get('score', 0))
    if s >= settings.ready_score:
        return 'READY'
    if s >= settings.developing_score:
        return 'DEVELOPING'
    if s >= settings.watch_score:
        return 'WATCH'
    return 'NO TRADE'


def cls_stage(stage):
    return {
        'READY':'arena-ready', 'DEVELOPING':'arena-developing', 'WATCH':'arena-watch',
        'NO TRADE':'arena-wait', 'ERROR':'arena-wait'
    }.get(stage, 'arena-wait')


def tone(x):
    return {
        'READY':'green','LONG':'green','RISK_ON':'green','DEVELOPING':'amber','WATCH':'blue',
        'SHORT':'red','RISK_OFF':'red','ERROR':'red','ELITE':'purple','STRONG':'green',
        'BUILDING':'amber','LOW':'gray','NO TRADE':'gray','WAIT':'gray','NEUTRAL':'gray'
    }.get(str(x).upper(),'gray')


def pill(txt, t=None, dark=False):
    return f"<span class='pill {'p-dark' if dark else 'p-'+(t or tone(txt))}'>{esc(txt)}</span>"


def fmt_price(x):
    if not isinstance(x,(int,float)) or math.isnan(x): return '-'
    if x >= 1000: return f'{x:,.2f}'
    if x >= 1: return f'{x:,.4f}'
    return f'{x:,.6f}'


def readable(v):
    return str(v).replace('_', ' ').title()


def power_class(power: str) -> str:
    return {
        'ELITE':'power-elite','STRONG':'power-strong','BUILDING':'power-building',
        'WATCH':'power-watch','LOW':'power-low'
    }.get(str(power).upper(),'power-low')


def verdict_text(r) -> str:
    stage = stage_of(r)
    direction = str(r.get('direction','WAIT')).upper()
    score = float(r.get('score',0))
    if stage == 'READY':
        return f'{direction} READY — setup is active now'
    if stage == 'DEVELOPING':
        return f'Building {direction} — close, but still waiting for confirmation'
    if stage == 'WATCH':
        return f'Watch {direction} — directional bias exists, but setup is incomplete'
    if stage == 'NO TRADE':
        if direction in ('LONG','SHORT') and score >= 40:
            return f'Wait for {direction} confirmation'
        return 'No clear trade yet'
    return 'Data issue — no trade decision'


def rsi_summary(r) -> str:
    d4 = (r.get('rsi_divergence_4h') or {}).get('type','none')
    d12 = (r.get('rsi_divergence_12h') or {}).get('type','none')
    if d4 == 'none' and d12 == 'none':
        return 'No confirmation'
    if d4 == d12 and d4 != 'none':
        return f'4H + 12H {d4}'
    parts = []
    if d4 != 'none': parts.append(f'4H {d4}')
    if d12 != 'none': parts.append(f'12H {d12}')
    return ' • '.join(parts) if parts else 'No confirmation'


def fib_summary(r) -> str:
    fib = r.get('fib', {}) or {}
    status = fib.get('status','none')
    direction = fib.get('direction','none')
    if status == 'healthy_pullback':
        return f'Healthy {direction}'
    if status == 'watch':
        return 'Watch zone'
    return 'No confirmation'


def target_side(r) -> str:
    return 'bullish' if r.get('long_score',0) >= r.get('short_score',0) else 'bearish'


def edge_summary(r) -> str:
    direction = str(r.get('direction','WAIT')).upper()
    gap = float(r.get('gap',0))
    score = float(r.get('score',0))
    if direction == 'WAIT':
        return 'Mixed'
    if gap >= 25 and score >= 75:
        return f'Strong {direction} bias'
    if gap >= 15:
        return f'Moderate {direction} bias'
    return f'Light {direction} bias'


def missing_summary(r) -> str:
    missing = r.get('missing_confirmations', []) or []
    if not missing:
        return 'No missing items.'
    return ' • '.join(missing[:3])


def checklist_pills(r):
    c = r.get('checklist', {})
    keys = [
        ('12H Trend', c.get('12h_structure')),
        ('4H Trend', c.get('4h_structure')),
        ('RSI 4H', c.get('rsi_div_4h')),
        ('RSI 12H', c.get('rsi_div_12h')),
        ('Fib', c.get('fib')),
        ('1H', c.get('candles_1h')),
    ]
    out = []
    target = target_side(r)
    for label, val in keys:
        sv = str(val or 'none').lower()
        ok = (target in sv) or (label == 'Fib' and 'healthy' in sv)
        out.append(pill(('✓ ' if ok else '○ ') + label, 'green' if ok else 'gray'))
    return ''.join(out)


@st.cache_data(ttl=45, show_spinner=False)
def scan_all_cached(_bucket:int):
    async def run():
        try:
            vix = await asyncio.to_thread(analyze_internal_vix)
        except Exception as e:
            vix = {'bias':'neutral','score':0,'source':'error','error':str(e)}

        async def one(symbol, asset_type):
            try:
                return await asyncio.wait_for(analyze_symbol(symbol, asset_type, vix.get('bias','neutral')), timeout=40)
            except asyncio.TimeoutError:
                return {'symbol':symbol,'asset_type':asset_type,'direction':'ERROR','score':0,'error':'Data source timeout'}
            except Exception as e:
                return {'symbol':symbol,'asset_type':asset_type,'direction':'ERROR','score':0,'error':str(e)}

        jobs = [one(s,'crypto') for s in settings.crypto_symbols] + [one(s,'stock') for s in settings.stock_symbols]
        return vix, list(await asyncio.gather(*jobs)), int(time.time())
    return asyncio.run(run())


def render_card(r, rank=None):
    stage = stage_of(r)
    direction = r.get('direction','-')
    score = float(r.get('score',0))
    power = r.get('setup_power','LOW')
    symbol = r.get('symbol','-')
    asset = 'CRYPTO' if r.get('asset_type') == 'crypto' else 'STOCK'
    icon = '₿' if asset == 'CRYPTO' else '◆'
    rank_html = f"<span class='rank'>{rank}</span>" if rank else ''
    verdict = verdict_text(r)

    st.markdown(f"""
    <div class='arena-card {cls_stage(stage)}'>
      <div class='card-head'>
        <div class='symbol-wrap'>
          <div class='symbol'>{rank_html}{icon} {esc(symbol)}</div>
          <div class='subtitle'>{esc(asset)}</div>
          <div class='verdict'>{esc(verdict)}</div>
          <div style='margin-top:.45rem'>{pill(stage)}{pill(direction)}{pill(power)}</div>
        </div>
        <div class='power {power_class(power)}'>
          <div class='power-score'>{score:.0f}</div>
          <div class='power-label'>SETUP POWER</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if 'error' in r:
        st.error(r['error'])
        return

    market_state = readable((r.get('market_regime_12h') or {}).get('regime','-'))
    st.markdown(f"""
    <div class='summary-grid'>
      <div class='summary'><div class='s-label'>Price</div><div class='s-value'>{fmt_price(r.get('price'))}</div></div>
      <div class='summary'><div class='s-label'>Market State</div><div class='s-value'>{esc(market_state)}</div></div>
      <div class='summary'><div class='s-label'>RSI Divergence</div><div class='s-value'>{esc(rsi_summary(r))}</div></div>
      <div class='summary'><div class='s-label'>Fib 0.50–0.618</div><div class='s-value'>{esc(fib_summary(r))}</div></div>
    </div>
    <div class='quest'>
      <div class='quest-title'>CONFIRMED CHECKLIST</div>
      <div class='quest-items'>{checklist_pills(r)}</div>
    </div>
    <div class='verdict-box'>
      <div class='verdict-title'>CURRENT VERDICT</div>
      <div class='verdict-text'>{esc(edge_summary(r))}</div>
    </div>
    """, unsafe_allow_html=True)

    missing = r.get('missing_confirmations', []) or []
    if missing:
        st.markdown(f"<div class='missing'><div class='missing-title'>NEXT MISSION — what is still missing</div><div class='missing-text'>{esc(missing_summary(r))}</div></div>", unsafe_allow_html=True)

    st.progress(min(max(score/100,0),1), text=f"Long {r.get('long_score','-')}  •  Short {r.get('short_score','-')}  •  1H candles: {str(r.get('one_hour_candles','-')).upper()}")

    with st.expander('Open tactical details'):
        a, b = st.columns(2)
        with a:
            st.markdown('**Structure & momentum**')
            st.write('12H regime:', r.get('market_regime_12h'))
            st.write('4H regime:', r.get('market_regime_4h'))
            st.write('12H BOS/CHoCH:', r.get('bos_12h'))
            st.write('4H BOS/CHoCH:', r.get('bos_4h'))
            st.write('RSI divergence 12H:', r.get('rsi_divergence_12h'))
            st.write('RSI divergence 4H:', r.get('rsi_divergence_4h'))
            st.write('Divergence sync:', r.get('divergence_sync'))
        with b:
            st.markdown('**Setup mechanics**')
            st.write('Fib:', r.get('fib'))
            st.write('Liquidity:', r.get('liquidity_sweep'))
            st.write('Pattern:', r.get('pattern'))
            st.write('Wyckoff:', r.get('wyckoff'))
            st.write('Support / resistance:', r.get('support_resistance'))
            st.write('4H volume ratio:', r.get('volume_ratio_4h'))
        st.markdown('**Why the score**')
        for reason in r.get('reasons', []):
            st.write('•', reason)
        st.markdown('**Data sources**')
        for tf, src in (r.get('sources') or {}).items():
            st.write(f'{tf}: {src}')


# Hero
st.markdown("""
<div class='hero'>
  <div class='hero-title'>⚡ Hadar Alpha Arena</div>
  <div class='hero-sub'>Game Premium decision engine • cleaner layout • 12H / 4H core • 1H candles only • no 15m • clearer verdicts and missing confirmations</div>
  <div class='hero-strip'>
    <span class='pill p-dark'>VIX Regime</span>
    <span class='pill p-dark'>RSI Divergence 4H + 12H</span>
    <span class='pill p-dark'>BOS / CHoCH</span>
    <span class='pill p-dark'>Smart Fib</span>
    <span class='pill p-dark'>Liquidity</span>
    <span class='pill p-dark'>Mission Checklist</span>
  </div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1.2, 1.35, 1])
with c1:
    mode = st.selectbox('Arena', ['All', 'Crypto only', 'Stocks only'])
with c2:
    sort_mode = st.selectbox('Priority', ['Highest Setup Power', 'LONG first', 'SHORT first', 'Alphabetical'])
with c3:
    st.write('')
    if st.button('⚡ RUN SCAN', use_container_width=True):
        st.cache_data.clear()

bucket = int(time.time() // 60)
with st.spinner('Reading market structure and building setup scores…'):
    vix, rows, ts = scan_all_cached(bucket)

if mode == 'Crypto only':
    rows = [r for r in rows if r.get('asset_type') == 'crypto']
elif mode == 'Stocks only':
    rows = [r for r in rows if r.get('asset_type') == 'stock']

ready = [r for r in rows if stage_of(r) == 'READY']
develop = [r for r in rows if stage_of(r) == 'DEVELOPING']
watch = [r for r in rows if stage_of(r) == 'WATCH']
wait = [r for r in rows if stage_of(r) == 'NO TRADE']
errors = [r for r in rows if stage_of(r) == 'ERROR']
valid = [r for r in rows if stage_of(r) != 'ERROR']


def ordered(xs):
    if sort_mode == 'Alphabetical':
        return sorted(xs, key=lambda r: r.get('symbol',''))
    if sort_mode == 'LONG first':
        return sorted(xs, key=lambda r: (r.get('direction') != 'LONG', -float(r.get('score',0))))
    if sort_mode == 'SHORT first':
        return sorted(xs, key=lambda r: (r.get('direction') != 'SHORT', -float(r.get('score',0))))
    return sorted(xs, key=lambda r: float(r.get('score',0)), reverse=True)

# Command center
st.markdown("<div class='section'>🎮 Command Center</div><div class='subsection'>Main market picture first. Then the closest target. Then the full arena.</div>", unsafe_allow_html=True)
bias = str(vix.get('bias','neutral')).upper()
leader = ordered(valid)[0] if valid else None
leader_dir = leader.get('direction','-') if leader else '-'
leader_power = leader.get('setup_power','-') if leader else '-'
leader_score = float(leader.get('score',0)) if leader else 0
leader_symbol = leader.get('symbol','-') if leader else '-'
leader_verdict = verdict_text(leader) if leader else 'No target yet'

st.markdown(f"""
<div class='command-grid'>
  <div class='panel command-left'>
    <div class='section' style='margin-top:0;margin-bottom:.5rem'>Market Regime</div>
    <div style='margin-bottom:.55rem'>{pill('VIX ' + bias)}{pill('VIX ' + str(vix.get('vix','-')),'gray')}{pill('VIX9D/VIX ' + str(vix.get('vix9d_ratio','-')),'gray')}</div>
    <div class='metric-grid'>
      <div class='metric'><div class='metric-label'>VIX Regime</div><div class='metric-value'>{esc(readable(bias))}</div></div>
      <div class='metric'><div class='metric-label'>VIX Score</div><div class='metric-value'>{esc(vix.get('score',0))}</div></div>
      <div class='metric'><div class='metric-label'>4H Divergence</div><div class='metric-value'>{esc(readable(vix.get('div4h','-')))}</div></div>
      <div class='metric'><div class='metric-label'>12H Divergence</div><div class='metric-value'>{esc(readable(vix.get('div12h','-')))}</div></div>
    </div>
  </div>
  <div class='top-target command-right'>
    <div>
      <div class='top-title'>Top Target Right Now</div>
      <div class='top-symbol'>{esc(leader_symbol)}</div>
      <div class='top-sub'>{esc(leader_verdict)}</div>
      <div style='margin-top:.45rem'>{pill(leader_dir, dark=True)} {pill(leader_power, dark=True)}</div>
    </div>
    <div class='top-score'>
      <div class='top-score-num'>{leader_score:.0f}</div>
      <div class='top-score-lab'>score</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class='status-grid'>
  <div class='status'><div class='status-name'>🟢 READY</div><div class='status-num'>{len(ready)}</div></div>
  <div class='status'><div class='status-name'>🟠 DEVELOPING</div><div class='status-num'>{len(develop)}</div></div>
  <div class='status'><div class='status-name'>🔵 WATCH</div><div class='status-num'>{len(watch)}</div></div>
  <div class='status'><div class='status-name'>⚪ WAIT</div><div class='status-num'>{len(wait)}</div></div>
  <div class='status'><div class='status-name'>⚠️ ERRORS</div><div class='status-num'>{len(errors)}</div></div>
</div>
""", unsafe_allow_html=True)

if errors:
    st.warning(f'⚠️ {len(errors)} data errors are separated from trade decisions.')

# Leaderboard
st.markdown("<div class='section'>🏆 Alpha Leaderboard</div><div class='subsection'>These are the 3 closest setups right now. They can appear here before they become READY.</div>", unsafe_allow_html=True)
for idx, r in enumerate(ordered(valid)[:3], 1):
    render_card(r, idx)
if not valid:
    st.info('No valid market data yet.')

# Full arena
st.markdown("<div class='section'>🗺️ Full Arena</div><div class='subsection'>Open only the stage you want. Heavy tactical detail stays hidden by default.</div>", unsafe_allow_html=True)
tabs = st.tabs([f'🟢 READY {len(ready)}', f'🟠 DEV {len(develop)}', f'🔵 WATCH {len(watch)}', f'⚪ WAIT {len(wait)}', f'⚠️ ERR {len(errors)}'])
for tab, grp in zip(tabs, [ready, develop, watch, wait, errors]):
    with tab:
        if not grp:
            st.info('Nothing here right now.')
        for r in ordered(grp):
            render_card(r)

st.caption('Game Premium v3.1 • Cleaner verdicts, simplified cards, clearer missing confirmations. Scores are analytical signals, not guarantees. Crypto fallback: Binance Vision → alternate Binance endpoints → Yahoo.')
