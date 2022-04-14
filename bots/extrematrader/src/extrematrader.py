import yfinance as yf
import pandas as pd
from scipy.signal import argrelextrema
import numpy as np
from tradinghandler.trading import TradingInteractor
from os import environ

ti = TradingInteractor(environ["BOTNAME"])
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

symbdict = {
    "ETH-USD" : "ETHUSDT",
    "BNB-USD" : "BNBUSDT",
    "SOL-USD" : "SOLUSDT",
    "XRP-USD" : "XRPUSDT",
    "AAPL" : "AAPLUSD",
    "MSFT" : "MSFTUSD",
    "TSLA" : "TSLAUSD",
}
SYMBOLS = list(symbdict.keys())

def setExtrema(df):
    n = 20

    df['minextrema'] = df.iloc[argrelextrema(df.Close.values, np.less_equal,
                        order=n)[0]]['Close']
    df['maxextrema'] = df.iloc[argrelextrema(df.Close.values, np.greater_equal,
                            order=n)[0]]['Close']
    return df

def whatWasLast(df):
    for i in reversed(range(len(df))):
        if df.iloc[i]['Close'] == df.minextrema.iloc[i]:
            return "min"
        elif df.iloc[i]['Close'] == df.maxextrema.iloc[i]:
            return "max"

# gedd data
# STOCKS = environ["STOCKNAMES"].split(",")
for stock in SYMBOLS:
    try:
        data = yf.download(stock, period = "200d", interval = "1d", progress = False)
        data = setExtrema(data)
        # lastDir = whatWasLast(data)
        if len(data) == 0:
            print("uhohhhh data is zero for: ", stock)
        holdingNr = portfolio.get(symbdict[stock], 0)
        # print(data.iloc[-5:]["maxextrema"])
        if not np.isnan(data.iloc[-1]["maxextrema"]):
            # our current value is still a maxextrema
            if holdingNr == 0:
                print("current is max extrema for %s. buy now! crntMax" % stock)
                # buy it
                ti.buy(symbdict[stock], usdt / len(SYMBOLS))
        # elif lastDir == "min":
        #     # buy
        #     if holdingNr == 0:
        #         print("current is max extrema for %s. buy now! lastDirMin" % stock)
        #         # buy it
        #         ti.buy(symbdict[stock], usdt / len(SYMBOLS))
        # elif lastDir == "max":
        #     # sell
        #     if holdingNr > 0:
        #         # sell it
        #         print("current is min extrema for %s. sell now! lastDirMax" % stock)
        #         ti.sell(symbdict[stock], -1)
        else:
            # our current value is still a minextrema
            if holdingNr > 0:
                # sell it
                print("current is min extrema for %s. sell now!" % stock)
                ti.sell(symbdict[stock], -1)
    except Exception as e:
        # print(e)
        raise