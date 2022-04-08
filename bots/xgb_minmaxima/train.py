from os import environ
import yfinance as yf
from ta import add_all_ta_features
import numpy as np
from scipy.signal import argrelextrema


def preprocess(symbol, lookback = "60d", interval = "30m"):
    data = yf.download(symbol, period=lookback, interval = interval)
    data.columns = [x.lower() for x in data.columns]
    data = add_all_ta_features(data, "open", "high", "low", "close", "volume")
    # replace np.inf with np.nan
    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.fillna(0)

    n = 20

    data["pctchange"] = data["close"].pct_change()
    data["pricedirection"] = np.sign(data["pctchange"])
    data['minextrema'] = data.iloc[argrelextrema(data.close.values, np.less_equal,
                    order=n)[0]]['close']
    data['maxextrema'] = data.iloc[argrelextrema(data.close.values, np.greater_equal,
                        order=n)[0]]['close']

    # now we label the target accordingly
    direction = None
    data["target"] = None
    tmp = []
    for i in range(len(data)):
        if data.iloc[i]['minextrema'] == data.iloc[i]['close']:
            # now up
            direction = 1
        elif data.iloc[i]['maxextrema'] == data.iloc[i]['close']:
            # now down
            direction = -1
        
        tmp.append(direction)
    data["target"] = tmp
    # fill the first points
    data = data.fillna(method="bfill")

    Y = data["target"]
    X = data.drop(["target", "minextrema", "maxextrema"], axis=1)
    return X, Y

def doTraining(symbol, lookback = "60d", interval = "30m"):
    X, Y = preprocess(symbol, lookback = lookback, interval = interval)
    from xgboost import XGBClassifier
    clf = XGBClassifier()
    clf.fit(X, Y)
    clf.save_model("persistent/%s_model.json" % symbol)

def loadModel(symbol):
    from xgboost import XGBClassifier
    clf = XGBClassifier()
    clf.load_model("persistent/%s_model.json" % symbol)
    return clf

if __name__ == "__main__":
    symbols = "AAPL,ETH-USD".split(",")
    for symbol in symbols:
        doTraining(symbol)
        # clf = loadModel(symbol)
