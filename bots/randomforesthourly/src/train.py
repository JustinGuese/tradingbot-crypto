import yfinance as yf
import numpy as np
from ta import add_all_ta_features
from scipy.signal import argrelextrema
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
from pathlib import Path
from datetime import datetime


def setExtrema(data):
        n = 20

        minextremai = argrelextrema(data.Close.values, np.less_equal,
                            order=n)[0]
        maxextremai = argrelextrema(data.Close.values, np.greater_equal,
                                order=n)[0]
        return minextremai, maxextremai

def train(symbol):
    data = yf.download(symbol, period = "720d", interval = "1h", progress = False)
    data = add_all_ta_features(data, open = "Open", high = "High", low = "Low", close = "Close", volume = "Volume")
    data = data.fillna(0)

    justholdWin = (10000 / data.iloc[0]["Open"]) * data.iloc[-1]["Close"]
    # print("with just holding you would have won: " + str(justholdWin))

    # label data with min max stuff

    minextremai, maxextremai = setExtrema(data)
    # which starts?
    targets = []
    crnt = 1
    for i in range(len(data)):
        if i in minextremai:
            crnt = -1
        elif i in maxextremai:
            crnt = 1
        targets.append(crnt)
    data["target"] = targets

    data = data.fillna(0)
    # replace np inf with 0
    data = data.replace([np.inf, -np.inf], 0)
    Y = data["target"].to_numpy()
    data = data.drop(["target"], axis = 1)
    # X = scaler.fit_transform(data)
    X = data.to_numpy()
    # from sklearn.tree import DecisionTreeClassifier
    # actually just faux to get the shuffle
    x_train, x_test, y_train, y_test = train_test_split(  X, Y, test_size=0.001, shuffle = True)
    highestScore = 0
    bestDepth = 0
    # for maxdepth in [ 10,9,8, 7, 5, 3]:
    #     clf = DecisionTreeClassifier(max_depth=maxdepth)
    #     clf.fit(x_train, y_train)
    #     score = clf.score(x_test, y_test)
    #     if score > highestScore:
    #         highestScore = score
    #         bestDepth = maxdepth
    #     print(score, maxdepth)
    # print(highestScore, " with depth: ", bestDepth)
    clf = RandomForestClassifier()
    clf.fit(x_train, y_train)

    # finally save model to disk
    Path("./persistent/models/").mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, "./persistent/models/" + symbol + ".pkl")

    # save last training
    with open("./persistent/lastTraining.txt", "w") as file:
        file.write(str(datetime.utcnow()))
    return clf

