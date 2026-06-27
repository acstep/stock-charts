#!/usr/bin/env python3
"""
kline_generator.py — 從 Yahoo Finance 抓半年日 K + mplfinance 畫圖
GitHub Actions 每天 15:00 台北時間（07:00 UTC）跑一次

Usage:
  python kline_generator.py            # 跑當天
  python kline_generator.py --date 2026-06-28   # 跑指定日期（補資料用）
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import matplotlib
matplotlib.use('Agg')  # 沒 X server 也跑得了

import mplfinance as mpf
import pandas as pd
import yfinance as yf

# 台北時區
TPE = timezone(timedelta(hours=8))

ROOT = os.path.dirname(os.path.abspath(__file__))
SYMBOLS_FILE = os.path.join(ROOT, 'symbols.json')
PNG_DIR = os.path.join(ROOT, 'png')

# 股票名稱對照（沿用舊 build_gallery.js 的 NAME_MAP，缺的話用 ticker 本身）
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


def load_symbols():
    with open(SYMBOLS_FILE) as f:
        return json.load(f)


def fetch_one(symbol, period='6mo'):
    """抓一支股票的 OHLCV 資料，回傳清理過的 DataFrame。失敗回 None。"""
    try:
        df = yf.download(symbol, period=period, interval='1d',
                         progress=False, auto_adjust=False)
    except Exception as e:
        print(f'  ✗ {symbol}: fetch error: {e}', file=sys.stderr)
        return None

    if df is None or df.empty:
        print(f'  ✗ {symbol}: empty data', file=sys.stderr)
        return None

    # yfinance 新版會回 multi-index columns（Price, Ticker），攤平成單層
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 確保欄位齊全
    needed = {'Open', 'High', 'Low', 'Close', 'Volume'}
    if not needed.issubset(df.columns):
        print(f'  ✗ {symbol}: missing columns {needed - set(df.columns)}',
              file=sys.stderr)
        return None

    return df[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()


def plot_one(df, symbol, out_path):
    """畫 K 線圖（半年日 K + 成交量），存到 out_path。"""
    name = NAME_MAP.get(symbol, symbol)

    # 自訂 mplfinance style（簡單、白底、清楚）
    custom_style = mpf.make_mpf_style(
        base_mpl_style='classic',
        marketcolors=mpf.make_marketcolors(
            up='#26a69a', down='#ef5350',
            edge='inherit', wick='inherit', volume='inherit',
        ),
        gridstyle=':',
        gridcolor='#dddddd',
        rc={'font.size': 10, 'axes.labelsize': 10, 'axes.titlesize': 12},
    )

    fig, axes = mpf.plot(
        df,
        type='candle',
        volume=True,
        style=custom_style,
        title=f'{symbol}  ·  {name}  ·  6-Month Daily',
        ylabel='Price (USD)',
        ylabel_lower='Volume',
        figsize=(12, 7),
        returnfig=True,
    )
    fig.savefig(out_path, dpi=100, bbox_inches='tight')
    plt_close(fig)
    return os.path.getsize(out_path)


def plt_close(fig):
    """mplfinance 回傳的 Figure 物件需要主動 close，否則吃 memory。"""
    import matplotlib.pyplot as plt
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', help='指定日期 YYYY-MM-DD（預設今天台北時間）')
    parser.add_argument('--period', default='6mo', help='yfinance period 參數')
    parser.add_argument('--limit', type=int, default=0, help='只跑前 N 檔（測試用）')
    args = parser.parse_args()

    if args.date:
        date_str = args.date
    else:
        date_str = datetime.now(TPE).strftime('%Y-%m-%d')

    os.makedirs(PNG_DIR, exist_ok=True)
    symbols = load_symbols()
    if args.limit:
        symbols = symbols[:args.limit]

    print(f'[kline_generator] {date_str}  ·  {len(symbols)} symbols  ·  period={args.period}')

    ok, fail, skipped = 0, 0, 0
    failed_list = []

    for i, sym in enumerate(symbols, 1):
        out_path = os.path.join(PNG_DIR, f'{sym}-{date_str}.png')
        if os.path.exists(out_path) and not args.limit:
            print(f'  [{i:2d}/{len(symbols)}] {sym} 已存在，跳過')
            skipped += 1
            continue

        df = fetch_one(sym, period=args.period)
        if df is None or df.empty:
            fail += 1
            failed_list.append(sym)
            time.sleep(0.5)
            continue

        try:
            size = plot_one(df, sym, out_path)
            print(f'  [{i:2d}/{len(symbols)}] ✓ {sym} ({len(df)} 交易日, {size//1024} KB)')
            ok += 1
        except Exception as e:
            print(f'  [{i:2d}/{len(symbols)}] ✗ {sym}: plot error: {e}', file=sys.stderr)
            fail += 1
            failed_list.append(sym)

        # rate limit 禮貌：每支 sleep 0.3s
        time.sleep(0.3)

    print()
    print(f'=== 結果：✓ {ok}  ·  ✗ {fail}  ·  ⤼ {skipped} 跳過 ===')
    if failed_list:
        print(f'失敗清單：{", ".join(failed_list)}')
        # 不要 exit 1，gallery 還是會用成功的部分建
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
