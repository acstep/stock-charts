#!/usr/bin/env python3
"""
build_gallery.py — 從 png/ 資料夾產生 K 線圖庫 HTML
跟舊 build_gallery.js 一樣的視覺風格（深色主題、2 欄網格）
"""
import os
import re
import sys
from datetime import datetime, timezone, timedelta

TPE = timezone(timedelta(hours=8))

ROOT = os.path.dirname(os.path.abspath(__file__))
PNG_DIR = os.path.join(ROOT, 'png')
CHARTS_DIR = os.path.join(ROOT, 'charts')
INDEX_FILE = os.path.join(ROOT, 'index.html')

# 台北時間日期
DATE_STR = datetime.now(TPE).strftime('%Y-%m-%d')

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
}


def gallery_html(items):
    cards = '\n'.join(
        f'''    <div class="card">
        <a href="{it['yahoo']}" target="_blank" rel="noopener">
            <img class="card-img" src="{it['png']}" alt="{it['symbol']} K 線圖" loading="lazy">
            <div class="card-meta">
                <div class="card-ticker">{it['symbol']}</div>
                <div class="card-name">{it['name']}</div>
                <div class="card-hint">→ 在 Yahoo Finance 開啟完整 K 線</div>
            </div>
        </a>
    </div>'''
        for it in items
    )

    utc_now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')

    return f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>K 線圖庫｜{DATE_STR} · AI 基建股（半年日 K）</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;background:#08080f;color:#e0e4f0;line-height:1.65;padding:0}}
.wrap{{max-width:1400px;margin:0 auto;padding:24px}}

.hero{{background:linear-gradient(135deg,#08081a 0%,#1a0a2a 50%,#0a0a1a 100%);border:1px solid rgba(91,127,255,0.25);border-radius:20px;padding:36px 40px;margin-bottom:24px;position:relative;overflow:hidden}}
.hero::before{{content:'';position:absolute;top:-50%;right:-20%;width:500px;height:500px;background:radial-gradient(circle,rgba(91,127,255,0.08) 0%,transparent 70%);pointer-events:none}}
.hero h1{{font-size:30px;color:#fff;margin-bottom:8px;letter-spacing:-0.5px;position:relative;background:linear-gradient(90deg,#00d4ff,#00ff88);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hero .sub{{color:#7880a0;font-size:13px;margin-bottom:4px;position:relative}}
.hero .meta{{margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;position:relative}}
.badge{{background:rgba(91,127,255,0.12);border:1px solid rgba(91,127,255,0.25);color:#8090d0;border-radius:20px;padding:5px 14px;font-size:11px;font-weight:600}}
.badge.green{{background:rgba(36,224,138,0.08);border-color:rgba(36,224,138,0.25);color:#24e08a}}
.badge.purple{{background:rgba(168,85,247,0.10);border-color:rgba(168,85,247,0.25);color:#a855f7}}

.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media (max-width:768px){{.grid{{grid-template-columns:1fr}}}}

.card{{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:14px;overflow:hidden;transition:all 0.25s}}
.card:hover{{border-color:rgba(0,212,255,0.4);box-shadow:0 8px 32px rgba(0,212,255,0.1);transform:translateY(-2px)}}
.card a{{display:block;text-decoration:none;color:inherit}}
.card-img{{width:100%;height:auto;display:block;background:#0a0a14;min-height:280px;object-fit:cover;object-position:top}}
.card-meta{{padding:12px 16px;border-top:1px solid rgba(255,255,255,0.05)}}
.card-ticker{{color:#00d4ff;font-weight:700;font-size:1.05em;letter-spacing:0.5px}}
.card-name{{color:#888;font-size:0.85em;margin-top:2px}}
.card-hint{{color:#a855f7;font-size:0.75em;margin-top:6px;display:flex;align-items:center;gap:4px}}

.foot{{text-align:center;color:#555;font-size:12px;padding:40px 20px;border-top:1px solid rgba(255,255,255,0.05);margin-top:40px}}
.foot a{{color:#00d4ff;text-decoration:none}}
</style>
</head>
<body>
<div class="wrap">
<div class="hero">
    <h1>📊 K 線圖庫｜{DATE_STR}</h1>
    <div class="sub">AI 基礎建設精選股 · 半年（120 個交易日）日 K + 成交量</div>
    <div class="meta">
        <span class="badge">每日 15:00 台北時間更新</span>
        <span class="badge green">{len(items)} 張 K 線</span>
        <span class="badge purple">點圖連 Yahoo Finance</span>
    </div>
</div>

<div class="grid">
{cards}
</div>

<div class="foot">
    📊 自動產生於 {utc_now} UTC<br>
    資料來源：<a href="https://finance.yahoo.com" target="_blank">Yahoo Finance</a> · 原始碼 <a href="https://github.com/acstep/stock-charts" target="_blank">github.com/acstep/stock-charts</a>
</div>
</div>
</body>
</html>'''


def index_html(all_charts):
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
<p class="sub">每日 AI 基建股 K 線圖庫 · 自動產生</p>

<div class="card">
    <h2>⭐ 最新圖庫</h2>
    <p>{latest or '尚無資料'}</p>
    <a class="btn" href="charts/{latest or ''}" target="_blank">開啟最新 K 線圖庫 →</a>
</div>

<div class="card">
    <h2>📅 歷史</h2>
    <ul>{links}</ul>
</div>

<div class="foot">
    🚀 自動部署於 <a href="https://github.com/acstep/stock-charts" target="_blank">GitHub Pages</a><br>
    每日 15:00 台北時間從 <a href="https://finance.yahoo.com" target="_blank">Yahoo Finance</a> 抓半年日 K 並自動生成圖庫
</div>
</div>
</body>
</html>'''


def main():
    os.makedirs(CHARTS_DIR, exist_ok=True)

    # 掃當天 PNG
    pngs = [f for f in os.listdir(PNG_DIR) if f.endswith(f'-{DATE_STR}.png')]
    print(f'[build_gallery] {DATE_STR}  ·  {len(pngs)} PNGs')

    items = []
    for f in sorted(pngs):
        sym = f.replace(f'-{DATE_STR}.png', '')
        items.append({
            'symbol': sym,
            'name': NAME_MAP.get(sym, sym),
            'png': f'../png/{f}',
            'yahoo': f'https://finance.yahoo.com/chart/{sym}',
        })

    out = os.path.join(CHARTS_DIR, f'{DATE_STR}.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(gallery_html(items))
    print(f'  ✓ {out}')

    # 掃所有歷史 charts/HTML
    all_charts = sorted(
        [d for d in os.listdir(CHARTS_DIR) if re.match(r'^\d{4}-\d{2}-\d{2}\.html$', d)],
        reverse=True,
    )
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(index_html(all_charts))
    print(f'  ✓ {INDEX_FILE} ({len(all_charts)} 歷史頁)')

    return 0


if __name__ == '__main__':
    sys.exit(main())
