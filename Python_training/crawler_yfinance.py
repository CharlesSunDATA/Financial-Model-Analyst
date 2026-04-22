



import yfinance as yf
import gspread

from datetime import datetime ,timezone

def convert_unix_timestamp_to_date(unix_timestamp):
    try:
        date = datetime.fromtimestamp(unix_timestamp, timezone.utc).strftime('%Y-%m-%d')
        return date
    except Exception as e:
        print(f"Error converting Unix timestamp to date: {e}")
        return None

def get_forward_PE(stock_symbol):
    try:
        stock = yf.Ticker(stock_symbol)
        forward_PE = stock.info['forwardPE']
        return forward_PE
    except Exception as e:
        print(f"Error retrieving forward PE for {stock_symbol}: {e}")
        return None


def get_price(stock_symbol):
    try:
        stock = yf.Ticker(stock_symbol)
        price = stock.info['open']
        return price
    except Exception as e:
        print(f"Error retrieving forward PE for {stock_symbol}: {e}")
        return None
    
def get_targetMedianPrice(stock_symbol):
    try:
        stock = yf.Ticker(stock_symbol)
        targetMedianPrice = stock.info['targetMedianPrice']
        return targetMedianPrice
    except Exception as e:
        print(f"Error retrieving forward PE for {stock_symbol}: {e}")
        return None

def get_mostRecentQuarter(stock_symbol):
    try:
        stock = yf.Ticker(stock_symbol)
        mostRecentQuarter = stock.info['mostRecentQuarter']
        date = convert_unix_timestamp_to_date(mostRecentQuarter)
        return date
        #return nextFiscalYearEnd
    except Exception as e:
        print(f"Error retrieving forward PE for {stock_symbol}: {e}")
        return None

# 用法示例
stock_symbols = ["AAPL", "NVDA","TSLA"]  # 你可以添加更多的股票代码
for symbol in stock_symbols:
    forward_PE = get_forward_PE(symbol)
    price = get_price(symbol)
    targetMedianPrice = get_targetMedianPrice(symbol)
    nextFiscalYearEnd = get_mostRecentQuarter(symbol)







data = [['Stock Symbol','Price', 'Forward PE','Target Median Price','Recent Quarter']]

# 获取每个股票的前向PE值并将其添加到数据列表中
for symbol in stock_symbols:
    forward_PE = get_forward_PE(symbol)
    price=get_price(symbol)
    targetMedianPrice=get_targetMedianPrice(symbol)
    nextFiscalYearEnd = get_mostRecentQuarter(symbol)

    if forward_PE is not None and price is not None:
        data.append([symbol,price,forward_PE,targetMedianPrice,nextFiscalYearEnd])


# 设置 Google Sheets 凭证
gc = gspread.service_account(filename='/Users/charles/Desktop/Python_training/Json/alert-cedar-419523-21be939107a8.json')

# 授权访问 Google Sheets
sh = gc.open("python import")
worksheet = sh.sheet1
        
# 清空工作表的内容
worksheet.clear()

worksheet.update('A1',data)