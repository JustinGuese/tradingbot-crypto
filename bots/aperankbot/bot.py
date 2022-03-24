# aperankday
NAME = "aperankday"
# looks at aperank dailies and buys top 10 ranks
from tradinghandler.trading import TradingInteractor

ti = TradingInteractor(NAME)
usdt = float(ti.getUSD())

ape = ti.getApeWisdom()

