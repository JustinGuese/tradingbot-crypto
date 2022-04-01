from datetime import datetime
from training import doTraining, ti
from os import environ
from pathlib import Path
from ta.momentum import rsi
import pandas as pd
from training import threeDFy, createModel, applyTA
import tensorflow as tf
import pickle
import numpy as np

# 
environ["SYMBOLS"] = "AVAXUSDT,BNBUSDT,ETHUSDT, XRPUSDT" # debug
SYMBOLS = environ["SYMBOLS"].split(",")

# check if we have to retrain
with open("./results/lastUpdate.txt", "r") as f:
    # check if retraining required
    lastTrainingDate = datetime.strptime(f.read(), "%Y-%m-%d %H:%M:%S.%f")
    if lastTrainingDate.month != datetime.now().month:
        doTraining(SYMBOLS)

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

def getXFinal(data):
    x_final = []
    x_final.append(data[-60:])
    x_final = tf.convert_to_tensor(x_final, dtype=tf.float32)
    return x_final


if __name__ == "__main__":
    portfolio = ti.getPortfolio()
    usdt = portfolio["USDT"]

    # load models
    MODELS = loadModelsForSymbols(SYMBOLS)

    sell = []
    buy = []

    for symbol in SYMBOLS:
        # get newest data
        data = ti.getData(symbol, lookback=30) # not a whole year
        data = applyTA(data)
        data = scale(data, MODELS[symbol]["scaler"])
        x_final = getXFinal(data)

        # let the model predict
        pred = MODELS[symbol]["model"].predict(x_final)
        pred = (pred > .5) * 1
        pred = pred[0][0]
        # 0 = sell, 1 = buy
        print("prediction for %s: %s" % (symbol, str(pred)))
        if pred == 0:
            sell.append(symbol)
        elif pred == 1:
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