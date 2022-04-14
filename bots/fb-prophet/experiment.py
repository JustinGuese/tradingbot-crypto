from prophet import Prophet
import yfinance as yf

data = yf.download("AAPL", period = "5y", interval = "1d")
