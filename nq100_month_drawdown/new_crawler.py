import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import ssl

def get_nq100_tickers():
    """
    獲取 NQ100 成分股。
    這裡簡單列舉一些主要的，或從維基百科抓取。
    為求穩定，我們先用一個常用的列表。
    """
    # 也可以考慮從維基百科抓取: 
    # table = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]
    # return table['Ticker'].tolist()
    
    # 為了示範完整性，我們嘗試從維基百科抓取
    try:
        # 解決 SSL 認證問題
        ssl._create_default_https_context = ssl._create_unverified_context
        url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        tables = pd.read_html(url)
        # 通常是第 4 個表格 (索引 3 或 4，視頁面結構而定)
        df = tables[4]
        if 'Ticker' in df.columns:
            return df['Ticker'].tolist()
        elif 'Symbol' in df.columns:
            return df['Symbol'].tolist()
    except Exception as e:
        print(f"無法從維基百科獲取成分股，使用預設列表。錯誤: {e}")
        
    # 預設一些大型科技股作為備案
    return ["AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "NVDA", "AVGO", "PEP"]

def calculate_drawdowns(tickers):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=45) # 抓多一點確保有足夠交易日
    
    results = []
    
    print(f"正在抓取 {len(tickers)} 檔標的的數據...")
    
    # 分批抓取或一次抓取
    data = yf.download(tickers, start=start_date.strftime('%Y-%m-%d'), 
                       end=end_date.strftime('%Y-%m-%d'), progress=False)['Close']
    
    # 如果只有一檔，data 會是 Series，轉換成 DataFrame
    if isinstance(data, pd.Series):
        data = data.to_frame(name=tickers[0])

    for ticker in tickers:
        if ticker not in data.columns:
            continue
            
        prices = data[ticker].dropna()
        if len(prices) < 2:
            continue
            
        # 限制在最近 30 天內的數據 (以日曆日計算)
        # 或者是以最近的 30 個交易日？通常使用者說「最近 30 天」是指日曆日。
        cutoff = prices.index.max() - timedelta(days=30)
        recent_prices = prices[prices.index >= cutoff]
        
        if len(recent_prices) < 2:
            continue
            
        # 最大跌幅 (Max Drawdown)
        # 跌幅定義: (當前價 / 區間最高價) - 1
        cum_max = recent_prices.cummax()
        drawdowns = (recent_prices / cum_max) - 1
        max_dd = drawdowns.min()
        
        # 平均跌幅
        # 這裡的「平均跌幅」通常指所有負報酬的平均，或是每日回撤的平均
        # 我們計算每日相對於區間最高點的回撤平均
        avg_dd = drawdowns.mean()
        
        results.append({
            'Ticker': ticker,
            'Max_Drawdown': round(max_dd * 100, 2), # 轉百分比
            'Avg_Drawdown': round(avg_dd * 100, 2), # 轉百分比
            'Start_Date': recent_prices.index.min().strftime('%Y-%m-%d'),
            'End_Date': recent_prices.index.max().strftime('%Y-%m-%d'),
            'Trading_Days': len(recent_prices)
        })
        
    return pd.DataFrame(results)

def main():
    tickers = get_nq100_tickers()
    df = calculate_drawdowns(tickers)
    
    if df.empty:
        print("沒有抓取到任何數據。")
        return

    # 排序：按最大跌幅排序 (跌越多排越前面)
    df = df.sort_values(by='Max_Drawdown', ascending=True)
    
    out_dir = Path(__file__).resolve().parent.parent / "database"
    out_dir.mkdir(parents=True, exist_ok=True)
    output_file = out_dir / "nq100_30d_drawdown.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n計算完成！")
    print(f"輸出檔案: {output_file}")
    print("\n前 10 名最大跌幅標的:")
    print(df.head(10)[['Ticker', 'Max_Drawdown', 'Avg_Drawdown']])

if __name__ == "__main__":
    main()
