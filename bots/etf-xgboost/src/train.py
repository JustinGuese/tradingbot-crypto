from sklearn.model_selection import train_test_split
import yfinance as yf
import pandas as pd
from scipy.signal import argrelextrema
from ta import add_all_ta_features
import numpy as np
from pathlib import Path
from xgboost import XGBClassifier

def getPreparedData(symbol, timeframe, training = False):
    if timeframe not in ["1d", "1h", "1wk"]:
        raise ValueError("Invalid timeframe. must be one of: 1d, 1h, 1wk")
    if timeframe == "1d":
        if training:
            lookback = "5y"
        else:
            lookback = "60d"
    elif timeframe == "1h":
        if training:
            lookback = "720d"
        else:
            lookback = "7d"
    elif timeframe == "1wk":
        if training:
            lookback = "5y"
        else:
            lookback = "6mo"
    # get data from yf
    data = yf.download(symbol, period = lookback, interval = timeframe, progress = False)
    if len(data) == 0:
        raise ValueError("length of dataframe is zeroo!!!")
    # set extrema
    n = 20

    data['minextrema'] = data.iloc[argrelextrema(data.Close.values, np.less_equal,
                        order=n)[0]]['Close']
    data['maxextrema'] = data.iloc[argrelextrema(data.Close.values, np.greater_equal,
                            order=n)[0]]['Close']

    # mark down signal
    last = None
    signals = []
    for i in range(len(data)):
        if data.minextrema[i] == data.Close[i]:
            last = 1
        elif data.maxextrema[i] == data.Close[i]:
            last = 0 # -1
        signals.append(last)
    data["signal"] = signals

    # add ta
    data = add_all_ta_features(data, open="Open", high="High", low="Low", close="Close", volume="Volume")
    data["signal"] = data.signal.fillna(method='ffill')
    data = data.fillna(method='ffill')
    data.replace(np.inf, 999, inplace=True)
    data.replace(-np.inf, -999, inplace=True)
    data = data.fillna(1)

    X = data.drop(["signal", "minextrema", "maxextrema"], axis = 1)
    Y = data["signal"]

    return X, Y

def trainModel(symbol, timeframe):
    X, Y = getPreparedData(symbol, timeframe, training = True)
    X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.0001, shuffle=True)
    
    # load model if exists
    my_file = Path("persistent/xgb_" + symbol + "_" + timeframe + ".pkl")
    if my_file.is_file():
        clf = XGBClassifier()
        clf.load_model("persistent/xgb_" + symbol + "_" + timeframe + ".pkl")
    else:
        clf = XGBClassifier()
    clf.fit(X_train, Y_train)
    clf.save_model("persistent/xgb_" + symbol + "_" + timeframe + ".pkl")
    return clf

def getModel(symbol, timeframe):
    my_file = Path("persistent/xgb_" + symbol + "_" + timeframe + ".pkl")
    if my_file.is_file():
        clf = XGBClassifier()
        clf.load_model("persistent/xgb_" + symbol + "_" + timeframe + ".pkl")
    else:
        print("model does not exist. train now")
        clf = trainModel(symbol, timeframe)
    return clf
