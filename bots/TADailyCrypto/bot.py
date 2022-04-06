
# coinsrankday
from cgitb import strong
from os import environ
NAME = environ["BOTNAME"]
# NAME = "CGtrendhr"
# looks at coinsrank dailies and buys top 10 ranks
from tradinghandler.trading import TradingInteractor
from pprint import pprint
from requests import get

ti = TradingInteractor(NAME)
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

strongbuys = []
buys = []
sells = []
strongsells = []

for symbol in "BTCUSDT,ETHUSDT,MATICUSDT,AVAXUSDT,XRPUSDT,BNBUSDT,LINKUSDT,ADAUSDT".split(","):
    decision = ti.getTARecommendation(symbol)
    # will be one of: None, SELL; BUY; NEUTRAL; STRONG_SELL; STRONG_BUY
    if decision is None:
        print("uhoh, symbol decision for %s is None!!!" % symbol)
    else:
        amountInPortfolio = 0
        if portfolio.get(symbol) is not None:
            amountInPortfolio = portfolio.get(symbol)
        if amountInPortfolio > 0:
            # we already have some
            if decision == "STRONG_BUY": # strong buy always nachkaufen
                buys.append(symbol)
            elif decision in ["SELL", "STRONG_SELL", "NEUTRAL"]:
                # sell it
                sells.append(symbol)
        else:
            # we did not buy it yet
            if decision == "STRONG_BUY":
                strongbuys.append(symbol)
            elif decision == "BUY":
                buys.append(symbol)

# then sell all first we have
for sell in sells:
    print("selling %s" % sell)
    ti.sell(sell, -1)
# get newest networth
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]
strongbuybudget = usdt * .75
buybudget = usdt * .25
if usdt > 10:
    for buy in strongbuys:
        print("strong buy %s" % buy)
        ti.buy(buy, strongbuybudget / len(strongbuybudget))
    for buy in buys:
        print("strong buy %s" % buy)
        ti.buy(buy, buybudget / len(buys))
