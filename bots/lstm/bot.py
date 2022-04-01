from datetime import datetime
from training import doTraining, ti, applyTA
from os import environ
from ta.momentum import rsi
import pickle
import numpy as np
import json
from tqdm import tqdm
from pathlib import Path
from subprocess import call


# 
environ["SYMBOLS"] = "AVAXUSDT,BNBUSDT,ETHUSDT,XRPUSDT" # debug
SYMBOLS = environ["SYMBOLS"].split(",")

# check if we have to retrain
if not Path("./results/lastUpdate.txt").is_file():
    print("!! first startup, need to copy all from resultsfirst directory into results")
    call("rsync -r ./resultsfirst/ ./results/", shell=True)

with open("./results/lastUpdate.txt", "r") as f:
    # check if retraining required
    lastTrainingDate = datetime.strptime(f.read(), "%Y-%m-%d %H:%M:%S.%f")
    if lastTrainingDate.month != datetime.now().month:
        doTraining(SYMBOLS)

with open("./results/bestLookbacks.json", "r") as f:
    BESTLOOKBACKS = json.load(f)

def loadModelsForSymbols(symbols):
    storage = dict()
    for symbol in symbols:
        tmp = dict()
        tmp["model"] = tf.keras.models.load_model("./results/mdl_stock_%s.hdf5" % symbol)
        tmp["scaler"] = pickle.load(open("./results/scaler_stock_%s.pkl" % symbol, "rb"))
        storage[symbol] = tmp
    return storage

def scale(data, scaler):
    return scaler.transform(data)

def get3dxtrain(data):
    
    # make 3d
    x_train = []
    y_train = []
    window = 60
    target = -1 # -1 should be ma5_win, change indicator bla bla 
    for i in range(window, len(data)):
        x_train.append(data[i-window:i])
        y_train.append(data[i, target]) 
    x_train, y_train = np.array(x_train), np.array(y_train)
    
    # the final x is missing here but lets just ignore it
    x_train = tf.convert_to_tensor(x_train, dtype=tf.float32)
    return x_train


if __name__ == "__main__":
    portfolio = ti.getPortfolio()
    usdt = portfolio["USDT"]

    # load models
    MODELS = None

    sell = []
    buy = []

    for symbol in tqdm(SYMBOLS):
        # get newest data
        data = ti.getData(symbol, lookback=30) # not a whole year
        rsidata = rsi(data["close"], 14)
        if rsidata[-1] <= 30 or rsidata[-1] >= 70: # only conditions on when we have to act
            if MODELS is None:
                # just load them now
                import tensorflow as tf
                MODELS = loadModelsForSymbols(SYMBOLS)
            data = applyTA(data)
            datascaled = scale(data, MODELS[symbol]["scaler"])
            x_train = get3dxtrain(datascaled)

            # let the model predict
            pred = MODELS[symbol]["model"].predict(x_train)
            pred = (pred > .5) * 1
            # now lookback in action
            lookback = BESTLOOKBACKS[symbol]
            pred = pred[-lookback:]
            pred = np.median(pred)
            # 0 = sell, 1 = buy
            print("prediction for %s: %s" % (symbol, str(pred)))

            if pred == 0:
                if portfolio.get(symbol, 0) > 0:
                    sell.append(symbol)
            elif pred == 1:
                if portfolio.get(symbol, 0) == 0:
                    buy.append(symbol)

        # execute the orders
        # first sell
        if len(sell) > 0:
            for symbol in sell:
                ti.sell(symbol, -1)
            portfolio = ti.getPortfolio()
            print(portfolio)
            usdt = portfolio["USDT"]
        # then buy
        if len(buy) > 0:
            for symbol in buy:
                ti.buy(symbol, usdt / len(buy) * 0.95)