"""
BIST200 Teknik Analiz Botu — Web Arayüzü v2 (yfinance)
=======================================================
Veri kaynağı: Yahoo Finance (yfinance) — Streamlit Cloud uyumlu
Telegram kaldırıldı, tüm kontrol web üzerinden.
"""

import os, time, json, re, threading
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

import streamlit as st

# ─── SAYFA AYARLARI ────────────────────────────────────────────────
st.set_page_config(
    page_title="BIST200 Analiz Botu",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Sora:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'Sora', sans-serif; background:#0b0e17; color:#dde3f0; }
.stApp { background:#0b0e17; }
section[data-testid="stSidebar"] { background:#0f1320; border-right:1px solid #1d2540; }
div[data-testid="metric-container"] { background:#131929; border:1px solid #1d2540; border-radius:8px; padding:14px; }
.stButton > button { background:#00e676; color:#0b0e17; font-family:'JetBrains Mono',monospace;
    font-weight:700; border:none; border-radius:6px; padding:8px 20px; width:100%; }
.stButton > button:hover { background:#00c853; color:#0b0e17; }
div[data-baseweb="tab-list"] { background:#0f1320; border-bottom:1px solid #1d2540; }
div[data-baseweb="tab"] { font-family:'JetBrains Mono',monospace; color:#546e7a; }
div[aria-selected="true"] { color:#00e676 !important; border-bottom:2px solid #00e676 !important; }
.stTextInput>div>div>input, .stNumberInput>div>div>input {
    background:#131929 !important; border:1px solid #1d2540 !important; color:#dde3f0 !important; }
hr { border-color:#1d2540 !important; }
</style>
""", unsafe_allow_html=True)

# ─── KÜTÜPHANELER ──────────────────────────────────────────────────
try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    st.error("yfinance veya pandas yüklü değil. requirements.txt dosyasını kontrol et.")

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

# ─── YAPILANDIRMA ──────────────────────────────────────────────────
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

# ─── LOG DİZİNİ ────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(_SCRIPT_DIR, "bist_logs")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    _probe = os.path.join(LOG_DIR, ".write_test")
    with open(_probe, 'w') as _f: _f.write("ok")
    os.remove(_probe)
except Exception:
    LOG_DIR = os.path.join(os.path.expanduser("~"), "bist_logs")
    os.makedirs(LOG_DIR, exist_ok=True)

DAILY_LOG_FILE   = os.path.join(LOG_DIR, "gunluk_log.txt")
STRONG_BUY_LOG   = os.path.join(LOG_DIR, "guclu_al_log.txt")
STATE_FILE       = os.path.join(LOG_DIR, "state.json")
STONKS_FILE      = os.path.join(LOG_DIR, "stonks.json")
MODEL_USAGE_FILE = os.path.join(LOG_DIR, "model_usage.json")

# ─── MODEL KOTALARI ────────────────────────────────────────────────
MODEL_DAILY_LIMITS = {
    "gemini-2.5-pro":        20,
    "gemini-2.5-flash":      20,
    "gemini-2.5-flash-lite": 100,
    "gemma-3-27b-it":        14400,
}
CHAIN_AIANALIZ = ["gemini-2.5-flash-lite","gemini-2.5-flash","gemma-3-27b-it"]
CHAIN_AIGUCLU  = ["gemini-2.5-pro","gemini-2.5-flash","gemini-2.5-flash-lite","gemma-3-27b-it"]

# ─── BIST HİSSE LİSTESİ ────────────────────────────────────────────
QUICK_TICKERS = [
    "THYAO","GARAN","AKBNK","ISCTR","EREGL","KCHOL","SAHOL","SISE",
    "TCELL","BIMAS","TUPRS","FROTO","ARCLK","TOASO","ASELS","YKBNK",
    "VAKBN","HALKB","SKBNK","EKGYO","KOZAL","SASA","PETKM","TKFEN",
    "TTKOM","TAVHL","PGSUS","MGROS","OTKAR","MAVI","DOHOL","CCOLA",
    "ENKAI","GUBRF","HEKTS","TSKB","TTRAK","ULKER","VESTL","ZOREN",
]

FULL_TICKERS = sorted(list(set(QUICK_TICKERS + [
    "AEFES","AGESA","AGHOL","AKBNK","AKCNS","AKSA","AKSEN","ALARK",
    "ALBRK","ANSGR","ARCLK","ASELS","ASTOR","ASUZU","BERA","BRSAN",
    "BRYAT","CIMSA","CLEBI","DOAS","ECILC","ECZYT","ENJSA","EUPWR",
    "GESAN","ISMEN","KARSN","KAYSE","KONTR","KONYA","KRDMD","KTLEV",
    "MIATK","MPARK","OBASE","ODAS","OYAKC","REEDR","SMRTG","SOKM",
    "TABGD","ADEL","AKGRT","ALKIM","ARDYZ","ARENA","AYGAZ","BAGFS",
    "BANVT","BIZIM","BOSSA","BRISA","DEVA","EMKEL","FONET","GLYHO",
    "GOODY","GRSEL","HATEK","IHLAS","INDES","INFO","ISFIN","ISGYO",
    "JANTS","KAREL","KARTN","KERVT","KLGYO","KLKIM","KONKA","KORDS",
    "LOGO","MARTI","MEPET","MERKO","NETAS","PARSN","PENTA","PETUN",
    "PNSUT","POLHO","RYSAS","SARKY","SELEC","SNGYO","TATGD","TMSN",
    "TRGYO","ULUSE","VAKKO","VKGYO","YATAS","YUNSA","EGEEN","KRDMA",
])))

def to_yf(t): return f"{t}.IS"

# ══════════════════════════════════════════════════════════════════
# TEKNİK İNDİKATÖR HESAPLAMA
# ══════════════════════════════════════════════════════════════════
def calc_rsi(s, p=14):
    d = s.diff(); g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    rs = g / l.replace(0, float('nan'))
    return 100 - (100 / (1 + rs))

def calc_ema(s, n): return s.ewm(span=n, adjust=False).mean()

def calc_macd(s):
    m = calc_ema(s,12) - calc_ema(s,26)
    return m, calc_ema(m,9)

def calc_bb(s, p=20, k=2):
    sma = s.rolling(p).mean(); std = s.rolling(p).std()
    return sma+k*std, sma, sma-k*std

def calc_atr(h, l, c, p=14):
    tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def calc_adx(h, l, c, p=14):
    try:
        atr = calc_atr(h,l,c,p)
        dp = (h.diff()).clip(lower=0); dm = (-l.diff()).clip(lower=0)
        dp[dp<dm]=0; dm[dm<dp]=0
        a14 = atr.rolling(p).mean()
        dip = 100*dp.rolling(p).mean()/a14.replace(0,float('nan'))
        dim = 100*dm.rolling(p).mean()/a14.replace(0,float('nan'))
        dx  = 100*(dip-dim).abs()/(dip+dim).replace(0,float('nan'))
        return dx.rolling(p).mean()
    except: return pd.Series([20.0]*len(c), index=c.index)

# ══════════════════════════════════════════════════════════════════
# VERİ ÇEKME
# ══════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def fetch_ohlcv(ticker_raw, period="3mo"):
    try:
        df = yf.download(to_yf(ticker_raw), period=period, interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 20: return None
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        return df
    except: return None

# ══════════════════════════════════════════════════════════════════
# ANALİZ
# ══════════════════════════════════════════════════════════════════
def analyze_stock(ticker_raw):
    if not YF_AVAILABLE: return None
    df = fetch_ohlcv(ticker_raw)
    if df is None or len(df) < 20: return None
    try:
        close = df['Close'].squeeze()
        high  = df['High'].squeeze()
        low   = df['Low'].squeeze()
        vol   = df['Volume'].squeeze()

        price    = float(close.iloc[-1])
        prev     = float(close.iloc[-2]) if len(close)>1 else price
        d_change = (price-prev)/prev*100
        w_price  = float(close.iloc[-6]) if len(close)>5 else float(close.iloc[0])
        w_change = (price-w_price)/w_price*100

        rsi_s    = calc_rsi(close)
        rsi      = float(rsi_s.iloc[-1]) if not pd.isna(rsi_s.iloc[-1]) else 50.0
        ema20    = float(calc_ema(close,20).iloc[-1])
        ema50    = float(calc_ema(close,50).iloc[-1])
        ema200   = float(calc_ema(close,min(200,len(close)-1)).iloc[-1])
        macd_s,msig_s = calc_macd(close)
        macd     = float(macd_s.iloc[-1])
        macd_sig = float(msig_s.iloc[-1])
        bb_u,_,bb_l = calc_bb(close)
        bb_upper = float(bb_u.iloc[-1])
        bb_lower = float(bb_l.iloc[-1])
        atr_s    = calc_atr(high,low,close)
        atr      = float(atr_s.iloc[-1]) if not pd.isna(atr_s.iloc[-1]) else price*0.02
        adx_s    = calc_adx(high,low,close)
        adx      = float(adx_s.iloc[-1]) if not pd.isna(adx_s.iloc[-1]) else 20.0

        low14  = low.rolling(14).min()
        high14 = high.rolling(14).max()
        stoch_k = float(100*(close.iloc[-1]-float(low14.iloc[-1]))/(float(high14.iloc[-1])-float(low14.iloc[-1])+1e-10))

        avg_vol  = float(vol.rolling(20).mean().iloc[-1])
        last_vol = float(vol.iloc[-1])

        score=0; signals=[]

        if rsi<30:   signals.append("RSI Aşırı Satım ✅"); score+=2
        elif rsi<45: signals.append("RSI Düşük ✅");        score+=1
        elif rsi>70: signals.append("RSI Aşırı Alım ❌");  score-=2
        elif rsi>55: signals.append("RSI Yüksek ❌");      score-=1

        if price>ema20:  signals.append("EMA20 üstü ✅"); score+=1
        else:            signals.append("EMA20 altı ❌");  score-=1
        if price>ema50:  signals.append("EMA50 üstü ✅"); score+=1
        else:            signals.append("EMA50 altı ❌");  score-=1
        if price>ema200: signals.append("EMA200 üstü ✅"); score+=1
        else:            signals.append("EMA200 altı ❌");  score-=1

        if macd>macd_sig: signals.append("MACD Pozitif ✅"); score+=1
        else:             signals.append("MACD Negatif ❌"); score-=1

        if price<bb_lower:   signals.append("BB Alt Band ✅"); score+=1
        elif price>bb_upper: signals.append("BB Üst Band ❌"); score-=1

        if stoch_k<20:   signals.append("Stoch Aşırı Satım ✅"); score+=1
        elif stoch_k>80: signals.append("Stoch Aşırı Alım ❌");  score-=1

        if adx>25:
            t='✅' if score>0 else '❌'
            signals.append(f"ADX Güçlü Trend ({adx:.0f}) {t}")
            score+=1 if score>0 else -1

        if avg_vol>0:
            if last_vol>avg_vol*1.5 and d_change>0:
                signals.append("Hacim + Yükseliş ✅"); score+=1
            elif last_vol>avg_vol*1.5 and d_change<0:
                signals.append("Hacim + Düşüş ❌"); score-=1

        stop=price-1.5*atr; target1=price+2.5*atr; target2=bb_upper
        rr1=(target1-price)/(price-stop) if (price-stop)>0 else 0

        if score>=6:    signal="🟢 GÜÇLÜ AL"
        elif score>=3:  signal="🔵 AL"
        elif score>=1:  signal="🔷 ZAYIF AL"
        elif score<=-6: signal="🔴 GÜÇLÜ SAT"
        elif score<=-3: signal="🟠 SAT"
        elif score<=-1: signal="🟡 ZAYIF SAT"
        else:           signal="⚪ NÖTR"

        return {
            'ticker':ticker_raw,'price':round(price,2),'d_change':round(d_change,2),
            'w_change':round(w_change,2),'rsi':round(rsi,1),'ema20':round(ema20,2),
            'ema50':round(ema50,2),'ema200':round(ema200,2),'atr':round(atr,2),
            'adx':round(adx,1),'score':score,'signal':signal,'sigs':signals,
            'stop':round(stop,2),'target1':round(target1,2),'target2':round(target2,2),
            'rr1':round(rr1,2),'bb_upper':round(bb_upper,2),'bb_lower':round(bb_lower,2),
            'volume':int(last_vol),'avg_volume':int(avg_vol),
        }
    except: return None

def scan_tickers(tickers, progress_cb=None):
    results=[]
    n=len(tickers)
    for i,t in enumerate(tickers):
        if progress_cb: progress_cb((i+1)/n, f"Tarıyor: {t} ({i+1}/{n})")
        r=analyze_stock(t)
        if r: results.append(r)
        if i%10==9: time.sleep(0.3)
    return results

# ══════════════════════════════════════════════════════════════════
# LOG KAYDETME
# ══════════════════════════════════════════════════════════════════
def save_daily_log(results):
    if not results: return
    try:
        now_str=datetime.now().strftime("%d.%m.%Y %H:%M")
        lines=[f"\n{'='*60}",f"TARAMA ZAMANI : {now_str}",f"TARANAN : {len(results)} hisse","="*60]
        for sec,mn,mx in [("[ GUCLU AL ]",6,99),("[ AL ]",3,5),("[ SAT ]",-5,-3),("[ GUCLU SAT ]",-99,-6)]:
            items=sorted([r for r in results if mn<=r['score']<=mx],key=lambda x:x['score'],reverse=(mn>0))
            if not items: continue
            lines+=["",sec,f"{'HISSE':<8} {'FIYAT':>8} {'HEDEF':>8} {'STOP':>8} {'RR':>5} {'GUN%':>7} {'HAF%':>7} {'RSI':>5} {'ADX':>5}  SINYAL","-"*80]
            for r in items:
                lines.append(f"{r['ticker']:<8} {r['price']:>8.2f} {r['target1']:>8.2f} {r['stop']:>8.2f} {r['rr1']:>5.2f} {r['d_change']:>+7.1f}% {r['w_change']:>+7.1f}% {r['rsi']:>5.1f} {r['adx']:>5.1f}  {r['signal']}")
        with open(DAILY_LOG_FILE,'a',encoding='utf-8') as f: f.write("\n".join(lines)+"\n")
        strong=[r for r in results if r['score']>=6]
        if strong:
            with open(STRONG_BUY_LOG,'a',encoding='utf-8') as f:
                f.write(f"\n[{now_str}] GÜÇLÜ AL ({len(strong)} hisse):\n")
                for r in sorted(strong,key=lambda x:x['score'],reverse=True):
                    f.write(f"  {r['ticker']:8s} {r['price']:8.2f}₺  skor:{r['score']}  RSI:{r['rsi']}  {r['signal']}\n")
    except: pass

def save_state(results):
    try:
        with open(STATE_FILE,'w',encoding='utf-8') as f:
            json.dump({'saved_at':datetime.now().strftime("%d.%m.%Y %H:%M"),
                       'last_results':results,'scan_day':datetime.now().strftime("%Y-%m-%d")},f,ensure_ascii=False)
    except: pass

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE,'r',encoding='utf-8') as f: return json.load(f)
    except: pass
    return {}

# ── Başlangıçta önceki taramayı yükle
if 'last_results' not in st.session_state:
    s = load_state()
    if s.get('last_results'):
        today = datetime.now().strftime("%Y-%m-%d")
        if s.get('scan_day') == today:
            st.session_state['last_results'] = s['last_results']
            st.session_state['last_scan_time'] = s.get('saved_at','?')

# ══════════════════════════════════════════════════════════════════
# GEMİNİ AI
# ══════════════════════════════════════════════════════════════════
_NEWS_FEEDS = ["https://bigpara.hurriyet.com.tr/rss/borsa.xml","https://www.bloomberght.com/rss"]

def get_news():
    if not FEEDPARSER_AVAILABLE: return "(Haber yüklenemedi)"
    h=[]
    for url in _NEWS_FEEDS:
        try:
            p=feedparser.parse(url)
            for e in p.entries[:5]:
                t=(e.get("title") or "").strip()
                if t and t not in h: h.append(t)
                if len(h)>=8: break
        except: pass
        if len(h)>=8: break
    return "\n".join(f"- {x}" for x in h) or "(Haber alınamadı)"

def _load_model_counts():
    today=datetime.now().strftime("%Y-%m-%d")
    try:
        if os.path.exists(MODEL_USAGE_FILE):
            with open(MODEL_USAGE_FILE,'r',encoding='utf-8') as f:
                data=json.load(f)
            if data.get('date')==today: return data.get('counts',{})
    except: pass
    return {}

def _save_model_counts(c):
    try:
        with open(MODEL_USAGE_FILE,'w',encoding='utf-8') as f:
            json.dump({'date':datetime.now().strftime("%Y-%m-%d"),'counts':c},f,indent=2)
    except: pass

def get_model_count(m): return int(_load_model_counts().get(m,0))
def model_has_quota(m): return get_model_count(m)<MODEL_DAILY_LIMITS.get(m,20)
def increment_model(m):
    c=_load_model_counts(); c[m]=int(c.get(m,0))+1; _save_model_counts(c); return c[m]
def is_gemma(m): return bool(m) and m.lower().startswith("gemma")

def gemini_analyze(results, mode="analiz"):
    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        return None,"Gemini API key ayarlanmamış. Sidebar'a ekle."
    min_s=7 if mode=="analiz" else 8
    chain=CHAIN_AIGUCLU if mode=="guclu" else CHAIN_AIANALIZ
    strong=sorted([r for r in results if r['score']>=min_s],key=lambda x:x['score'],reverse=True)[:10]
    if not strong: return None,f"Skor ≥ {min_s} olan hisse yok. Önce tarama yap."
    stock_data="\n".join([f"{r['ticker']}: fiyat={r['price']}₺ skor={r['score']} RSI={r['rsi']} ADX={r['adx']} hedef={r['target1']}₺ stop={r['stop']}₺ RR={r['rr1']}" for r in strong])
    prompt=f"""Kıdemli Türkiye borsa analistisin.

HABERLER:
{get_news()}

TEKNİK VERİLER (skor≥{min_s}):
{stock_data}

Sadece JSON döndür:
{{"piyasa_ozeti":"1-2 cümle","piyasa_rengi":"POZITIF|NEGATIF|NOTR",
"top_hisseler":[{{"hisse":"THYAO","guven":8,"anahtar_kelime":"Momentum","neden":"max 80 karakter","beklenti":"kısa vade","hedef_yuzde":"+4-7%","risk":"ORTA","gundem_etkisi":"max 80 karakter"}}],
"genel_uyari":"kısa risk notu"}}"""
    client=genai.Client(api_key=GEMINI_API_KEY)
    active=[m for m in chain if model_has_quota(m)] or [chain[0]]
    for model in active:
        try:
            cfg=None if is_gemma(model) else types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=0))
            kw={"model":model,"contents":prompt}
            if cfg: kw["config"]=cfg
            r=client.models.generate_content(**kw)
            increment_model(model)
            return r.text,f"✅ {model} ({get_model_count(model)}/{MODEL_DAILY_LIMITS.get(model,20)})"
        except: continue
    return None,"Tüm modeller meşgul veya kota doldu."

def parse_ai_json(raw):
    if not raw: return None
    t=re.sub(r'^```(?:json)?\s*','',raw.strip()); t=re.sub(r'\s*```$','',t)
    s,e=t.find('{'),t.rfind('}')
    if s<0 or e<0: return None
    try: return json.loads(t[s:e+1])
    except: return None

# ══════════════════════════════════════════════════════════════════
# STONKS
# ══════════════════════════════════════════════════════════════════
def stonks_load():
    try:
        if os.path.exists(STONKS_FILE):
            with open(STONKS_FILE,'r',encoding='utf-8') as f: return json.load(f)
    except: pass
    return {}

def stonks_save(data):
    with open(STONKS_FILE,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def get_current_price(t):
    try:
        df=fetch_ohlcv(t,period="5d")
        if df is not None and len(df)>0: return float(df['Close'].squeeze().iloc[-1])
    except: pass
    return None

# ══════════════════════════════════════════════════════════════════
# OTOMATİK TARAMA
# ══════════════════════════════════════════════════════════════════
def _auto_loop():
    while st.session_state.get('auto_scan_enabled',False):
        now=datetime.now()
        is_market=(now.weekday()<5 and ((now.hour==9 and now.minute>=50) or (10<=now.hour<=17) or (now.hour==18 and now.minute<=0)))
        if is_market and YF_AVAILABLE:
            st.session_state['auto_scan_running']=True
            res=scan_tickers(QUICK_TICKERS)
            if res:
                st.session_state['last_results']=res
                st.session_state['last_scan_time']=datetime.now().strftime("%H:%M:%S")
                save_daily_log(res); save_state(res)
            st.session_state['auto_scan_running']=False
            time.sleep(300)
        else:
            time.sleep(60)

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<p style="font-family:JetBrains Mono,monospace;font-size:22px;color:#00e676;font-weight:700;letter-spacing:3px;">📈 BIST200</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#546e7a;font-size:11px;">v2 · Yahoo Finance</p>', unsafe_allow_html=True)
    st.divider()

    api_key_input=st.text_input("🔑 Gemini API Key",value=GEMINI_API_KEY,type="password",placeholder="AIza...")
    if api_key_input: GEMINI_API_KEY=api_key_input
    st.divider()

    st.markdown("**📁 bist_logs/**")
    try:
        lf=[f for f in os.listdir(LOG_DIR) if os.path.isfile(os.path.join(LOG_DIR,f))]
        for fname in sorted(lf):
            fsize=os.path.getsize(os.path.join(LOG_DIR,fname))
            st.caption(f"📄 {fname} ({fsize/1024:.1f} KB)")
        if not lf: st.caption("(henüz log yok)")
    except: st.caption("(log klasörü bulunamadı)")

    st.divider()
    auto_scan=st.toggle("🔄 Otomatik Tarama (Borsa saati)",value=st.session_state.get('auto_scan_enabled',False))
    st.session_state['auto_scan_enabled']=auto_scan
    if auto_scan and not st.session_state.get('auto_thread_started',False):
        threading.Thread(target=_auto_loop,daemon=True).start()
        st.session_state['auto_thread_started']=True

    if st.session_state.get('auto_scan_running',False):
        st.markdown('<span style="color:#ffd740;font-family:monospace;">⚡ TARAMA ÇALIŞIYOR...</span>',unsafe_allow_html=True)
    if st.session_state.get('last_scan_time'):
        st.caption(f"Son tarama: {st.session_state['last_scan_time']}")
    st.divider()
    st.caption("⚠️ Yatırım tavsiyesi değildir.")

# ══════════════════════════════════════════════════════════════════
# ANA İÇERİK
# ══════════════════════════════════════════════════════════════════
st.markdown('<p style="font-family:JetBrains Mono,monospace;font-size:24px;color:#dde3f0;font-weight:700;">BIST200 Teknik Analiz Paneli</p>', unsafe_allow_html=True)

results=st.session_state.get('last_results',[])
if results:
    c1,c2,c3,c4=st.columns(4)
    c1.metric("🟢 Güçlü AL",  sum(1 for r in results if r['score']>=6))
    c2.metric("🔵 AL",        sum(1 for r in results if 3<=r['score']<6))
    c3.metric("🟠 SAT",       sum(1 for r in results if -6<r['score']<=-3))
    c4.metric("🔴 Güçlü SAT", sum(1 for r in results if r['score']<=-6))
    st.divider()

tab1,tab2,tab3,tab4,tab5=st.tabs(["🔍 Tarama","📊 Tek Hisse","🤖 AI Analiz","💼 Portföy","📋 Log"])

# ── TAB 1: TARAMA ─────────────────────────────────────────────────
with tab1:
    st.markdown("#### BIST200 Tarama")
    if not YF_AVAILABLE:
        st.error("yfinance yüklü değil!")
    else:
        col_a,col_b,col_c=st.columns(3)
        run_quick=col_a.button("⚡ HIZLI TARA (~40 hisse, ~1 dk)")
        run_full =col_b.button("🔍 TAM TARA (~120 hisse, ~4 dk)")

        if run_quick or run_full:
            tickers=QUICK_TICKERS if run_quick else FULL_TICKERS
            prog=st.progress(0,"Başlıyor...")
            def _cb(pct,msg): prog.progress(pct,msg)
            res=scan_tickers(tickers,progress_cb=_cb)
            prog.empty()
            if res:
                st.session_state['last_results']=res
                st.session_state['last_scan_time']=datetime.now().strftime("%H:%M:%S")
                save_daily_log(res); save_state(res)
                st.success(f"✅ {len(res)} hisse analiz edildi — bist_logs'a kaydedildi!")
            else:
                st.error("Veri alınamadı. Biraz bekleyip tekrar dene.")

        results=st.session_state.get('last_results',[])
        if results:
            cf1,cf2,cf3=st.columns(3)
            filtre  =cf1.selectbox("Filtre",["Hepsi","Güçlü AL","AL","SAT","Güçlü SAT"])
            sort_by =cf2.selectbox("Sırala",["Skor","RSI","RR"])
            min_sc  =cf3.slider("Min Skor",-10,10,-10)

            filtered=results
            if filtre=="Güçlü AL":    filtered=[r for r in results if r['score']>=6]
            elif filtre=="AL":        filtered=[r for r in results if 3<=r['score']<6]
            elif filtre=="SAT":       filtered=[r for r in results if -6<r['score']<=-3]
            elif filtre=="Güçlü SAT": filtered=[r for r in results if r['score']<=-6]
            filtered=[r for r in filtered if r['score']>=min_sc]

            if sort_by=="RSI":  filtered.sort(key=lambda x:x['rsi'])
            elif sort_by=="RR": filtered.sort(key=lambda x:x['rr1'],reverse=True)
            else:               filtered.sort(key=lambda x:x['score'],reverse=True)

            st.caption(f"{len(filtered)} hisse · Son tarama: {st.session_state.get('last_scan_time','')}")

            df_show=pd.DataFrame([{
                "Hisse":r['ticker'],"Fiyat (₺)":r['price'],"Sinyal":r['signal'],
                "Skor":r['score'],"RSI":r['rsi'],"ADX":r['adx'],
                "Hedef (₺)":r['target1'],"Stop (₺)":r['stop'],"RR":r['rr1'],
                "Gün %":r['d_change'],"Hafta %":r['w_change'],
            } for r in filtered])

            def csig(v):
                if "GÜÇLÜ AL" in str(v): return "color:#00e676;font-weight:bold"
                if "AL" in str(v): return "color:#40c4ff"
                if "GÜÇLÜ SAT" in str(v): return "color:#ff1744;font-weight:bold"
                if "SAT" in str(v): return "color:#ff6d00"
                return "color:#90a4ae"

            st.dataframe(df_show.style.applymap(csig,subset=["Sinyal"]),
                         use_container_width=True,height=480)
        else:
            st.info("⚡ HIZLI TARA'ya bas — ~1 dakikada sonuç alırsın.")

# ── TAB 2: TEK HİSSE ──────────────────────────────────────────────
with tab2:
    st.markdown("#### Tek Hisse Detay Analizi")
    h1,h2=st.columns([2,1])
    ticker_in=h1.text_input("Sembol",placeholder="THYAO, GARAN...").upper().strip()
    abtn=h2.button("📊 ANALİZ ET")
    if abtn and ticker_in:
        with st.spinner(f"{ticker_in} analiz ediliyor..."):
            r=analyze_stock(ticker_in)
        if r:
            m1,m2,m3,m4=st.columns(4)
            m1.metric("Fiyat",f"{r['price']:.2f} ₺",f"{r['d_change']:+.2f}%")
            m2.metric("Sinyal",r['signal'])
            m3.metric("Skor",r['score'])
            m4.metric("RSI",r['rsi'])
            st.divider()
            m5,m6,m7=st.columns(3)
            m5.metric("🎯 Hedef",f"{r['target1']:.2f} ₺",f"+{((r['target1']-r['price'])/r['price']*100):.1f}%")
            m6.metric("🛑 Stop", f"{r['stop']:.2f} ₺", f"-{((r['price']-r['stop'])/r['price']*100):.1f}%")
            m7.metric("⚖️ RR",f"{r['rr1']:.2f}x")
            st.divider()
            m8,m9,m10=st.columns(3)
            m8.metric("ADX",r['adx']); m9.metric("EMA20",r['ema20']); m10.metric("EMA50",r['ema50'])
            st.markdown("**Sinyal detayları:**")
            for s in r['sigs']: st.markdown(f"- {s}")

            if PLOTLY_OK:
                with st.spinner("Grafik yükleniyor..."):
                    df_c=fetch_ohlcv(ticker_in,period="3mo")
                if df_c is not None:
                    cl=df_c['Close'].squeeze()
                    fig=go.Figure()
                    fig.add_trace(go.Candlestick(x=df_c.index,open=df_c['Open'].squeeze(),
                        high=df_c['High'].squeeze(),low=df_c['Low'].squeeze(),close=cl,
                        increasing_line_color='#00e676',decreasing_line_color='#ff1744',
                        increasing_fillcolor='#00e676',decreasing_fillcolor='#ff1744'))
                    fig.add_trace(go.Scatter(x=df_c.index,y=cl.ewm(span=20,adjust=False).mean(),name="EMA20",line=dict(color='#ffd740',width=1)))
                    fig.add_trace(go.Scatter(x=df_c.index,y=cl.ewm(span=50,adjust=False).mean(),name="EMA50",line=dict(color='#40c4ff',width=1)))
                    fig.update_layout(height=320,paper_bgcolor='#131929',plot_bgcolor='#131929',
                        font=dict(color='#dde3f0'),xaxis_rangeslider_visible=False,
                        xaxis=dict(gridcolor='#1d2540'),yaxis=dict(gridcolor='#1d2540'),
                        margin=dict(l=0,r=0,t=20,b=0))
                    st.plotly_chart(fig,use_container_width=True)
        else:
            st.error(f"'{ticker_in}' için veri alınamadı. Örnek: THYAO, GARAN, EREGL")

# ── TAB 3: AI ANALİZ ──────────────────────────────────────────────
with tab3:
    st.markdown("#### 🤖 Gemini AI Analizi")
    if not GEMINI_API_KEY:
        st.warning("Gemini API key gerekli. Sidebar'a ekle veya Streamlit Secrets'a `GEMINI_API_KEY` tanımla.")
    results=st.session_state.get('last_results',[])
    if not results:
        st.info("Önce 'Tarama' sekmesinden tarama yap.")
    else:
        a1,a2=st.columns(2)
        b1=a1.button("🧠 AI ANALİZ (skor≥7)"); b2=a2.button("🏆 AI GÜÇLÜ (skor≥8)")
        mode="analiz" if b1 else ("guclu" if b2 else None)
        if mode:
            with st.spinner("Gemini analiz yapıyor..."):
                raw,info=gemini_analyze(results,mode=mode)
            st.caption(f"Model: {info}")
            if raw:
                data=parse_ai_json(raw)
                if data:
                    renk=data.get("piyasa_rengi","NOTR")
                    em={"POZITIF":"🟢","NEGATIF":"🔴","NOTR":"⚪"}.get(renk,"⚪")
                    st.markdown(f"### {em} {data.get('piyasa_ozeti','')}")
                    st.divider()
                    for i,h in enumerate(data.get("top_hisseler",[]),1):
                        ca,cb=st.columns([1,3])
                        ca.markdown(f"**#{i} {h.get('hisse','')}**")
                        ca.metric("Güven",f"{h.get('guven',0)}/10")
                        ca.caption(f"Risk: {h.get('risk','')}")
                        cb.markdown(f"🔑 *{h.get('anahtar_kelime','')}*")
                        cb.markdown(f"📌 {h.get('neden','')}")
                        cb.markdown(f"📈 {h.get('beklenti','')} — **{h.get('hedef_yuzde','')}**")
                        cb.caption(f"📰 {h.get('gundem_etkisi','')}")
                        st.divider()
                    if data.get("genel_uyari"): st.warning(f"⚠️ {data['genel_uyari']}")
                else:
                    st.markdown(raw)
            else:
                st.error(info)
        with st.expander("📊 Model Kotaları"):
            for m,lim in MODEL_DAILY_LIMITS.items():
                c=get_model_count(m)
                st.progress(min(c/lim,1.0),text=f"{m}: {c}/{lim}")

# ── TAB 4: PORTFÖY ────────────────────────────────────────────────
with tab4:
    st.markdown("#### 💼 Sanal Portföy")
    with st.expander("➕ Yeni Yatırım Ekle"):
        pp1,pp2,pp3=st.columns(3)
        pt=pp1.text_input("Hisse",placeholder="THYAO").upper()
        pa=pp2.number_input("Tutar (₺)",min_value=100.0,value=10000.0,step=100.0)
        pb=pp3.button("Ekle",key="addbtn")
        if pb and pt:
            with st.spinner("Fiyat alınıyor..."):
                px=get_current_price(pt)
            if px:
                d=stonks_load()
                if "default" not in d: d["default"]=[]
                d["default"].append({"ticker":pt,"amount":pa,"buy_price":round(px,2),
                    "shares":round(pa/px,4),"date":datetime.now().strftime("%d.%m.%Y %H:%M")})
                stonks_save(d); st.success(f"✅ {pt} eklendi! Alış: {px:.2f}₺")
            else:
                st.error("Fiyat alınamadı.")

    portfolio=stonks_load().get("default",[])
    if not portfolio:
        st.info("Portföy boş.")
    else:
        ti=tc=0
        for e in portfolio:
            cpx=get_current_price(e["ticker"]) or e["buy_price"]
            cv=e["shares"]*cpx; pr=cv-e["amount"]; pct=(pr/e["amount"])*100
            ti+=e["amount"]; tc+=cv
            ico="🟢" if pr>=0 else "🔴"
            ea,eb,ec,ed=st.columns([1,2,2,1])
            ea.markdown(f"**{ico} {e['ticker']}**")
            eb.metric("Alış/Güncel",f"{e['buy_price']:.2f}₺",f"{cpx:.2f}₺")
            ec.metric("K/Z",f"{pr:+,.0f}₺",f"{pct:+.1f}%")
            if ed.button("🗑",key=f"d_{e['ticker']}_{e['date']}"):
                dd=stonks_load(); dd["default"]=[x for x in dd["default"] if not(x["ticker"]==e["ticker"] and x["date"]==e["date"])]; stonks_save(dd); st.rerun()
        st.divider()
        tp=tc-ti
        t1,t2,t3=st.columns(3)
        t1.metric("Toplam Yatırım",f"{ti:,.0f}₺")
        t2.metric("Güncel Değer",  f"{tc:,.2f}₺")
        t3.metric("Toplam K/Z",    f"{tp:+,.2f}₺",f"{(tp/ti*100):+.1f}%" if ti else "0%")

# ── TAB 5: LOG ────────────────────────────────────────────────────
with tab5:
    st.markdown("#### 📋 Log Dosyaları")
    st.info(f"📁 `{LOG_DIR}`")
    avail=[f for f in ["gunluk_log.txt","guclu_al_log.txt","state.json","stonks.json","model_usage.json"]
           if os.path.exists(os.path.join(LOG_DIR,f))]
    if not avail:
        st.info("Henüz log yok. Tarama sonrası burada görünür.")
    else:
        l1,l2=st.columns(2)
        lc=l1.selectbox("Dosya",avail)
        nl=l2.slider("Son satır",50,500,100)
        lpath=os.path.join(LOG_DIR,lc)
        with open(lpath,'r',encoding='utf-8') as f: cnt=f.readlines()
        st.caption(f"Toplam {len(cnt)} satır")
        st.code("".join(cnt[-nl:]),language="text")
        with open(lpath,'rb') as f:
            st.download_button(f"⬇️ {lc} indir",f.read(),lc,"text/plain")
    if st.button("🗑 Logları temizle",type="secondary"):
        for fp in [DAILY_LOG_FILE,STRONG_BUY_LOG]:
            if os.path.exists(fp):
                with open(fp,'w') as f: f.write("")
        st.success("Loglar temizlendi.")
.stButton > button { background:#00e676; color:#0b0e17; font-family:'JetBrains Mono',monospace;
    font-weight:700; border:none; border-radius:6px; padding:8px 20px; width:100%; }
.stButton > button:hover { background:#00c853; color:#0b0e17; }
div[data-baseweb="tab-list"] { background:#0f1320; border-bottom:1px solid #1d2540; }
div[data-baseweb="tab"] { font-family:'JetBrains Mono',monospace; color:#546e7a; }
div[aria-selected="true"] { color:#00e676 !important; border-bottom:2px solid #00e676 !important; }
.stTextInput>div>div>input { background:#131929 !important; border:1px solid #1d2540 !important; color:#dde3f0 !important; }
.stNumberInput>div>div>input { background:#131929 !important; border:1px solid #1d2540 !important; color:#dde3f0 !important; }
hr { border-color:#1d2540 !important; }
</style>
""", unsafe_allow_html=True)

# ─── YAPILANDIRMA ──────────────────────────────────────────────────
# API anahtarlarını Streamlit Secrets'tan oku (güvenli yöntem)
# share.streamlit.io → App ayarları → Secrets bölümüne ekle:
#   GEMINI_API_KEY = "AIza..."
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
GEMINI_MODEL   = "gemini-2.5-flash"

# ─── LOG DİZİNİ ────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(_SCRIPT_DIR, "bist_logs")
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    _probe = os.path.join(LOG_DIR, ".write_test")
    with open(_probe, 'w') as _f: _f.write("ok")
    os.remove(_probe)
except Exception:
    LOG_DIR = os.path.join(os.path.expanduser("~"), "bist_logs")
    os.makedirs(LOG_DIR, exist_ok=True)

DAILY_LOG_FILE   = os.path.join(LOG_DIR, "gunluk_log.txt")
WEEKLY_LOG_FILE  = os.path.join(LOG_DIR, "haftalik_log.txt")
STRONG_BUY_LOG   = os.path.join(LOG_DIR, "guclu_al_log.txt")
ELITE_BUY_LOG    = os.path.join(LOG_DIR, "elit_al_log.txt")
STATE_FILE       = os.path.join(LOG_DIR, "state.json")
STONKS_FILE      = os.path.join(LOG_DIR, "stonks.json")
MODEL_USAGE_FILE = os.path.join(LOG_DIR, "model_usage.json")

# ─── MODEL KOTALARI ────────────────────────────────────────────────
MODEL_DAILY_LIMITS = {
    "gemini-2.5-pro":        20,
    "gemini-2.5-flash":      20,
    "gemini-2.5-flash-lite": 100,
    "gemma-3-27b-it":        14400,
    "gemma-3-12b-it":        14400,
    "gemma-3-4b-it":         14400,
}
CHAIN_AIANALIZ = ["gemini-2.5-flash-lite","gemini-2.5-flash","gemma-3-27b-it","gemma-3-12b-it","gemma-3-4b-it"]
CHAIN_AIGUCLU  = ["gemini-2.5-pro","gemini-2.5-flash","gemini-2.5-flash-lite","gemma-3-27b-it","gemma-3-12b-it","gemma-3-4b-it"]

# ─── BIST200 LİSTESİ ───────────────────────────────────────────────
BIST200 = sorted(list(set([
    "AEFES","AGESA","AGHOL","AHGAZ","AKBNK","AKCNS","AKFGY","AKFYE",
    "AKSA","AKSEN","ALARK","ALBRK","ALFAS","ANSGR","ARCLK","ASELS",
    "ASTOR","ASUZU","AYDEM","BERA","BIENY","BIMAS","BINHO","BRSAN",
    "BRYAT","BUCIM","CANTE","CCOLA","CIMSA","CLEBI","CWENE","DOAS",
    "DOHOL","ECILC","ECZYT","EGEEN","EKGYO","ENERY","ENJSA","ENKAI",
    "ERCB","EREGL","EUPWR","FROTO","GARAN","GESAN","GUBRF","HALKB",
    "HEKTS","ISCTR","ISMEN","KARSN","KAYSE","KCAER","KCHOL","KONTR",
    "KONYA","KOZAL","KRDMD","KTLEV","MAVI","MGROS","MIATK","MPARK",
    "OBASE","ODAS","OTKAR","OYAKC","PETKM","PGSUS","REEDR","SAHOL",
    "SASA","SISE","SKBNK","SMRTG","SOKM","TABGD","TAVHL","TCELL",
    "THYAO","TKFEN","TOASO","TSKB","TTKOM","TTRAK","TUKAS","TUPRS",
    "TURSG","ULKER","VAKBN","VESTL","VESBE","YKBNK","YEOTK","ZOREN",
    "A1CAP","ADEL","AFYON","AGROT","AKGRT","AKSGY","ALCAR","ALCTL",
    "ALKIM","ALTNY","ANHYT","ARDYZ","ARENA","ARSAN","AVPGY","AVOD",
    "AYGAZ","AZTEK","BAGFS","BAKAB","BANVT","BASGZ","BFREN","BIZIM",
    "BMSCH","BOBET","BOSSA","BRISA","CEMTS","DAGI","DAPGM","DESA",
    "DESPC","DEVA","DGNMO","DMSAS","DOCO","EGGUB","EMKEL","ESEN",
    "EUREN","FONET","FORMT","GEDZA","GENIL","GENTS","GLYHO","GOLTS",
    "GOODY","GOZDE","GRSEL","GRTRK","GWIND","HATEK","HATSN","HDFGS",
    "HTTBT","HRKET","IEYHO","IHLAS","IHLGM","INDES","INFO","INVEO",
    "IPEKE","ISFIN","ISGYO","ISSEN","IZMDC","JANTS","KAREL","KARTN",
    "KATMR","KERVT","KFEIN","KLGYO","KLKIM","KLMSN","KLNMA","KLRHO",
    "KLSER","KMPUR","KNFRT","KONKA","KORDS","KRDMA","KRONT","KRTEK",
    "KUTPO","LIDER","LIDFA","LOGO","LUKSK","MACKO","MAGEN","MANAS",
    "MARTI","MEGMT","MEPET","MERKO","METUR","MOGAN","NETAS","NTHOL",
    "NUGYO","OYLUM","OZKGY","PAPIL","PARSN","PCILT","PENTA","PETUN",
    "PKART","PNLSN","PNSUT","POLHO","POLTK","PRKAB","PRKME","QUAGR",
    "RALYH","RYSAS","SAMAT","SANFM","SARKY","SAYAS","SDTTR","SELEC",
    "SELVA","SEYKM","SNGYO","SNICA","SOKE","SONME","SUNTK","TATGD",
    "TEZOL","TLMAN","TMPOL","TMSN","TRGYO","TRILC","TUCLK","ULUSE",
    "VAKKO","VERTU","VBTYZ","VKGYO","YATAS","YAYLA","YUNSA",
])))

# ─── GLOBAL STATE (session_state üzerinden) ────────────────────────
def _state(key, default=None):
    if key not in st.session_state:
        st.session_state[key] = default
    return st.session_state[key]

# ══════════════════════════════════════════════════════════════════
# MODEL KOTA YÖNETİMİ
# ══════════════════════════════════════════════════════════════════
def _load_model_counts():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        if os.path.exists(MODEL_USAGE_FILE):
            with open(MODEL_USAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('date') == today:
                return data.get('counts', {})
    except Exception: pass
    return {}

def _save_model_counts(counts):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open(MODEL_USAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'date': today, 'counts': counts}, f, indent=2)
    except Exception: pass

def get_model_count(m): return int(_load_model_counts().get(m, 0))
def model_has_quota(m): return get_model_count(m) < MODEL_DAILY_LIMITS.get(m, 20)
def increment_model_count(m):
    counts = _load_model_counts(); counts[m] = int(counts.get(m, 0)) + 1
    _save_model_counts(counts); return counts[m]
def is_gemma_model(m): return bool(m) and m.lower().startswith("gemma")

def _build_model_chain(order):
    chain = [m for m in order if model_has_quota(m)]
    return chain if chain else [order[0]]

# ══════════════════════════════════════════════════════════════════
# TRADINGVIEW VERİ ÇEKME
# ══════════════════════════════════════════════════════════════════
def tv_fetch_analyses(symbols, interval):
    if not TVTA_AVAILABLE: return {}
    try:
        result = {}
        handlers = {s: TA_Handler(
            symbol=s.replace("BIST:",""),
            screener="turkey",
            exchange="BIST",
            interval=interval
        ) for s in symbols}
        batch = get_multiple_analysis(handlers)
        for key, analysis in (batch or {}).items():
            if analysis: result[f"BIST:{key}" if not key.startswith("BIST:") else key] = analysis
        return result
    except Exception as e:
        st.session_state['last_error'] = str(e)
        return {}

def fetch_analysis(ticker, interval):
    if not TVTA_AVAILABLE: return None
    try:
        h = TA_Handler(symbol=ticker, screener="turkey", exchange="BIST", interval=interval)
        return h.get_analysis()
    except: return None

# ══════════════════════════════════════════════════════════════════
# TEKNİK ANALİZ (orijinal bottan bire bir taşındı)
# ══════════════════════════════════════════════════════════════════
def analyze_single_stock(ticker, analysis=None, weekly_analysis=None):
    if not TVTA_AVAILABLE: return None
    try:
        if analysis is None:
            analysis = fetch_analysis(ticker, Interval.INTERVAL_1_DAY)
        if not analysis: return None

        ind = analysis.indicators
        price = float(ind.get('close', 0) or 0)
        if price <= 0: return None

        rsi_val  = float(ind.get('RSI', 50) or 50)
        ema20    = float(ind.get('EMA20', price) or price)
        ema50    = float(ind.get('EMA50', price) or price)
        ema200   = float(ind.get('EMA200', price) or price)
        macd     = float(ind.get('MACD.macd', 0) or 0)
        macd_sig = float(ind.get('MACD.signal', 0) or 0)
        bb_upper = float(ind.get('BB.upper', price*1.02) or price*1.02)
        bb_lower = float(ind.get('BB.lower', price*0.98) or price*0.98)
        atr_val  = float(ind.get('ATR', price*0.02) or price*0.02)
        adx_val  = float(ind.get('ADX', 0) or 0)
        cci_val  = float(ind.get('CCI20', 0) or 0)
        stoch_k  = float(ind.get('Stoch.K', 50) or 50)
        stoch_d  = float(ind.get('Stoch.D', 50) or 50)
        d_change = float(ind.get('change', 0) or 0)

        w_change = 0
        if weekly_analysis:
            try: w_change = float(weekly_analysis.indicators.get('change', 0) or 0)
            except: pass

        summary  = analysis.summary
        tv_buy    = int(summary.get('BUY', 0) or 0)
        tv_sell   = int(summary.get('SELL', 0) or 0)
        tv_neutral= int(summary.get('NEUTRAL', 0) or 0)
        tv_rec    = summary.get('RECOMMENDATION', 'NEUTRAL')

        high_52w = float(ind.get('high', price) or price)
        low_52w  = float(ind.get('low',  price) or price)
        support    = bb_lower
        resistance = bb_upper

        score = 0; signals = []

        # RSI
        if rsi_val < 30:   signals.append("RSI Aşırı Satım ✅"); score += 2
        elif rsi_val < 45: signals.append("RSI Düşük ✅");        score += 1
        elif rsi_val > 70: signals.append("RSI Aşırı Alım ❌");  score -= 2
        elif rsi_val > 55: signals.append("RSI Yüksek ❌");      score -= 1

        # EMA
        if price > ema20: signals.append("Fiyat EMA20 üstü ✅"); score += 1
        else:             signals.append("Fiyat EMA20 altı ❌");  score -= 1
        if price > ema50: signals.append("Fiyat EMA50 üstü ✅"); score += 1
        else:             signals.append("Fiyat EMA50 altı ❌");  score -= 1
        if price > ema200:signals.append("Fiyat EMA200 üstü ✅");score += 1
        else:             signals.append("Fiyat EMA200 altı ❌"); score -= 1

        # MACD
        if macd > macd_sig: signals.append("MACD Pozitif ✅"); score += 1
        else:               signals.append("MACD Negatif ❌"); score -= 1

        # Bollinger
        if price < bb_lower:   signals.append("BB Alt Bantı ✅"); score += 1
        elif price > bb_upper: signals.append("BB Üst Bantı ❌"); score -= 1

        # Stochastic
        if stoch_k < 20 and stoch_d < 20:  signals.append("Stoch Aşırı Satım ✅"); score += 1
        elif stoch_k > 80 and stoch_d > 80: signals.append("Stoch Aşırı Alım ❌"); score -= 1

        # CCI
        if cci_val < -100:   signals.append("CCI Aşırı Satım ✅"); score += 1
        elif cci_val > 100:  signals.append("CCI Aşırı Alım ❌");  score -= 1

        # ADX
        if adx_val > 25:
            tag = '✅' if score > 0 else '❌'
            signals.append(f"ADX Güçlü Trend ({int(adx_val)}) {tag}")
            score += 1 if score > 0 else -1

        # TradingView özeti
        if tv_buy >= 12:   signals.append(f"TradingView: Güçlü AL ({tv_buy}) ✅"); score += 2
        elif tv_buy >= 7:  signals.append(f"TradingView: AL ({tv_buy}) ✅");        score += 1
        elif tv_sell >= 12:signals.append(f"TradingView: Güçlü SAT ({tv_sell}) ❌");score -= 2
        elif tv_sell >= 7: signals.append(f"TradingView: SAT ({tv_sell}) ❌");       score -= 1

        stop    = price - 1.5 * atr_val
        target1 = price + 2.5 * atr_val
        target2 = bb_upper
        rr1 = (target1 - price) / (price - stop) if (price - stop) > 0 else 0

        if score >= 6:    signal = "🟢 GÜÇLÜ AL"
        elif score >= 3:  signal = "🔵 AL"
        elif score >= 1:  signal = "🔷 ZAYIF AL"
        elif score <= -6: signal = "🔴 GÜÇLÜ SAT"
        elif score <= -3: signal = "🟠 SAT"
        elif score <= -1: signal = "🟡 ZAYIF SAT"
        else:             signal = "⚪ NÖTR"

        return {
            'ticker':ticker,'price':round(price,2),'d_change':round(d_change,2),
            'w_change':round(w_change,2),'rsi':round(rsi_val,1),'ema20':round(ema20,2),
            'ema50':round(ema50,2),'ema200':round(ema200,2),'atr':round(atr_val,2),
            'adx':round(adx_val,1),'support':round(support,2),'resistance':round(resistance,2),
            'score':score,'signal':signal,'sigs':signals,'stop':round(stop,2),
            'target1':round(target1,2),'target2':round(target2,2),'rr1':round(rr1,2),
            'tv_buy':tv_buy,'tv_sell':tv_sell,'tv_neutral':tv_neutral,'tv_rec':tv_rec,
        }
    except Exception as e:
        return None

# ══════════════════════════════════════════════════════════════════
# BATCH TARAMA
# ══════════════════════════════════════════════════════════════════
def _batch_fetch(symbols, interval, chunk_size=50):
    combined = {}
    for start in range(0, len(symbols), chunk_size):
        chunk = symbols[start:start+chunk_size]
        batch = tv_fetch_analyses(chunk, interval)
        if batch: combined.update(batch)
        time.sleep(0.5)
    return combined

def scan_all(progress_cb=None):
    if not TVTA_AVAILABLE: return []
    symbols = [f"BIST:{t}" for t in BIST200]
    if progress_cb: progress_cb(0.1, f"Günlük veri çekiliyor ({len(BIST200)} hisse)...")
    daily_batch  = _batch_fetch(symbols, Interval.INTERVAL_1_DAY)
    if progress_cb: progress_cb(0.5, "Haftalık veri çekiliyor...")
    weekly_batch = _batch_fetch(symbols, Interval.INTERVAL_1_WEEK)
    if progress_cb: progress_cb(0.8, "Analiz hesaplanıyor...")
    results = []
    for ticker in BIST200:
        key = f"BIST:{ticker}"
        daily_a  = daily_batch.get(key)
        weekly_a = weekly_batch.get(key)
        if not daily_a: continue
        try:
            res = analyze_single_stock(ticker, analysis=daily_a, weekly_analysis=weekly_a)
            if res: results.append(res)
        except: pass
    if progress_cb: progress_cb(1.0, f"Tamamlandı: {len(results)} hisse analiz edildi.")
    return results

# ══════════════════════════════════════════════════════════════════
# LOG KAYDETME (bist_logs klasörüne)
# ══════════════════════════════════════════════════════════════════
def save_daily_log(results):
    if not results: return
    try:
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        lines = [f"\n{'='*60}", f"TARAMA ZAMANI : {now_str}", f"TARANAN       : {len(results)} hisse", "="*60]
        for section, min_s, max_s in [
            ("[ GUCLU AL ]", 6, 99), ("[ AL ]", 3, 5),
            ("[ SAT ]", -5, -3),     ("[ GUCLU SAT ]", -99, -6)
        ]:
            items = sorted([r for r in results if min_s <= r['score'] <= max_s],
                           key=lambda x: x['score'], reverse=(min_s > 0))
            if not items: continue
            lines += ["", section]
            lines.append(f"{'HISSE':<8} {'FIYAT':>7} {'HEDEF':>7} {'STOP':>7} {'TARGET2':>8} {'RR':>5} {'GUN%':>6} {'HAF%':>6} {'RSI':>5} {'ADX':>5} {'ATR':>6}  SINYAL")
            lines.append("-"*90)
            for r in items:
                lines.append(
                    f"{r['ticker']:<8} {r['price']:>7.2f} {r['target1']:>7.2f} {r['stop']:>7.2f} "
                    f"{r['target2']:>8.2f} {r['rr1']:>5.2f} {r['d_change']:>+6.1f}% {r['w_change']:>+6.1f}% "
                    f"{r['rsi']:>5.1f} {r['adx']:>5.1f} {r['atr']:>6.2f}  {r['signal']}"
                )
        with open(DAILY_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")
        # Güçlü AL logunu ayrıca kaydet
        strong = [r for r in results if r['score'] >= 6]
        if strong:
            with open(STRONG_BUY_LOG, 'a', encoding='utf-8') as f:
                f.write(f"\n[{now_str}] GÜÇLÜ AL ({len(strong)} hisse):\n")
                for r in sorted(strong, key=lambda x: x['score'], reverse=True):
                    f.write(f"  {r['ticker']:8s} {r['price']:7.2f}₺  skor:{r['score']}  RSI:{r['rsi']}  {r['signal']}\n")
    except Exception as e:
        st.session_state['last_error'] = f"Log kaydetme hatası: {e}"

def save_state(results, daily_snaps):
    try:
        state = {
            'saved_at': datetime.now().strftime("%d.%m.%Y %H:%M"),
            'last_results': results,
            'daily_snapshots': daily_snaps,
            'scan_day': datetime.now().strftime("%Y-%m-%d"),
        }
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)
    except: pass

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {}

# ══════════════════════════════════════════════════════════════════
# GEMİNİ AI ANALİZ
# ══════════════════════════════════════════════════════════════════
_NEWS_FEEDS = [
    "https://bigpara.hurriyet.com.tr/rss/borsa.xml",
    "https://bigpara.hurriyet.com.tr/rss/ekonomi.xml",
    "https://www.bloomberght.com/rss",
]

def get_recent_news():
    if not FEEDPARSER_AVAILABLE: return "(Haber yüklenemedi)"
    collected = []
    for url in _NEWS_FEEDS:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:5]:
                title = (entry.get("title") or "").strip()
                if title and title not in collected:
                    collected.append(title)
                if len(collected) >= 8: break
        except: pass
        if len(collected) >= 8: break
    return "\n".join(f"- {h}" for h in collected) if collected else "(Haber alınamadı)"

def _call_gemini(client, model, prompt):
    gen_config = None if is_gemma_model(model) else types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )
    try:
        kwargs = {"model": model, "contents": prompt}
        if gen_config: kwargs["config"] = gen_config
        r = client.models.generate_content(**kwargs)
        return "ok", r.text, model
    except Exception as e:
        return "error", str(e), model

def gemini_analyze(results, mode="analiz"):
    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        return None, "Gemini API key ayarlanmamış. Sidebar'daki ayarlara ekle."

    min_score = 7 if mode == "analiz" else 8
    chain = CHAIN_AIGUCLU if mode == "guclu" else CHAIN_AIANALIZ

    strong = sorted([r for r in results if r['score'] >= min_score],
                    key=lambda x: x['score'], reverse=True)[:10]
    if not strong:
        return None, f"Skor ≥ {min_score} olan hisse bulunamadı. Önce tarama yap."

    stock_data = "\n".join([
        f"{r['ticker']}: fiyat={r['price']}₺ skor={r['score']} RSI={r['rsi']} "
        f"ADX={r['adx']} hedef={r['target1']}₺ stop={r['stop']}₺ TV={r['tv_rec']}"
        for r in strong
    ])
    news = get_recent_news()
    prompt = f"""Sen kıdemli bir Türkiye borsa analistisin.

GÜNCEL HABERLER:
{news}

TEKNİK ANALİZ VERİLERİ (Bot seçimi — skor ≥ {min_score}):
{stock_data}

Sadece JSON döndür, başka hiçbir şey yazma:
{{
  "piyasa_ozeti": "1-2 cümle genel durum",
  "piyasa_rengi": "POZITIF|NEGATIF|NOTR",
  "top_hisseler": [
    {{
      "hisse": "THYAO",
      "guven": 8,
      "anahtar_kelime": "Momentum",
      "neden": "Kısa gerekçe (max 80 karakter)",
      "beklenti": "Kısa vade yükseliş",
      "hedef_yuzde": "+4-7%",
      "risk": "ORTA",
      "gundem_etkisi": "Gündemden nasıl etkileniyor (max 80 karakter)"
    }}
  ],
  "genel_uyari": "Kısa risk notu"
}}"""

    client = genai.Client(api_key=GEMINI_API_KEY)
    active_chain = _build_model_chain(chain)
    for model in active_chain:
        status, payload, used = _call_gemini(client, model, prompt)
        if status == "ok":
            increment_model_count(used)
            return payload, f"✅ {used} ({get_model_count(used)}/{MODEL_DAILY_LIMITS.get(used,20)})"
    return None, "Tüm modeller meşgul veya kota doldu."

def _parse_gemini_json(raw):
    if not raw: return None
    t = raw.strip()
    t = re.sub(r'^```(?:json)?\s*', '', t)
    t = re.sub(r'\s*```$', '', t)
    s, e = t.find('{'), t.rfind('}')
    if s < 0 or e < 0: return None
    try: return json.loads(t[s:e+1])
    except: return None

# ══════════════════════════════════════════════════════════════════
# SANAL PORTFÖY (Stonks)
# ══════════════════════════════════════════════════════════════════
def stonks_load():
    try:
        if os.path.exists(STONKS_FILE):
            with open(STONKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {}

def stonks_save(data):
    with open(STONKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_current_price(ticker):
    a = fetch_analysis(ticker, Interval.INTERVAL_1_DAY)
    if a and a.indicators:
        px = a.indicators.get('close', 0) or 0
        return float(px) if px > 0 else None
    return None

# ══════════════════════════════════════════════════════════════════
# OTOMATİK TARAMA DÖNGÜSÜ (arka plan thread)
# ══════════════════════════════════════════════════════════════════
def _auto_scan_loop():
    """Borsa saatlerinde (09:50-18:00) otomatik tarama döngüsü"""
    while st.session_state.get('auto_scan_enabled', False):
        now = datetime.now()
        is_weekday = now.weekday() < 5
        is_market  = is_weekday and (
            (now.hour == 9 and now.minute >= 50) or
            (10 <= now.hour <= 17) or
            (now.hour == 18 and now.minute <= 0)
        )
        if is_market and TVTA_AVAILABLE:
            st.session_state['auto_scan_running'] = True
            results = scan_all()
            if results:
                st.session_state['last_results'] = results
                st.session_state['last_scan_time'] = datetime.now().strftime("%H:%M:%S")
                if 'daily_snaps' not in st.session_state:
                    st.session_state['daily_snaps'] = []
                st.session_state['daily_snaps'].append(results)
                save_daily_log(results)
                save_state(results, st.session_state['daily_snaps'])
            st.session_state['auto_scan_running'] = False
            time.sleep(30)  # 30 saniye bekle
        else:
            time.sleep(60)  # 1 dakika bekle

# ══════════════════════════════════════════════════════════════════
# SINYAL CSS SINIFI
# ══════════════════════════════════════════════════════════════════
def signal_class(signal):
    if "GÜÇLÜ AL" in signal:  return "signal-guclu-al"
    if "AL" in signal:        return "signal-al"
    if "GÜÇLÜ SAT" in signal: return "signal-guclu-sat"
    if "SAT" in signal:       return "signal-sat"
    return "signal-notr"

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<p style="font-family:JetBrains Mono,monospace;font-size:22px;color:#00e676;font-weight:700;letter-spacing:3px;">📈 BIST200</p>', unsafe_allow_html=True)
    st.markdown('<p style="color:#546e7a;font-size:12px;letter-spacing:1px;">TEKNİK ANALİZ BOTU</p>', unsafe_allow_html=True)
    st.divider()

    # Gemini API Key
    api_key_input = st.text_input("🔑 Gemini API Key", value=GEMINI_API_KEY,
                                   type="password", placeholder="AIza...")
    if api_key_input:
        GEMINI_API_KEY = api_key_input

    st.divider()

    # Log dizini durumu
    log_files = [f for f in os.listdir(LOG_DIR) if os.path.isfile(os.path.join(LOG_DIR, f))]
    st.markdown(f"**📁 bist_logs/**")
    st.caption(f"`{LOG_DIR}`")
    for fname in sorted(log_files):
        fpath = os.path.join(LOG_DIR, fname)
        fsize = os.path.getsize(fpath)
        st.caption(f"📄 {fname} ({fsize/1024:.1f} KB)")

    st.divider()

    # Otomatik tarama
    auto_scan = st.toggle("🔄 Otomatik Tarama (Borsa saati)", value=_state('auto_scan_enabled', False))
    st.session_state['auto_scan_enabled'] = auto_scan

    if auto_scan and not st.session_state.get('auto_thread_started', False):
        t = threading.Thread(target=_auto_scan_loop, daemon=True)
        t.start()
        st.session_state['auto_thread_started'] = True
        st.success("Otomatik tarama başlatıldı!")

    if st.session_state.get('auto_scan_running', False):
        st.markdown('<span class="scan-running">⚡ TARAMA ÇALIŞIYOR...</span>', unsafe_allow_html=True)

    if st.session_state.get('last_scan_time'):
        st.caption(f"Son tarama: {st.session_state['last_scan_time']}")

    st.divider()
    st.caption("⚠️ Yatırım tavsiyesi değildir.")

# ══════════════════════════════════════════════════════════════════
# ANA İÇERİK
# ══════════════════════════════════════════════════════════════════
st.markdown('<p style="font-family:JetBrains Mono,monospace;font-size:26px;color:#dde3f0;font-weight:700;">BIST200 Teknik Analiz Paneli</p>', unsafe_allow_html=True)

# Durum çubuğu
col_status = st.columns([1,1,1,1])
results = st.session_state.get('last_results', [])
if results:
    guclu_al  = sum(1 for r in results if r['score'] >= 6)
    al        = sum(1 for r in results if 3 <= r['score'] < 6)
    sat       = sum(1 for r in results if -6 < r['score'] <= -3)
    guclu_sat = sum(1 for r in results if r['score'] <= -6)
    col_status[0].metric("🟢 Güçlü AL", guclu_al)
    col_status[1].metric("🔵 AL", al)
    col_status[2].metric("🟠 SAT", sat)
    col_status[3].metric("🔴 Güçlü SAT", guclu_sat)

st.divider()

# SEKMELER
tab_tarama, tab_hisse, tab_ai, tab_portfoy, tab_log = st.tabs([
    "🔍 Tarama", "📊 Tek Hisse", "🤖 AI Analiz", "💼 Portföy", "📋 Log"
])

# ─── TAB 1: TARAMA ──────────────────────────────────────────────
with tab_tarama:
    st.markdown("#### BIST200 Tam Tarama")

    if not TVTA_AVAILABLE:
        st.error("tradingview-ta yüklü değil. `pip install tradingview-ta` komutunu çalıştır.")
    else:
        col_btn1, col_btn2, col_btn3 = st.columns([1,1,2])
        run_scan   = col_btn1.button("🔍 TÜMÜNÜ TARA")
        show_all   = col_btn2.toggle("Tümünü göster", value=False)

        if run_scan:
            prog = st.progress(0, "Tarama başlıyor...")
            def _cb(pct, msg): prog.progress(pct, msg)
            with st.spinner("BIST200 taranıyor..."):
                res = scan_all(progress_cb=_cb)
            if res:
                st.session_state['last_results'] = res
                st.session_state['last_scan_time'] = datetime.now().strftime("%H:%M:%S")
                if 'daily_snaps' not in st.session_state: st.session_state['daily_snaps'] = []
                st.session_state['daily_snaps'].append(res)
                save_daily_log(res)
                save_state(res, st.session_state['daily_snaps'])
                st.success(f"✅ {len(res)} hisse analiz edildi ve bist_logs'a kaydedildi!")
            else:
                st.error("Tarama başarısız. İnternet bağlantısını veya tradingview-ta durumunu kontrol et.")
            prog.empty()

        results = st.session_state.get('last_results', [])
        if results:
            # Filtrele
            col_f1, col_f2, col_f3 = st.columns(3)
            filtre = col_f1.selectbox("Filtre", ["Hepsi","Güçlü AL","AL","SAT","Güçlü SAT","NÖTR"], index=0)
            sort_by = col_f2.selectbox("Sırala", ["Skor (yüksek→alçak)","RSI","Fiyat","RR"])
            min_score_f = col_f3.slider("Min Skor", -10, 10, -10)

            filtered = results
            if filtre == "Güçlü AL":  filtered = [r for r in results if r['score'] >= 6]
            elif filtre == "AL":      filtered = [r for r in results if 3 <= r['score'] < 6]
            elif filtre == "SAT":     filtered = [r for r in results if -6 < r['score'] <= -3]
            elif filtre == "Güçlü SAT": filtered = [r for r in results if r['score'] <= -6]
            elif filtre == "NÖTR":    filtered = [r for r in results if -3 < r['score'] < 3]

            filtered = [r for r in filtered if r['score'] >= min_score_f]

            if sort_by == "RSI":    filtered.sort(key=lambda x: x['rsi'])
            elif sort_by == "Fiyat": filtered.sort(key=lambda x: x['price'], reverse=True)
            elif sort_by == "RR":   filtered.sort(key=lambda x: x['rr1'], reverse=True)
            else:                   filtered.sort(key=lambda x: x['score'], reverse=True)

            if not show_all: filtered = filtered[:20]

            st.caption(f"{len(filtered)} hisse gösteriliyor (toplam: {len(results)})")

            import pandas as pd
            df = pd.DataFrame([{
                "Hisse": r['ticker'], "Fiyat (₺)": r['price'],
                "Sinyal": r['signal'], "Skor": r['score'],
                "RSI": r['rsi'], "ADX": r['adx'],
                "Hedef (₺)": r['target1'], "Stop (₺)": r['stop'],
                "RR": r['rr1'], "Gün %": r['d_change'], "Hafta %": r['w_change'],
                "TV": r['tv_rec'],
            } for r in filtered])

            def color_signal(val):
                if "GÜÇLÜ AL" in str(val): return "color: #00e676; font-weight: bold"
                if "AL" in str(val): return "color: #40c4ff"
                if "GÜÇLÜ SAT" in str(val): return "color: #ff1744; font-weight: bold"
                if "SAT" in str(val): return "color: #ff6d00"
                return "color: #90a4ae"

            styled = df.style.applymap(color_signal, subset=["Sinyal"])
            st.dataframe(styled, use_container_width=True, height=500)
        else:
            st.info("Henüz tarama yapılmadı. 'TÜMÜNÜ TARA' butonuna tıkla veya otomatik taramayı aç.")

# ─── TAB 2: TEK HİSSE ────────────────────────────────────────────
with tab_hisse:
    st.markdown("#### Tek Hisse Detay Analizi")
    col_h1, col_h2 = st.columns([2,1])
    ticker_input = col_h1.text_input("Hisse Sembolü", placeholder="THYAO, GARAN, ASELS...").upper().strip()
    analyze_btn  = col_h2.button("📊 ANALİZ ET", key="btn_single")

    if analyze_btn and ticker_input:
        with st.spinner(f"{ticker_input} analiz ediliyor..."):
            r = analyze_single_stock(ticker_input)

        if r:
            sc = signal_class(r['signal'])
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Fiyat", f"{r['price']:.2f} ₺", f"{r['d_change']:+.2f}% gün")
            col_b.metric("Sinyal", r['signal'])
            col_c.metric("Skor", r['score'])
            col_d.metric("RSI", r['rsi'])

            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Hedef", f"{r['target1']:.2f} ₺", f"+{((r['target1']-r['price'])/r['price']*100):.1f}%")
            c2.metric("Stop",  f"{r['stop']:.2f} ₺",  f"-{((r['price']-r['stop'])/r['price']*100):.1f}%")
            c3.metric("Risk/Ödül", f"{r['rr1']:.2f}x")

            st.divider()
            c4, c5, c6 = st.columns(3)
            c4.metric("ADX", r['adx'])
            c5.metric("EMA20", r['ema20'])
            c6.metric("TradingView", r['tv_rec'])

            st.markdown(f"**📋 Sinyal detayları:**")
            for s in r['sigs']:
                st.markdown(f"- {s}")
        elif ticker_input:
            st.error(f"'{ticker_input}' için veri alınamadı. Sembolü kontrol et (örn: THYAO, GARAN).")

# ─── TAB 3: AI ANALİZ ────────────────────────────────────────────
with tab_ai:
    st.markdown("#### 🤖 Gemini AI Analizi")

    if not GEMINI_API_KEY:
        st.warning("Gemini API key gerekli. Soldaki Sidebar'a ekle veya Streamlit Secrets'a GEMINI_API_KEY olarak tanımla.")
    
    results = st.session_state.get('last_results', [])
    if not results:
        st.info("Önce 'Tarama' sekmesinden tarama yap.")
    else:
        col_ai1, col_ai2 = st.columns(2)
        ai_btn1 = col_ai1.button("🧠 AI ANALİZ (skor ≥ 7)")
        ai_btn2 = col_ai2.button("🏆 AI GÜÇLÜ (skor ≥ 8)")

        mode = None
        if ai_btn1: mode = "analiz"
        if ai_btn2: mode = "guclu"

        if mode:
            with st.spinner("Gemini analiz yapıyor..."):
                raw, info = gemini_analyze(results, mode=mode)
            st.caption(f"Model: {info}")

            if raw:
                data = _parse_gemini_json(raw)
                if data:
                    renk = data.get("piyasa_rengi","NOTR")
                    renk_emoji = {"POZITIF":"🟢","NEGATIF":"🔴","NOTR":"⚪"}.get(renk,"⚪")
                    st.markdown(f"### {renk_emoji} Piyasa: {data.get('piyasa_ozeti','')}")
                    st.divider()

                    top = data.get("top_hisseler", [])
                    for i, h in enumerate(top, 1):
                        with st.container():
                            ca, cb = st.columns([1,3])
                            ca.markdown(f"**#{i} {h.get('hisse','')}**")
                            ca.markdown(f"Güven: **{h.get('guven',0)}/10**")
                            ca.markdown(f"Risk: {h.get('risk','')}")
                            cb.markdown(f"🔑 *{h.get('anahtar_kelime','')}*")
                            cb.markdown(f"📌 {h.get('neden','')}")
                            cb.markdown(f"📈 Beklenti: {h.get('beklenti','')} — **{h.get('hedef_yuzde','')}**")
                            cb.caption(f"📰 {h.get('gundem_etkisi','')}")
                        st.divider()

                    if data.get("genel_uyari"):
                        st.warning(f"⚠️ {data['genel_uyari']}")
                else:
                    st.markdown(raw)  # JSON parse olmadıysa ham metin göster
            else:
                st.error(info)

        # Model kotaları
        with st.expander("📊 Model Kotaları"):
            for m, limit in MODEL_DAILY_LIMITS.items():
                c = get_model_count(m)
                st.progress(c/limit, text=f"{m}: {c}/{limit}")

# ─── TAB 4: PORTFÖY ──────────────────────────────────────────────
with tab_portfoy:
    st.markdown("#### 💼 Sanal Portföy")
    portfolio_data = stonks_load()

    with st.expander("➕ Yeni Yatırım Ekle"):
        col_p1, col_p2, col_p3 = st.columns(3)
        p_ticker = col_p1.text_input("Hisse", placeholder="THYAO").upper()
        p_amount = col_p2.number_input("Tutar (₺)", min_value=100.0, value=10000.0, step=100.0)
        p_btn    = col_p3.button("Ekle", key="btn_stonks_add")

        if p_btn and p_ticker:
            with st.spinner(f"{p_ticker} fiyatı alınıyor..."):
                price = get_current_price(p_ticker)
            if price:
                shares = p_amount / price
                entry = {
                    "ticker": p_ticker, "amount": p_amount,
                    "buy_price": round(price,2), "shares": round(shares,4),
                    "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                }
                data = stonks_load()
                if "default" not in data: data["default"] = []
                data["default"].append(entry)
                stonks_save(data)
                st.success(f"✅ {p_ticker} eklendi! Alış: {price:.2f}₺ | Lot: {shares:.4f}")
            else:
                st.error("Fiyat alınamadı. Sembolü kontrol et.")

    portfolio = stonks_load().get("default", [])
    if not portfolio:
        st.info("Portföy boş. Yukarıdan hisse ekle.")
    else:
        total_inv = total_cur = 0
        for entry in portfolio:
            ticker = entry["ticker"]
            amount = entry["amount"]
            buy_px = entry["buy_price"]
            shares = entry["shares"]

            cur_px = get_current_price(ticker) or buy_px
            cur_val = shares * cur_px
            profit  = cur_val - amount
            pct     = (profit/amount)*100

            total_inv += amount
            total_cur += cur_val

            icon = "🟢" if profit >= 0 else "🔴"
            col_pa, col_pb, col_pc, col_pd = st.columns([1,2,2,1])
            col_pa.markdown(f"**{icon} {ticker}**")
            col_pb.metric("Alış/Güncel", f"{buy_px:.2f}₺", f"{cur_px:.2f}₺")
            col_pc.metric("K/Z", f"{profit:+,.0f}₺", f"{pct:+.1f}%")
            if col_pd.button("🗑", key=f"del_{ticker}_{entry['date']}"):
                data = stonks_load()
                data["default"] = [e for e in data["default"] if not (e["ticker"]==ticker and e["date"]==entry["date"])]
                stonks_save(data)
                st.rerun()

        st.divider()
        total_profit = total_cur - total_inv
        pf_icon = "📈" if total_profit >= 0 else "📉"
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("Toplam Yatırım", f"{total_inv:,.0f}₺")
        col_t2.metric("Güncel Değer",   f"{total_cur:,.2f}₺")
        col_t3.metric(f"{pf_icon} Toplam K/Z", f"{total_profit:+,.2f}₺", f"{(total_profit/total_inv*100):+.1f}%" if total_inv else "0%")

# ─── TAB 5: LOG ──────────────────────────────────────────────────
with tab_log:
    st.markdown("#### 📋 Log Dosyaları (bist_logs/)")
    st.info(f"📁 Log klasörü: `{LOG_DIR}`")

    col_l1, col_l2 = st.columns(2)
    log_choice = col_l1.selectbox("Log dosyası seç", [
        "gunluk_log.txt", "haftalik_log.txt", "guclu_al_log.txt",
        "elit_al_log.txt", "state.json", "model_usage.json", "stonks.json"
    ])
    n_lines = col_l2.slider("Son kaç satır", 50, 500, 100)

    log_path = os.path.join(LOG_DIR, log_choice)
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            content = f.readlines()
        st.caption(f"Toplam {len(content)} satır — son {n_lines} gösteriliyor")
        st.code("".join(content[-n_lines:]), language="text")

        # İndir butonu
        with open(log_path, 'rb') as f:
            st.download_button(
                label=f"⬇️ {log_choice} indir",
                data=f.read(),
                file_name=log_choice,
                mime="text/plain"
            )
    else:
        st.info(f"'{log_choice}' henüz oluşturulmadı. Tarama yaptıkça dosyalar burada görünür.")

    # Log temizle
    if st.button("🗑 Tüm logları temizle", type="secondary"):
        for fname in [DAILY_LOG_FILE, WEEKLY_LOG_FILE, STRONG_BUY_LOG, ELITE_BUY_LOG]:
            if os.path.exists(fname):
                with open(fname, 'w') as f: f.write("")
        st.success("Loglar temizlendi.")
