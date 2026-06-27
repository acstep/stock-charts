#!/bin/bash
# 每日 14:00 跑 K 線截圖（120 個交易日 / 半年）+ 圖庫產生 + push
# 這個 job 用 google/gemma-4-31b-it 跑（單純 shell script，省 token）
#
# 用法：
#   bash run-charts.sh                      # 重抓全部
#   bash run-charts.sh --only NVDA,AMD,WDC  # 只重抓指定的（修補用）
#   bash run-charts.sh --skip-screenshot    # 只 rebuild gallery + push
set -e

DATE_STR=$(TZ=Asia/Taipei date +%Y-%m-%d)
cd /home/matt/.openclaw/workspace/stock-charts

# 解析參數
ONLY_FLAG=""
SKIP_SCREENSHOT=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --only)
            ONLY_FLAG="--only $2"
            shift 2
            ;;
        --skip-screenshot)
            SKIP_SCREENSHOT=true
            shift
            ;;
        *)
            echo "Unknown arg: $1"
            exit 1
            ;;
    esac
done

if [ -n "$ONLY_FLAG" ]; then
    echo "[$(date +%H:%M:%S)] === 模式：只重抓 $ONLY_FLAG ==="
fi

echo "[$(date +%H:%M:%S)] Step 1: 找最新報告"
REPORT=$(ls -t /home/matt/.openclaw/workspace/stock-reports/reports/*.html 2>/dev/null | head -1)
if [ -z "$REPORT" ]; then
    echo "ERROR: 找不到 stock-reports"
    exit 1
fi
echo "  → $REPORT"

if [ "$SKIP_SCREENSHOT" = false ]; then
    echo "[$(date +%H:%M:%S)] Step 2: 抓 K 線截圖（120 個交易日 / 半年）"
    if [ -n "$ONLY_FLAG" ]; then
        node scripts/screenshot_charts.js "$REPORT" ./png $ONLY_FLAG 2>&1 | tail -20
    else
        node scripts/screenshot_charts.js "$REPORT" ./png 2>&1 | tail -20
    fi
fi

echo "[$(date +%H:%M:%S)] Step 3: 產生圖庫頁"
node scripts/build_gallery.js 2>&1 | tail -5

# 檢查 build_gallery.js 是否把缺圖的股票跳過了
if [ -n "$ONLY_FLAG" ]; then
    echo "[$(date +%H:%M:%S)] (--only 模式) 跳過自動 push，請手動確認後再 push"
    echo "Done (local only)。Push 指令："
    echo "  git add png/ charts/ index.html"
    echo "  git commit -m 'fix: 重抓 $ONLY_FLAG'"
    echo "  GIT_TERMINAL_PROMPT=0 git push origin main"
    exit 0
fi

echo "[$(date +%H:%M:%S)] Step 4: git push"
git add png/ charts/ index.html 2>&1
if git diff --cached --quiet; then
    echo "  (沒新東西要 push)"
    exit 0
fi
git commit -m "Daily K-line charts ${DATE_STR}" 2>&1 | tail -3
GIT_TERMINAL_PROMPT=0 git push origin main 2>&1 | tail -3

echo "[$(date +%H:%M:%S)] ✅ Done"
