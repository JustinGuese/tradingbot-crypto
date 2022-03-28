# aperankday
from os import environ
NAME = environ["BOTNAME"] # "aperankhr"
# looks at aperank dailies and buys top 10 ranks
from tradinghandler.trading import TradingInteractor
from pprint import pprint

ti = TradingInteractor(NAME)
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

ape = ti.getApeWisdomLast()
# take top 10
ape = ape[:20]
# keep only names
ape = [x["ticker"] for x in ape]

weights = [.15, .13, .11, .1, .1, .1, .08, .07, .06, .05] # ~0.95
# first sell if not in there anymore
for position in portfolio:
    if position not in ape and position != "USDT":
        print("trying to sell: ", position)
        ti.sell(position, -1)
# then get new volume
ti.portfolio = None # force new download
usdt = ti.getUSD()
print("i have %.2f $ to spend" % usdt)
nrPurchases = 0 # max 10
for i,symbol in enumerate(ape):
    if symbol in list(portfolio.keys()):
        continue
    if nrPurchases >= 10:
        break # stop buying
    # else buy
    print("trying to buy: ", symbol)
    try:
        portf = ti.buy(symbol, weights[i] * usdt)
    except Exception as e:
        print("problem with buying %s. will skip to next" % symbol)

pprint(portf)