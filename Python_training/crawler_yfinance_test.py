import yfinance as yf

# 用法示例
stock_symbols = ["AAPL"]

with open("data.txt", "w") as f:
    for symbol in stock_symbols:
        stock = yf.Ticker(symbol)
        f.write(f"Stock symbol: {symbol}\n")
        f.write("Available info keys:\n")
        for key, value in stock.info.items():
            f.write(f"{key}: {value}\n")
        f.write("\n")