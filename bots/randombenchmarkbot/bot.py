from tradinghandler.trading import TradingInteractor
from os import environ
from random import random

# environ["SYMBOLS"] = "AVAXUSDT,BNBUSDT,ETHUSDT,XRPUSDT" # debug
SYMBOLS = environ["SYMBOLS"].split(",")

ti = TradingInteractor(environ["BOTNAME"]) # url = "10.147.17.73")
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]
for symbol in SYMBOLS:
    randomnumber = random()
    # will be between 0. and 1.
    # buy in .5 of cases
    if randomnumber <= 0.5:
        if portfolio.get(symbol, 0) == 0:
            # buy
            ti.buy(symbol, usdt / 2)
    elif randomnumber >= .98: # only sell in 2 pct of cases
        if portfolio.get(symbol, 0) > 0:
            # sell
            ti.sell(symbol, portfolio[symbol])