
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
import tensorflow as tf # This code has been tested with TensorFlow 1.6
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import classification_report

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import LSTM
from tensorflow.keras.layers import Dropout
from tensorflow.keras.metrics import AUC,Precision,Recall
from tensorflow.keras.callbacks import ReduceLROnPlateau,EarlyStopping,ModelCheckpoint


ti = TradingInteractor(environ["BOTNAME"], url = "10.147.17.73")# )
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

def oneSimulation(comb_tuple):
    data, smallSMA, bigSMA = comb_tuple
    tmpdata = data.copy()
    tmpdata['smaSmall'] = tmpdata["close"].rolling(smallSMA).mean()
    tmpdata['smaBig'] = tmpdata["close"].rolling(bigSMA).mean()
    nrStocks = 0
    startingMoney = 10000 # 10 k starting
    money = startingMoney #  10k starting
    boughtFor = 0
    boughtAtI = 0
    trades = []
    for i in range(len(data)):
        SMASmall, SMABig, rsi = tmpdata.iloc[i]['smaSmall'], tmpdata.iloc[i]['smaBig'], tmpdata.iloc[i]['rsi']
        if SMASmall > SMABig and nrStocks == 0 and rsi <= 30:
            # buy
            boughtFor, boughtAtI, money, nrStocks = buySim(tmpdata, money, nrStocks, i)

        elif SMASmall < SMABig and nrStocks > 0 and rsi >= 70:
            # sell
            trades, nrStocks, money = sellSim(tmpdata, trades, money, nrStocks, i, boughtFor, boughtAtI)
    # on last day sell if we have stocks
    if nrStocks > 0:
        trades, nrStocks, money = sellSim(tmpdata, trades, money, nrStocks, i, boughtFor, boughtAtI)
    
    totalWin = (money - startingMoney) / len(data) # to average it to the timestep
    # avg/median Trade per timestep (hour)
    if len(trades) > 0:
        avgTrade = np.mean(trades)
        medTrade = np.median(trades)
    else:
        avgTrade = 0
        medTrade = 0

    # we are working with hour data on crypto, so i wanna take it * 24 * 30 to get monthly averages
    totalWin *= 24 * 30
    pctWinPerMonth = totalWin / startingMoney * 100
    pctWinPerYear = pctWinPerMonth * 12 # 12 months
    avgTrade *= 24 * 30
    medTrade *= 24 * 30 
    nrTrades = len(trades)
    return smallSMA, bigSMA, round(totalWin, 2), round(pctWinPerMonth, 2), round(pctWinPerYear, 2), round(avgTrade, 2), round(medTrade, 2), nrTrades

def threeDFy(data, traintestsplit = True): 
    if traintestsplit:   
        split = int(len(data) * 0.9)
        train_data = data.iloc[:split]
        test_data = data.iloc[split:]
    else:
        train_data = data

    # scaling
    sc = MinMaxScaler(feature_range = (0, 1))
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
        x_train.append(train_data[i-window:i])
        y_train.append(train_data[i, target]) 
    x_train, y_train = np.array(x_train), np.array(y_train)
    # test data
    if traintestsplit:
        for i in range(window, len(test_data)):
            x_test.append(test_data[i-window:i])
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
    traini = np.arange(x_train.shape[0])
    np.random.shuffle(traini)
    x_train = x_train[traini]
    y_train = y_train[traini]
    if traintestsplit:
        testi = np.arange(x_test.shape[0])
        np.random.shuffle(testi)
        x_test = x_test[testi]
        y_test = y_test[testi]
    # i think we need to convert to tensor
    x_train = tf.convert_to_tensor(x_train, dtype=tf.float32)
    x_test = tf.convert_to_tensor(x_test, dtype=tf.float32)
    y_train = tf.convert_to_tensor(y_train, dtype=tf.float32)
    y_test = tf.convert_to_tensor(y_test, dtype=tf.float32)
    x_final = tf.convert_to_tensor(x_final, dtype=tf.float32)
    
    return xtrainshape, x_train, x_test, y_train, y_test, x_final, sc

def createModel(xtrainshape):
    # val_loss
    redlr = ReduceLROnPlateau(monitor="loss",patience=100)
    es = EarlyStopping(monitor="loss",patience=200)
    mcp_save = ModelCheckpoint('results/mdl_stock.hdf5', save_best_only=True, monitor='val_loss', mode='min')
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

def getBestCombination(symbol):
    # like training
    # get data
    # 24 hours in a day, so to get 200 we need to get the last 200 days
    # 6 months are 24 * 180 = 4320
    data = ti.getData(symbol, lookback=4300) # not a whole year
    # apply all the ta we have
    data = add_all_ta_features(data, open="open", high= "high", low = "low", close = "close", volume = "volume")
    #we have to define a binary target
    # make moving average
    data['MA3'] = data["close"].rolling(window=3).mean()
    data['MA3_win'] = np.sign(data['MA3'].pct_change())
    data["target"] = data["MA3_win"].shift(-1)
    data["target"] = data["target"].replace(0, 1) # no hodl just buy
    # 3dfy it
    data = data.drop(["symbol"], axis = 1)
    data = data.fillna(method = "bfill")
    data.replace(np.inf, 999, inplace=True)
    data.replace(-np.inf, -999, inplace=True)
    # tmp save to disk
    # data.to_csv("traindata.csv")

    xtrainshape, x_train, x_test, y_train, y_test, x_final, scaler = threeDFy(data, traintestsplit= True)
    # create model
    print("creating model now...")
    model, redlr,es,mcp_save = createModel(xtrainshape)

    # train it
    print("training model now...")
    # validation_data=(x_test,y_test)
    model.fit(x_train,y_train,epochs=1, validation_data=(x_test,y_test), batch_size=256,callbacks=[redlr,es,mcp_save] )

    # check results
    # classification report
    pred_train = (model.predict(x_train) > .5) * 1
    # pred_train = model.predict(x_train)
    # print(type(pred_train))
    # format is actually [ [0],[0]]
    # print("predtrain: ", pred_train)
    # pred_train = [x[0] for x in pred_train]
    print("predictions: ", np.unique(pred_train, return_counts=True))
    cr = classification_report(y_train, pred_train, target_names=["sell","buy"])
    print("TRAIN CR" ,cr)

    model.save("results/mdl_stock_%s.hdf5" % symbol)
    pickle.dump(scaler, open("results/scaler_stock_%s.pkl" % symbol, "wb"))

def doTraining(SYMBOLS):
    currentBest = []
    for symbol in tqdm(SYMBOLS):
        # get training best combination if not exists
        getBestCombination(symbol)
    # and save last update
    with open("results/lastUpdate.txt", "w") as f:
        f.write(str(datetime.now()))

if __name__ == "__main__":
    environ["SYMBOLS"] = "AVAXUSDT" # ,BNBUSDT,ETHUSDT,XRPUSDT" # debug
    SYMBOLS = environ["SYMBOLS"].split(",")
    doTraining(SYMBOLS)