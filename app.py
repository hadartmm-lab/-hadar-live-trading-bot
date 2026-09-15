from __future__ import annotations
import asyncio, json, os, time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from config import settings
from engine import analyze_symbol
from vix_engine import analyze_internal_vix, set_external
from notifier import telegram
from datafeeds import history_df
from backtest import backtest_frames

app=FastAPI(title='Hadar Live Trading Decision Engine')
app.mount('/static', StaticFiles(directory='static'), name='static')
STATE={'results':{},'vix':{},'last_scan':0,'errors':{}}
CLIENTS=set(); LAST_ALERT={}

class VixSignal(BaseModel):
    bias:str
    score:float=0.0

@app.get('/')
def home(): return FileResponse('static/index.html')

@app.get('/api/state')
def state(): return STATE

@app.post('/api/vix/external')
def vix_external(x:VixSignal):
    if x.bias not in ('risk_on','risk_off','neutral'): return JSONResponse({'error':'bias must be risk_on/risk_off/neutral'},400)
    return set_external(x.bias,x.score)

@app.get('/api/backtest/{asset_type}/{symbol}')
async def backtest_symbol(asset_type:str, symbol:str, days:int=365):
    asset_type=asset_type.lower(); symbol=symbol.upper(); days=max(120,min(days,730))
    if asset_type not in ('crypto','stock'):
        return JSONResponse({'error':'asset_type must be crypto or stock'},400)
    try:
        d1=await history_df(symbol,'1h',asset_type,days)
        d4=await history_df(symbol,'4h',asset_type,days)
        d12=await history_df(symbol,'12h',asset_type,days)
        dd=await history_df(symbol,'1d',asset_type,days)
        result=backtest_frames(d12,d4,d1,dd)
        result.update({'symbol':symbol,'asset_type':asset_type,'days_requested':days,'note':'Calibration backtest; excludes fees, slippage and execution latency.'})
        return result
    except Exception as e:
        return JSONResponse({'error':str(e)},500)

@app.post('/webhook/tradingview')
async def tradingview_webhook(payload:dict):
    # Store TV alerts as auxiliary evidence/event log without auto-trading.
    STATE.setdefault('tradingview_events',[]).append({'ts':int(time.time()),'payload':payload})
    STATE['tradingview_events']=STATE['tradingview_events'][-100:]
    return {'ok':True}

async def broadcast():
    dead=[]; msg=json.dumps(STATE,default=str)
    for ws in list(CLIENTS):
        try: await ws.send_text(msg)
        except: dead.append(ws)
    for ws in dead: CLIENTS.discard(ws)

async def maybe_alert(r):
    symbol=r['symbol']; direction=r['direction']; score=r['score']
    stage='NO_TRADE'
    if direction!='WAIT':
        if score>=settings.ready_score: stage='READY'
        elif score>=settings.developing_score: stage='DEVELOPING'
        elif score>=settings.watch_score: stage='WATCH'
    r['stage']=stage
    key=(direction,stage,int(score//5))
    if stage in ('DEVELOPING','READY') and LAST_ALERT.get(symbol)!=key:
        LAST_ALERT[symbol]=key
        await telegram(f'{symbol} | {stage} | {direction} | score {score}/100 | price {r["price"]}\n1H candles: {r["one_hour_candles"]}\nFib: {r["fib"].get("status")} {r["fib"].get("direction")}')

async def scan_loop():
    while True:
        try:
            v=await asyncio.to_thread(analyze_internal_vix); STATE['vix']=v
        except Exception as e:
            STATE['errors']['VIX']=str(e); v={'bias':'neutral'}
        jobs=[]
        for s in settings.crypto_symbols: jobs.append((s,'crypto'))
        for s in settings.stock_symbols: jobs.append((s,'stock'))
        for s,t in jobs:
            try:
                r=await analyze_symbol(s,t,v.get('bias','neutral'))
                await maybe_alert(r); STATE['results'][s]=r; STATE['errors'].pop(s,None)
            except Exception as e: STATE['errors'][s]=str(e)
        STATE['last_scan']=int(time.time()); await broadcast(); await asyncio.sleep(settings.scan_interval)

@app.on_event('startup')
async def startup(): asyncio.create_task(scan_loop())

@app.websocket('/ws')
async def ws(ws:WebSocket):
    await ws.accept(); CLIENTS.add(ws)
    try:
        await ws.send_text(json.dumps(STATE,default=str))
        while True: await ws.receive_text()
    except WebSocketDisconnect: CLIENTS.discard(ws)
