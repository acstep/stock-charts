#!/usr/bin/env python3
"""
build_gallery.py — 從 png/ 資料夾 + recommendations/{date}.json 產 K 線圖庫 HTML

新版結構（每張卡片全寬 1 欄）：
  ┌────────────────────────────────────────────────────────┐
  │ [6 月 K 線]  [1 月 K 線]                                  │
  │ NVDA · NVIDIA  $215.33 (+2.1%)  📈 AI 晶片/GPU            │
  ├────────────────────────────────────────────────────────┤
  │ P/E (TTM): 30.5  |  P/E (Fwd): 25.2                       │
  │ EPS (TTM): $24.69  |  EPS (Fwd): $32.10                   │
  ├────────────────────────────────────────────────────────┤
  │ 💡 AI 推薦：[2-3 句中文推薦]                                  │
  ├────────────────────────────────────────────────────────┤
  │ 📰 最新新聞（3 天內）                                        │
  │ • [中文標題 1] — Yahoo Finance (link)                       │
  │ • [中文標題 2] — Yahoo Finance (link)                       │
  │ • [中文標題 3] — Yahoo Finance (link)                       │
  └────────────────────────────────────────────────────────┘

資料來源：
- png/{SYM}-{date}-6mo.png + png/{SYM}-{date}-1mo.png    ← kline_generator.py
- recommendations/{date}.json                          ← stock-reports cron 產
- yfinance ticker.info (currentPrice, PE, EPS)         ← 這邊 build 時抓
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

import yfinance as yf

TPE = timezone(timedelta(hours=8))

ROOT = os.path.dirname(os.path.abspath(__file__))
PNG_DIR = os.path.join(ROOT, 'png')
CHARTS_DIR = os.path.join(ROOT, 'charts')
INDEX_FILE = os.path.join(ROOT, 'index.html')
DATA_DIR = os.path.join(ROOT, 'data')

# 台北時間日期
DATE_STR = datetime.now(TPE).strftime('%Y-%m-%d')

# ============================================================================
# 常數
# ============================================================================

NAME_MAP = {
    'NVDA': 'NVIDIA', 'AMD': 'AMD', 'INTC': 'Intel', 'AVGO': 'Broadcom',
    'QCOM': 'Qualcomm', 'MRVL': 'Marvell', 'ARM': 'ARM Holdings', 'TSM': 'TSMC',
    'AMAT': 'Applied Materials', 'KLAC': 'KLA', 'LRCX': 'Lam Research',
    'AMKR': 'Amkor', 'ASX': 'ASE Tech', 'TER': 'Teradyne',
    'MU': 'Micron', 'WDC': 'Western Digital', 'STX': 'Seagate', 'NTAP': 'NetApp',
    'SMCI': 'Super Micro', 'DELL': 'Dell', 'ANET': 'Arista', 'CSCO': 'Cisco',
    'ORCL': 'Oracle', 'GOOGL': 'Alphabet', 'MSFT': 'Microsoft',
    'AMZN': 'Amazon', 'META': 'Meta',
    'VST': 'Vistra', 'CEG': 'Constellation', 'ETN': 'Eaton', 'VRT': 'Vertiv',
    'NRG': 'NRG Energy', 'BE': 'Bloom Energy', 'NEE': 'NextEra',
    'GLW': 'Corning', 'CIEN': 'Ciena', 'NET': 'Cloudflare',
    'CRWD': 'CrowdStrike', 'PANW': 'Palo Alto', 'PLTR': 'Palantir',
    'P': 'Everpure',  # 原 PSTG (Pure Storage) 2026 改名
}

# 類別分組（依 user 決定 Q12(b)）
CATEGORY_ORDER = [
    ('01_AI晶片', '💾 AI 晶片/GPU'),
    ('02_AI封裝', '📦 AI 先進封裝/CoWoS'),
    ('07_AI儲存', '💾 AI 儲存/記憶體'),
    ('03_AI散熱', '🧊 AI 散熱/液冷'),
    ('04_AI電力', '⚡ AI 電力/能源'),
    ('05_AI網路', '📡 AI 網路/光纖'),
    ('06_AI伺服器', '🖥️ AI 伺服器/雲端'),
    ('08_AI資安', '🔐 AI 資安/雲端'),
    ('09_AI軟體', '🤖 AI 軟體/資料分析'),
    ('10_AI雲端', '☁️ AI 雲端平台'),
    ('11_其他基建', '🏭 AI 基礎建設其他'),
]

CATEGORY_MAP = {
    # 1. AI 晶片/GPU (8)
    'NVDA': '01_AI晶片', 'AMD': '01_AI晶片', 'AVGO': '01_AI晶片',
    'INTC': '01_AI晶片', 'QCOM': '01_AI晶片', 'MRVL': '01_AI晶片',
    'ARM': '01_AI晶片', 'TSM': '01_AI晶片',
    # 2. AI 封裝 (4)
    'AMAT': '02_AI封裝', 'LRCX': '02_AI封裝', 'AMKR': '02_AI封裝', 'ASX': '02_AI封裝',
    # 3. AI 散熱 (2)
    'VRT': '03_AI散熱', 'SPXC': '03_AI散熱',
    # 4. AI 電力/能源 (9)
    'VST': '04_AI電力', 'CEG': '04_AI電力', 'ETN': '04_AI電力',
    'NRG': '04_AI電力', 'NEE': '04_AI電力', 'AAON': '04_AI電力',
    'GEV': '04_AI電力', 'PNRG': '04_AI電力', 'TLN': '04_AI電力',
    # 5. AI 網路 (6)
    'GLW': '05_AI網路', 'CIEN': '05_AI網路', 'ANET': '05_AI網路',
    'CSCO': '05_AI網路', 'NET': '05_AI網路', 'LUMN': '05_AI網路',
    # 6. AI 伺服器 (3)
    'SMCI': '06_AI伺服器', 'DELL': '06_AI伺服器', 'HPQ': '06_AI伺服器',
    # 7. AI 儲存 (5)
    'MU': '07_AI儲存', 'WDC': '07_AI儲存', 'STX': '07_AI儲存',
    'NTAP': '07_AI儲存', 'P': '07_AI儲存',
    # 8. AI 資安 (5)
    'CRWD': '08_AI資安', 'PANW': '08_AI資安', 'S': '08_AI資安',
    'OKTA': '08_AI資安', 'ZS': '08_AI資安',
    # 9. AI 軟體 (3)
    'PLTR': '09_AI軟體', 'CRM': '09_AI軟體', 'SNOW': '09_AI軟體',
    # 10. AI 雲端 (5)
    'ORCL': '10_AI雲端', 'GOOGL': '10_AI雲端', 'MSFT': '10_AI雲端',
    'AMZN': '10_AI雲端', 'META': '10_AI雲端',
    # 11. 其他 (2)
    'AES': '11_其他基建', 'ASML': '11_其他基建',
}


# ============================================================================
# 資料抓取
# ============================================================================

def load_symbols():
    with open(os.path.join(ROOT, 'symbols.json')) as f:
        return json.load(f)


def load_recommendations(date_str):
    """抓 recommendations/{date}.json。

    優先順序：
    1. stock-reports repo raw URL（來自 cron 12:00 生成的）
    2. fallback: 本地 data/recommendations/{date}.json（示範 / 離線使用）

    如果都找不到，回傳 None（build 還是會跑，但 AI 推薦欄位顯示 placeholder）
    """
    import urllib.request

    # 1. stock-reports raw URL
    url = f'https://raw.githubusercontent.com/acstep/stock-reports/main/recommendations/{date_str}.json'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            print(f'  [recs] ✓ from stock-reports: {len(data.get("tickers", {}))} tickers')
            return data
    except Exception as e:
        print(f'  [recs] stock-reports fetch failed ({type(e).__name__}), fallback local', file=sys.stderr)

    # 2. fallback 本地
    local_path = os.path.join(DATA_DIR, 'recommendations', f'{date_str}.json')
    if os.path.exists(local_path):
        with open(local_path) as f:
            data = json.load(f)
            print(f'  [recs] ✓ from local fallback: {len(data.get("tickers", {}))} tickers')
            return data
    return None


def fetch_yfinance_info(symbol):
    """抓 yfinance ticker.info，回傳 dict。

    只抓我們要用的欄位，避免 ticker.info 太肥。
    失敗回 None。
    """
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        return {
            'currentPrice': info.get('currentPrice') or info.get('regularMarketPrice'),
            'previousClose': info.get('previousClose') or info.get('regularMarketPreviousClose'),
            'change_pct': (
                round((info.get('currentPrice', 0) - info.get('previousClose', 0)) / info['previousClose'] * 100, 2)
                if info.get('currentPrice') and info.get('previousClose')
                else None
            ),
            'trailingPE': info.get('trailingPE'),
            'forwardPE': info.get('forwardPE'),
            'trailingEps': info.get('trailingEps'),
            'forwardEps': info.get('forwardEps'),
            'marketCap': info.get('marketCap'),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh'),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow'),
        }
    except Exception as e:
        print(f'    [info] {symbol} ERR: {e}', file=sys.stderr)
        return None


# ============================================================================
# HTML template
# ============================================================================

def render_card(item):
    """渲染單張卡片 HTML。

    item: {
      symbol, name, category_label,
      price, change_pct,
      png_6mo, png_1mo,
      pe_ttm, pe_fwd, eps_ttm, eps_fwd,
      recommendation (str or None),
      news (list of {title_zh, title_en, url}),
    }
    """
    sym = item['symbol']
    name = item['name']
    cat = item.get('category_label', '')

    price = item.get('price')
    chg = item.get('change_pct')
    price_str = f'${price:,.2f}' if price else '—'
    chg_str = ''
    if chg is not None:
        sign = '+' if chg >= 0 else ''
        color = '#24e08a' if chg >= 0 else '#ef5350'
        chg_str = f'<span style="color:{color};font-weight:700">{sign}{chg:.2f}%</span>'
    else:
        chg_str = '<span style="color:#888">—</span>'

    pe_ttm = item.get('pe_ttm')
    pe_fwd = item.get('pe_fwd')
    eps_ttm = item.get('eps_ttm')
    eps_fwd = item.get('eps_fwd')

    pe_ttm_str = f'{pe_ttm:.1f}' if pe_ttm else '—'
    pe_fwd_str = f'{pe_fwd:.1f}' if pe_fwd else '—'
    eps_ttm_str = f'${eps_ttm:.2f}' if eps_ttm else '—'
    eps_fwd_str = f'${eps_fwd:.2f}' if eps_fwd else '—'

    rec = item.get('recommendation') or '— 等待下次報告更新 —'

    news = item.get('news') or []
    news_items = []
    for n in news[:3]:
        title_zh = n.get('title_zh') or n.get('title') or '(無標題)'
        title_en = n.get('title_en', '')
        url = n.get('url', '#')
        news_items.append(
            f'    <li><a href="{url}" target="_blank" rel="noopener">{title_zh}</a>'
            + (f' <span style="color:#666;font-size:0.85em">— {title_en}</span>' if title_en else '')
            + '</li>'
        )
    if not news_items:
        news_items = ['    <li style="color:#888">— 無 3 天內新聞 —</li>']

    png_6mo = item.get('png_6mo', '')
    png_1mo = item.get('png_1mo', '')

    return f'''    <div class="card">
        <div class="card-header">
            <div class="card-ticker-block">
                <span class="card-ticker">{sym}</span>
                <span class="card-name">{name}</span>
            </div>
            <div class="card-price-block">
                <span class="card-price">{price_str}</span>
                <span class="card-change">{chg_str}</span>
            </div>
            <div class="card-category">{cat}</div>
        </div>

        <div class="kline-row">
            <div class="kline-cell">
                <div class="kline-label">📊 半年日 K</div>
                <img class="kline-img" src="../png/{png_6mo}" alt="{sym} 6 月 K 線" loading="lazy">
            </div>
            <div class="kline-cell">
                <div class="kline-label">📊 一月日 K（22 交易日）</div>
                <img class="kline-img" src="../png/{png_1mo}" alt="{sym} 1 月 K 線" loading="lazy">
            </div>
        </div>

        <div class="metrics-row">
            <div class="metric"><span class="metric-key">P/E (TTM)</span><span class="metric-val">{pe_ttm_str}</span></div>
            <div class="metric"><span class="metric-key">P/E (Fwd)</span><span class="metric-val">{pe_fwd_str}</span></div>
            <div class="metric"><span class="metric-key">EPS (TTM)</span><span class="metric-val">{eps_ttm_str}</span></div>
            <div class="metric"><span class="metric-key">EPS (Fwd)</span><span class="metric-val">{eps_fwd_str}</span></div>
        </div>

        <div class="rec-block">
            <div class="block-title">💡 AI 推薦</div>
            <div class="rec-text">{rec}</div>
        </div>

        <div class="news-block">
            <div class="block-title">📰 最新新聞（3 天內）</div>
            <ul class="news-list">
{chr(10).join(news_items)}
            </ul>
        </div>
    </div>'''


def render_html(cards_by_category, has_recommendations, total_count):
    """組裝整個圖庫頁 HTML。"""
    sections_html = []
    for cat_key, cat_label in CATEGORY_ORDER:
        cards = cards_by_category.get(cat_key, [])
        if not cards:
            continue
        sections_html.append(f'''    <section class="category-section">
        <h2 class="category-title">{cat_label} <span class="category-count">({len(cards)})</span></h2>
        <div class="cards-grid">
{chr(10).join(cards)}
        </div>
    </section>''')

    utc_now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    rec_badge = (
        '<span class="badge green">✓ AI 推薦已就緒</span>'
        if has_recommendations
        else '<span class="badge" style="background:rgba(255,180,0,0.1);border-color:rgba(255,180,0,0.3);color:#ffb84d">⚠ AI 推薦待下次 cron 補</span>'
    )

    return f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>K 線圖庫｜{DATE_STR} · AI 基建 52 檔深度版</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;background:#08080f;color:#e0e4f0;line-height:1.65;padding:0}}
.wrap{{max-width:1400px;margin:0 auto;padding:24px}}

.hero{{background:linear-gradient(135deg,#08081a 0%,#1a0a2a 50%,#0a0a1a 100%);border:1px solid rgba(91,127,255,0.25);border-radius:20px;padding:36px 40px;margin-bottom:24px;position:relative;overflow:hidden}}
.hero h1{{font-size:30px;color:#fff;margin-bottom:8px;background:linear-gradient(90deg,#00d4ff,#00ff88);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero .sub{{color:#7880a0;font-size:13px;margin-bottom:4px}}
.hero .meta{{margin-top:14px;display:flex;gap:8px;flex-wrap:wrap}}
.badge{{background:rgba(91,127,255,0.12);border:1px solid rgba(91,127,255,0.25);color:#8090d0;border-radius:20px;padding:5px 14px;font-size:11px;font-weight:600}}
.badge.green{{background:rgba(36,224,138,0.08);border-color:rgba(36,224,138,0.25);color:#24e08a}}

.category-section{{margin-bottom:32px}}
.category-title{{color:#fff;font-size:1.4em;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.08)}}
.category-count{{color:#7880a0;font-size:0.7em;font-weight:400}}

.cards-grid{{display:flex;flex-direction:column;gap:20px}}

.card{{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:20px;transition:all 0.25s}}
.card:hover{{border-color:rgba(0,212,255,0.3);box-shadow:0 4px 24px rgba(0,212,255,0.06)}}

.card-header{{display:flex;align-items:center;gap:16px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,0.05)}}
.card-ticker-block{{display:flex;align-items:baseline;gap:10px;flex:0 0 auto}}
.card-ticker{{color:#00d4ff;font-weight:700;font-size:1.4em;letter-spacing:0.5px}}
.card-name{{color:#888;font-size:0.95em}}
.card-price-block{{display:flex;align-items:baseline;gap:10px;flex:1}}
.card-price{{color:#fff;font-weight:700;font-size:1.15em}}
.card-change{{font-size:0.95em}}
.card-category{{background:rgba(91,127,255,0.1);border:1px solid rgba(91,127,255,0.2);color:#8090d0;border-radius:14px;padding:3px 12px;font-size:0.8em;font-weight:600;flex:0 0 auto}}

.kline-row{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}}
.kline-cell{{background:#0a0a14;border-radius:10px;padding:8px;overflow:hidden}}
.kline-label{{color:#7880a0;font-size:0.8em;margin-bottom:6px;text-align:center}}
.kline-img{{width:100%;height:auto;display:block;border-radius:6px}}

.metrics-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px;padding:10px;background:rgba(255,255,255,0.02);border-radius:10px}}
.metric{{display:flex;flex-direction:column;align-items:center;gap:4px}}
.metric-key{{color:#7880a0;font-size:0.78em}}
.metric-val{{color:#fff;font-weight:700;font-size:1.05em}}

.rec-block,.news-block{{margin-bottom:12px;padding:12px 14px;background:rgba(255,255,255,0.02);border-radius:10px}}
.rec-block{{border-left:3px solid #00d4ff}}
.news-block{{border-left:3px solid #a855f7}}
.block-title{{color:#00d4ff;font-size:0.85em;font-weight:700;margin-bottom:8px}}
.news-block .block-title{{color:#a855f7}}
.rec-text{{color:#d0d4e0;font-size:0.92em;line-height:1.65;white-space:pre-line}}
.news-list{{list-style:none;padding:0;font-size:0.88em;line-height:1.7}}
.news-list li{{padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04)}}
.news-list li:last-child{{border-bottom:none}}
.news-list a{{color:#00d4ff;text-decoration:none}}
.news-list a:hover{{color:#00ff88;text-decoration:underline}}

.foot{{text-align:center;color:#555;font-size:12px;padding:40px 20px;border-top:1px solid rgba(255,255,255,0.05);margin-top:40px}}
.foot a{{color:#00d4ff;text-decoration:none}}

@media (max-width:900px){{
    .kline-row{{grid-template-columns:1fr}}
    .metrics-row{{grid-template-columns:repeat(2,1fr)}}
    .card-header{{flex-wrap:wrap}}
    .card-price-block{{order:3;width:100%;flex-basis:100%}}
}}
</style>
</head>
<body>
<div class="wrap">
<div class="hero">
    <h1>📊 K 線圖庫｜{DATE_STR}</h1>
    <div class="sub">AI 基礎建設精選 {total_count} 檔 · 半年日 K + 一月日 K + P/E + EPS + AI 推薦 + 最新新聞</div>
    <div class="meta">
        <span class="badge">每日 15:00 台北時間更新</span>
        <span class="badge green">{total_count} 張深度卡</span>
        {rec_badge}
    </div>
</div>

{chr(10).join(sections_html)}

<div class="foot">
    📊 自動產生於 {utc_now} UTC<br>
    資料來源：<a href="https://finance.yahoo.com" target="_blank">Yahoo Finance</a> · 原始碼 <a href="https://github.com/acstep/stock-charts" target="_blank">github.com/acstep/stock-charts</a> · AI 報告來自 <a href="https://acstep.github.io/stock-reports/" target="_blank">stock-reports</a>
</div>
</div>
</body>
</html>'''


def render_index(all_charts):
    """首頁 index.html（維持原樣）"""
    latest = all_charts[0] if all_charts else None
    links = '\n'.join(
        f'<li><a href="charts/{d}">{d}{" ⭐" if d == latest else ""}</a></li>'
        for d in all_charts
    ) or '<li>尚無歷史</li>'

    return f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stock Charts｜每日 K 線圖庫</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC",sans-serif;background:#08080f;color:#e0e4f0;line-height:1.7;padding:40px 20px}}
.wrap{{max-width:800px;margin:0 auto}}
h1{{color:#00d4ff;font-size:2em;margin-bottom:8px;background:linear-gradient(90deg,#00d4ff,#00ff88);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.sub{{color:#7880a0;margin-bottom:30px}}
.card{{background:rgba(255,255,255,0.03);border:1px solid rgba(91,127,255,0.25);border-radius:14px;padding:24px;margin-bottom:20px}}
.card h2{{color:#fff;font-size:1.3em;margin-bottom:8px}}
.btn{{display:inline-block;background:linear-gradient(135deg,#00d4ff,#00ff88);color:#08080f;font-weight:700;padding:12px 24px;border-radius:8px;text-decoration:none;margin-top:10px}}
ul{{list-style:none;padding:0}}
li{{padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)}}
li a{{color:#00d4ff;text-decoration:none}}
li a:hover{{color:#00ff88}}
.foot{{color:#555;font-size:0.85em;margin-top:40px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.05)}}
</style>
</head>
<body>
<div class="wrap">
<h1>📊 Stock Charts</h1>
<p class="sub">每日 AI 基建股 K 線圖庫 · 自動產生（含 P/E、EPS、AI 推薦、最新新聞）</p>

<div class="card">
    <h2>⭐ 最新圖庫</h2>
    <p>{latest or '尚無資料'}</p>
    <a class="btn" href="charts/{latest or ''}" target="_blank">開啟最新深度圖庫 →</a>
</div>

<div class="card">
    <h2>📅 歷史</h2>
    <ul>{links}</ul>
</div>

<div class="foot">
    🚀 自動部署於 <a href="https://github.com/acstep/stock-charts" target="_blank">GitHub Pages</a><br>
    每日 15:00 台北時間從 <a href="https://finance.yahoo.com" target="_blank">Yahoo Finance</a> 抓半年+一月日 K，AI 推薦來自 <a href="https://acstep.github.io/stock-reports/" target="_blank">stock-reports</a>
</div>
</div>
</body>
</html>'''


# ============================================================================
# Main
# ============================================================================

def main():
    os.makedirs(CHARTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, 'recommendations'), exist_ok=True)

    symbols = load_symbols()
    recs = load_recommendations(DATE_STR)
    recs_tickers = (recs.get('tickers') or {}) if recs else {}
    has_recommendations = bool(recs)

    print(f'[build_gallery] {DATE_STR}')
    print(f'  symbols.json: {len(symbols)} 個 ticker')
    print(f'  recommendations JSON: {"✓ " + str(len(recs_tickers)) + " 個 ticker" if recs else "✗ 找不到（將顯示 placeholder）"}')
    print()

    # 對每個 ticker 抓 yfinance info + 找 PNG + 找 recommendations
    cards_by_category = {}  # {cat_key: [card_html, ...]}

    ok = 0
    fail_info = 0

    for sym in symbols:
        # 1. 找 PNG（必須 6mo + 1mo 都有）
        png_6mo = f'{sym}-{DATE_STR}-6mo.png'
        png_1mo = f'{sym}-{DATE_STR}-1mo.png'
        if not (os.path.exists(os.path.join(PNG_DIR, png_6mo)) and
                os.path.exists(os.path.join(PNG_DIR, png_1mo))):
            # 缺任一張就跳過（避免半殘卡片）
            continue

        # 2. 抓 yfinance info
        info = fetch_yfinance_info(sym)
        if info is None:
            fail_info += 1
            # 還是建卡片，但欄位會是 None

        # 3. 從 recommendations 拿推薦 + 新聞
        r = recs_tickers.get(sym, {})
        rec_text = r.get('recommendation')
        news = r.get('news') or []

        # 4. 組裝 item
        item = {
            'symbol': sym,
            'name': (info and info.get('name')) or NAME_MAP.get(sym, sym) or r.get('name', sym),
            'category_label': next((lbl for k, lbl in CATEGORY_ORDER if k == CATEGORY_MAP.get(sym)), ''),
            'price': info['currentPrice'] if info else None,
            'change_pct': info['change_pct'] if info else None,
            'png_6mo': png_6mo,
            'png_1mo': png_1mo,
            'pe_ttm': info['trailingPE'] if info else None,
            'pe_fwd': info['forwardPE'] if info else None,
            'eps_ttm': info['trailingEps'] if info else None,
            'eps_fwd': info['forwardEps'] if info else None,
            'recommendation': rec_text,
            'news': news,
        }

        cat = CATEGORY_MAP.get(sym, '11_其他基建')
        cards_by_category.setdefault(cat, []).append(render_card(item))
        ok += 1

        # 禮貌 sleep，yfinance rate limit
        if info is not None:
            time.sleep(0.1)

    print(f'\n=== 結果：✓ {ok} 卡片  ·  ✗ {fail_info} info 抓不到 ===\n')

    # 組 HTML
    html = render_html(cards_by_category, has_recommendations, ok)
    out_path = os.path.join(CHARTS_DIR, f'{DATE_STR}.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  ✓ {out_path}')

    # 更新 index.html
    all_charts = sorted(
        [d for d in os.listdir(CHARTS_DIR) if re.match(r'^\d{4}-\d{2}-\d{2}\.html$', d)],
        reverse=True,
    )
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(render_index(all_charts))
    print(f'  ✓ {INDEX_FILE} ({len(all_charts)} 歷史頁)')

    return 0 if fail_info == 0 else 1


if __name__ == '__main__':
    sys.exit(main())