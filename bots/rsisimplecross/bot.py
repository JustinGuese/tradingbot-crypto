from datetime import datetime
from os import environ
from pathlib import Path
from ta.momentum import rsi
import pandas as pd
from tradinghandler.trading import TradingInteractor


# environ["SYMBOLS"] = "AVAXUSDT,BNBUSDT,ETHUSDT,XRPUSDT" # debug
SYMBOLS = environ["SYMBOLS"].split(",")

ti = TradingInteractor(environ["BOTNAME"]) # url = "10.147.17.73")
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

for symbol in SYMBOLS:

    try:
        
        data = ti.getData(symbol, 40)
        data["rsi"] = rsi(data["close"], 14)
        positionUp = 0
        if data.iloc[-1]["rsi"] <= 30:
            positionUp = 1
        elif data.iloc[-1]["rsi"] >= 70:
            positionUp = -1
        
        sell = []
        buy = []
        if portfolio.get(symbol) is None:
            if positionUp == 1:
                print("buying " + symbol)
                buy.append(symbol)
                # ti.buy(symbol, usdt / len(SYMBOLS) * 0.95) # buy 95% of usdt / number of symbols
        else:
            if positionUp == -1:
                # sell
                nrHolding = portfolio.get(symbol, 0)
                if nrHolding > 0:
                    print("selling " + symbol)
                    # ti.sell(symbol, -1) # sell all we have
                    sell.append(symbol)
        # first sell
        if len(sell) > 0:
            for symbol in sell:
                ti.sell(symbol, -1)
            portfolio = ti.getPortfolio()
            print(portfolio)
            usdt = portfolio["USDT"]
        # then buy
        if len(buy) > 0:
            for symbol in buy:
                ti.buy(symbol, usdt / len(buy) * 0.95)

    except Exception as e:
        print("problem/skip with: " + symbol + " " + str(e))
        # raise
