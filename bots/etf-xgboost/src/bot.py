from train import getModel, trainModel, getPreparedData
from os import environ
from tradinghandler.trading import TradingInteractor
import numpy as np
import warnings
warnings.filterwarnings("ignore")

ti = TradingInteractor(environ["BOTNAME"])
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

SYMBOL = environ["SYMBOL"]
TIMEFRAME = environ["TIMEFRAME"]

model = getModel(SYMBOL, TIMEFRAME)
X, Y = getPreparedData(SYMBOL, TIMEFRAME)
prediction = np.median(model.predict(X)[-3:])
# just take the mean of the prediction
# 1 is buy, 0 is sell

TISYMBOL = SYMBOL + "USD" # aims at etf
if prediction == 1 and portfolio.get(TISYMBOL, 0) == 0 and usdt > 10:
    print("buying " + TISYMBOL)
    ti.buy(SYMBOL, usdt)
elif prediction == 0 and portfolio.get(TISYMBOL, 0) > 0:
    print("selling " + TISYMBOL)
    ti.sell(SYMBOL, -1)
else:
    if prediction == 0.:
        prediction = "sell"
    elif prediction == 1.:
        prediction = "buy"
    print("do nothing. but i predict: " + str(prediction))