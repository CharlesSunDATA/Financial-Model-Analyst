# NQ100 最大回撤排行（Yahoo Finance 日線）

預設會上網抓價、覆寫上一層 `database/nq100_daily_prices.csv`，並寫入 `database/nq100_max_drawdown_last_month_rank.csv`。成分與產業來自 `database/nq100_health_metrics.csv`。

## 一次性執行

```bash
cd main_code
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python nq100_month_drawdown.py
```

離線（只讀既有日線）：

```bash
python nq100_month_drawdown.py --local-only
```

## 每日自動更新（macOS / Linux：`cron`）

1. 確認 `run_daily.sh` 可執行：`chmod +x run_daily.sh`
2. 編輯排程（將路徑改成你的專案路徑）：

```bash
crontab -e
```

例如每個**美股交易日約收盤後**（此例為 UTC 21:30，請依你時區調整）：

```
30 21 * * 1-5 /Users/charles/Desktop/Python/main_code/run_daily.sh
```

日誌寫在 `main_code/logs/daily.log`。

## 常用參數

| 參數 | 說明 |
|------|------|
| `--days 22` | 最近幾個交易日算回撤 |
| `--yf-period 3mo` | yfinance 下載區間（須夠長以涵蓋 `--days`） |
| `--no-save-prices` | 只更新排行、不覆寫日線 CSV |
| `--prices` / `--rank-out` | 自訂日線與排行輸出路徑 |
