
# coinsrankday
from os import environ
import pickle
# simplsmahr
# environ["BOTNAME"] = "simplsmahr"
# looks at coinsrank dailies and buys top 10 ranks
from tradinghandler.trading import TradingInteractor
import numpy as np
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from multiprocessing import Pool
from ta import add_all_ta_features
from ta.momentum import rsi
import tensorflow as tf # This code has been tested with TensorFlow 1.6
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import classification_report
from pathlib import Path


from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import LSTM
from tensorflow.keras.layers import Dropout
from tensorflow.keras.metrics import AUC,Precision,Recall
from tensorflow.keras.callbacks import ReduceLROnPlateau,EarlyStopping,ModelCheckpoint
import json


ti = TradingInteractor(environ["BOTNAME"])# )  "10.147.17.73"
portfolio = ti.getPortfolio()
usdt = portfolio["USDT"]


#  golden cross. When the 50 EMA moves above the 200 SMA,

def buySim(tmpdata, money, nrStocks, i):
    crntPrice = tmpdata.iloc[i]['close']
    amount = money / crntPrice * 0.99
    cost = amount * crntPrice * (1 + 0.00025) # binance fees
    boughtFor = cost
    boughtAtI = i
    money -= cost
    nrStocks += amount
    return boughtFor, boughtAtI, money, nrStocks

def sellSim(tmpdata, trades, money, nrStocks, i, boughtFor, boughtAtI):
    crntPrice = tmpdata.iloc[i]['close']
    win = nrStocks * crntPrice * (1 - 0.00025) # commission
    money += win
    nrStocks = 0
    heldfor = i - boughtAtI # days
    profit = win - boughtFor # profit
    if heldfor == 0:
        # print("heldfor is zero, shouldnt be i, boughtAtI" , i, boughtAtI)
        # happens if buying at the last step
        # equal to profit / 1
        trades.append(profit)
    else:
        trades.append(profit / heldfor) # profit per day helt for
    return trades, nrStocks, money

def threeDFy(data, scaler = None, traintestsplit = True): 
    if traintestsplit:   
        split = int(len(data) * 0.9999999999) # fake split
        train_data = data.iloc[:split]
        test_data = data.iloc[split:]
    else:
        train_data = data

    # scaling
    if scaler == None:
        sc = MinMaxScaler(feature_range = (0, 1))
    else:
        sc = scaler
    train_data = sc.fit_transform(train_data)
    if traintestsplit:
        test_data = sc.transform(test_data)

    # make 3d
    x_train = []
    y_train = []
    x_test = []
    y_test = []
    window = 60
    target = -1 # -1 should be ma5_win, change indicator bla bla 
    for i in range(window, len(train_data)):
        x_train.append(train_data[i-window:i, :-1]) # we dont wanna take target, bc we take info 
        y_train.append(train_data[i, target]) 
    x_train, y_train = np.array(x_train), np.array(y_train)
    # test data
    if traintestsplit:
        for i in range(window, len(test_data)):
            x_test.append(test_data[i-window:i, :-1])
            y_test.append(test_data[i, target])
    x_test, y_test = np.array(x_test), np.array(y_test)
    #final pred
    x_final = []
    if traintestsplit:
        x_final.append(test_data[-60:])
    else:
        x_final.append(train_data[-60:])
    x_final = np.array(x_final)
    # reshape?
    # X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))
    print(x_test.shape,x_train.shape,y_train.shape,y_test.shape,x_final.shape)
    xtrainshape = (x_train.shape[1], x_train.shape[2])
    # then shuffle array for increased randomness
    # traini = np.arange(x_train.shape[0])
    # np.random.shuffle(traini)
    # x_train = x_train[traini]
    # y_train = y_train[traini]
    # if traintestsplit:
    #     testi = np.arange(x_test.shape[0])
    #     np.random.shuffle(testi)
    #     x_test = x_test[testi]
    #     y_test = y_test[testi]
    # i think we need to convert to tensor
    x_train = tf.convert_to_tensor(x_train, dtype=tf.float32)
    x_test = tf.convert_to_tensor(x_test, dtype=tf.float32)
    y_train = tf.convert_to_tensor(y_train, dtype=tf.float32)
    y_test = tf.convert_to_tensor(y_test, dtype=tf.float32)
    x_final = tf.convert_to_tensor(x_final, dtype=tf.float32)
    
    return xtrainshape, x_train, x_test, y_train, y_test, x_final, sc

def createModel(xtrainshape, symbol):
    # val_loss
    redlr = ReduceLROnPlateau(monitor="loss",patience=100)
    es = EarlyStopping(monitor="loss",patience=200)
    mcp_save = ModelCheckpoint('results/mdl_stock_%s.hdf5' % symbol, save_best_only=True, monitor='val_loss', mode='min')
    classifier = Sequential()

    classifier.add(LSTM(units = 200, return_sequences = True, input_shape =xtrainshape))
    classifier.add(Dropout(0.2))

    # classifier.add(LSTM(units = 50, return_sequences = True))
    # classifier.add(Dropout(0.2))

    classifier.add(LSTM(units = 128, return_sequences = True))
    classifier.add(Dropout(0.2))

    classifier.add(LSTM(units = 200))
    classifier.add(Dropout(0.2))

    classifier.add(Dense(units = 1, activation='sigmoid'))

    classifier.compile(optimizer = 'adam', loss = 'binary_crossentropy',metrics=['accuracy']) # y_train[y_train==0.5] = 0
    return classifier, redlr,es,mcp_save

def applyTA(data):
    # data = add_all_ta_features(data, open="open", high= "high", low = "low", close = "price", volume = "volume")
    #we have to define a binary target
    # make moving average
    # data['SMA3price'] = data["price"].rolling(window=3).mean()
    data['pricepct'] = data['price'].pct_change()
    data['pricesign'] = np.sign(data['price'].pct_change())
    # data["target"] = data["pricepct"].shift(-1) # i think we cant do shift, bc that would take the info from the next day
    data = data.fillna(method = "bfill")
    data["target"] = data["pricesign"].replace(0, None) # so we can exchange it with clostest next one
    # 3dfy it
    data = data.drop(["symbol", "time"], axis = 1)
    data = data.fillna(method = "ffill")
    data.replace(np.inf, 999, inplace=True)
    data.replace(-np.inf, -999, inplace=True)
    return data

def oneSimulation(data, predictions, predlookback):
    startMoney = 10000
    money = startMoney
    stocks = 0
    # rsidata = rsi(data["price"], 14) # 3 should equal close?
    for i in range(predlookback, len(predictions)):
        crntPrice = data.iloc[i]["price"]
        predicts = predictions[i-predlookback:i]
        # rsinow = rsidata[i]
        prediction = np.median(predicts)
        if prediction == 1:
            # simulate buy
            if money > 10 and stocks == 0:
                amount = money / crntPrice * .95
                cost = amount * crntPrice * 1.00025 # commission
                money -= cost
                stocks = amount
        elif prediction == 0:
            # simulate sell
            if stocks > 0:
                cost = stocks * crntPrice * (1 - 0.00025) # commission
                money += cost
                stocks = 0
    # if done sell if we still have stock
    if stocks > 0:
        cost = stocks * crntPrice * (1 - 0.00025) # commission
        money += cost
        stocks = 0
    return money - startMoney

def optimizeLookback(data, predictions):
    bestWin = -999999999999999999999999
    bestLookback = -1
    for lookback in [1,5,10,50,100, 300, 500]:
        win = oneSimulation(data, predictions, lookback)
        if win > bestWin:
            bestWin = win
            bestLookback = lookback
    timeMonths = len(data) / 24 / 30
    return bestWin, bestLookback, timeMonths


def doOneTraining(symbol, epochs = 20):
    # like training
    # get data
    # 24 hours in a day, so to get 200 we need to get the last 200 days
    # 6 months are 24 * 180 = 4320
    # data = ti.getData(symbol, lookback=4300) # not a whole year
    data = ti.getBinanceRecentTrades(symbol, lookbackdays=-1)
    # switch order bc we want newest at bottom
    data = data.iloc[::-1]
    # apply all the ta we have
    data = applyTA(data)
    # tmp save to disk
    data.to_csv("traindata_%s.csv" % symbol)

    # check if we have a scaler
    scalerfilename = "results/scaler_stock_%s.pkl" % symbol
    if Path(scalerfilename).is_file():
        scaler = pickle.load(open(scalerfilename, "rb"))
    else:
        scaler = None
    xtrainshape, x_train, x_test, y_train, y_test, x_final, scaler = threeDFy(data, scaler = scaler, traintestsplit= True)
    # create model
    print("creating model now...")
    modelfilename = "results/mdl_stock_%s.hdf5" % symbol
    if Path(modelfilename).is_file():
        model = tf.keras.models.load_model("./results/mdl_stock_%s.hdf5" % symbol)
    else:
        print("no model fou! creating new")
        model, redlr,es,mcp_save = createModel(xtrainshape, symbol)


    # train it
    print("training model now...")
    # validation_data=(x_test,y_test)
    model.fit(x_train,y_train,epochs=epochs, validation_data=(x_test,y_test), batch_size=256 )

    # check results
    # classification report
    pred_train = (model.predict(x_train) > .5) * 1
    # pred_train = model.predict(x_train)
    # print(type(pred_train))
    # format is actually [ [0],[0]]
    # print("predtrain: ", pred_train)
    # pred_train = [x[0] for x in pred_train]
    print("predictions what it should be: ", np.unique(y_train, return_counts=True))
    print("predictions: ", np.unique(pred_train, return_counts=True))
    cr = classification_report(y_train, pred_train, target_names=["sell", "buy"])
    print("TRAIN CR" ,cr)

    model.save("results/mdl_stock_%s.hdf5" % symbol)
    pickle.dump(scaler, open("results/scaler_stock_%s.pkl" % symbol, "wb"))

    # finally find best lookback period
    bestWin, bestLookback, timeMonths = optimizeLookback(data, pred_train)
    # tryna calculate win pct per year
    mult = timeMonths / 12
    winPctYear = (10000 + bestWin / mult) / 10000 * 100
    return bestWin, bestLookback, timeMonths, winPctYear

def doTraining(SYMBOLS, epochs = 20):
    currentBest = []
    bestLookbacks = dict()
    for symbol in tqdm(SYMBOLS):
        # get training best combination if not exists
        try:
            bestWin, bestLookback, timeMonths, winPctYear = doOneTraining(symbol, epochs = epochs)
            print("best simulated win for %s is %.2f$ or %.1f pct/year in %.2f months with lookback %d" % (symbol, bestWin, winPctYear, timeMonths, bestLookback))
            bestLookbacks[symbol] = bestLookback
        except Exception as e:
            print(e)
            raise
    # and save last update
    with open("results/lastUpdate.txt", "w") as f:
        f.write(str(datetime.now()))
    with open("results/bestLookbacks.json", "w") as f:
        json.dump(bestLookbacks, f, indent = 4)

if __name__ == "__main__":
    environ["SYMBOLS"] = "AVAXUSDT" #,BNBUSDT,ETHUSDT,XRPUSDT" # debug
    SYMBOLS = environ["SYMBOLS"].split(",")
    doTraining(SYMBOLS, epochs = 1)