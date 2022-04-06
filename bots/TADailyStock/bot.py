
# coinsrankday
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


headers = {
    'accept': 'application/json',
}
