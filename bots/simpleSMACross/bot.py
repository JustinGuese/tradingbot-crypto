
# coinsrankday
from os import environ
# simplsmahr
# environ["BOTNAME"] = "simplsmahr"
NAME = "simplsmahr"
# looks at coinsrank dailies and buys top 10 ranks
from tradinghandler.trading import TradingInteractor
import pandas as pd

ti = TradingInteractor(NAME)
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

SYMBOLS = environ["SYMBOLS"].split(",")
#  golden cross. When the 50 EMA moves above the 200 SMA,

def checkCross(symbol):
    # get data
    # 24 hours in a day, so to get 200 we need to get the last 200 days
    # 200 hours are 8.33 days
    data = ti.getData(symbol, lookback=11)
    if len(data) < 200:
        raise ValueError("length of df is less than minimum 200... is: ", len(data))
    data['ema50'] = pd.Series.ewm(data['close'], span=50).mean()
    data['sma200'] = data["close"].rolling(200).mean()
    # newest values are at the top, little weird
    # check if we have a cross
    print("current position of %s. ema50 %.2f and sma200 %.2f is upwardstrend? " % (symbol, data.iloc[-1]['ema50'], data.iloc[-1]['sma200']), data.iloc[-1]['ema50'] > data.iloc[-1]['sma200'])
    if data.iloc[-1]['ema50'] > data.iloc[-1]['sma200'] and data.iloc[-2]['ema50'] <= data.iloc[-2]['sma200']:
        return "upcross", True
    elif data.iloc[-1]['ema50'] < data.iloc[-1]['sma200'] and data.iloc[-2]['ema50'] >= data.iloc[-2]['sma200']:
        return "downcross", False
    else: 
        return "nocross", data.iloc[-1]['ema50'] > data.iloc[-1]['sma200']

for symbol in SYMBOLS:
    try:
        cross, positionUp = checkCross(symbol)
        if portfolio.get(symbol) is None:
            if positionUp:
                print("buying " + symbol)
                ti.buy(symbol, usdt / len(SYMBOLS) * 0.95) # buy 95% of usdt / number of symbols
        else:
            if not positionUp:
                # sell
                print("selling " + symbol)
                ti.sell(symbol, -1) # sell all we have
    except Exception as e:
        print("problem with: " + symbol + " " + str(e))