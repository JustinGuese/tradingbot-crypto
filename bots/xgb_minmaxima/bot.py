from train import preprocess, doTraining, loadModel
from tradinghandler.trading import TradingInteractor
from pathlib import Path
from datetime import time, datetime
from os import environ
import numpy as np



ti = TradingInteractor(environ["BOTNAME"])
portfolio = ti.getPortfolio()
usdt = portfolio.get("USDT")

# hardcoded bc too complicated for yfinance
symbdict = {
    "ETH-USD" : "ETHUSDT",
    "BNB-USD" : "BNBUSDT",
    "SOL-USD" : "SOLUSDT",
    "XRP-USD" : "XRPUSDT",
}
SYMBOLS = list(symbdict.keys())

toBuy = []
for symbol in SYMBOLS:
    if Path("persistent/%s_model.json" % symbol).is_file():
        model = loadModel(symbol)
    # every day retraining between 11:30 and 12
    elif time(11,30) < datetime.now().time() < time(12,0):
        doTraining(symbol, lookback = environ["LOOKBACK_TRAINING"], interval = environ["INTERVAL"])
        model = loadModel(symbol)
    else:
        doTraining(symbol, lookback = environ["LOOKBACK_TRAINING"], interval = environ["INTERVAL"])
        model = loadModel(symbol)
    X, Y = preprocess(symbol, lookback = environ["LOOKBACK_PREDICTION"])
    pred = model.predict(X)
    # latestPredictions = pred[-2:]
    latestPrediction = np.median(pred[-int(environ["LOOKBACK_MEDIAN_PRED"]):])
    if portfolio.get(symbdict[symbol], 0) > 0 and latestPrediction == -1:
        print("Selling %s" % symbol)
        ti.sell(symbdict[symbol], -1)
    elif portfolio.get(symbdict[symbol], 0) == 0 and latestPrediction == 1:
        # ti.buy(symbol, 1)
        toBuy.append(symbdict[symbol])

portfolio = ti.getPortfolio()
usdt = portfolio.get("USDT")
for symbol in toBuy:
    print("Buying %s" % symbol)
    ti.buy(symbol, usdt / len(toBuy))