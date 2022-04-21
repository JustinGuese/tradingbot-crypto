from train import train
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path
from datetime import datetime, timedelta
from tradinghandler.trading import TradingInteractor
from os import environ
import joblib
from ta import add_all_ta_features
import yfinance as yf
import numpy as np
from tqdm import tqdm

ti = TradingInteractor(environ["BOTNAME"])
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]

symbdict = {
    "ETH-USD" : "ETHUSDT",
    "BNB-USD" : "BNBUSDT",
    "SOL-USD" : "SOLUSDT",
    "XRP-USD" : "XRPUSDT",
    "AAPL" : "AAPLUSD",
    "MSFT" : "MSFTUSD",
    "TSLA" : "TSLAUSD",
}
SYMBOLS = list(symbdict.keys())

# check when we had last training
TRAINING = False
if Path("persistent/lastTraining.txt").is_file():
    with open("persistent/lastTraining.txt", "r") as f:
        lastTraining = f.read()
    lastTraining = datetime.strptime(lastTraining, "%Y-%m-%d %H:%M:%S.%f")
    if (lastTraining - datetime.utcnow()) > timedelta(days=7):
        TRAINING = True
else:
    TRAINING = True

def getModel(symbol):
    return joblib.load("./persistent/models/" + symbol + ".pkl")

if TRAINING:
    print("have to retrain... (every 7 days)")
    for symbol in tqdm(SYMBOLS):
        try:
            train(symbol)
        except Exception as e:
            print("train problem with: ", symbol)
            print(repr(e))

# then trade
for symbol in SYMBOLS:
    try:
        model = getModel(symbol)
        data = yf.download(symbol, period = "20d", interval = "1h", progress = False)
        data = add_all_ta_features(data, open = "Open", high = "High", low = "Low", close = "Close", volume = "Volume")
        data = data.fillna(0)
        data = data.replace([np.inf, -np.inf], 0)
        decision = model.predict(data)
        decision = np.median(decision[-5:])
        print("prediction for %s is %s" % (symbol, decision))
        # should be -1 or 1
        if decision == 1 and portfolio.get(symbdict[symbol], 0) == 0:
            print("buying %s" % symbol)
            ti.buy(symbdict[symbol], usdt / 4)
        elif decision == -1 and portfolio.get(symbdict[symbol], 0) > 0:
            print("selling %s" % symbol)
            ti.sell(symbdict[symbol], -1)
    except Exception as e:
        print("predict problem with: ", symbol)
        print(repr(e))