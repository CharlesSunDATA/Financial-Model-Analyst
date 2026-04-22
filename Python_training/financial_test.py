import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.arima_model import ARIMA

# Load data
df = pd.read_csv('AAPL_histery_data.csv')

# Data cleaning
df = df.dropna()
df['Date'] = pd.to_datetime(df['Date'])

# Exploratory Data Analysis
print(df.describe())

# Visualize closing price
plt.figure(figsize=(10, 6))
plt.plot(df['Date'], df['Close'])
plt.title('Stock Closing Prices Over Time')
plt.xlabel('Date')
plt.ylabel('Close Price')
plt.show()

# Calculate moving averages
df['SMA_50'] = df['Close'].rolling(window=50).mean()
df['SMA_200'] = df['Close'].rolling(window=200).mean()

# Plot moving averages
plt.figure(figsize=(10, 6))
plt.plot(df['Date'], df['Close'], label='Close Price')
plt.plot(df['Date'], df['SMA_50'], label='50-day SMA')
plt.plot(df['Date'], df['SMA_200'], label='200-day SMA')
plt.title('Stock Price with Moving Averages')
plt.xlabel('Date')
plt.ylabel('Price')
plt.legend()
plt.show()

# ARIMA model
model = ARIMA(df['Close'], order=(5,1,0))
model_fit = model.fit(disp=0)
plt.plot(df['Date'], df['Close'])
plt.plot(df['Date'], model_fit.fittedvalues, color='red')
plt.title('ARIMA Model')
plt.show()
