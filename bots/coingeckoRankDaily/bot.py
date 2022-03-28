
# coinsrankday
NAME = "CGtrendhr"
# looks at coinsrank dailies and buys top 10 ranks
from tradinghandler.trading import TradingInteractor
from pprint import pprint
from requests import get

ti = TradingInteractor(NAME)
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]


headers = {
    'accept': 'application/json',
}

coins = get('https://api.coingecko.com/api/v3/search/trending', headers=headers).json()["coins"]

# keep only names
coins = [c["item"]["symbol"] + "USDT" for c in coins]


weights = [.2, .15, .13, .12, .11, .1, .1] # ~0.9
# first sell if not in there anymore
for position in portfolio:
    if position not in coins and position != "USDT":
        print("trying to sell: ", position)
        ti.sell(position, -1)
# then get new volume
ti.portfolio = None # force new download
usdt = ti.getUSD()
print("i have %.2f $ to spend" % usdt)
nrPurchases = 0 # max 10
i = 0
for symbol in coins:
    print("trying to buy: ", symbol)
    try:
        portf = ti.buy(symbol, weights[i] * usdt)
        i += 1
    except Exception as e:
        print("problem with buying %s. will skip to next" % symbol)

pprint(portf)