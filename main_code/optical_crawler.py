from pathlib import Path

import yfinance as yf
import pandas as pd
import gspread
from datetime import datetime, timedelta

def get_optical_tickers():
    # List of US stocks focused on the optical communication industry
    return ["COHR", "LITE", "FN", "INFN", "MRVL", "AVGO", "CRDO", "ANET", "CIEN", "CSCO", "GLW"]

def calculate_drawdowns(tickers):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=45) # Fetch more data to ensure enough trading days
    
    results = []
    
    print(f"正在抓取 {len(tickers)} 檔標的的數據...")
    
    data = yf.download(tickers, start=start_date.strftime("%Y-%m-%d"), 
                       end=end_date.strftime("%Y-%m-%d"), progress=False)["Close"]
    
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])

    for ticker in tickers:
        if ticker not in data.columns:
            continue
            
        prices = data[ticker].dropna()
        if len(prices) < 2:
            continue
            
        cutoff = prices.index.max() - timedelta(days=30)
        recent_prices = prices[prices.index >= cutoff]
        
        if len(recent_prices) < 2:
            continue
            
        cum_max = recent_prices.cummax()
        drawdowns = (recent_prices / cum_max) - 1
        max_dd = drawdowns.min()
        
        avg_dd = drawdowns.mean()
        
        results.append({
            "Ticker": ticker,
            "Max_Drawdown": round(max_dd * 100, 2),
            "Avg_Drawdown": round(avg_dd * 100, 2),
            "Start_Date": recent_prices.index.min().strftime("%Y-%m-%d"),
            "End_Date": recent_prices.index.max().strftime("%Y-%m-%d"),
            "Trading_Days": len(recent_prices)
        })
        
    return pd.DataFrame(results)

def main():
    tickers = get_optical_tickers()
    df = calculate_drawdowns(tickers)
    
    if df.empty:
        print("沒有抓取到任何數據。")
        return

    df = df.sort_values(by='Max_Drawdown', ascending=True)
    
    out_dir = Path(__file__).resolve().parent.parent / "database"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_file = out_dir / "optical_30d_drawdown.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    # Upload to Google Sheets
    try:
        gc = gspread.service_account(
            filename=str(Path(__file__).resolve().parent.parent / "credentials.json")
        )
        sh = gc.open('NQ100_DATA')
        worksheet = sh.sheet1
        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        print("數據已成功上傳到 Google Sheets。")
    except Exception as e:
        print(f"上傳 Google Sheets 失敗: {e}")
    
    print(f"\n計算完成！")
    print(f"輸出檔案: {output_file}")
    print("\n前 10 名最大跌幅標的:")
    print(df.head(10)[["Ticker", "Max_Drawdown", "Avg_Drawdown"]])

if __name__ == "__main__":
    main()